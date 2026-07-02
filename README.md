# Agent Runtime sandbox

* [Agent Runtime Intro (LangChain)](./intro-agent-runtime/README.md)
* [Agent Development Kit Python Quickstart](./intro-adk/README.md)
* [Agent Runtime + ADK Example](./agent-runtime-adk/README.md)

## Further Reading

* [Example that expands upon this pattern, extending to memories and more expansive tool definitions](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/create-an-adk-agent)
* [Example running on gke](https://cloud.google.com/blog/topics/developers-practitioners/scaling-ai-agents-a-step-by-step-guide-to-deploying-adk-on-gke-autopilot)
  * seemingly creates agent runtime interfaces via the agent runtime api, but backs the function/tool runtime on gke
    * is this lower latency startup?
    * how does this work with agent gateway, given the example uses gateway api?
* [Agent Skills on Github][https://github.com/google/agents-cli#agent-skills]