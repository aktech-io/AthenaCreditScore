from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
from sqlalchemy import text

from db.database import AsyncSessionLocal
from scoring.base_scorer import calculate_base_score
from scoring.crb_extractor import extract_crb_metrics
from scoring.hybrid_scorer import compute_hybrid_score

app_server = Server("athena-mcp-server")


# ── Tool: get_customer_profile ──────────────────────────────────────────────
@app_server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(name="get_customer_profile",       description="Fetch customer profile from DB", inputSchema={"type": "object", "properties": {"customer_id": {"type": "integer"}}, "required": ["customer_id"]}),
        Tool(name="get_transactions_for_analysis", description="Fetch recent transactions", inputSchema={"type": "object", "properties": {"customer_id": {"type": "integer"}, "limit": {"type": "integer", "default": 500}}, "required": ["customer_id"]}),
        Tool(name="get_previous_decisions",     description="Fetch previous score events", inputSchema={"type": "object", "properties": {"customer_id": {"type": "integer"}}, "required": ["customer_id"]}),
        Tool(name="calculate_base_score",       description="Compute quantitative base score", inputSchema={"type": "object", "properties": {"customer_id": {"type": "integer"}, "analysis_period_days": {"type": "integer", "default": 180}}, "required": ["customer_id"]}),
        Tool(name="fetch_crb_report",           description="Retrieve latest CRB report from DB", inputSchema={"type": "object", "properties": {"customer_id": {"type": "integer"}, "crb_name": {"type": "string", "default": "any"}}, "required": ["customer_id"]}),
        Tool(name="extract_crb_metrics",        description="Parse CRB JSON and compute contribution", inputSchema={"type": "object", "properties": {"crb_report": {"type": "object"}}, "required": ["crb_report"]}),
        Tool(name="calculate_credit_score",     description="Orchestrate full hybrid credit score", inputSchema={"type": "object", "properties": {"customer_id": {"type": "integer"}, "model_target": {"type": "string", "default": "champion"}}, "required": ["customer_id"]}),
    ]


@app_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    async with AsyncSessionLocal() as db:

        if name == "get_customer_profile":
            cid = arguments["customer_id"]
            row = await db.execute(text(
                "SELECT customer_id, first_name, last_name, mobile_number, national_id, region FROM customers WHERE customer_id = :cid"
            ), {"cid": cid})
            r = row.fetchone()
            result = dict(r._mapping) if r else {}
            return [TextContent(type="text", text=json.dumps(result, default=str))]

        elif name == "get_transactions_for_analysis":
            cid = arguments["customer_id"]
            limit = arguments.get("limit", 500)
            rows = await db.execute(text("""
                SELECT transaction_date, amount, transaction_type, category, description, balance_after
                FROM transactions WHERE customer_id = :cid ORDER BY transaction_date DESC LIMIT :lim
            """), {"cid": cid, "lim": limit})
            txns = [dict(r._mapping) for r in rows.fetchall()]
            return [TextContent(type="text", text=json.dumps(txns, default=str))]

        elif name == "get_previous_decisions":
            cid = arguments["customer_id"]
            rows = await db.execute(text("""
                SELECT final_score, score_band, pd_probability, scored_at
                FROM credit_score_events WHERE customer_id = :cid ORDER BY scored_at DESC LIMIT 5
            """), {"cid": cid})
            decisions = [dict(r._mapping) for r in rows.fetchall()]
            return [TextContent(type="text", text=json.dumps(decisions, default=str))]

        elif name == "calculate_base_score":
            cid = arguments["customer_id"]
            period = arguments.get("analysis_period_days", 180)
            rows = await db.execute(text("""
                SELECT transaction_date, amount, transaction_type, category, balance_after
                FROM transactions WHERE customer_id = :cid ORDER BY transaction_date DESC LIMIT 1000
            """), {"cid": cid})
            txns = [dict(r._mapping) for r in rows.fetchall()]
            result = calculate_base_score(txns, period)
            return [TextContent(type="text", text=json.dumps(result.__dict__, default=str))]

        elif name == "fetch_crb_report":
            cid = arguments["customer_id"]
            crb_name = arguments.get("crb_name", "any")
            q = "SELECT raw_report, crb_name, report_date, bureau_score FROM crb_reports WHERE customer_id = :cid"
            if crb_name != "any":
                q += " AND crb_name = :crb_name"
            q += " ORDER BY report_date DESC LIMIT 1"
            params = {"cid": cid, "crb_name": crb_name}
            row = await db.execute(text(q), params)
            r = row.fetchone()
            if not r:
                return [TextContent(type="text", text=json.dumps({}))]
            return [TextContent(type="text", text=json.dumps(dict(r._mapping), default=str))]

        elif name == "extract_crb_metrics":
            crb_report = arguments["crb_report"]
            metrics = extract_crb_metrics(crb_report)
            return [TextContent(type="text", text=json.dumps(metrics.__dict__, default=str))]

        elif name == "calculate_credit_score":
            cid = arguments["customer_id"]
            model_target = arguments.get("model_target", "champion")

            # Fetch all needed data
            profile_row = await db.execute(text(
                "SELECT first_name, last_name FROM customers WHERE customer_id = :cid"
            ), {"cid": cid})
            profile = profile_row.fetchone()
            customer_name = f"{profile[0]} {profile[1]}" if profile else "Unknown"

            tx_rows = await db.execute(text("""
                SELECT transaction_date, amount, transaction_type, category, description, balance_after
                FROM transactions WHERE customer_id = :cid ORDER BY transaction_date DESC LIMIT 500
            """), {"cid": cid})
            transactions = [dict(r._mapping) for r in tx_rows.fetchall()]

            crb_row = await db.execute(text(
                "SELECT raw_report FROM crb_reports WHERE customer_id = :cid ORDER BY report_date DESC LIMIT 1"
            ), {"cid": cid})
            crb_r = crb_row.fetchone()
            crb_raw = dict(crb_r._mapping)["raw_report"] if crb_r else None

            result = await compute_hybrid_score(
                customer_id=cid,
                customer_name=customer_name,
                transactions=transactions,
                crb_raw_report=crb_raw,
                model_target=model_target,
            )
            output = {
                "customer_id": result.customer_id,
                "base_score": result.base_score,
                "crb_contribution": result.crb_contribution,
                "llm_adjustment": result.llm_adjustment,
                "pd_probability": result.pd_probability,
                "final_score": result.final_score,
                "score_band": result.score_band,
                "reasoning": result.reasoning,
            }
            return [TextContent(type="text", text=json.dumps(output, default=str))]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
