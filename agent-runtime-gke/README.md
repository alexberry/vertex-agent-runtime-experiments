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
| `currency-agent-gke` | Model Armor template | Minimal (per-call screening) |

**Teardown:** `terraform destroy` in `terraform/`, then delete the Agent Engine context resource manually (or add it to a cleanup script).

## Gateway API vs. Agent Gateway

These are two completely different products that happen to share "gateway" in their names.

| | Kubernetes Gateway API | Google Cloud Agent Gateway |
|---|---|---|
| **What** | GKE's L7 load-balancer construct | Cross-agent governance product |
| **API group** | `gateway.networking.k8s.io` | `networkservices.googleapis.com` (Agent Gateway resource) |
| **Objects** | `Gateway`, `HTTPRoute`, `GatewayClass` | `AgentGateway`, `AuthzPolicy`, `AuthzExtension` |
| **Purpose** | Route external HTTP traffic into the cluster | Enforce Model Armor screening on agent-to-agent traffic |
| **Enforcement point** | GKE control plane (L7 routing rules) | Vertex AI platform (server-side flag on Reasoning Engine) |
| **This experiment** | Used in `k8s/gateway.yaml` + `httproute.yaml` | Spike attempted — see Agent Gateway Spike below |

The blog post this experiment is based on uses the Kubernetes Gateway API. It makes no mention of the Agent Gateway product.

### How Agent Gateway enforcement actually works

Agent Gateway is **not an HTTP proxy** that sits in front of an endpoint. Enforcement is anchored to the Vertex AI platform via a flag (`agent_gateway_config`) set server-side on a Reasoning Engine resource. When that flag is present, Vertex AI refuses to invoke the engine without routing through the gateway first:

```
client.agent_engines.get(name=…).stream_query(…)   ← Vertex AI SDK
  → Vertex AI detects agent_gateway_config on the Reasoning Engine
    → routes call through Agent Gateway (Model Armor screening)
      → Reasoning Engine executes
```

A GKE pod has no equivalent enforcement point:
- It is not a Reasoning Engine — there is no `agent_gateway_config` to set
- The Agent Registry `services` entry (used to register a GKE endpoint) is discovery-only; Agent Gateway reads the registry to find agents, but cannot intercept HTTP calls to them
- The pod's external IP remains directly reachable regardless of what the registry says

This is why governance is tied to the hosting layer, not to the network path:

| Host | Agent Gateway governance? | Model Armor screening achievable? | How |
|---|---|---|---|
| Vertex AI Agent Engine (managed) | Yes | Yes | `agent_gateway_config` on Reasoning Engine; Vertex AI enforces it server-side |
| GKE pod | No | Yes (via `GCPTrafficExtension`) | Attach to the Kubernetes Gateway; LB screens every request before forwarding to pod |

If governance on a GKE-hosted agent is required, the options are:

| Approach | Where screening happens | Bypassable? | Caveat |
|---|---|---|---|
| `GCPTrafficExtension` on the Kubernetes Gateway | Load balancer, before traffic reaches the pod | No — only if Service is ClusterIP (which it is here) | Model Armor only parses OpenAI-format bodies; ADK's `/run` schema is not screened (see [limitation note](#limitation-model-armor-only-parses-openai-format-request-bodies-at-the-lb-layer)) |
| In-process `before_model_callback` | Inside the ADK process | Yes — a caller that hits the pod directly (e.g. via port-forward or if Service has an external IP) skips it | None |
| Istio/ASM sidecar | Service mesh layer | No, but requires mesh setup | None |

