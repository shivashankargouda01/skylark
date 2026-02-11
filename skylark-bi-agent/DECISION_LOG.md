# Decision Log — Skylark BI Agent

Version: 1.0 • Date: 2026-02-11

## Overview
Goal: Build an AI agent that answers founder-level BI questions by reading Monday.com boards (Deals, Work Orders) and producing executive-style insights. The agent is resilient to messy, incomplete data and provides clarifications/caveats.

## Key Decisions
1. Tech Stack: FastAPI + Uvicorn, Requests, Pandas, python-dotenv, optional OpenAI SDK.
2. Monday Integration: Read-only via GraphQL API. We fetch board columns + items and map column IDs → human titles for flexible schemas.
3. Query Understanding: Prefer OpenAI for structured intent; robust heuristic fallback detects metric, sector, timeframe, and data source without AI.
4. Executive Summaries: COO-style prompt for AI; smart manual fallback that never echoes JSON and reads like a business briefing.
5. Data Resilience: Clean currency and dates, normalize casing, auto-detect value columns, and surface caveats when data is missing.

## Assumptions
- Pipeline = sum of non-won deal values. If a Probability column exists (0..1 or “60%”), use weighted pipeline = Σ(value × probability).
- Revenue = sum of values where status == "Won".
- Sector normalization: missing sectors → "Unknown"; string casing/title normalized.
- Date normalization: `pd.to_datetime(errors="coerce")` with quarter filtering across `close_date` or `start_date` when present.
- Active work orders exclude statuses in {Completed, Closed, Cancelled}.

## Trade-offs
- Simplicity over breadth: no server-side caching yet; focus on correctness + resilience.
- Read-only integration to avoid permission complexity and reduce risk.
- Heuristic intent when AI is unavailable; slightly less nuanced than LLM but robust.
- Cleaner favors common column names; auto-detects money-like columns to avoid zero outcomes.

## Integration Approach (Monday.com)
- GraphQL: `boards(ids: [ID!]) { columns {id title} items_page(limit: 500) { items { id name column_values { id text value type }}}}`.
- We convert items to a DataFrame using column titles, preferring `text` for readability and parsing JSON values when needed.
- `.env` controls API key and board IDs; deterministic loading prevents path issues.

## Query Understanding Strategy
- Intent schema: { metric ∈ [pipeline_value, revenue, active_projects_value, sector_breakdown], sector?, timeframe?, data_source ∈ [deals, work_orders] }.
- Fallback detects phrases like “Q1/Q2…/last quarter”, sector keywords (“Healthcare”, “Operations”), and source hints (operations/work orders/projects).
- `/ask` adds "clarifications" when sector/timeframe are missing for better context.

## Data Resilience & Cleaning
- Deals: Recognize value via titles ["Deal Value", "Amount", "Value", "Projected Revenue", "Deal Size", "Budget"]. Auto-detect money column if none match. Parse Probability when present. Normalize Status/Sector. Coerce `close_date`.
- Work Orders: Recognize ["Contract Value", "Amount", "Budget", "Project Value"]. Normalize Status/Sector. Coerce `start_date`/`end_date`.
- Caveats: Surface empty data, missing board IDs, and fetch failures to keep leadership aware.

## Analytics Definitions
- Pipeline Value: Non-won sum; weighted by Probability when available.
- Revenue: Won sum.
- Active Projects Value: Sum of contract values for non-completed statuses.
- Sector Breakdown: Per-sector pipeline and revenue, top sectors summarized in briefings.

## Executive Insight (Leadership Updates)
- AI Prompt: "You are a COO giving a business update…" (plain English, no JSON, mention caveats naturally).
- Manual Fallback: Business briefing style (currency formatting, concise context). Example: 
	"Your Healthcare pipeline for Q1 currently stands at $0, indicating no active deals scheduled to close this quarter. Additionally, work order data is unavailable, limiting visibility into operational capacity."
- Clarifications: `/ask` suggests adding sector/timeframe when missing.

## Risks & Mitigations
- Schema variance across boards → flexible column mapping + auto-detect money-like columns.
- API rate limits/latency → future caching and pagination via `items_page` cursor.
- Secrets handling → `.env` locally; Render environment variables in production; `.gitignore` excludes `.env`.

## Testing & Validation
- Local: Swagger `/docs`, `/health`. Direct function calls for intent/analytics. Weighted pipeline verified for probability presence.
- Render: `render.yaml` uses `$PORT`; start via `python -m uvicorn`. Env vars set in dashboard.
- Smoke: Distinct intent per question; summaries are executive-style; caveats appear on missing data.

## Future Work
- Add pagination/cursor support for >500 items.
- Basic caching + graceful backoff for Monday API.
- Sector dictionary/ontology across boards.
- Unit tests for edge cases (dates, money parsing, probability).
- Observability: structured logs and `/metrics` endpoint.
- Role-specific briefings (CEO/COO/CFO) with tailored focus.

## Configuration Notes (for reviewers)
- Import CSVs into two Monday boards: Deals and Work Orders.
- Ensure columns exist for Status, Value/Amount (numeric), and Dates; Probability optional.
- Set `DEALS_BOARD_ID` and `WORK_ORDERS_BOARD_ID` via environment.


