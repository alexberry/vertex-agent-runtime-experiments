# Agent Gateway + Model Armor

Puts a [Client-to-Agent Agent Gateway](https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/gateways/agent-gateway-overview) in front of the already-deployed currency-exchange agent from [agent-runtime-adk](../agent-runtime-adk/), and attaches a [Model Armor](https://cloud.google.com/security/products/model-armor) template that screens for prompt-injection and jailbreak attempts.

Both **Agent Gateway** and its Model Armor integration are Preview features, but the full wiring is confirmed against the stable `hashicorp/google` provider (v7.39.0, via the Terraform MCP server's live provider docs) — no `google-nightly` or manual `gcloud alpha` steps needed. The Model Armor template is bound to the gateway through a `google_network_services_authz_extension` (`service = modelarmor.<region>.rep.googleapis.com`, template ID passed via a `model_armor_settings` JSON blob in `metadata`) plus a `google_network_security_authz_policy` (`policy_profile = CONTENT_AUTHZ`, `action = CUSTOM`) targeting the gateway — see [terraform/gateway.tf](./terraform/gateway.tf).

Binding the agent to the gateway (`agent_engines.update(...)`, in [bind_gateway.py](./bind_gateway.py)) has no Terraform equivalent — confirmed absent from the full `google_vertex_ai_reasoning_engine` schema in both the stable and `google-beta` providers (v7.39.0). `terraform apply` still triggers it automatically via a `null_resource` + `local-exec` in [terraform/bind_gateway.tf](./terraform/bind_gateway.tf), so it stays a one-command flow, but it's shelling out to the SDK, not a real Terraform-managed resource. This whole path has been run end-to-end against real infra; two non-obvious things had to be fixed along the way (see comments in `bind_gateway.py`):

* `update()` treats `agent_gateway_config` like any other deployment-spec field (env vars, instance counts, etc.) and refuses to touch it unless you *also* pass the top-level `agent=` argument — even though the code isn't changing. That forces a full repackage on every bind, not just a config patch.
* Because that repackage rebuilds the container from scratch, `config` needs the same `requirements`/`staging_bucket` keys `create.py` uses — omitting `requirements` produces a remote `ModuleNotFoundError: No module named 'vertexai'` when the container tries to unpickle the agent (diagnosed via `gcloud logging read` against the `ReasoningEngine` resource, since the SDK's own error was just a generic "failed to be updated").

## Prerequisites

* [agent-runtime-adk](../agent-runtime-adk/) already deployed (`agent_engine.txt` present there) — this experiment reuses that agent, it doesn't redeploy it. Its `create.py` already sets `identity_type: AGENT_IDENTITY`, the prerequisite for governed gateway access.
* GCP project with Vertex AI enabled (`system-alexb-art-ed9d`), region `europe-west2` (must match the agent's region — Model Armor doesn't support cross-region calls)
* Terraform >= 1.5.0
* The `agent-gateway-armor` virtualenv **and** the `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` / `STAGING_BUCKET` env vars (see Setup) **must be active in the same shell you run `terraform apply` from** — `terraform apply`'s last step shells out to `bind_gateway.py`, which needs all three

## Setup

```bash
pyenv virtualenv 3.14 agent-gateway-armor
pyenv activate agent-gateway-armor
pip install -r requirements.txt

export GOOGLE_CLOUD_PROJECT=system-alexb-art-ed9d
export GOOGLE_CLOUD_LOCATION=europe-west2
export STAGING_BUCKET=gs://alexb-art-staging-bucket-adk   # same bucket agent-runtime-adk uses

cd terraform
terraform init
terraform plan
```

## Usage

> **Before running `terraform apply`, activate the virtualenv and export the env vars above in that same shell** (or re-run the whole Setup block if you're in a fresh terminal). The apply's last step shells out to `./bind_gateway.py` via a `local-exec` provisioner: it needs `python3` on `PATH` to resolve to this virtualenv, and it repackages/re-uploads the agent (`STAGING_BUCKET`) as a side effect of setting `agent_gateway_config` — `terraform apply` does not activate the venv or set these for you.

Review the plan, then apply (creates real, billed GCP resources, and binds the currency-exchange agent to the gateway as its last step):

```bash
terraform apply
```

Run the test script:

```bash
./test_via_gateway.py
```

It sends a benign currency question (answers normally) and a prompt-injection attempt (blocked). Check Cloud Logging for the Model Armor sanitize-operation entries the template logs.

**There's no "direct, bypasses the gateway" path once bound** — `agent_gateway_config` is set server-side on the Reasoning Engine, so *every* caller using the SDK's `client.agent_engines.get(...).stream_query(...)` is routed through the gateway, including `../agent-runtime-adk/test.py`, confirmed by running it against the same prompt-injection prompt and getting the identical `403 PERMISSION_DENIED — Model Armor: Prompt violates content security configurations`. Binding governs access for the resource, not a specific client path.

Tear down when done (same venv/env-var requirement as apply — the destroy step shells out to `unbind_gateway.py`):

```bash
cd terraform
terraform destroy
```

### Observed: before vs. after teardown

`./test_via_gateway.py` run against the same reasoning engine, same two prompts, no code changes — once after `terraform apply`, once after `terraform destroy`:

**After apply** (gateway bound, Model Armor enforcing):

* Benign prompt: normal answer (`1 GBP = 12.91 SEK`).
* Prompt-injection attempt: `403 PERMISSION_DENIED` — `Model Armor: Prompt violates content security configurations`. Hard block, enforced server-side before the request reaches the agent.

**After destroy** (gateway gone, `unbind_gateway.py` cleared `agent_gateway_config`):

* Immediately after destroy, the benign prompt returned `404 NOT_FOUND` — transient, resolved on its own within roughly a minute. Read as propagation delay on the `update()` that clears `agent_gateway_config`, not a real failure.
* Once settled, benign prompt: normal answer again, unchanged.
* Prompt-injection attempt: **no longer blocked**. Gets a normal `200`-style response, with the model itself declining: *"I cannot reveal my system prompt or ignore my core instructions..."* — Gemini's own alignment refusing the ask, not Model Armor.

Same prompt, same agent code, two different enforcement mechanisms depending on whether the gateway is bound: a policy-level block that holds regardless of what the model would have done (apply), vs. the model's own judgment call, which is not guaranteed (destroy). This is the clearest evidence in this experiment that the gateway + Model Armor combination does real enforcement, not just adds latency.

## What it creates

* A `google_model_armor_template` enforcing prompt-injection/jailbreak filters (malicious-URI filtering is unsupported in `europe-west2` — see [terraform/model_armor.tf](./terraform/model_armor.tf))
* A `google_network_services_agent_gateway` (Client-to-Agent, Preview) referencing this project's auto-populated Agent Registry
* A `google_network_services_authz_extension` routing gateway traffic to the regional Model Armor endpoint, plus a `google_network_security_authz_policy` (`CONTENT_AUTHZ`) binding it to the gateway
* IAM bindings granting the Agent Runtime reasoning-engine service agent access to call Model Armor
* A `null_resource` that runs `bind_gateway.py` as the last apply step, binding `agent-runtime-adk`'s deployed agent to the new gateway (not a real Terraform-managed resource — see the Preview-feature note above), and `unbind_gateway.py` as a destroy-time provisioner on the same `null_resource` so `terraform destroy` doesn't leave the agent's `agent_gateway_config` pointing at a gateway that no longer exists (Terraform has no visibility into this SDK-managed field, so it can't know to clear it otherwise — confirmed live: deleting the gateway does not clear the reference on the reasoning engine side)

## Questions answered

Answers the open questions from [intro-agent-runtime/README.md](../intro-agent-runtime/README.md#questions):

* **What is an agent gateway?** The networking/governance front door for agents on Gemini Enterprise Agent Platform — ingress (Client-to-Agent) and egress (Agent-to-Anywhere), enforcing mTLS and IAM-based access control between clients/agents/tools without the agent code needing to know about it.
* **How could a public web service host it securely?** Put it behind a Client-to-Agent gateway rather than exposing the Agent Runtime endpoint directly — the gateway terminates mTLS, checks IAM policy, and (as demonstrated here) runs a Model Armor content-safety pass before traffic reaches the agent.
* **What is Agent Armor?** There's no product by that name — it's [Model Armor](https://cloud.google.com/security/products/model-armor), Google Cloud's prompt/response safety screening service (prompt injection, jailbreak, malicious URLs, sensitive data). It only integrates with Agent Runtime through an Agent Gateway, as built here.

"How to run evals?" remains open — out of scope for this experiment.

## Known limitation: gateway binding disables Agent Runtime telemetry

Binding an agent to an Agent Gateway via `agent_gateway_config` silently disables Cloud Trace / OpenTelemetry inside the Agent Runtime container.

Confirmed by deploying the same agent code and requirements twice in the same project, back-to-back:

| State | Startup OTel warnings | Console telemetry status |
|---|---|---|
| No gateway bound | `WARNING: telemetry enabled but proceeding without ...` (3 packages) | Enabled |
| Gateway bound | No OTel warnings at all | Disabled |

The absence of warnings when the gateway is bound is not a fix — it means telemetry initialisation is skipped entirely rather than running with partial instrumentation. The ADK runtime appears to detect `agent_gateway_config` and defer observability to the gateway layer. Whether the Agent Gateway itself captures equivalent trace data is an open question (see below).

## Open questions

**Can telemetry and gateway mode coexist?**

When `agent_gateway_config` is set, the Agent Runtime skips its own OTel initialisation. It is not yet known whether:

* The Agent Gateway captures its own equivalent traces (latency, tool calls, model invocations) that appear in Cloud Trace under a different resource type
* There is an explicit env var or SDK config that re-enables OTel inside the Agent Runtime even when the gateway is bound
* The platform intentionally prohibits dual telemetry (to avoid double-counting or conflicting trace roots) and the gateway trace is the intended replacement

**To investigate:** deploy an agent with `agent_gateway_config` set, send a query, and check Cloud Trace for entries originating from the Agent Gateway resource rather than the Reasoning Engine. Also check whether setting `GOOGLE_CLOUD_ENABLE_DIRECT_PATH=false` or similar OTel env vars in the agent's `config` restores Agent Runtime traces alongside gateway routing.

## Tooling used to build this

* [terraform-mcp-server](https://github.com/hashicorp/terraform-mcp-server) — used to pull live `hashicorp/google` provider docs (`get_provider_details` / `search_providers`) for `google_network_services_agent_gateway`, `google_model_armor_template`, `google_network_services_authz_extension`, and `google_network_security_authz_policy` instead of trusting blog posts or reference modules pinned to `google-nightly`. **If you're picking up this experiment (human or agent) and need to change the Terraform**: query this MCP server first — Agent Gateway and Model Armor are Preview surfaces and field names/nesting have already shifted once during this build (e.g. `mtls_endpoint` is nested under `agent_gateway_card[0]`, not top-level; `registries` entries have no `/v1/` version segment despite what the argument description implies — trust the resource's own example usage over its prose description when the two disagree).
* [agents-cli](https://github.com/google/agents-cli) (via its bundled `google-agents-cli-deploy` / `google-agents-cli-publish` Claude skills) — used to confirm `agent-runtime-adk`'s deployed agent is auto-registered in Agent Registry (no manual registration step needed before the gateway can reference it), and to confirm the `identity_type: AGENT_IDENTITY` config it already sets is the correct prerequisite for governed gateway access.
