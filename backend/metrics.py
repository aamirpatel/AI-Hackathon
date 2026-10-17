from collections import Counter
def calculate(events):
    total = len(events)
    failed = sum(1 for e in events if e.status.lower() in {"error","failed","timeout"})
    durations = sorted(float(e.duration_ms or 0) for e in events)
    p95 = durations[min(len(durations)-1, int(.95*(len(durations)-1)))] if durations else 0
    tools = Counter((e.tool_name or "agent") for e in events if e.status.lower() in {"error","failed","timeout"})
    categories = Counter((e.error_category or "unknown") for e in events if e.status.lower() in {"error","failed","timeout"})
    return {"total_events":total,"failed_events":failed,"failure_rate_pct":round(failed/total*100,2) if total else 0,"success_rate_pct":round((total-failed)/total*100,2) if total else 100,"average_latency_ms":round(sum(durations)/len(durations),2) if durations else 0,"p95_latency_ms":round(p95,2),"top_failed_tools":[{"name":k,"count":v} for k,v in tools.most_common(5)],"failure_categories":[{"name":k,"count":v} for k,v in categories.most_common()]}
