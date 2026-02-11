import json
import os
from typing import Dict, Any, List

from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT / ".env")

# Try both OpenAI client styles for compatibility
try:
    from openai import OpenAI
    _OPENAI_CLIENT_STYLE = "new"
    _client = OpenAI()
except Exception:
    import openai
    _OPENAI_CLIENT_STYLE = "legacy"
    openai.api_key = os.getenv("OPENAI_API_KEY")
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
    You are an executive assistant. Summarize results into a crisp executive-style paragraph.
    Include the metric, sector context, timeframe if provided, and key caveats.
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
    if not os.getenv("OPENAI_API_KEY"):
        # Fallback heuristic if no key
        lower = question.lower()
        intent = {
            "metric": "pipeline_value" if "pipeline" in lower else (
                "revenue" if "revenue" in lower else (
                    "active_projects_value" if "active" in lower else "sector_breakdown"
                )
            ),
            "sector": None,
            "timeframe": None,
            "data_source": "deals",
        }
        return intent

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
        # Fallback heuristic
        return {
            "metric": "pipeline_value",
            "sector": None,
            "timeframe": None,
            "data_source": "deals",
        }


def generate_summary(results: Dict[str, Any], caveats: List[str]) -> str:
    """Generate an executive-style summary using OpenAI; fallback to string formatting."""
    prompt = (
        "Results: " + json.dumps(results, ensure_ascii=False) + "\n\n" +
        "Caveats: " + ("; ".join(caveats) if caveats else "None")
    )

    if not os.getenv("OPENAI_API_KEY"):
        # Basic deterministic summary
        return (
            f"Summary: {results}. Caveats: " + ("; ".join(caveats) if caveats else "None")
        )

    messages = [
        {"role": "system", "content": SYSTEM_SUMMARY},
        {"role": "user", "content": prompt},
    ]
    try:
        return _chat(messages)
    except Exception:
        return (
            f"Summary: {results}. Caveats: " + ("; ".join(caveats) if caveats else "None")
        )
