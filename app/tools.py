"""Tools the agent can call. Each tool is a plain function plus a JSON schema."""
from __future__ import annotations

import os
from pathlib import Path

import httpx

RUNBOOK_DIR = Path(os.getenv("RUNBOOK_DIR", Path(__file__).parent.parent / "runbooks"))


def search_runbooks(query: str) -> str:
    """Return runbooks whose name or content matches any keyword in the query."""
    words = [w.lower() for w in query.split() if len(w) > 2]
    hits = []
    for path in sorted(RUNBOOK_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        score = sum(text.lower().count(w) + 3 * path.stem.lower().count(w) for w in words)
        if score:
            hits.append((score, path.stem, text))
    if not hits:
        return "No matching runbook found."
    hits.sort(reverse=True)
    return "\n\n".join(f"### {name}\n{text[:1500]}" for _, name, text in hits[:2])


def get_service_context(service: str) -> str:
    """Static service catalog. In production this would query a CMDB or Backstage."""
    catalog = {
        "checkout-api": "Owner: payments-team | Tier 1 | Runs on Kubernetes (ns: payments) | Depends on: postgres-orders, redis-cache",
        "orders-worker": "Owner: orders-team | Tier 2 | Kubernetes CronJob/Deployment (ns: orders) | Depends on: rabbitmq",
        "web-frontend": "Owner: web-team | Tier 1 | Kubernetes (ns: web) behind ingress-nginx",
    }
    return catalog.get(service, f"Service '{service}' not found in catalog.")


def post_to_slack(message: str) -> str:
    """Send the triage summary to Slack via incoming webhook (skipped if not configured)."""
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return "Slack not configured; message not sent."
    r = httpx.post(url, json={"text": message}, timeout=10)
    return f"Slack responded {r.status_code}"


TOOLS = {
    "search_runbooks": search_runbooks,
    "get_service_context": get_service_context,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_runbooks",
            "description": "Search internal runbooks by keywords (e.g. 'OOMKilled memory', 'CrashLoopBackOff').",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_context",
            "description": "Get owner, tier and dependencies for a service.",
            "parameters": {
                "type": "object",
                "properties": {"service": {"type": "string"}},
                "required": ["service"],
            },
        },
    },
]
