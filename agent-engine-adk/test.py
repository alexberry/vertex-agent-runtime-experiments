#!/usr/bin/env python3
import pathlib
from vertexai import agent_engines

PROJECT_ID = "system-alexb-art-ed9d"  # @param {type:"string"}
LOCATION = "europe-west2"  # @param {type:"string"}

import vertexai

vertexai.init(project=PROJECT_ID, location=LOCATION)

config_path = pathlib.Path(__file__).parent / "agent_engine.txt"
AGENT_ENGINE_RESOURCE_NAME = config_path.read_text().strip()

prompt = "What's the exchange rate from UK Pounds to Swedish currency today? Terse response."
print(f"Prompt: {prompt}")

remote_agent = agent_engines.get(AGENT_ENGINE_RESOURCE_NAME)

session = remote_agent.create_session(user_id="test-user")
for event in remote_agent.stream_query(
    message=prompt,
    user_id="test-user",
    session_id=session["id"],
):
    for part in event.get("content", {}).get("parts", []):
        if "text" in part:
            print(part["text"])
