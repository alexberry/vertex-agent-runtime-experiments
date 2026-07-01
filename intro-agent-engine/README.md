# Agent Engine Intro Jupyter Notebook

Jumping off point is the [google agent engine intro jupyter notebook](./intro_agent_engine.ipynb) ([original](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/agent-engine/intro_agent_engine.ipynb)). This demo uses the [langchain](https://docs.langchain.com/oss/python/langchain/overview) Library to build an engine and deploy it to agent engine.

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

## Questions

* What is an agent gateway
* How could a public web service host it securely
* what is agentarmor
* how to enable sessions
* how to persist with memories
* how to run evals