# Agent Engine Intro (LangChain)

Jumping off point is the [Google Agent Engine intro Jupyter notebook](./intro_agent_engine.ipynb) ([original](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/agent-engine/intro_agent_engine.ipynb)). Uses [LangChain](https://docs.langchain.com/oss/python/langchain/overview) to build and deploy a currency exchange agent to Agent Engine.

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
./create.py   # Package and deploy agent to Agent Engine
./test.py     # Query the deployed agent
./delete.py   # Tear down the agent
```

## What it creates

* Artifacts in the staging bucket (pkl, requirements, tarball)
* A managed container build (similar to Cloud Functions)
* An Agent Engine instance queryable via Python SDK or curl

## Feature parity with ADK

The [ADK experiment](../agent-engine-adk) gets sessions, memory, tracing, and a playground UI for free — they are built into the ADK framework and Agent Engine supports them natively. Reaching the same capabilities here requires significant additional work:

* **Sessions** — `LangchainAgent.query()` is stateless. Adding session history requires switching to LangGraph (also supported by Agent Engine) or managing conversation state in an external store (e.g. Firestore) and injecting it on every call.
* **Memory** — ADK's `MemoryService` persists facts across sessions automatically. LangChain memory modules have no equivalent integration with Agent Engine's session store; external storage must be wired up manually.
* **Tracing** — ADK instruments with Cloud Trace out of the box. LangChain tracing runs through LangSmith (separate SaaS). Adding Cloud Trace requires manual OpenTelemetry instrumentation.
* **Playground** — `adk web` and the Agent Engine console playground are ADK-specific. The LangChain equivalent is LangSmith's playground, a different ecosystem entirely.

If these features matter, migrating to ADK (as in `agent-engine-adk`) is lower effort than adding them here.

## Questions

* What is an agent gateway?
* How could a public web service host it securely?
* What is Agent Armor?
* How to run evals?
