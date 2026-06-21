"""
Layer 5: FastAPI API + Frontend Server
Serves both the API and the frontend from a single process.

Run:  python -m uvicorn src.api.main:app --reload
Docs: http://127.0.0.1:8000/docs
App:  http://127.0.0.1:8000/
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DB_PATH    = Path(__file__).resolve().parents[2] / "data" / "financial_kpi.db"
FRONT_DIR  = Path(__file__).resolve().parents[2] / "frontend"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


app = FastAPI(
    title="Financial KPI Monitor",
    description="Real financial KPIs — search any ticker",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Serve frontend ─────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(FRONT_DIR / "index.html")


# Mount CSS/JS/assets — must come AFTER all API routes are defined
# (we register this at the end of the file)


# ── /fetch/{ticker} — on-demand pipeline ─────────────────────────────────────
@app.post("/fetch/{ticker}", summary="Fetch & analyse any ticker on demand")
def fetch_ticker(ticker: str):
    ticker = ticker.upper().strip()
    t0 = time.time()

    try:
        from src.etl.extract import fetch_company_financials, save_raw
        data = fetch_company_financials(ticker)
        if not data.get("income_stmt"):
            raise HTTPException(
                status_code=404,
                detail=f"No financial data found for '{ticker}'. Check the ticker symbol."
            )
        save_raw(ticker, data)

        from src.etl.transform import transform_ticker
        frames = transform_ticker(ticker)

        import pandas as pd
        from src.etl.load import load_companies, get_connection, _clean_val

        load_companies()

        inc = frames.get("income",   pd.DataFrame())
        bal = frames.get("balance",  pd.DataFrame())
        cf  = frames.get("cashflow", pd.DataFrame())

        def insert_df(df, table, columns):
            if df.empty:
                return
            conn = get_connection()
            cur  = conn.cursor()
            ph   = ", ".join(["?"] * len(columns))
            sql  = f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({ph})"
            for _, row in df.iterrows():
                cur.execute(sql, [_clean_val(row.get(c)) for c in columns])
            conn.commit()
            conn.close()

        insert_df(inc, "income_stmt", [
            "ticker","year","total_revenue","gross_profit",
            "operating_income","net_income","ebitda"
        ])
        insert_df(bal, "balance_sheet", [
            "ticker","year","total_assets","total_liabilities",
            "stockholders_equity","current_assets","current_liabilities",
            "cash","inventory","total_debt"
        ])
        insert_df(cf, "cashflow", [
            "ticker","year","operating_cashflow","capex","free_cashflow"
        ])

        from src.kpi.calculations import load_data, compute_kpis, save_kpis
        all_data    = load_data()
        ticker_data = all_data[all_data["ticker"] == ticker]
        if ticker_data.empty:
            raise HTTPException(status_code=422, detail="Data loaded but KPI computation failed.")
        kpi_df = compute_kpis(ticker_data)

        conn     = get_connection()
        existing = pd.read_sql("SELECT * FROM kpis WHERE ticker != ?", conn, params=[ticker])
        conn.close()
        save_kpis(pd.concat([existing, kpi_df], ignore_index=True))

        elapsed = round(time.time() - t0, 1)
        return {
            "success": True,
            "ticker": ticker,
            "company": data["info"].get("shortName", ticker),
            "sector":  data["info"].get("sector"),
            "years_loaded": len(inc),
            "elapsed_seconds": elapsed,
            "message": f"Successfully fetched and analysed {ticker} in {elapsed}s"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed for '{ticker}': {str(e)}")


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
    row  = conn.execute("SELECT * FROM companies WHERE ticker = ?", (ticker.upper(),)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    return dict(row)


# ── /kpis ─────────────────────────────────────────────────────────────────────
@app.get("/kpis", summary="All KPIs with optional filters")
def list_kpis(
    ticker: Optional[str] = Query(None),
    year:   Optional[int] = Query(None),
):
    sql, params = "SELECT * FROM kpis WHERE 1=1", []
    if ticker:
        sql += " AND ticker = ?"; params.append(ticker.upper())
    if year:
        sql += " AND year = ?";   params.append(year)
    sql += " ORDER BY ticker, year DESC"
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows_to_list(rows)


@app.get("/kpis/{ticker}", summary="All years of KPIs for one company")
def get_kpis_for_ticker(ticker: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM kpis WHERE ticker = ? ORDER BY year DESC", (ticker.upper(),)
    ).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No KPI data for '{ticker}'")
    return rows_to_list(rows)


@app.get("/kpis/{ticker}/latest", summary="Latest year KPIs for one company")
def get_latest_kpis(ticker: str):
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM kpis WHERE ticker = ? ORDER BY year DESC LIMIT 1", (ticker.upper(),)
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
        WHERE k.year = (SELECT MAX(year) FROM kpis k2 WHERE k2.ticker = k.ticker)
        ORDER BY k.ticker
    """).fetchall()
    conn.close()
    return rows_to_list(rows)


# ── /trends ───────────────────────────────────────────────────────────────────
@app.get("/trends/{ticker}", summary="Year-over-year trend data for charts")
def get_trends(ticker: str):
    conn = get_conn()
    rows = conn.execute("""
        SELECT k.year, k.gross_margin, k.net_margin, k.operating_margin,
               k.revenue_growth_yoy, k.return_on_equity, k.return_on_assets,
               k.current_ratio, k.free_cashflow_margin,
               i.total_revenue, i.net_income, i.gross_profit
        FROM kpis k
        JOIN income_stmt i ON k.ticker = i.ticker AND k.year = i.year
        WHERE k.ticker = ?
        ORDER BY k.year ASC
    """, (ticker.upper(),)).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No trend data for '{ticker}'")
    return rows_to_list(rows)


# ── Mount static files (CSS, JS) — must be last ───────────────────────────────
app.mount("/", StaticFiles(directory=str(FRONT_DIR)), name="static")