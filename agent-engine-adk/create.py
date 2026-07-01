#!/usr/bin/env python3
PROJECT_ID = "system-alexb-art-ed9d"  # @param {type:"string"}
LOCATION = "europe-west2"  # @param {type:"string"}
STAGING_BUCKET = "gs://alexb-art-staging-bucket"  # @param {type:"string"}

import vertexai

client = vertexai.Client(
    project=PROJECT_ID,               # Your project ID.
    location=LOCATION,                # Your cloud region.
)

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
    )
    return response.json()

from google.adk.agents import Agent
from vertexai import agent_engines

agent = Agent(
    model="gemini-3.5-flash",
    name='currency_exchange_agent',
    tools=[get_exchange_rate],
)

app = agent_engines.AdkApp(agent=agent)

from vertexai import types

import pathlib

remote_agent = client.agent_engines.create(
    agent=app,
    config={
        "requirements": ["google-cloud-aiplatform[agent_engines,adk]"],
        "staging_bucket": STAGING_BUCKET,
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "display_name": "Currency Converter - ADK"
    }

)

config_path = pathlib.Path(__file__).parent / "agent_engine.txt"
config_path.write_text(remote_agent.api_resource.name)
print(f"Resource name written to {config_path}")