from fastapi import FastAPI, HTTPException

app = FastAPI()

# Static rates for demo -- this service's purpose is to demonstrate
# in-cluster traffic from the agent, not to serve live data.
RATES = {
    "USD/EUR": 0.92,
    "EUR/USD": 1.09,
    "GBP/USD": 1.27,
    "USD/GBP": 0.79,
    "USD/JPY": 157.5,
    "JPY/USD": 0.00635,
    "EUR/GBP": 0.85,
    "GBP/EUR": 1.18,
}


@app.get("/rate")
def get_rate(pair: str = "USD/EUR"):
    if pair not in RATES:
        raise HTTPException(status_code=404, detail=f"Unknown pair '{pair}'. Known: {list(RATES)}")
    return {"pair": pair, "rate": RATES[pair], "source": "internal-fx-rates-service"}


@app.get("/health")
def health():
    return {"status": "ok"}
