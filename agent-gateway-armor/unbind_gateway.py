#!/usr/bin/env python3
"""Unbinds the agent-runtime-adk currency-exchange agent from the Client-to-
Agent gateway. Run before `terraform destroy` deletes the gateway -- wired in
as a destroy-time provisioner on null_resource.bind_gateway in
terraform/bind_gateway.tf, since destroying that null_resource alone does
nothing (no destroy behavior for a resource that only ever ran a create-time
local-exec). Without this, the reasoning engine is left with
agent_gateway_config still pointing at a gateway that no longer exists.
"""
import os
import pathlib

import vertexai
from google.adk.agents import Agent
from vertexai import agent_engines

# Same agent definition as bind_gateway.py / ../agent-runtime-adk/create.py --
# update() requires it even when only clearing agent_gateway_config.
def get_exchange_rate(
    currency_from: str = "USD",
    currency_to: str = "EUR",
    currency_date: str = "latest",
):
    """Retrieves the exchange rate between two currencies on a specified date."""
    import requests

    response = requests.get(
        f"https://api.frankfurter.app/{currency_date}",
        params={"from": currency_from, "to": currency_to},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

agent = Agent(
    model="gemini-3.5-flash",
    name="currency_exchange_agent",
    tools=[get_exchange_rate],
)
app = agent_engines.AdkApp(agent=agent)

client = vertexai.Client()

agent_engine_path = pathlib.Path(__file__).parent.parent / "agent-runtime-adk" / "agent_engine.txt"
AGENT_ENGINE_RESOURCE_NAME = agent_engine_path.read_text().strip()

client.agent_engines.update(
    name=AGENT_ENGINE_RESOURCE_NAME,
    agent=app,
    config={
        "staging_bucket": os.environ["STAGING_BUCKET"],
        "requirements": ["google-cloud-aiplatform[agent_engines,adk]"],
        "identity_type": "AGENT_IDENTITY",
        # `{}` is silently ignored by the SDK (falsy-checked before it builds
        # the deployment_spec/update_mask entry) -- has to be a non-empty dict
        # with the nested config explicitly set to None to actually clear it.
        "agent_gateway_config": {"client_to_agent_config": None},
    },
)
print(f"Unbound {AGENT_ENGINE_RESOURCE_NAME} from its gateway")
