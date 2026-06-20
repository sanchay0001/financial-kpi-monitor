"""
run_pipeline.py — Full pipeline orchestrator
Runs: Extract → Transform → Load → KPI Calculation in one command.

Usage:
    python run_pipeline.py            # refresh all tickers
    python run_pipeline.py AAPL MSFT  # refresh specific tickers only
"""

import sys
import time

def main():
    tickers = sys.argv[1:] if len(sys.argv) > 1 else None
    start = time.time()

    print("=" * 50)
    print("  Financial KPI Monitor — Pipeline")
    print("=" * 50)

    # Layer 1: Extract
    print("\n[1/4] Extracting raw data from yfinance...")
    from src.etl.extract import run as extract
    extract(tickers)

    # Layer 2: Transform
    print("\n[2/4] Transforming raw data...")
    from src.etl.transform import run as transform
    transform(tickers)

    # Layer 3: Load
    print("\n[3/4] Loading into SQLite...")
    from src.db.models import create_tables
    from src.etl.load import run as load
    create_tables()
    load()

    # Layer 4: KPIs
    print("\n[4/4] Computing KPIs...")
    from src.kpi.calculations import run as calc_kpis
    calc_kpis()

    elapsed = round(time.time() - start, 1)
    print(f"\n{'='*50}")
    print(f"  Pipeline complete in {elapsed}s")
    print(f"  Start the API:  python -m uvicorn src.api.main:app --reload")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()