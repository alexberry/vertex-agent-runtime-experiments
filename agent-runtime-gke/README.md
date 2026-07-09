# agent-runtime-gke

Self-hosting ADK's agent runtime on GKE Autopilot. Answers two open questions from the root README: whether GKE cold-start is faster than managed Agent Runtime, and how the Kubernetes Gateway API in the GKE blog post relates to (or doesn't) the Agent Gateway product.

## What it creates

| Resource | Type | Cost note |
|---|---|---|
| `agent-runtime-gke` | GKE Autopilot cluster | Billed per pod resource + cluster management fee |
| `agent-runtime-gke` | Artifact Registry repo | Minimal (storage only) |
| `agent-runtime-gke-memory-context` | Vertex AI Agent Engine | Billed per session/memory API call |
| `currency-agent-gateway` | Kubernetes L7 external load balancer + static IP | Continuously billed |
| `fx-rates-svc` | ClusterIP Service (no external IP) | No extra cost |

**Teardown:** `terraform destroy` in `terraform/`, then delete the Agent Engine context resource manually (or add it to a cleanup script).

## Gateway API vs. Agent Gateway

These are two completely different products that happen to share "gateway" in their names.

| | Kubernetes Gateway API | Google Cloud Agent Gateway |
|---|---|---|
| **What** | GKE's L7 load-balancer construct | Cross-agent governance product |
| **API group** | `gateway.networking.k8s.io` | `networkservices.googleapis.com` (Agent Gateway resource) |
| **Objects** | `Gateway`, `HTTPRoute`, `GatewayClass` | `AgentGateway`, `AuthzPolicy`, `AuthzExtension` |
| **Purpose** | Route external HTTP traffic into the cluster | Enforce Model Armor screening on agent-to-agent traffic |
| **This experiment** | Used in `k8s/gateway.yaml` + `httproute.yaml` | Spike attempted — see Agent Gateway Spike below |

The blog post this experiment is based on uses the Kubernetes Gateway API. It makes no mention of the Agent Gateway product.

## Prerequisites

- `gcloud` CLI authenticated (`gcloud auth login`, `gcloud auth application-default login`)
- `gke-gcloud-auth-plugin` installed (`gcloud components install gke-gcloud-auth-plugin`)
- Docker running locally
- Terraform >= 1.5.0
- `kubectl`
- Python 3.12+ with `pyenv` (`pyenv virtualenv 3.14 agent-runtime-gke`)

```bash
pyenv activate agent-runtime-gke
pip install -r requirements.txt
```

## Setup

### 1. Provision cluster + registry (Terraform)

```bash
cd terraform/
terraform init
terraform validate
terraform plan    # review before applying -- real, continuously-billed infra
terraform apply
cd ..
```

This creates the Autopilot cluster, Artifact Registry repo, a `currency-agent` Google Service Account with `roles/aiplatform.user`, and the Workload Identity binding that allows the default KSA to impersonate it. Takes ~5 minutes for Autopilot to finish provisioning.

Configure `kubectl`:
```bash
gcloud container clusters get-credentials agent-runtime-gke --region europe-west2 --project system-alexb-art-ed9d
```

Annotate the default Kubernetes Service Account with the GSA email output by Terraform. This is what activates the Workload Identity exchange — without it pods fall back to the node SA and Vertex AI calls return 403:

```bash
GSA=$(terraform -chdir=terraform output -raw agent_gsa_email)
kubectl annotate serviceaccount default \
  --namespace default \
  iam.gke.io/gcp-service-account="$GSA"
```

### 2. Provision memory (Agent Engine context)

```bash
GOOGLE_CLOUD_PROJECT=system-alexb-art-ed9d \
GOOGLE_CLOUD_LOCATION=europe-west2 \
python provision_memory.py
```

This writes the resource name to `agent_engine_context.txt`. Copy it into `k8s/configmap.yaml`:

```bash
RESOURCE_NAME=$(cat agent_engine_context.txt)
# Edit k8s/configmap.yaml -- replace the placeholder with $RESOURCE_NAME
```

### 3. Build and test containers locally

Both Dockerfiles target `linux/amd64` (GKE node architecture). On an Apple Silicon Mac, Docker runs the amd64 image via Rosetta/QEMU emulation — functional but slower than a native build. Use `memory://` service URIs for local testing so no GCP credentials are needed for sessions.

**Agent:**
```bash
cd agent/
docker build -t currency-agent:local .
docker run --rm -p 8080:8080 \
  -e SESSION_SERVICE_URI=memory:// \
  -e MEMORY_SERVICE_URI=memory:// \
  -e GOOGLE_CLOUD_PROJECT=system-alexb-art-ed9d \
  -e GOOGLE_CLOUD_LOCATION=europe-west2 \
  -v ~/.config/gcloud:/root/.config/gcloud:ro \
  currency-agent:local
# In another terminal:
curl http://localhost:8080/list-apps
cd ..
```

**fx-rates-service:**
```bash
cd fx-rates-service/
docker build -t fx-rates-service:local .
docker run --rm -p 8081:8080 fx-rates-service:local
curl http://localhost:8081/rate?pair=USD/EUR
cd ..
```

### 4. Push images to Artifact Registry

The `--platform linux/amd64` flag is already baked into both Dockerfiles, so a plain `docker build` on Apple Silicon produces the correct x86 image for GKE.

