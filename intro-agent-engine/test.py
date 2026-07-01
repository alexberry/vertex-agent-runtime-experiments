#!/usr/bin/env python3
import pathlib
from vertexai import agent_engines

PROJECT_ID = "system-alexb-art-ed9d"  # @param {type:"string"}
LOCATION = "europe-west2"  # @param {type:"string"}

import vertexai

vertexai.init(project=PROJECT_ID, location=LOCATION)

config_path = pathlib.Path(__file__).parent / "agent_engine.txt"
AGENT_ENGINE_RESOURCE_NAME = config_path.read_text().strip()

prompt="What's the exchange rate from UK Pounds to Swedish currency today? Terse response."
print(f"Prompt: {prompt}")

remote_agent = agent_engines.get(AGENT_ENGINE_RESOURCE_NAME)
response = remote_agent.query(input=prompt)
print(response["output"][0]["text"])