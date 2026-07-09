import requests
from google.adk.agents import Agent
from google.adk.tools import preload_memory


def get_exchange_rate(
    currency_from: str = "USD",
    currency_to: str = "EUR",
    currency_date: str = "latest",
):
    """Retrieves the exchange rate between two currencies on a specified date."""
    response = requests.get(
        f"https://api.frankfurter.app/{currency_date}",
        params={"from": currency_from, "to": currency_to},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_internal_rate(currency_pair: str = "USD/EUR"):
    """Retrieves a cached exchange rate from the cluster-internal fx-rates service.

    Only callable from within the cluster -- the fx-rates-svc Service has no
    external IP. Demonstrates in-cluster service-to-service traffic.
    """
    response = requests.get(
        "http://fx-rates-svc.default.svc.cluster.local/rate",
        params={"pair": currency_pair},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


root_agent = Agent(
    model="gemini-2.5-flash",
    name="currency_exchange_agent",
    tools=[get_exchange_rate, get_internal_rate, preload_memory],
)