```bash
REGISTRY=europe-west2-docker.pkg.dev/system-alexb-art-ed9d/agent-runtime-gke
gcloud auth configure-docker europe-west2-docker.pkg.dev

docker build -t $REGISTRY/currency-agent:latest agent/
docker push $REGISTRY/currency-agent:latest

docker build -t $REGISTRY/fx-rates-service:latest fx-rates-service/
docker push $REGISTRY/fx-rates-service:latest
```

### 5. Deploy to cluster

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/fx-rates-service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/gateway.yaml
kubectl apply -f k8s/httproute.yaml
```

Check rollout:
```bash
kubectl get pods
kubectl get gateway currency-agent-gateway
# Wait for the gateway to show an external IP (takes 1-2 minutes)
```

## Usage

```bash
GATEWAY_IP=$(kubectl get gateway currency-agent-gateway -o jsonpath='{.status.addresses[0].value}')
python test_via_gke.py --gateway-ip $GATEWAY_IP
```

## Memory

The agent uses Vertex AI Sessions (persists conversation state within a session) and Memory Bank (surfaces relevant facts across sessions via `preload_memory`).

**Demo transcript:**

```
# Session 1 -- tell the agent a fact
curl -X POST http://$GATEWAY_IP/apps/app/users/demo-user/sessions/s1
curl -X POST http://$GATEWAY_IP/run \
  -H 'Content-Type: application/json' \
  -d '{"app_name":"app","user_id":"demo-user","session_id":"s1",
       "new_message":{"role":"user","parts":[{"text":"My name is Alex and I prefer EUR as my base currency."}]}}'

# Session 2 (new session) -- confirm memory recall
curl -X POST http://$GATEWAY_IP/apps/app/users/demo-user/sessions/s2
curl -X POST http://$GATEWAY_IP/run \
  -H 'Content-Type: application/json' \
  -d '{"app_name":"app","user_id":"demo-user","session_id":"s2",
       "new_message":{"role":"user","parts":[{"text":"What is my preferred base currency?"}]}}'
# Expected: agent recalls EUR without being told again in this session
```

## Agent Gateway Spike

**Outcome: registration succeeds, governance does not.**

### What we tried

1. Called the Agent Registry `services` API directly to register the GKE external IP as a Service entry:

   ```python
   POST https://agentregistry.googleapis.com/v1/projects/{project}/locations/{region}/services?serviceId=currency-agent-gke
   {
     "displayName": "Currency Agent - GKE",
     "agentSpec": { "type": "NO_SPEC" },
     "interfaces": [{ "url": "http://34.160.136.215", "protocolBinding": "HTTP_JSON" }]
   }
   ```

   This **succeeds** and returns an LRO that creates an Agent Registry entry (`registryResource: projects/.../agents/agentregistry-...`).

2. Checked whether the existing `currency-agent-gateway` (already deployed by `agent-gateway-armor`) picks up the new entry — it does, because it references the entire `europe-west2` registry.

### Why governance still doesn't work

The Agent Gateway governs traffic by enforcing that calls to a Reasoning Engine **must** go through the gateway (`agent_gateway_config` set server-side on the Reasoning Engine). The call path is:

```
client.agent_engines.get(name=…).stream_query(…)   ← Vertex AI SDK
  → Agent Gateway (Model Armor screening)
    → Reasoning Engine
```

For a GKE agent, there is no equivalent enforcement point:
- The `agent_gateway_config` binding is a Vertex AI Reasoning Engine concept — it has no counterpart in the Agent Registry `services` API or in GKE
- The external IP (`http://34.160.136.215`) remains publicly reachable regardless of whether a gateway entry exists
- The Agent Registry is a **discovery** service, not an invocation proxy; the gateway cannot rewrite arbitrary HTTP traffic to/from a GKE pod

### Workaround: in-process Model Armor

Model Armor screening is wired directly in `agent.py` via a `before_model_callback`. This gives prompt-injection/jailbreak screening without the gateway enforcement layer (the GKE endpoint remains reachable directly, so it's not governance in the Agent Gateway sense, but it does screen every request that flows through the ADK agent):

```python
# In agent.py — screens every prompt before it reaches the model.
# Does not prevent callers from bypassing via direct HTTP to the pod's
# /run endpoint, unlike Agent Gateway governance on Agent Runtime.
def model_armor_callback(callback_context, llm_request):
    ...
```

See `agent/agent.py` for the full implementation.

## Questions answered

### Is GKE cold-start lower latency than managed Agent Runtime?

*To be measured.* Managed Agent Runtime (`agent-runtime-adk`) cold-starts in approximately X seconds (measure via `test.py` on a fresh session). This GKE Autopilot deployment cold-starts in approximately Y seconds. Key difference: Autopilot scales to zero between requests (pod start included in cold path), while Agent Runtime keeps a warm replica.

*Update with actual measured values after running both experiments back-to-back.*

### How does the Kubernetes Gateway API relate to Agent Gateway?

They are unrelated products at different layers. The Kubernetes Gateway API handles L7 HTTP routing into the cluster. Agent Gateway enforces Model Armor screening on agent invocations. The blog post uses only the Kubernetes Gateway API. See the [Gateway API vs. Agent Gateway](#gateway-api-vs-agent-gateway) table above.

## Teardown

```bash
# Delete k8s resources
kubectl delete -f k8s/

# Destroy cluster and registry (data in registry will be deleted too)
cd terraform/
terraform destroy
cd ..

# Delete Agent Engine context resource
RESOURCE_NAME=$(cat agent_engine_context.txt)
gcloud ai reasoning-engines delete $RESOURCE_NAME --region=europe-west2
```
