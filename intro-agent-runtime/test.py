#!/usr/bin/env python3
import pathlib
import vertexai

client = vertexai.Client()

config_path = pathlib.Path(__file__).parent / "agent_engine.txt"
AGENT_ENGINE_RESOURCE_NAME = config_path.read_text().strip()

prompt = (
    "What's the exchange rate from UK Pounds to Swedish currency today? Terse response."
)
print(f"Prompt: {prompt}")

remote_agent = client.agent_engines.get(name=AGENT_ENGINE_RESOURCE_NAME)
response = remote_agent.query(input=prompt)
print(response["output"][0]["text"])
