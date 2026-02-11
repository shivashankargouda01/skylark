from typing import Optional, Dict, Any

import pandas as pd


def _quarter_str(dt: pd.Timestamp) -> str:
    if pd.isna(dt):
        return ""
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}Q{q}"


def _filter(df: pd.DataFrame, sector: Optional[str] = None, quarter: Optional[str] = None) -> pd.DataFrame:
    out = df.copy()
    if sector:
        out = out[out["sector"].astype(str).str.strip().str.casefold() == sector.strip().casefold()]
    if quarter:
        qcol = out.get("close_date") or out.get("start_date")
        if qcol is not None:
            qvals = qcol.apply(_quarter_str)
            out = out[qvals == quarter]
    return out


def calculate_pipeline_value(deals_df: pd.DataFrame, sector: Optional[str] = None, quarter: Optional[str] = None) -> float:
    """Sum of values for non-won deals, optionally filtered by sector and quarter."""
    if deals_df is None or deals_df.empty:
        return 0.0
    df = _filter(deals_df, sector, quarter)
    pipeline = df[df["status"].str.lower() != "won"]["value"].fillna(0).sum()
    return float(pipeline)


def calculate_revenue(deals_df: pd.DataFrame) -> float:
    """Sum of values for won deals."""
    if deals_df is None or deals_df.empty:
        return 0.0
    revenue = deals_df[deals_df["status"].str.lower() == "won"]["value"].fillna(0).sum()
    return float(revenue)


def active_projects_value(work_orders_df: pd.DataFrame) -> float:
    """Sum of contract_value for active projects (exclude Completed/Closed)."""
    if work_orders_df is None or work_orders_df.empty:
        return 0.0
    active = work_orders_df[~work_orders_df["status"].str.lower().isin(["completed", "closed", "cancelled"])]
    return float(active["contract_value"].fillna(0).sum())


def sector_breakdown(deals_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Aggregate pipeline and revenue by sector."""
    if deals_df is None or deals_df.empty:
        return {}
    df = deals_df.copy()
    df["is_won"] = df["status"].str.lower() == "won"
    grp = df.groupby("sector", dropna=False)[["value", "is_won"]]
    results: Dict[str, Dict[str, Any]] = {}
    for sector, g in grp:
        revenue = g[g["is_won"]]["value"].fillna(0).sum()
        pipeline = g[~g["is_won"]]["value"].fillna(0).sum()
        results[str(sector or "Unknown")] = {
            "revenue": float(revenue),
            "pipeline": float(pipeline),
        }
    return results
