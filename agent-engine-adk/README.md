# Agent Engine + ADK

Based on [GCP's ADK Quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/quickstart-adk) and aligning with the langchain implementation in [intro-agent-engine](../intro-agent-engine/), this implements a currency exchange service using the ADK instead of langchain.

This appears to automatically implement:
* [Traces](https://console.cloud.google.com/agent-platform/runtimes/locations/europe-west2/agent-engines/9005519200973750272/traces?project=system-alexb-art-ed9d&pageState=(%22timeRange%22:(%22duration%22:%22PT1H%22),%22tracesView%22:(%22t%22:%220%22,%22f%22:%22%22)))
* [Sessions](https://console.cloud.google.com/agent-platform/runtimes/locations/europe-west2/agent-engines/9005519200973750272/sessions?project=system-alexb-art-ed9d)
* [Playground](https://console.cloud.google.com/agent-platform/runtimes/locations/europe-west2/agent-engines/9005519200973750272/playground?project=system-alexb-art-ed9d) - Interactive test interface, implements test.py

It requires:

* A project with vertex enabled
* A bucket built in same location as the agent

It creates:

* Artifacts  in the staging bucket for build purposes
* Managed build from these files (a la cloud function) in to container
* Ships container to agent engine
* Agent engine instance, queryable by python library or curl

## Test scripts

Basic set of scripts derived from intro jupyter notebook, can be run end-to-end:

```bash
./create.py && ./test.py && ./delete.py
```