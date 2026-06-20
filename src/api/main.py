"""
Layer 5: FastAPI API
Exposes KPI and financial data as JSON endpoints for the frontend.

Run:  uvicorn src.api.main:app --reload
Docs: http://127.0.0.1:8000/docs

Endpoints:
  GET /companies              - list all companies with basic info
  GET /companies/{ticker}     - single company info
  GET /kpis                   - all KPIs (optional ?ticker=AAPL&year=2024)
  GET /kpis/{ticker}          - all years of KPIs for one company
  GET /kpis/{ticker}/latest   - most recent year's KPIs for one company
  GET /compare                - latest KPIs for all companies side-by-side
  GET /trends/{ticker}        - year-over-year trend data for charts
"""

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ── DB path ──────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "financial_kpi.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Financial KPI Monitor",
    description="Real financial KPIs for AAPL, MSFT, GOOGL, AMZN, TSLA",
    version="1.0.0",
)

# Allow frontend (any origin during dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── /companies ────────────────────────────────────────────────────────────────
@app.get("/companies", summary="List all companies")
def list_companies():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM companies ORDER BY ticker").fetchall()
    conn.close()
    return rows_to_list(rows)


@app.get("/companies/{ticker}", summary="Single company info")
def get_company(ticker: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM companies WHERE ticker = ?", (ticker.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    return dict(row)


# ── /kpis ─────────────────────────────────────────────────────────────────────
@app.get("/kpis", summary="All KPIs with optional filters")
def list_kpis(
    ticker: Optional[str] = Query(None, description="Filter by ticker e.g. AAPL"),
    year: Optional[int] = Query(None, description="Filter by year e.g. 2024"),
):
    sql = "SELECT * FROM kpis WHERE 1=1"
    params = []
    if ticker:
        sql += " AND ticker = ?"
        params.append(ticker.upper())
    if year:
        sql += " AND year = ?"
        params.append(year)
    sql += " ORDER BY ticker, year DESC"

    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows_to_list(rows)


@app.get("/kpis/{ticker}", summary="All years of KPIs for one company")
def get_kpis_for_ticker(ticker: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM kpis WHERE ticker = ? ORDER BY year DESC",
        (ticker.upper(),)
    ).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No KPI data for '{ticker}'")
    return rows_to_list(rows)


@app.get("/kpis/{ticker}/latest", summary="Latest year KPIs for one company")
def get_latest_kpis(ticker: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM kpis WHERE ticker = ? ORDER BY year DESC LIMIT 1",
        (ticker.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"No KPI data for '{ticker}'")
    return dict(row)


# ── /compare ──────────────────────────────────────────────────────────────────
@app.get("/compare", summary="Latest KPIs for all companies side by side")
def compare_companies():
    conn = get_conn()
    rows = conn.execute("""
        SELECT k.*, c.short_name, c.sector
        FROM kpis k
        JOIN companies c ON k.ticker = c.ticker
        WHERE k.year = (
            SELECT MAX(year) FROM kpis k2 WHERE k2.ticker = k.ticker
        )
        ORDER BY k.ticker
    """).fetchall()
    conn.close()
    return rows_to_list(rows)


# ── /trends ───────────────────────────────────────────────────────────────────
@app.get("/trends/{ticker}", summary="Year-over-year trend data for charts")
def get_trends(ticker: str):
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            k.year,
            k.gross_margin,
            k.net_margin,
            k.operating_margin,
            k.revenue_growth_yoy,
            k.return_on_equity,
            k.return_on_assets,
            k.current_ratio,
            k.free_cashflow_margin,
            i.total_revenue,
            i.net_income,
            i.gross_profit
        FROM kpis k
        JOIN income_stmt i ON k.ticker = i.ticker AND k.year = i.year
        WHERE k.ticker = ?
        ORDER BY k.year ASC
    """, (ticker.upper(),)).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No trend data for '{ticker}'")
    return rows_to_list(rows)


# ── health check ──────────────────────────────────────────────────────────────
@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "message": "Financial KPI Monitor API is running"}