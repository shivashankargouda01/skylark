import json
import os
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT / ".env")

# Try OpenAI client; gracefully handle when package isn't installed
try:
    from openai import OpenAI
    _OPENAI_CLIENT_STYLE = "new"
    _client = OpenAI()
except Exception:
    try:
        import openai  # type: ignore
        _OPENAI_CLIENT_STYLE = "legacy"
        openai.api_key = os.getenv("OPENAI_API_KEY")
        _client = None
    except Exception:
        _OPENAI_CLIENT_STYLE = "none"
        _client = None

SYSTEM_INTERPRET = (
    """
    You are a business analytics intent parser. Given a founder question, return a JSON with keys:
    - metric (one of: pipeline_value, revenue, active_projects_value, sector_breakdown)
    - sector (string or null)
    - timeframe (like '2025Q1' or null)
    - data_source ("deals" or "work_orders")

    Be concise and only output JSON.
    """
)

SYSTEM_SUMMARY = (
    """
    You are a COO giving a business update.
    Write a short executive summary in plain English.
    Do NOT mention JSON or technical structures.
    Explain what the metric means for the business.
    Mention any data caveats naturally.
    """
)


def _chat(messages: List[Dict[str, str]], model: str = "gpt-4o-mini") -> str:
    """Return the assistant content using available OpenAI client style."""
    if _OPENAI_CLIENT_STYLE == "new":
        resp = _client.chat.completions.create(model=model, messages=messages)
        return resp.choices[0].message.content
    else:
        resp = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
        return resp["choices"][0]["message"]["content"]


def interpret_question(question: str) -> Dict[str, Any]:
    """Send the question to OpenAI and extract structured intent."""
    def _detect_metric(q: str) -> str:
        ql = q.lower()
        if "sector breakdown" in ql or "breakdown" in ql:
            return "sector_breakdown"
        if "revenue" in ql or "won" in ql:
            return "revenue"
        if "active project" in ql or "active projects" in ql or "operations value" in ql:
            return "active_projects_value"
        return "pipeline_value"

    def _detect_sector(q: str) -> Optional[str]:
        ql = q.lower()
        # simple keyword list; expand as needed
        sectors = [
            "healthcare", "operations", "finance", "retail", "education", "energy", "manufacturing",
        ]
        for s in sectors:
            if s in ql:
                return s.title()
        # parse "in <sector>" phrase
        if " in " in ql:
            try:
                after = ql.split(" in ", 1)[1]
                token = after.split()[0].strip(". ,;")
                return token.title()
            except Exception:
                pass
        return None

    def _detect_timeframe(q: str) -> Optional[str]:
        ql = q.lower()
        # Explicit quarter like Q1/Q2/etc -> assume current year
        for i in range(1, 5):
            tag = f"q{i}"
            if tag in ql:
                from datetime import datetime
                year = datetime.now().year
                return f"{year}Q{i}"
        # "last quarter" -> compute previous quarter
        if "last quarter" in ql:
            from datetime import datetime
            now = datetime.now()
            q = (now.month - 1) // 3 + 1
            prev_q = 4 if q == 1 else q - 1
            year = now.year - 1 if q == 1 else now.year
            return f"{year}Q{prev_q}"
        return None

    def _detect_source(q: str) -> str:
        ql = q.lower()
        if "work order" in ql or "operations" in ql or "projects" in ql:
            return "work_orders"
        return "deals"

    # Fallback heuristic path (used when OpenAI unavailable or fails)
    if not os.getenv("OPENAI_API_KEY") or _OPENAI_CLIENT_STYLE == "none":
        return {
            "metric": _detect_metric(question),
            "sector": _detect_sector(question),
            "timeframe": _detect_timeframe(question),
            "data_source": _detect_source(question),
        }

    messages = [
        {"role": "system", "content": SYSTEM_INTERPRET},
        {"role": "user", "content": question},
    ]
    try:
        content = _chat(messages)
        intent = json.loads(content)
        # Basic normalization
        intent.setdefault("metric", "pipeline_value")
        intent.setdefault("sector", None)
        intent.setdefault("timeframe", None)
        intent.setdefault("data_source", "deals")
        return intent
    except Exception:
        # Fallback heuristic when model errors or returns non-JSON
        return {
            "metric": _detect_metric(question),
            "sector": _detect_sector(question),
            "timeframe": _detect_timeframe(question),
            "data_source": _detect_source(question),
        }


def _fmt_currency(val: Any) -> str:
    try:
        v = float(val)
        return f"$ {v:,.0f}"
    except Exception:
        return str(val)

def fallback_summary(intent: Dict[str, Any], metrics: Dict[str, Any], caveats: List[str]) -> str:
    """Manual executive-style fallback summary (no AI)."""
    metric = intent.get("metric")
    sector = intent.get("sector")
    timeframe = intent.get("timeframe")

    ctx_parts = []
    if sector:
        ctx_parts.append(f"for the {sector} sector")
    if timeframe:
        ctx_parts.append(f"in {timeframe}")
    ctx = (" " + " ".join(ctx_parts)) if ctx_parts else ""

    summary = ""
    if metric == "pipeline_value":
        value = metrics.get("pipeline_value", 0)
        summary = f"The pipeline value{ctx} is currently {_fmt_currency(value)}."
        try:
            if float(value) == 0:
                summary += " This indicates no active deals scheduled to close in the selected period."
        except Exception:
            pass
    elif metric == "revenue":
        value = metrics.get("revenue", 0)
        summary = f"Revenue{ctx} is {_fmt_currency(value)}."
    elif metric == "active_projects_value":
        value = metrics.get("active_projects_value", 0)
        summary = f"Active projects value{ctx} totals {_fmt_currency(value)}."
    elif metric == "sector_breakdown":
        sb = metrics.get("sector_breakdown", {})
        if sb:
            ranked = sorted(((k, v.get("pipeline", 0.0), v.get("revenue", 0.0)) for k, v in sb.items()), key=lambda x: x[1], reverse=True)
            top = ranked[:3]
            parts = [f"{name}: pipeline {_fmt_currency(p)}, revenue {_fmt_currency(r)}" for name, p, r in top]
            summary = "Sector performance" + (ctx if ctx else "") + ": " + "; ".join(parts) + "."
        else:
            summary = "Sector performance data is unavailable."
    else:
        summary = "No recognized metric; defaulted to pipeline insights."

    if caveats:
        summary += " Note: " + "; ".join(caveats) + "."
    return summary

def generate_summary(results: Dict[str, Any], caveats: List[str]) -> str:
    """Generate an executive-style summary using OpenAI; smart manual fallback when AI unavailable."""
    prompt = (
        "Results: " + json.dumps(results, ensure_ascii=False) + "\n\n" +
        "Caveats: " + ("; ".join(caveats) if caveats else "None")
    )

    if not os.getenv("OPENAI_API_KEY") or _OPENAI_CLIENT_STYLE == "none":
        return fallback_summary(results.get("intent", {}), results.get("metrics", {}), caveats)

    messages = [
        {"role": "system", "content": SYSTEM_SUMMARY},
        {"role": "user", "content": prompt},
    ]
    try:
        return _chat(messages)
    except Exception:
        # Smart manual fallback
        return fallback_summary(results.get("intent", {}), results.get("metrics", {}), caveats)
