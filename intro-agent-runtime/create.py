#!/usr/bin/env python3
import os
import pathlib
import vertexai
from vertexai.preview.reasoning_engines import LangchainAgent

# vertexai.init sets the default location baked into the LangchainAgent at pickle time
vertexai.init(
    project=os.environ["GOOGLE_CLOUD_PROJECT"],
    location=os.environ["GOOGLE_CLOUD_LOCATION"],
)
client = vertexai.Client()

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
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


agent = LangchainAgent(
    model=model,
    tools=[get_exchange_rate],
    agent_executor_kwargs={"return_intermediate_steps": True},
)

remote_agent = client.agent_engines.create(
    agent=agent,
    config={
        "requirements": [
            "google-cloud-aiplatform[agent_engines,langchain]",
            "cloudpickle>=3.1.0",
            "pydantic>=2.10",
            "requests",
        ],
        "staging_bucket": os.environ["STAGING_BUCKET"],
        "display_name": "Currency Converter",
    },
)

config_path = pathlib.Path(__file__).parent / "agent_engine.txt"
config_path.write_text(remote_agent.api_resource.name)
print(f"Resource name written to {config_path}")
