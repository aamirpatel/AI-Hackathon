import uuid, random
from datetime import datetime, timezone, timedelta
from .db import Base, engine, SessionLocal
from .models import Event
from .security import redact
Base.metadata.create_all(bind=engine)
def seed():
    db=SessionLocal()
    try:
        if db.query(Event).count(): print("Seed skipped: events already exist"); return
        random.seed(17); now=datetime.now(timezone.utc)
        scenarios=[("success",None,"success",["customer_profile","loan_status"]),("kyc_timeout","tool_timeout","timeout",["customer_profile","kyc_verification"]),("risk_error","api_failure","error",["customer_profile","risk_assessment"]),("validation","validation_failure","failed",["loan_status"]),("slow","latency_bottleneck","success",["customer_profile","loan_status","risk_assessment"])]
        for i in range(30):
            scenario,err,status,tools=scenarios[i%len(scenarios)]; session=f"sess-{i+1:04d}"; trace=f"trace-{uuid.uuid4().hex[:12]}"; created=now-timedelta(hours=i*2)
            db.add(Event(event_id=f"evt-{i}-user",session_id=session,trace_id=trace,span_id="root",agent_version="loan-agent-v1" if i<15 else "loan-agent-v2",event_type="user_request",status="success",duration_ms=10,request_text="What is the current status of my loan?",attributes={"source":"synthetic_seed","scenario":scenario},created_at=created))
            for j,tool in enumerate(tools):
                failed=(status!="success" and j==len(tools)-1); dur=random.randint(80,350) if scenario!="slow" else random.randint(1200,2200)
                db.add(Event(event_id=f"evt-{i}-tool-{j}",session_id=session,trace_id=trace,span_id=f"span-{j+1}",parent_span_id="root",agent_version="loan-agent-v1" if i<15 else "loan-agent-v2",event_type="tool_call",tool_name=tool,status=(status if failed else "success"),duration_ms=dur,error_category=(err if failed else None),attributes=redact({"http_status":504 if scenario=="kyc_timeout" and failed else 500 if failed else 200,"synthetic":True,"scenario":scenario}),created_at=created+timedelta(milliseconds=(j+1)*100)))
            db.add(Event(event_id=f"evt-{i}-response",session_id=session,trace_id=trace,span_id="final",parent_span_id="root",agent_version="loan-agent-v1" if i<15 else "loan-agent-v2",event_type="agent_response",status="failed" if status!="success" else "success",duration_ms=random.randint(400,2600),error_category=err,response_text="Demo response: the loan inquiry was processed." if status=="success" else "Demo response: the inquiry could not be completed.",attributes={"synthetic":True,"quality_score":0.92 if i<15 else 0.78},created_at=created+timedelta(seconds=1)))
        db.commit(); print("Seeded 30 synthetic banking sessions")
    finally: db.close()
if __name__=="__main__": seed()
