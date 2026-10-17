from sqlalchemy import String, Text, DateTime, Float, Integer, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .db import Base

class Event(Base):
    __tablename__ = "agent_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    trace_id: Mapped[str] = mapped_column(String(128), index=True)
    span_id: Mapped[str] = mapped_column(String(128), index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    agent_version: Mapped[str] = mapped_column(String(64), default="demo-v1")
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    request_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
Index("ix_events_trace_created", Event.trace_id, Event.created_at)
