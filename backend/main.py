import os, uuid, json
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from .db import Base, engine, SessionLocal
from .models import Event
from .schemas import EventIn, BatchIn
from .security import redact
from .metrics import calculate
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app=FastAPI(title="Banking Agent Observability API", version="1.0.0", description="Synthetic demo platform for banking AI agent operations")
Base.metadata.create_all(bind=engine)
# Platform service telemetry is independent of the persisted agent-event store.
if not isinstance(trace.get_tracer_provider(), TracerProvider):
    provider = TracerProvider(resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "banking-agent-observability-api")}))
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint.rstrip("/") + "/v1/traces" if not endpoint.endswith("/v1/traces") else endpoint)))
        except Exception:
            # Local demo must continue if optional exporter configuration is unavailable.
            pass
    trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
def event_dict(e):
    return {"event_id":e.event_id,"session_id":e.session_id,"trace_id":e.trace_id,"span_id":e.span_id,"parent_span_id":e.parent_span_id,"agent_version":e.agent_version,"event_type":e.event_type,"tool_name":e.tool_name,"status":e.status,"duration_ms":e.duration_ms,"error_category":e.error_category,"request_text":e.request_text,"response_text":e.response_text,"attributes":redact(e.attributes or {}),"created_at":e.created_at.isoformat() if e.created_at else None}
def persist(payload, db):
    old=db.scalar(select(Event).where(Event.event_id==payload.event_id))
    if old: return old, False
    d=payload.model_dump(); d["attributes"]=redact(d.get("attributes") or {})
    # Avoid saving raw credentials/PII in free-text fields; synthetic demo text is expected.
    d["request_text"]=redact({"text":d.get("request_text")}).get("text")
    d["response_text"]=redact({"text":d.get("response_text")}).get("text")
    obj=Event(**d); db.add(obj); db.flush(); return obj, True
@app.get("/health")
def health(): return {"status":"ok","service":"banking-agent-observability"}
@app.post("/api/v1/events")
def ingest(payload:EventIn, db:Session=Depends(get_db)):
    try: obj,created=persist(payload,db); db.commit(); db.refresh(obj); return {"accepted":True,"created":created,"event":event_dict(obj)}
    except Exception as e: db.rollback(); raise HTTPException(500, f"event ingestion failed: {type(e).__name__}")
@app.post("/api/v1/traces/batch")
def ingest_batch(payload:BatchIn, db:Session=Depends(get_db)):
    try:
        results=[persist(p,db) for p in payload.events]; db.commit()
        return {"accepted":len(results),"created":sum(1 for _,created in results if created),"duplicates":sum(1 for _,created in results if not created)}
    except Exception as e: db.rollback(); raise HTTPException(500, f"batch ingestion failed: {type(e).__name__}")
@app.get("/api/v1/sessions")
def sessions(limit:int=Query(100,ge=1,le=500), status:str|None=None, db:Session=Depends(get_db)):
    q=select(Event).order_by(desc(Event.created_at))
    if status: q=q.where(Event.status==status)
    events=db.scalars(q.limit(limit*10)).all(); groups={}
    for e in events:
        g=groups.setdefault(e.session_id,{"session_id":e.session_id,"trace_ids":set(),"events":0,"failures":0,"latest":event_dict(e)["created_at"]})
        g["trace_ids"].add(e.trace_id); g["events"]+=1; g["failures"]+=int(e.status.lower() in {"error","failed","timeout"})
    out=[]
    for g in list(groups.values())[:limit]: g["trace_ids"]=sorted(g["trace_ids"]); out.append(g)
    return {"items":out,"count":len(out)}
@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id:str, db:Session=Depends(get_db)):
    events=db.scalars(select(Event).where(Event.session_id==session_id).order_by(Event.created_at,Event.id)).all()
    if not events: raise HTTPException(404,"session not found")
    return {"session_id":session_id,"events":[event_dict(e) for e in events]}
@app.get("/api/v1/traces/{trace_id}")
def get_trace(trace_id:str, db:Session=Depends(get_db)):
    events=db.scalars(select(Event).where(Event.trace_id==trace_id).order_by(Event.created_at,Event.id)).all()
    if not events: raise HTTPException(404,"trace not found")
    return {"trace_id":trace_id,"session_id":events[0].session_id,"events":[event_dict(e) for e in events]}
@app.get("/api/v1/traces/{trace_id}/timeline")
def timeline(trace_id:str, db:Session=Depends(get_db)): return get_trace(trace_id,db)
@app.get("/api/v1/traces/{trace_id}/replay")
def recorded_replay(trace_id:str, db:Session=Depends(get_db)):
    data=get_trace(trace_id,db)
    return {"mode":"recorded_replay","external_calls_made":False,"trace_id":trace_id,"event_count":len(data["events"]),"timeline":data["events"],"note":"Historical reconstruction only; no agent, tool, or banking API was invoked."}
@app.post("/api/v1/replay/simulate")
def simulate(payload:dict):
    # Safe, deterministic mock simulation only; never calls banking systems.
    scenario=str(payload.get("scenario","success")); failed=scenario in {"kyc_timeout","risk_api_error"}
    return {"mode":"mock_simulation","scenario":scenario,"status":"failed" if failed else "success","tool_sequence":["customer_profile","loan_status"]+(["kyc_verification"] if scenario=="kyc_timeout" else [])+(["risk_assessment"] if scenario=="risk_api_error" else []),"external_calls_made":False,"note":"Synthetic simulation only; no production banking operation executed."}
@app.get("/api/v1/metrics/overview")
def overview(db:Session=Depends(get_db)):
    events=db.scalars(select(Event)).all(); result=calculate(events); result["sessions"]=len({e.session_id for e in events}); result["traces"]=len({e.trace_id for e in events}); result["operational_health"]="healthy" if result["failure_rate_pct"]<5 else "degraded" if result["failure_rate_pct"]<20 else "critical"; return result
@app.get("/api/v1/metrics/failures")
def failures(db:Session=Depends(get_db)):
    events=db.scalars(select(Event)).all(); return {"top_failed_tools":calculate(events)["top_failed_tools"],"failure_categories":calculate(events)["failure_categories"]}
@app.get("/api/v1/metrics/latency")
def latency(db:Session=Depends(get_db)):
    events=db.scalars(select(Event)).all(); return {"average_latency_ms":calculate(events)["average_latency_ms"],"p95_latency_ms":calculate(events)["p95_latency_ms"],"by_tool":_latency_by_tool(events)}
def _latency_by_tool(events):
    d={}
    for e in events: d.setdefault(e.tool_name or "agent",[]).append(float(e.duration_ms or 0))
    return [{"tool":k,"avg_ms":round(sum(v)/len(v),2),"count":len(v)} for k,v in d.items()]
@app.get("/api/v1/quality/trends")
def quality(db:Session=Depends(get_db)):
    events=db.scalars(select(Event).order_by(Event.created_at)).all(); grouped={}
    for e in events: grouped.setdefault(e.agent_version,[]).append(e)
    return {"items":[{"agent_version":k,"events":len(v),"failure_rate_pct":calculate(v)["failure_rate_pct"]} for k,v in grouped.items()]}
@app.get("/api/v1/events/recent")
def recent(limit:int=Query(100,ge=1,le=500), db:Session=Depends(get_db)):
    events=db.scalars(select(Event).order_by(desc(Event.created_at)).limit(limit)).all(); return {"items":[event_dict(e) for e in events]}
