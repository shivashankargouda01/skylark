import re
from typing import Optional

import pandas as pd

MONEY_REGEX = re.compile(r"[-+]?\$?\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)(?:\.[0-9]{1,2})?")


def _parse_money(value: Optional[str]) -> Optional[float]:
    if value is None:
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
    return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


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
        elif "status" in lc:
            colmap[col] = "status"
        elif any(k in lc for k in ["deal value", "amount", "value"]):
            colmap[col] = "value"
        elif any(k in lc for k in ["close date", "expected close", "close"]):
            colmap[col] = "close_date"

    df2 = df.rename(columns=colmap)

    # Ensure required columns exist
    for req in ["deal_name", "sector", "status", "value", "close_date"]:
        if req not in df2.columns:
            df2[req] = None

    # Money to float
    df2["value"] = df2["value"].apply(_parse_money)

    # Dates
    df2["close_date"] = _to_dt(df2["close_date"])

    # Missing sector
    df2["sector"] = df2["sector"].fillna("Unknown")

    # Normalize status casing
    df2["status"] = df2["status"].astype(str).str.strip().str.title()

    return df2[["deal_name", "sector", "status", "value", "close_date"]]


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
        elif "status" in lc:
            colmap[col] = "status"
        elif any(k in lc for k in ["contract value", "value", "amount"]):
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
    df2["start_date"] = _to_dt(df2["start_date"]) if "start_date" in df2 else None
    df2["end_date"] = _to_dt(df2["end_date"]) if "end_date" in df2 else None

    df2["sector"] = df2["sector"].fillna("Unknown")
    df2["status"] = df2["status"].astype(str).str.strip().str.title()

    return df2[["project_name", "sector", "status", "contract_value", "start_date", "end_date"]]
