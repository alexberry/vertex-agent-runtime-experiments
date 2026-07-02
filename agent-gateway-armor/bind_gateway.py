#!/usr/bin/env python3
"""Binds the already-deployed agent-runtime-adk currency-exchange agent to
the Client-to-Agent gateway created by terraform/. Run once after `terraform
apply`. Gateway governance then applies server-side -- callers keep using the
same query()/stream_query() calls, they just get screened by Model Armor now.
"""
import os
import pathlib

import vertexai
from google.adk.agents import Agent
from vertexai import agent_engines

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
REGION = os.environ["GOOGLE_CLOUD_LOCATION"]
GATEWAY_NAME = "currency-agent-gateway"


# `agent_engines.update()` bundles `agent_gateway_config` into the same
# deployment-spec update path as env_vars/instance counts/etc, and its SDK
# refuses to touch any of those unless `agent` (or a source-code option) is
# also supplied -- even though the code itself isn't changing. So the agent
# definition has to be reconstructed here, byte-for-byte matching
# ../agent-runtime-adk/create.py. Keep the two in sync if that file changes.
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

gateway_resource_name = f"projects/{PROJECT}/locations/{REGION}/agentGateways/{GATEWAY_NAME}"

client.agent_engines.update(
    name=AGENT_ENGINE_RESOURCE_NAME,
    agent=app,
    config={
        # Required whenever `agent` is supplied: update() repackages the
        # agent through the same path as create() (staging_bucket, pickle,
        # requirements upload) even though the code itself is unchanged --
        # same bucket agent-runtime-adk/create.py used.
        "staging_bucket": os.environ["STAGING_BUCKET"],
        "requirements": ["google-cloud-aiplatform[agent_engines,adk]"],
        "identity_type": "AGENT_IDENTITY",
        "agent_gateway_config": {"client_to_agent_config": {"agent_gateway": gateway_resource_name}},
    },
)
print(f"Bound {AGENT_ENGINE_RESOURCE_NAME} to gateway {gateway_resource_name}")
