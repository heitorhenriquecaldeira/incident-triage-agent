"""FastAPI webhook: receives alerts (e.g. Datadog/Alertmanager) and returns the triage."""
import logging

from fastapi import FastAPI

from .agent import Alert, Triage, format_slack, triage
from .tools import post_to_slack

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Incident Triage Agent")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/alerts", response_model=Triage)
def receive_alert(alert: Alert) -> Triage:
    result = triage(alert)
    post_to_slack(format_slack(alert, result))
    return result
