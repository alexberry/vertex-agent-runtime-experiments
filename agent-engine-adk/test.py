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

session = remote_agent.create_session(user_id="test-user")
try:
    for event in remote_agent.stream_query(
        message=prompt,
        user_id="test-user",
        session_id=session["id"],
    ):
        for part in event.get("content", {}).get("parts", []):
            if "text" in part:
                print(part["text"])
finally:
    remote_agent.delete_session(user_id="test-user", session_id=session["id"])
