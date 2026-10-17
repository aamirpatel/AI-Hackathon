import os, requests, pandas as pd, streamlit as st, plotly.express as px
API=os.getenv("API_BASE_URL","http://localhost:8000")
st.set_page_config(page_title="Banking Agent Ops",layout="wide",page_icon="🏦")
st.title("🏦 Banking AI Agent Observability & Replay")
st.caption("Synthetic hackathon demo • Recorded replay never invokes banking APIs")
def get(path):
    try:
        r=requests.get(API+path,timeout=5); r.raise_for_status(); return r.json()
    except Exception as e: st.error(f"Backend unavailable at {API}: {e}"); st.stop()
page=st.sidebar.radio("Workspace",["Executive Overview","Session Explorer","Failure Analysis","Replay & Comparison","Quality & Latency"])
if page=="Executive Overview":
    m=get("/api/v1/metrics/overview")
    cols=st.columns(5)
    for c,label,val in zip(cols,["Sessions","Traces","Success rate","Failure rate","Avg latency"],[m.get("sessions",0),m.get("traces",0),f"{m['success_rate_pct']}%",f"{m['failure_rate_pct']}%",f"{m['average_latency_ms']} ms"]): c.metric(label,val)
    st.subheader("Operational health"); st.write(f"**{m['operational_health'].upper()}** — based on current event failure rate")
    events=get("/api/v1/events/recent?limit=500")["items"]
    if events:
        df=pd.DataFrame(events); df["created_at"]=pd.to_datetime(df["created_at"]); daily=df.groupby(df.created_at.dt.date).size().reset_index(name="events"); st.plotly_chart(px.line(daily,x="created_at",y="events",title="Event volume over time"),use_container_width=True)
        st.dataframe(df[["session_id","trace_id","event_type","tool_name","status","duration_ms","error_category","agent_version"]],use_container_width=True,hide_index=True)
    else: st.info("No events yet. Load synthetic seed data or POST an event to the API.")
elif page=="Session Explorer":
    sessions=get("/api/v1/sessions?limit=500")["items"]
    if not sessions: st.info("No sessions available.")
    else:
        df=pd.DataFrame(sessions); st.dataframe(df,use_container_width=True,hide_index=True)
        sid=st.selectbox("Choose session",df.session_id.tolist()); data=get(f"/api/v1/sessions/{sid}"); st.subheader(f"Session {sid}"); st.json(data["events"])
        trace=st.selectbox("Trace",sorted({e["trace_id"] for e in data["events"]})); st.json(get(f"/api/v1/traces/{trace}/timeline"))
elif page=="Failure Analysis":
    f=get("/api/v1/metrics/failures"); c1,c2=st.columns(2)
    c1.subheader("Top failed tools/APIs"); c1.plotly_chart(px.bar(pd.DataFrame(f["top_failed_tools"]),x="name",y="count",title="Failed tool calls"),use_container_width=True) if f["top_failed_tools"] else c1.info("No failures")
    c2.subheader("Failure categories"); c2.plotly_chart(px.pie(pd.DataFrame(f["failure_categories"]),names="name",values="count",title="Failure distribution"),use_container_width=True) if f["failure_categories"] else c2.info("No failures")
    st.subheader("Recent failed events"); ev=get("/api/v1/events/recent?limit=500")["items"]; df=pd.DataFrame(ev); st.dataframe(df[df.status.isin(["error","failed","timeout"])],use_container_width=True,hide_index=True) if not df.empty else st.info("No events")
elif page=="Replay & Comparison":
    traces=get("/api/v1/events/recent?limit=500")["items"]
    if not traces: st.info("No traces to replay")
    else:
        ids=sorted({e["trace_id"] for e in traces}); trace=st.selectbox("Historical trace",ids); replay=get(f"/api/v1/traces/{trace}/replay")
        st.warning("Recorded replay reconstructs stored events only. It makes no external calls.")
        st.metric("Recorded events",replay["event_count"]); st.json(replay)
        scenario=st.selectbox("Mock simulation scenario",["success","kyc_timeout","risk_api_error"]); 
        if st.button("Run safe mock simulation"):
            original=get(f"/api/v1/traces/{trace}"); sim=requests.post(API+"/api/v1/replay/simulate",json={"scenario":scenario},timeout=5).json(); st.subheader("Simulation result"); st.json(sim); st.subheader("Original vs simulated"); st.write({"original_event_count":len(original["events"]),"simulated_status":sim["status"],"simulated_tool_sequence":sim["tool_sequence"]})
elif page=="Quality & Latency":
    q=get("/api/v1/quality/trends")["items"]; lat=get("/api/v1/metrics/latency"); a,b,c=st.columns(3); a.metric("Average latency",f"{lat['average_latency_ms']} ms"); b.metric("p95 latency",f"{lat['p95_latency_ms']} ms"); c.metric("Agent versions",len(q))
    if q: st.plotly_chart(px.bar(pd.DataFrame(q),x="agent_version",y="failure_rate_pct",title="Failure rate by agent version (%)"),use_container_width=True)
    if lat["by_tool"]: st.plotly_chart(px.bar(pd.DataFrame(lat["by_tool"]),x="tool",y="avg_ms",title="Average latency by tool"),use_container_width=True)
