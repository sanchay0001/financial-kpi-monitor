"""
Layer 4: KPI Calculations
Reads from SQLite, computes financial KPIs per company per year,
and saves results to data/processed/kpis.csv + kpis table in SQLite.

KPIs calculated:
  Profitability  : gross_margin, operating_margin, net_margin, ebitda_margin
  Growth         : revenue_growth_yoy, net_income_growth_yoy
  Liquidity      : current_ratio, quick_ratio
  Leverage       : debt_to_equity, debt_to_assets
  Efficiency     : return_on_assets (ROA), return_on_equity (ROE)
  Cash Flow      : operating_cashflow_margin, free_cashflow_margin

Run directly:  python src/kpi/calculations.py
"""

import sqlite3
import math
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "financial_kpi.db"
PROCESSED_DIR = ROOT / "data" / "processed"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_div(numerator, denominator, scale=1):
    """Divide safely; return None if denominator is 0 or either value is None."""
    try:
        if numerator is None or denominator is None:
            return None
        if math.isnan(numerator) or math.isnan(denominator):
            return None
        if denominator == 0:
            return None
        return round((numerator / denominator) * scale, 4)
    except Exception:
        return None


def _pct_change(current, previous):
    """Year-over-year % change."""
    if current is None or previous is None or previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 2)


def load_data() -> pd.DataFrame:
    """Join all three financial statement tables into one wide DataFrame."""
    conn = get_connection()
    query = """
        SELECT
            i.ticker,
            i.year,
            i.total_revenue,
            i.gross_profit,
            i.operating_income,
            i.net_income,
            i.ebitda,
            b.total_assets,
            b.total_liabilities,
            b.stockholders_equity,
            b.current_assets,
            b.current_liabilities,
            b.cash,
            b.inventory,
            b.total_debt,
            c.operating_cashflow,
            c.capex,
            c.free_cashflow
        FROM income_stmt i
        LEFT JOIN balance_sheet b ON i.ticker = b.ticker AND i.year = b.year
        LEFT JOIN cashflow c      ON i.ticker = c.ticker AND i.year = c.year
        ORDER BY i.ticker, i.year DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def compute_kpis(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("year", ascending=False).reset_index(drop=True)

        for i, row in group.iterrows():
            r = dict(row)
            prev = dict(group.iloc[i + 1]) if i + 1 < len(group) else {}

            kpi = {
                "ticker": ticker,
                "year": int(r["year"]),

                # --- Profitability (%) ---
                "gross_margin":        _safe_div(r["gross_profit"],      r["total_revenue"], 100),
                "operating_margin":    _safe_div(r["operating_income"],  r["total_revenue"], 100),
                "net_margin":          _safe_div(r["net_income"],        r["total_revenue"], 100),
                "ebitda_margin":       _safe_div(r["ebitda"],            r["total_revenue"], 100),

                # --- Growth (%) ---
                "revenue_growth_yoy":      _pct_change(r["total_revenue"], prev.get("total_revenue")),
                "net_income_growth_yoy":   _pct_change(r["net_income"],    prev.get("net_income")),

                # --- Liquidity (ratio) ---
                "current_ratio": _safe_div(r["current_assets"], r["current_liabilities"]),
                "quick_ratio":   _safe_div(
                    (r["current_assets"] or 0) - (r["inventory"] or 0),
                    r["current_liabilities"]
                ),

                # --- Leverage (ratio) ---
                "debt_to_equity": _safe_div(r["total_debt"],       r["stockholders_equity"]),
                "debt_to_assets": _safe_div(r["total_liabilities"], r["total_assets"]),

                # --- Efficiency (%) ---
                "return_on_assets": _safe_div(r["net_income"], r["total_assets"],       100),
                "return_on_equity": _safe_div(r["net_income"], r["stockholders_equity"], 100),

                # --- Cash Flow (%) ---
                "operating_cashflow_margin": _safe_div(r["operating_cashflow"], r["total_revenue"], 100),
                "free_cashflow_margin":      _safe_div(r["free_cashflow"],      r["total_revenue"], 100),
            }
            rows.append(kpi)

    return pd.DataFrame(rows)


def save_kpis(kpi_df: pd.DataFrame):
    # Save CSV
    csv_path = PROCESSED_DIR / "kpis.csv"
    kpi_df.to_csv(csv_path, index=False)
    print(f"Saved kpis.csv  ({len(kpi_df)} rows x {len(kpi_df.columns)} cols)")

    # Save to SQLite
    conn = get_connection()
    conn.execute("DROP TABLE IF EXISTS kpis")
    kpi_df.to_sql("kpis", conn, if_exists="replace", index=False)
    conn.commit()

    # Verify
    count = conn.execute("SELECT COUNT(*) FROM kpis").fetchone()[0]
    conn.close()
    print(f"Saved kpis table in SQLite  ({count} rows)")


def print_summary(kpi_df: pd.DataFrame):
    print("\n--- KPI Preview (latest year per company) ---")
    latest = kpi_df.groupby("ticker").first().reset_index()
    cols = ["ticker", "year", "gross_margin", "net_margin",
            "revenue_growth_yoy", "current_ratio", "return_on_equity"]
    print(latest[cols].to_string(index=False))


def run():
    print("Computing KPIs...")
    df = load_data()
    kpi_df = compute_kpis(df)
    save_kpis(kpi_df)
    print_summary(kpi_df)


if __name__ == "__main__":
    run()