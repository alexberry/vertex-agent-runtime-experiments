#!/usr/bin/env python3
import pathlib
import vertexai

client = vertexai.Client()

config_path = pathlib.Path(__file__).parent / "agent_engine.txt"
AGENT_ENGINE_RESOURCE_NAME = config_path.read_text().strip()

remote_agent = client.agent_engines.get(name=AGENT_ENGINE_RESOURCE_NAME)
remote_agent.delete(force=True)
