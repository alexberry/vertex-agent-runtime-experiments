# Agent Runtime sandbox

Hands-on experiments with Vertex AI Agent Runtime, ADK, Agent Gateway, and GKE self-hosting. Each experiment builds on the one before it.

## Experiments

### 1. [Agent Runtime Intro (LangChain)](./intro-agent-runtime/README.md)

**Goal:** Follow Google's official Agent Runtime intro notebook — build and deploy a currency-exchange agent using LangChain as a baseline for what the managed platform provides.

**Outcome:** Agent deploys and is queryable. However, the LangChain path lacks sessions, memory, Cloud Trace, and a playground UI without significant extra work. Surfaced a capability gap relative to the ADK approach, motivating the next experiment. Three questions left open: agent gateways, Model Armor, and evals.

---

### 2. [ADK Python Quickstart](./intro-adk/README.md)

**Goal:** Run a local ADK agent (no GCP deployment) and investigate three questions: how ADK interacts with Agent Engine, whether Agent Engine is required for the playground, and whether ADK instruments with OpenTelemetry.

**Outcome:** Local agent runs with CLI and Web UI. The three questions are answered implicitly by the subsequent `agent-runtime-adk` experiment — this README establishes the baseline without resolving them directly.

---

### 3. [Agent Runtime + ADK](./agent-runtime-adk/README.md)

**Goal:** Replicate the LangChain currency-exchange agent using ADK deployed to Agent Runtime, to confirm whether ADK's extra capabilities materialise on the managed platform.

**Outcome:** Achieved. On Agent Runtime, ADK automatically provides Cloud Trace / OpenTelemetry (zero config), managed session state, and an interactive playground UI. None of these required explicit setup.

---

### 4. [Agent Gateway + Model Armor](./agent-gateway-armor/README.md)

**Goal:** Put a Client-to-Agent Agent Gateway in front of the ADK agent and attach a Model Armor template to screen prompt-injection and jailbreak attempts. Answer three open questions from the LangChain experiment: what is an agent gateway, how to host it securely, and what is "Agent Armor".

**Outcome:** Achieved. All three questions resolved: Agent Gateway is the networking/governance front door; secure public hosting goes through Client-to-Agent gateway rather than exposing Agent Runtime directly; "Agent Armor" is a naming confusion — the product is Model Armor. Confirmed with live evidence: prompt-injection attempt returns `403 PERMISSION_DENIED` when gateway is bound; only a soft model refusal after teardown. Evals remain out of scope.

---

### 5. [ADK on GKE Autopilot](./agent-runtime-gke/README.md)

**Goal:** Self-host the ADK runtime on GKE Autopilot with Vertex AI Sessions + Memory Bank. Answer two questions: is GKE cold-start lower latency than managed Agent Runtime, and how does the Kubernetes Gateway API (from the GKE blog post) relate to the Agent Gateway product?

**Outcome:** Partially achieved.

| Question | Status |
|---|---|
| Kubernetes Gateway API vs. Agent Gateway | Answered — entirely unrelated products at different layers; see [the README](./agent-runtime-gke/README.md#gateway-api-vs-agent-gateway) |
| Can Agent Gateway govern a GKE-hosted agent? | Answered (no) — enforcement anchors to a Vertex AI Reasoning Engine resource, which has no GKE equivalent; in-process `before_model_callback` implemented as workaround |
| GKE cold-start vs. managed Agent Runtime latency | Not measured — infrastructure is live but comparison values were never collected |

## Further Reading

* [Example that expands upon this pattern, extending to memories and more expansive tool definitions](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/create-an-adk-agent)
* [Example running on gke](https://cloud.google.com/blog/topics/developers-practitioners/scaling-ai-agents-a-step-by-step-guide-to-deploying-adk-on-gke-autopilot) — see [agent-runtime-gke/README.md](./agent-runtime-gke/README.md) for hands-on answers to both open questions
* [Agent Skills on Github](https://github.com/google/agents-cli#agent-skills)