import os
import json
from typing import Dict, List, Any

import requests
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT / ".env")

MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")


class MondayClientError(Exception):
    pass


def _headers() -> Dict[str, str]:
    if not MONDAY_API_KEY:
        raise MondayClientError("MONDAY_API_KEY not set in environment")
    return {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json",
    }


def fetch_board_items(board_id: int) -> Dict[str, Any]:
    """Fetch item names and column values from a monday.com board.

    Returns the raw JSON dict from monday.com. Raises MondayClientError on failure.
    """
    query = """
    query ($board_id: ID!) {
        boards (ids: [$board_id]) {
            columns { id title }
            items_page (limit: 500) {
                items {
                    id
                    name
                    column_values { id text value type }
                }
            }
        }
    }
    """
    # monday.com expects ID (string) type for board ids
    payload = {"query": query, "variables": {"board_id": str(board_id)}}
    try:
        resp = requests.post(MONDAY_API_URL, headers=_headers(), json=payload, timeout=30)
    except requests.RequestException as e:
        raise MondayClientError(f"Network error calling monday.com: {e}")

    try:
        data = resp.json()
    except ValueError:
        raise MondayClientError("Invalid JSON response from monday.com")

    if resp.status_code != 200 or "errors" in data:
        raise MondayClientError(f"monday.com API error: status={resp.status_code} errors={data.get('errors')}")

    return data


def items_to_dataframe(data: Dict[str, Any]) -> pd.DataFrame:
    """Convert monday.com items JSON to a flat pandas DataFrame.

    Columns are derived from column_value titles using their `text` field for readability.
    """
    boards = data.get("data", {}).get("boards", [])
    if not boards:
        return pd.DataFrame()

    b0 = boards[0]
    items = b0.get("items_page", {}).get("items", [])
    columns = b0.get("columns", [])
    title_map = {c.get("id"): c.get("title") for c in columns}
    rows: List[Dict[str, Any]] = []
    for item in items:
        row: Dict[str, Any] = {"name": item.get("name")}
        for cv in item.get("column_values", []):
            cv_id = cv.get("id")
            title = title_map.get(cv_id) or cv_id
            # Prefer human-readable text; fallback to raw value
            text = cv.get("text")
            val = text if text not in (None, "") else cv.get("value")
            # Some values are JSON strings — attempt to parse, then fallback
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    val = parsed
                except Exception:
                    pass
            row[title] = val
        rows.append(row)
    df = pd.DataFrame(rows)
    return df


def fetch_board_dataframe(board_id: int) -> pd.DataFrame:
    """Convenience wrapper that returns a DataFrame for a board."""
    raw = fetch_board_items(board_id)
    return items_to_dataframe(raw)
