"""Incident triage agent: a small tool-calling loop over an OpenAI-compatible API (OpenRouter)."""
from __future__ import annotations

import json
import logging
import os
from typing import Callable

import httpx
from pydantic import BaseModel, Field, ValidationError

from .tools import TOOL_SCHEMAS, TOOLS

log = logging.getLogger("triage-agent")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_STEPS = 5

SYSTEM_PROMPT = """You are an SRE incident triage assistant.
Given an alert, use the tools to look up service context and runbooks, then answer ONLY with JSON:
{"severity": "SEV1|SEV2|SEV3|SEV4", "summary": str, "probable_cause": str,
 "next_steps": [str, ...], "owner": str, "runbook": str|null}
Rules: SEV1 = customer-facing Tier 1 outage; SEV2 = degraded Tier 1 or down Tier 2;
SEV3 = partial/non-customer impact; SEV4 = informational. Never invent commands that modify
production; suggest read-only diagnostics first."""


class Alert(BaseModel):
    title: str
    service: str
    message: str = ""
    tags: list[str] = Field(default_factory=list)


class Triage(BaseModel):
    severity: str
    summary: str
    probable_cause: str
    next_steps: list[str]
    owner: str
    runbook: str | None = None


LLMFn = Callable[[list[dict]], dict]


def openrouter_chat(messages: list[dict]) -> dict:
    """Call OpenRouter and return the assistant message dict."""
    key = os.environ["OPENROUTER_API_KEY"]
    model = os.getenv("TRIAGE_MODEL", "openai/gpt-4o-mini")
    resp = httpx.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": messages, "tools": TOOL_SCHEMAS, "temperature": 0},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[1]
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def triage(alert: Alert, llm: LLMFn = openrouter_chat) -> Triage:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Alert:\n{alert.model_dump_json(indent=2)}"},
    ]
    for step in range(MAX_STEPS):
        msg = llm(messages)
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            try:
                return Triage(**_parse_json(msg.get("content") or ""))
            except (ValueError, ValidationError) as exc:
                log.warning("Invalid JSON from model: %s", exc)
                messages.append({"role": "user", "content": "Reply again with valid JSON only."})
                continue
        for call in calls:
            name = call["function"]["name"]
            args = json.loads(call["function"].get("arguments") or "{}")
            fn = TOOLS.get(name)
            result = fn(**args) if fn else f"Unknown tool {name}"
            log.info("step=%s tool=%s args=%s", step, name, args)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    # Safe fallback: never drop an alert silently.
    return Triage(
        severity="SEV2",
        summary=f"Automatic triage failed for: {alert.title}",
        probable_cause="unknown",
        next_steps=["Escalate to on-call engineer for manual triage"],
        owner="on-call",
    )


def format_slack(alert: Alert, t: Triage) -> str:
    steps = "\n".join(f"• {s}" for s in t.next_steps)
    rb = f"\n*Runbook:* {t.runbook}" if t.runbook else ""
    return (f"*[{t.severity}] {alert.title}* — `{alert.service}` (owner: {t.owner})\n"
            f"{t.summary}\n*Probable cause:* {t.probable_cause}\n*Next steps:*\n{steps}{rb}")
