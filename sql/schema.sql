-- Reference schema; SQLAlchemy creates this table on API startup.
CREATE TABLE IF NOT EXISTS agent_events (
 id SERIAL PRIMARY KEY, event_id VARCHAR(128) UNIQUE NOT NULL, session_id VARCHAR(128) NOT NULL,
 trace_id VARCHAR(128) NOT NULL, span_id VARCHAR(128) NOT NULL, parent_span_id VARCHAR(128),
 agent_version VARCHAR(64) NOT NULL DEFAULT 'demo-v1', event_type VARCHAR(64) NOT NULL, tool_name VARCHAR(128),
 status VARCHAR(32) NOT NULL, duration_ms DOUBLE PRECISION NOT NULL DEFAULT 0, error_category VARCHAR(64),
 request_text TEXT, response_text TEXT, attributes JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX IF NOT EXISTS ix_events_session_id ON agent_events(session_id);
CREATE INDEX IF NOT EXISTS ix_events_trace_id ON agent_events(trace_id);
CREATE INDEX IF NOT EXISTS ix_events_created_at ON agent_events(created_at);
