#!/usr/bin/env python3
import os
import pathlib
import vertexai
from google.adk.agents import Agent
from vertexai import agent_engines, types

client = vertexai.Client()


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

remote_agent = client.agent_engines.create(
    agent=app,
    config={
        "requirements": ["google-cloud-aiplatform[agent_engines,adk]"],
        "staging_bucket": os.environ["STAGING_BUCKET"],
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "display_name": "Currency Converter - ADK",
    },
)

config_path = pathlib.Path(__file__).parent / "agent_engine.txt"
config_path.write_text(remote_agent.api_resource.name)
print(f"Resource name written to {config_path}")
