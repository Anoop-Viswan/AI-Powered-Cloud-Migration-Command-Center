"""Diagnostics API: summary, request log, config (for Admin Diagnostics tab)."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.services.diagnostics.cost import estimate_cost_usd
from backend.services.diagnostics.store import get_diagnostics_store

router = APIRouter()


@router.get("/summary")
def get_summary(period: str = Query("24h", description="24h | 7d | 30d")):
    """Aggregated metrics for the period: LLM calls/tokens/cost, Tavily calls, and alerts."""
    store = get_diagnostics_store()
    data = store.get_summary(period=period)
    # Add approximate cost for LLM
    total_in = data["llm"]["total_input_tokens"] or 0
    total_out = data["llm"]["total_output_tokens"] or 0
    total_cost = round(estimate_cost_usd(None, total_in, total_out), 4)
    data["llm"]["approx_cost_usd"] = total_cost
    by_op = data["llm"].get("by_operation") or []
    for op in by_op:
        op_cost = round(
            estimate_cost_usd(None, op.get("input_tokens") or 0, op.get("output_tokens") or 0), 4
        )
        op["approx_cost_usd"] = op_cost
        op["cost_pct"] = round((op_cost / total_cost * 100), 1) if total_cost > 0 else 0
    data["llm"]["by_operation"] = by_op
    # Thresholds and alerts (simple: no alert logic in v1, just return config)
    config = store.get_config()
    data["thresholds"] = {
        "daily_token_limit": int(config.get("daily_token_limit") or 500000),
        "daily_cost_limit_usd": float(config.get("daily_cost_limit_usd") or 5.0),
        "alert_at_percent": int(config.get("alert_at_percent") or 80),
    }
    total_tokens = total_in + total_out
    daily_limit = data["thresholds"]["daily_token_limit"]
    cost_limit = data["thresholds"]["daily_cost_limit_usd"]
    alert_pct = data["thresholds"]["alert_at_percent"]
    data["alerts"] = []
    if period == "24h" and daily_limit > 0 and total_tokens >= daily_limit * (alert_pct / 100):
        data["alerts"].append({
            "type": "exceeded" if total_tokens >= daily_limit else "approaching",
            "metric": "daily_token_limit",
            "current": total_tokens,
            "limit": daily_limit,
            "unit": "tokens",
        })
    if period == "24h" and cost_limit > 0:
        cost = data["llm"]["approx_cost_usd"]
        if cost >= cost_limit * (alert_pct / 100):
            data["alerts"].append({
                "type": "exceeded" if cost >= cost_limit else "approaching",
                "metric": "daily_cost_usd",
                "current": round(cost, 2),
                "limit": cost_limit,
                "unit": "USD",
            })
    return data


@router.get("/requests")
def get_requests(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    interface: str = Query(None, description="llm | tool to filter"),
):
    """Request log: recent LLM and tool calls with tokens, latency, status."""
    store = get_diagnostics_store()
    return {"requests": store.get_requests(limit=limit, offset=offset, interface=interface)}


@router.get("/config")
def get_config():
    """Current threshold and alert configuration."""
    store = get_diagnostics_store()
    return store.get_config()


class ConfigUpdate(BaseModel):
    daily_token_limit: int | None = None
    daily_cost_limit_usd: float | None = None
    alert_at_percent: int | None = None
    tavily_daily_limit: int | None = None


@router.patch("/config")
def update_config(body: ConfigUpdate):
    """Update threshold and alert configuration."""
    store = get_diagnostics_store()
    updates = {}
    if body.daily_token_limit is not None:
        if body.daily_token_limit < 0:
            raise HTTPException(400, "daily_token_limit must be >= 0")
        updates["daily_token_limit"] = body.daily_token_limit
    if body.daily_cost_limit_usd is not None:
        if body.daily_cost_limit_usd < 0:
            raise HTTPException(400, "daily_cost_limit_usd must be >= 0")
        updates["daily_cost_limit_usd"] = body.daily_cost_limit_usd
    if body.alert_at_percent is not None:
        if not (1 <= body.alert_at_percent <= 100):
            raise HTTPException(400, "alert_at_percent must be 1-100")
        updates["alert_at_percent"] = body.alert_at_percent
    if body.tavily_daily_limit is not None:
        if body.tavily_daily_limit < 0:
            raise HTTPException(400, "tavily_daily_limit must be >= 0")
        updates["tavily_daily_limit"] = body.tavily_daily_limit
    if updates:
        store.update_config(updates)
    return {"ok": True, "updated": list(updates.keys())}


@router.get("/interfaces")
def get_interfaces(period: str = Query("24h", description="24h | 7d | 30d")):
    """Per-interface breakdown for External interfaces section: calls, errors, cost, latency, status."""
    store = get_diagnostics_store()
    data = store.get_summary(period=period)
    stats = store.get_interface_stats(period=period)
    config = store.get_config()
    total_in = data["llm"]["total_input_tokens"] or 0
    total_out = data["llm"]["total_output_tokens"] or 0
    total_tokens = total_in + total_out
    cost = round(estimate_cost_usd(None, total_in, total_out), 4)
    # LLM status: based on configured thresholds (only for 24h so we compare daily usage to daily limits)
    daily_token_limit = int(config.get("daily_token_limit") or 500000)
    daily_cost_limit = float(config.get("daily_cost_limit_usd") or 5.0)
    alert_at_percent = int(config.get("alert_at_percent") or 80)
    llm_status = "ok"
    if period == "24h":
        token_at_alert = daily_token_limit * (alert_at_percent / 100) if daily_token_limit > 0 else 0
        cost_at_alert = daily_cost_limit * (alert_at_percent / 100) if daily_cost_limit > 0 else 0
        if daily_token_limit > 0 and total_tokens >= daily_token_limit:
            llm_status = "exceeded"
        elif daily_cost_limit > 0 and cost >= daily_cost_limit:
            llm_status = "exceeded"
        elif (daily_token_limit > 0 and total_tokens >= token_at_alert) or (daily_cost_limit > 0 and cost >= cost_at_alert):
            llm_status = "warn"
        elif data["llm"]["errors"] > 0:
            llm_status = "warn"  # show warn when there are errors (so user checks)
    else:
        if data["llm"]["errors"] > 0:
            llm_status = "warn"
    tavily_status = "ok"
    if data["tavily"]["errors"] > 0:
        tavily_status = "warn"
    return {
        "llm": {
            "name": "LLM",
            "model": stats["llm"].get("model"),
            "calls": stats["llm"]["calls"],
            "errors": stats["llm"]["errors"],
            "approx_cost_usd": cost,
            "p95_latency_ms": stats["llm"].get("p95_latency_ms"),
            "total_input_tokens": stats["llm"]["total_input_tokens"],
            "total_output_tokens": stats["llm"]["total_output_tokens"],
            "status": llm_status,
        },
        "tavily": {
            "name": "Tavily (web search)",
            "calls": stats["tavily"]["calls"],
            "errors": stats["tavily"]["errors"],
            "avg_latency_ms": stats["tavily"].get("avg_latency_ms"),
            "status": tavily_status,
        },
        "pinecone": {
            "name": "Pinecone (KB)",
            "queries": stats["pinecone"]["queries"],
            "errors": stats["pinecone"]["errors"],
            "status": "ok",
        },
    }


@router.get("/patterns")
def get_patterns(period: str = Query("7d", description="24h | 7d | 30d")):
    """Top consumers by cost % and usage by day for Patterns section chart."""
    store = get_diagnostics_store()
    data = store.get_summary(period=period)
    total_in = data["llm"].get("total_input_tokens") or 0
    total_out = data["llm"].get("total_output_tokens") or 0
    total_cost = estimate_cost_usd(None, total_in, total_out)
    by_op = data["llm"].get("by_operation") or []
    top_consumers = []
    for op in by_op:
        cost_usd = round(estimate_cost_usd(None, op.get("input_tokens") or 0, op.get("output_tokens") or 0), 4)
        pct = round((cost_usd / total_cost * 100), 1) if total_cost > 0 else 0
        top_consumers.append({
            "operation": op["operation"],
            "calls": op["calls"],
            "tokens": (op.get("input_tokens") or 0) + (op.get("output_tokens") or 0),
            "cost_usd": cost_usd,
            "cost_pct": pct,
        })
    top_consumers.sort(key=lambda x: x["cost_usd"], reverse=True)
    usage_by_day = store.get_usage_by_day(period=period)
    for day in usage_by_day:
        day["cost_usd"] = round(estimate_cost_usd(None, day["input_tokens"], day["output_tokens"]), 4)
        day["tokens"] = day["input_tokens"] + day["output_tokens"]
    return {"period": period, "top_consumers": top_consumers, "usage_by_day": usage_by_day}
