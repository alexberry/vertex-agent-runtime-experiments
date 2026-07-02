# Agent Engine + ADK

Based on [GCP's ADK Quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/quickstart-adk). Implements the same currency exchange service as [intro-agent-engine](../intro-agent-engine/) using ADK instead of LangChain.

## Prerequisites

* GCP project with Vertex AI enabled (`system-alexb-art-ed9d`)
* Staging bucket in the same region (`gs://alexb-art-staging-bucket-adk`, `europe-west2`)

## Setup

```bash
pyenv virtualenv 3.14 agent-engine-adk
pyenv activate agent-engine-adk
pip install -r requirements.txt
```

## Usage

Export required environment variables:

```bash
export GOOGLE_CLOUD_PROJECT=system-alexb-art-ed9d
export GOOGLE_CLOUD_LOCATION=europe-west2
export STAGING_BUCKET=gs://alexb-art-staging-bucket-adk
```

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

## ADK extras

The ADK integration automatically instruments:

* Traces
* Sessions
* A playground UI (interactive equivalent of `test.py`)

These are accessible via the [Agent Platform console](https://console.cloud.google.com/agent-platform/runtimes?project=system-alexb-art-ed9d).
