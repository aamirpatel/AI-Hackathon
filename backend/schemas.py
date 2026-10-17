from pydantic import BaseModel, Field, ConfigDict
from typing import Any
class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=128)
    span_id: str = Field(min_length=1, max_length=128)
    parent_span_id: str | None = None
    agent_version: str = "demo-v1"
    event_type: str = Field(default="tool_call", max_length=64)
    tool_name: str | None = None
    status: str = "success"
    duration_ms: float = Field(default=0, ge=0)
    error_category: str | None = None
    request_text: str | None = None
    response_text: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
class BatchIn(BaseModel): events: list[EventIn] = Field(min_length=1, max_length=500)
