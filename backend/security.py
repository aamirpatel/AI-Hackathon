import re
SENSITIVE_KEYS = re.compile(r"(account|customer_?id|phone|email|address|ssn|token|password|secret|dob)", re.I)
def redact(value):
    """Redact configured sensitive keys recursively before persistence/display."""
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if SENSITIVE_KEYS.search(str(k)) else redact(v)) for k,v in value.items()}
    if isinstance(value, list): return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"[REDACTED]", value)
        return value
    return value
