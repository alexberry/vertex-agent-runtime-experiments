#!/usr/bin/env python3
PROJECT_ID = "system-alexb-art-ed9d"  # @param {type:"string"}
LOCATION = "europe-west2"  # @param {type:"string"}
STAGING_BUCKET = "gs://alexb-art-staging-bucket"  # @param {type:"string"}

import vertexai

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

from vertexai import agent_engines
from vertexai.preview.reasoning_engines import LangchainAgent

model = "gemini-3.5-flash"

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

agent = LangchainAgent(
    model=model,
    tools=[get_exchange_rate],
    agent_executor_kwargs={"return_intermediate_steps": True},
)

agent = LangchainAgent(
    model=model,
    tools=[get_exchange_rate],
)

import pathlib

remote_agent = agent_engines.create(
    agent,
    requirements=[
        "google-cloud-aiplatform[agent_engines,langchain]",
        "cloudpickle>=3.1.0",
        "pydantic>=2.10",
        "requests",
    ],
    display_name="Currency Converter"
)

config_path = pathlib.Path(__file__).parent / "agent_engine.txt"
config_path.write_text(remote_agent.resource_name)
print(f"Resource name written to {config_path}")