This experiment uses `GCPTrafficExtension` — see [Attach Model Armor to the Gateway](#6-attach-model-armor-to-the-gateway) below.

**Limitation: Model Armor only parses OpenAI-format request bodies at the LB layer.**
Google's `GCPTrafficExtension` + Model Armor integration is designed for OpenAI-compatible endpoints (`/v1/chat/completions`). It extracts user text from `messages[].content`. ADK's `/run` endpoint uses a different schema (`new_message.parts[].text`) that Model Armor does not recognise. In testing, prompt-injection payloads sent to `/run` are not blocked at the LB layer — the extension is fully programmed and traffic is screened, but Model Armor finds no user text to evaluate and passes the request through. The model's own trained safety guardrails still refuse such prompts, but that enforcement is in-process, not at the network layer.

To achieve effective LB-layer screening with ADK, options are: (a) expose an OpenAI-compatible endpoint alongside `/run` and route that through the extension; (b) call the Model Armor REST API directly from agent code (`sanitizeUserPrompt` / `sanitizeModelResponse`) before/after each turn; (c) add a WasmPlugin to the gateway that rewrites the ADK body to OpenAI format before the callout.

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

On Apple Silicon, pass `--platform linux/amd64 --provenance=false` to match GKE's node architecture. Docker runs the amd64 image via Rosetta/QEMU emulation — functional but slower than native. Use `memory://` service URIs for local testing so no GCP credentials are needed for sessions.

**Agent:**
```bash
cd agent/
docker build --platform linux/amd64 --provenance=false -t currency-agent:local .
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
docker build --platform linux/amd64 --provenance=false -t fx-rates-service:local .
docker run --rm -p 8081:8080 fx-rates-service:local
curl http://localhost:8081/rate?pair=USD/EUR
cd ..
```

### 4. Push images to Artifact Registry

On Apple Silicon, pass `--platform linux/amd64` to target GKE's x86 nodes and `--provenance=false` to produce a single-arch manifest. Without `--provenance=false`, Docker Desktop creates a manifest list with an attestation entry that GKE's kubelet rejects with "no match for platform in manifest".

```bash
REGISTRY=europe-west2-docker.pkg.dev/system-alexb-art-ed9d/agent-runtime-gke
gcloud auth configure-docker europe-west2-docker.pkg.dev

docker build --platform linux/amd64 --provenance=false -t $REGISTRY/currency-agent:latest agent/
docker push $REGISTRY/currency-agent:latest

docker build --platform linux/amd64 --provenance=false -t $REGISTRY/fx-rates-service:latest fx-rates-service/
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

### 6. Attach Model Armor to the Gateway

The Model Armor template is created by Terraform in step 1. Get its resource path and apply the `GCPTrafficExtension`:

```bash
TEMPLATE=$(terraform -chdir=terraform output -raw model_armor_template_resource)
sed "s|TEMPLATE_RESOURCE_PLACEHOLDER|$TEMPLATE|" k8s/model-armor-extension.yaml \
  | kubectl apply -f -
```

The extension attaches to `currency-agent-gateway` and intercepts all requests to `/run` and `/run_sse` before they reach the pod. Because the `currency-agent` Service is `ClusterIP`, this Gateway is the only public path in — there is no bypass route.

If the IAM bindings for the LB service agent fail on first `terraform apply` (the `gcp-sa-dep` service account is created lazily when the extension is first provisioned), apply the extension first then run `terraform apply` again:

```bash
# If lb_model_armor_* resources errored on first apply:
sed "s|TEMPLATE_RESOURCE_PLACEHOLDER|$TEMPLATE|" k8s/model-armor-extension.yaml \
  | kubectl apply -f -
terraform -chdir=terraform apply   # picks up the now-existing service account
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

See [How Agent Gateway enforcement actually works](#how-agent-gateway-enforcement-actually-works) above for the full explanation. Short version: Agent Gateway is not an HTTP proxy. It enforces by setting `agent_gateway_config` on a Vertex AI Reasoning Engine — a concept that has no GKE equivalent. The Agent Registry entry we created is read-only discovery metadata; it gives the gateway visibility of the endpoint but no ability to intercept calls to it. The pod's external IP remains directly reachable whether or not the registry entry exists.

### Workaround: Model Armor via GCPTrafficExtension

Rather than Agent Gateway, Model Armor screening is attached to the existing Kubernetes Gateway via a `GCPTrafficExtension` resource. This gives hard enforcement at the load balancer layer — every request to `/run` is screened before it reaches the pod. Because the `currency-agent` Service is `ClusterIP`, the Gateway is the only public ingress path, so there is no bypass route.

See [Attach Model Armor to the Gateway](#6-attach-model-armor-to-the-gateway) for setup and `k8s/model-armor-extension.yaml` for the full resource definition.

## Questions answered

### Is GKE cold-start lower latency than managed Agent Runtime?

*To be measured.* Managed Agent Runtime (`agent-runtime-adk`) cold-starts in approximately X seconds (measure via `test.py` on a fresh session). This GKE Autopilot deployment cold-starts in approximately Y seconds. Key difference: Autopilot scales to zero between requests (pod start included in cold path), while Agent Runtime keeps a warm replica.

*Update with actual measured values after running both experiments back-to-back.*

### How does the Kubernetes Gateway API relate to Agent Gateway?

They are unrelated products at different layers. The Kubernetes Gateway API handles L7 HTTP routing into the cluster. Agent Gateway enforces Model Armor screening on agent invocations via a server-side flag on Vertex AI Reasoning Engines — a concept that has no GKE equivalent.

However, the two are complementary: `GCPTrafficExtension` lets you attach Model Armor directly to a Kubernetes Gateway, giving GKE-hosted agents the same prompt-screening capability as Agent Gateway provides for managed agents, at the load balancer layer. This experiment uses that approach. See [Attach Model Armor to the Gateway](#6-attach-model-armor-to-the-gateway) and `k8s/model-armor-extension.yaml`.

## Teardown

```bash
# Delete k8s resources (including the Model Armor extension)
kubectl delete -f k8s/

# Destroy cluster and registry (data in registry will be deleted too)
cd terraform/
terraform destroy
cd ..

# Delete Agent Engine context resource
RESOURCE_NAME=$(cat agent_engine_context.txt)
gcloud ai reasoning-engines delete $RESOURCE_NAME --region=europe-west2
```
