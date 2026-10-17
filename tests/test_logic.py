from types import SimpleNamespace
from backend.metrics import calculate
from backend.security import redact

def ev(status="success", duration=100, tool="loan_status", category=None):
    return SimpleNamespace(status=status,duration_ms=duration,tool_name=tool,error_category=category)
def test_metrics_failure_rate():
    result=calculate([ev(),ev("error",200,"kyc", "tool_timeout")])
    assert result["total_events"]==2
    assert result["failure_rate_pct"]==50
    assert result["top_failed_tools"][0]["name"]=="kyc"
def test_redacts_sensitive_keys():
    data=redact({"account_number":"123","nested":{"email":"a@b.com","safe":"ok"}})
    assert data["account_number"]=="[REDACTED]"
    assert data["nested"]["email"]=="[REDACTED]"
    assert data["nested"]["safe"]=="ok"
