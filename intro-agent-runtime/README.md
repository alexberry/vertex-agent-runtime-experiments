# Agent Runtime Intro (LangChain)

Jumping off point is the [Google Agent Runtime intro Jupyter notebook](./intro_agent_engine.ipynb) ([original](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/agent-engine/intro_agent_engine.ipynb)). Uses [LangChain](https://docs.langchain.com/oss/python/langchain/overview) to build and deploy a currency exchange agent to Agent Runtime.

## Prerequisites

* GCP project with Vertex AI enabled (`system-alexb-art-ed9d`)
* Staging bucket in the same region (`gs://alexb-art-staging-bucket`, `europe-west2`)

## Setup

```bash
pyenv virtualenv 3.14 agent-runtime
pyenv activate agent-runtime
pip install -r requirements.txt
```

## Usage

Export required environment variables:

```bash
export GOOGLE_CLOUD_PROJECT=system-alexb-art-ed9d
export GOOGLE_CLOUD_LOCATION=europe-west2
export STAGING_BUCKET=gs://alexb-art-staging-bucket
```

> **Note:** `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` are required by `create.py` — they are baked into the LangChain agent at pickle time and determine where the model is called from at runtime. Unlike the ADK experiment, they cannot be inferred from ADC.

Then run the scripts:

```bash
./create.py   # Package and deploy agent to Agent Runtime
./test.py     # Query the deployed agent
./delete.py   # Tear down the agent
```

## What it creates

* Artifacts in the staging bucket (pkl, requirements, tarball)
* A managed container build (similar to Cloud Functions)
* An Agent Runtime instance queryable via Python SDK or curl

## Feature parity with ADK

The [ADK experiment](../agent-runtime-adk) gets sessions, memory, tracing, and a playground UI for free — they are built into the ADK framework and Agent Runtime supports them natively. Reaching the same capabilities here requires significant additional work:

* **Sessions** — `LangchainAgent.query()` is stateless. Adding session history requires switching to LangGraph (also supported by Agent Runtime) or managing conversation state in an external store (e.g. Firestore) and injecting it on every call.
* **Memory** — ADK's `MemoryService` persists facts across sessions automatically. LangChain memory modules have no equivalent integration with Agent Runtime's session store; external storage must be wired up manually.
* **Tracing** — ADK emits OpenTelemetry spans to Cloud Trace automatically; no configuration required. LangChain's native tracing runs through LangSmith (separate SaaS). Adding Cloud Trace to LangChain requires writing and wiring up a custom OTel exporter.
* **Playground** — `adk web` and the Agent Runtime console playground are ADK-specific. The LangChain equivalent is LangSmith's playground, a different ecosystem entirely.

If these features matter, migrating to ADK (as in `agent-runtime-adk`) is lower effort than adding them here.

## Questions

* [What is an agent gateway? How could a public web service host it securely?](../agent-gateway-armor/README.md#questions-answered)
* [What is Agent Armor?](../agent-gateway-armor/README.md#questions-answered)
* How to run evals?
