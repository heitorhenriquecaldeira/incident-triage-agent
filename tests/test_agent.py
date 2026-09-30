import json

from app.agent import Alert, triage
from app.tools import get_service_context, search_runbooks


def fake_llm_factory():
    """Scripted LLM: first calls tools, then returns the final JSON."""
    calls = {"n": 0}

    def fake(messages):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"role": "assistant", "content": None, "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "get_service_context", "arguments": json.dumps({"service": "checkout-api"})}},
                {"id": "2", "type": "function", "function": {"name": "search_runbooks", "arguments": json.dumps({"query": "OOMKilled memory"})}},
            ]}
        tool_outputs = [m["content"] for m in messages if m.get("role") == "tool"]
        assert "payments-team" in tool_outputs[0]
        assert "oomkilled" in tool_outputs[1].lower()
        return {"role": "assistant", "content": json.dumps({
            "severity": "SEV2", "summary": "checkout-api pods restarting", "probable_cause": "memory limit",
            "next_steps": ["kubectl describe pod"], "owner": "payments-team", "runbook": "oomkilled"})}
    return fake


def test_triage_uses_tools_and_returns_structured_result():
    alert = Alert(title="Pods OOMKilled", service="checkout-api", message="container exceeded memory")
    result = triage(alert, llm=fake_llm_factory())
    assert result.severity == "SEV2"
    assert result.owner == "payments-team"


def test_fallback_when_model_never_answers():
    loop = lambda m: {"role": "assistant", "content": "not json"}
    result = triage(Alert(title="x", service="y"), llm=loop)
    assert result.severity == "SEV2" and result.owner == "on-call"


def test_tools():
    assert "No matching" in search_runbooks("zzzqqq")
    assert "not found" in get_service_context("nope")
