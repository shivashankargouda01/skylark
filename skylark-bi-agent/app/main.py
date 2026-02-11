import os
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

from .monday_client import fetch_board_dataframe
from .data_cleaning import clean_deals, clean_work_orders
from .analytics import (
    calculate_pipeline_value,
    calculate_revenue,
    active_projects_value,
    sector_breakdown,
)
from .ai_agent import interpret_question, generate_summary

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT / ".env")

app = FastAPI(title="Skylark BI Agent")


class AskPayload(BaseModel):
    question: str


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}

@app.post("/ask")
def ask(payload: AskPayload) -> Dict[str, Any]:
    question = payload.question
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    intent = interpret_question(question)
    metric = intent.get("metric")
    sector = intent.get("sector")
    timeframe = intent.get("timeframe")
    data_source = intent.get("data_source", "deals")

    # Fetch data
    try:
        deals_board_id = int(os.getenv("DEALS_BOARD_ID", "0"))
        work_orders_board_id = int(os.getenv("WORK_ORDERS_BOARD_ID", "0"))
    except ValueError:
        deals_board_id = 0
        work_orders_board_id = 0

    deals_df = pd.DataFrame()
    work_orders_df = pd.DataFrame()
    caveats: List[str] = []
    clarifications: List[str] = []

    try:
        if deals_board_id:
            deals_df = fetch_board_dataframe(deals_board_id)
        else:
            caveats.append("DEALS_BOARD_ID not set; using empty deals data")
    except Exception as e:
        caveats.append(f"Failed to fetch deals: {e}")

    try:
        if work_orders_board_id:
            work_orders_df = fetch_board_dataframe(work_orders_board_id)
        else:
            caveats.append("WORK_ORDERS_BOARD_ID not set; using empty work orders data")
    except Exception as e:
        caveats.append(f"Failed to fetch work orders: {e}")

    # Clean data
    deals_clean = clean_deals(deals_df)
    work_orders_clean = clean_work_orders(work_orders_df)

    # Data quality notes
    if deals_clean.empty:
        caveats.append("Deals data empty")
    if work_orders_clean.empty:
        caveats.append("Work orders data empty")

    # Analytics
    results: Dict[str, Any] = {
        "intent": intent,
        "metrics": {},
    }

    try:
        if metric == "pipeline_value":
            val = calculate_pipeline_value(deals_clean, sector=sector, quarter=timeframe)
            results["metrics"]["pipeline_value"] = val
            if sector is None:
                clarifications.append("Specify a sector (e.g., Healthcare) for focused pipeline insights.")
            if timeframe is None:
                clarifications.append("Add a timeframe (e.g., 2026Q1 or 'last quarter') to filter pipeline.")
        elif metric == "revenue":
            val = calculate_revenue(deals_clean)
            results["metrics"]["revenue"] = val
            if timeframe is None:
                clarifications.append("If you meant a specific quarter, include it (e.g., 'last quarter').")
        elif metric == "active_projects_value":
            val = active_projects_value(work_orders_clean)
            results["metrics"]["active_projects_value"] = val
            if sector is None:
                clarifications.append("Provide a sector (e.g., Operations) to focus active projects value.")
        elif metric == "sector_breakdown":
            results["metrics"]["sector_breakdown"] = sector_breakdown(deals_clean)
        else:
            caveats.append(f"Unknown metric '{metric}', defaulting to pipeline_value")
            val = calculate_pipeline_value(deals_clean, sector=sector, quarter=timeframe)
            results["metrics"]["pipeline_value"] = val
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {e}")

    summary = generate_summary(results, caveats)

    return {
        "intent": intent,
        "summary": summary,
        "caveats": caveats,
        "clarifications": clarifications,
        "details": results,
    }
