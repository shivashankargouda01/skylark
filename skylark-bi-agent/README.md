# Skylark BI Agent

A lightweight FastAPI-based AI business analyst that connects to monday.com, cleans data with pandas, applies business analytics, and returns executive-style insights.

## Setup

1. Create a virtual environment (Windows):
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

2. Install dependencies:
   ```cmd
   pip install fastapi uvicorn requests pandas python-dotenv openai
   pip freeze > requirements.txt
   ```

3. Create `.env` in project root:
   ```
   MONDAY_API_KEY=your_key
   OPENAI_API_KEY=your_key
   DEALS_BOARD_ID=<deals_board_id_from_url>
   WORK_ORDERS_BOARD_ID=<work_orders_board_id_from_url>
   ```

## Run locally

```cmd
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs to try the `/ask` endpoint.

### Health
`GET /health` returns `{ "status": "ok" }` for smoke tests.

## Deployment (Render)

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
- Add environment variables in Render dashboard.

### Monday.com configuration
- Import CSVs to two boards (Deals, Work Orders).
- Ensure columns like Status, Sector (if present), Value/Amount, and dates exist.
- Copy board IDs from their URLs into `.env`.

### Architecture Overview
- FastAPI `/ask` orchestrates:
   1. Interpret question (OpenAI or heuristic)
   2. Fetch Monday data via GraphQL
   3. Clean with pandas
   4. Run analytics
   5. Generate executive summary

### Example Questions
- "What’s our Q1 pipeline value in healthcare?"
- "Total revenue from won deals last quarter"
- "Active projects value in operations"

## Decision Log

### Assumptions
- Pipeline = non-won deals
- Revenue = won deals
- Sector normalized

### Tradeoffs
- No caching initially
- Focused on core metrics

### Leadership Updates
- Implemented weekly executive summary across pipeline + operations.
See `DECISION_LOG.md` for full assumptions, tradeoffs, and future work.
