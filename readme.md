# Financial KPI Monitor

A full-stack data analysis project that pulls real financial data for major tech companies, computes 14 financial KPIs, and visualizes them on an interactive dashboard.

**Stack:** Python · yfinance · Pandas · SQLite · FastAPI · HTML/CSS/JS · Chart.js

---

## Features

- **Real financial data** — income statements, balance sheets, and cash flows via yfinance (AAPL, MSFT, GOOGL, AMZN, TSLA)
- **14 KPIs computed** across Profitability, Growth, Liquidity, Leverage, Efficiency, and Cash Flow
- **Interactive dashboard** — company switcher, KPI cards, 4 trend charts, comparison table
- **REST API** — 6 FastAPI endpoints serving JSON
- **SQLite storage** — structured relational schema with 4 tables

---

## Project Structure

```
financial-kpi-monitor/
├── data/
│   ├── raw/                  # Raw JSON pulled from yfinance
│   ├── processed/            # Cleaned CSVs + kpis.csv
│   └── financial_kpi.db      # SQLite database
├── src/
│   ├── etl/
│   │   ├── extract.py        # Pull data from yfinance
│   │   ├── transform.py      # Clean + normalize into DataFrames
│   │   └── load.py           # Insert into SQLite
│   ├── kpi/
│   │   └── calculations.py   # Compute all 14 KPIs
│   ├── db/
│   │   ├── models.py         # Create SQLite tables
│   │   └── database.py       # DB connection helper
│   └── api/
│       └── main.py           # FastAPI app
├── frontend/
│   ├── index.html            # Dashboard UI
│   ├── style.css             # Dark theme styles
│   └── script.js             # API calls + Chart.js rendering
├── run_pipeline.py           # Run full ETL + KPI pipeline in one command
└── requirements.txt
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full pipeline (extract → transform → load → KPIs)
python run_pipeline.py

# 3. Start the API
python -m uvicorn src.api.main:app --reload

# 4. Open the dashboard
# Open frontend/index.html in your browser
```

---

## KPIs Computed

| Category | KPIs |
|---|---|
| Profitability | Gross Margin, Operating Margin, Net Margin, EBITDA Margin |
| Growth | Revenue Growth YoY%, Net Income Growth YoY% |
| Liquidity | Current Ratio, Quick Ratio |
| Leverage | Debt-to-Equity, Debt-to-Assets |
| Efficiency | Return on Assets (ROA), Return on Equity (ROE) |
| Cash Flow | Operating CF Margin, Free CF Margin |

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /companies` | List all companies |
| `GET /companies/{ticker}` | Single company info |
| `GET /kpis/{ticker}` | All years of KPIs for a company |
| `GET /kpis/{ticker}/latest` | Latest year KPIs |
| `GET /compare` | All companies side by side |
| `GET /trends/{ticker}` | Year-over-year trend data |

Interactive docs at `http://127.0.0.1:8000/docs`

---

## Refreshing Data

To pull fresh data at any time:

```bash
python run_pipeline.py            # refresh all companies
python run_pipeline.py AAPL MSFT  # refresh specific tickers
```

---

*Data sourced via yfinance · For educational and portfolio purposes only*