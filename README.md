# Incident Triage Agent

An AI agent that receives monitoring alerts (Datadog, Alertmanager or any webhook), gathers context with tools, and returns a structured triage: severity, probable cause, next steps and owner. It can also post the result to Slack.

Built from real on-call work: in a NOC/command-center setting, much of the first 10 minutes of an incident goes to the same steps (who owns this service, is there a runbook, how bad is it). This agent does those steps automatically.

## How it works

```
Alert webhook ──> FastAPI /alerts ──> Agent loop (LLM via OpenRouter)
                                         │  tool: get_service_context (owner, tier, deps)
                                         │  tool: search_runbooks (markdown runbooks)
                                         ▼
                                 Structured JSON triage ──> Slack
```

- **Tool-calling loop** over an OpenAI-compatible API (OpenRouter), capped at 5 steps.
- **Structured output** validated with Pydantic; the agent retries if the JSON is invalid.
- **Safe fallback**: if the model fails, the alert is escalated as SEV2 to on-call and never dropped.
- **Guardrails**: the prompt only suggests read-only diagnostics first.
- **Model is configurable** (`TRIAGE_MODEL`), so you can trade cost against quality.

## Run locally

```bash
cp .env.example .env   # add your OpenRouter key
pip install -r requirements.txt
export $(cat .env | xargs) && uvicorn app.main:app --reload
```

```bash
curl -X POST localhost:8000/alerts -H 'Content-Type: application/json' -d '{
  "title": "Pods OOMKilled",
  "service": "checkout-api",
  "message": "3 pods restarted in 10m, container exceeded memory limit",
  "tags": ["env:prod", "kube_namespace:payments"]
}'
```

Or with Docker:

```bash
docker build -t incident-triage-agent .
docker run --env-file .env -p 8000:8000 incident-triage-agent
```

## Tests

```bash
pytest -q
```

The tests use a scripted fake LLM, so they run in CI without an API key.

## Roadmap

- Pull live context from Datadog (recent deploys, monitors) and Kubernetes (read-only `kubectl`)
- Semantic runbook search with embeddings
- Deploy with a Helm chart

## Author

Heitor Silva, Senior DevOps / Cloud Infrastructure Engineer · [LinkedIn](https://linkedin.com/in/heitorhenrique)
