import re
from typing import Optional

import pandas as pd

MONEY_REGEX = re.compile(r"[-+]?\$?\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)(?:\.[0-9]{1,2})?")
PCT_REGEX = re.compile(r"([0-9]{1,3})(?:\.[0-9]+)?\s*%")


def _parse_money(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None

def _parse_probability(value: Optional[str]) -> Optional[float]:
    """Parse probability strings like '60%' or numbers 0-100 into 0..1 floats."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return v / 100.0 if v > 1 else max(0.0, min(1.0, v))
    s = str(value).strip()
    if not s:
        return None
    m = PCT_REGEX.search(s)
    if m:
        try:
            return float(m.group(1)) / 100.0
        except Exception:
            return None
    try:
        v = float(s)
        return v / 100.0 if v > 1 else max(0.0, min(1.0, v))
    except Exception:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    # Remove currency symbols and commas
    s = s.replace("$", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        # Try regex capture
        m = MONEY_REGEX.search(s)
        if m:
            try:
                return float(m.group(0).replace("$", "").replace(",", ""))
            except Exception:
                return None
        return None


def _to_dt(series: pd.Series) -> pd.Series:
    # Pandas 3.0 removed infer_datetime_format; rely on default parsing with coercion
    return pd.to_datetime(series, errors="coerce")


def clean_deals(df: pd.DataFrame) -> pd.DataFrame:
    """Clean deals board data and standardize columns.

    Expected input columns (flexible): name, Sector, Status, Deal Value, Close Date.
    Output columns: deal_name, sector, status, value, close_date.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["deal_name", "sector", "status", "value", "close_date"])  # empty frame

    # Flexible column mapping based on common monday.com titles
    colmap = {}
    for col in df.columns:
        lc = col.lower()
        if lc in ("name", "item"):
            colmap[col] = "deal_name"
        elif "sector" in lc:
            colmap[col] = "sector"
        elif "status" in lc or "stage" in lc:
            colmap[col] = "status"
        elif any(k in lc for k in ["deal value", "amount", "value", "projected revenue", "deal size", "budget"]):
            colmap[col] = "value"
        elif any(k in lc for k in ["close date", "expected close", "close", "due date", "date"]):
            colmap[col] = "close_date"
        elif any(k in lc for k in ["probability", "win likelihood", "confidence"]):
            colmap[col] = "probability"

    df2 = df.rename(columns=colmap)

    # Ensure required columns exist
    for req in ["deal_name", "sector", "status", "value", "close_date", "probability"]:
        if req not in df2.columns:
            df2[req] = None

    # Money to float
    df2["value"] = df2["value"].apply(_parse_money)
    # If value is entirely missing, attempt to auto-detect a money-like column
    if df2["value"].isna().all():
        for col in df.columns:
            if col in df2.columns:
                continue
            parsed = df[col].apply(_parse_money)
            if parsed.notna().sum() >= max(3, int(0.3 * len(df))):
                df2["value"] = parsed
                break

    # Dates
    df2["close_date"] = _to_dt(df2["close_date"])
    df2["probability"] = df2["probability"].apply(_parse_probability)

    # Missing sector
    df2["sector"] = df2["sector"].fillna("Unknown")

    # Normalize status casing
    df2["status"] = df2["status"].astype(str).str.strip().str.title()

    return df2[["deal_name", "sector", "status", "value", "close_date", "probability"]]


def clean_work_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Clean work orders/operations board data.

    Expected input columns (flexible): name, Sector, Status, Contract Value, Start Date, End Date.
    Output columns: project_name, sector, status, contract_value, start_date, end_date.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["project_name", "sector", "status", "contract_value", "start_date", "end_date"])  # empty

    colmap = {}
    for col in df.columns:
        lc = col.lower()
        if lc in ("name", "item"):
            colmap[col] = "project_name"
        elif "sector" in lc:
            colmap[col] = "sector"
        elif "status" in lc or "stage" in lc:
            colmap[col] = "status"
        elif any(k in lc for k in ["contract value", "value", "amount", "budget", "project value"]):
            colmap[col] = "contract_value"
        elif "start" in lc:
            colmap[col] = "start_date"
        elif "end" in lc or "finish" in lc:
            colmap[col] = "end_date"

    df2 = df.rename(columns=colmap)

    for req in ["project_name", "sector", "status", "contract_value", "start_date", "end_date"]:
        if req not in df2.columns:
            df2[req] = None

    df2["contract_value"] = df2["contract_value"].apply(_parse_money)
    if df2["contract_value"].isna().all():
        for col in df.columns:
            if col in df2.columns:
                continue
            parsed = df[col].apply(_parse_money)
            if parsed.notna().sum() >= max(3, int(0.3 * len(df))):
                df2["contract_value"] = parsed
                break
    df2["start_date"] = _to_dt(df2["start_date"]) if "start_date" in df2 else None
    df2["end_date"] = _to_dt(df2["end_date"]) if "end_date" in df2 else None

    df2["sector"] = df2["sector"].fillna("Unknown")
    df2["status"] = df2["status"].astype(str).str.strip().str.title()

    return df2[["project_name", "sector", "status", "contract_value", "start_date", "end_date"]]
