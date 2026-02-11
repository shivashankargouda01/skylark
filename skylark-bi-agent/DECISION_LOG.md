# Decision Log — Skylark BI Agent

## Assumptions
- Pipeline = sum of deal values where status != "Won".
- Revenue = sum of deal values where status == "Won".
- Sector normalization: missing sectors become "Unknown"; string casing normalized.
- Date normalization: `pd.to_datetime(errors="coerce")` for flexible parsing.
- Work orders "active" excludes statuses in {Completed, Closed, Cancelled}.

## Trade-offs
- No caching initially to keep architecture simple; future: per-board short TTL.
- Monday.com GraphQL read-only integration; write operations omitted.
- Fallback heuristics if OpenAI is unavailable to ensure answers still work.
- Data cleaning is opinionated but resilient to messy inputs (currency strings, dates).

## Query Understanding
- Primary: OpenAI intent parsing to JSON {metric, sector, timeframe, data_source}.
- Fallback: simple heuristics keyed on words like "pipeline", "revenue", "active".
- Clarifying questions can be added by prompting the LLM to request missing parameters.

## Leadership Updates (Optional requirement)
- Implemented `generate_summary(results, caveats)` to produce executive-style summaries.
- Weekly cadence suggestion: run a scheduled job to hit `/ask` with three presets: pipeline, revenue, ops active value; compile into a short memo.
- Caveats are surfaced (empty data, API issues) to inform risk-aware leadership decisions.

## What we’d do with more time
- Pagination for boards >500 items using `items_page` cursor.
- Add caching + rate-limit protection.
- Robust sector mapping dictionary across boards.
- Unit tests covering analytics edge cases and date/amount parsing.
- Observability: structured logs, timings, error tags; `/metrics` endpoint.
- Role-based question templates (CEO, COO) with tailored insight prompts.

## Architecture Overview
- FastAPI `/ask` endpoint orchestrates: interpret → fetch monday → clean → analyze → summarize.
- Monday client: GraphQL `boards(ids: [ID!]) { columns {id title} items_page { items { column_values { id text value type } } } }`.
- Data cleaning normalizes money/date strings and fills missing sectors.
- Analytics computes pipeline, revenue, active project value, sector breakdown.
- AI agent summarizes results and caveats for exec readability.

## Monday.com Configuration (for reviewers)
- Import provided CSVs into two boards: Deals and Work Orders.
- Include columns for Status, Sector (if available), Amount/Value, and relevant dates.
- Use board IDs from their URLs in `.env`.

