const API = "https://financial-kpi-monitor.onrender.com";;

let allCompareData = [];
let activeTicker = "AAPL";
let charts = {};

// ── Boot ──────────────────────────────────────────────────────────────────────
async function init() {
  const [companies, compareData] = await Promise.all([
    fetchJSON("/companies"),
    fetchJSON("/compare"),
  ]);
  allCompareData = compareData;
  renderTickerTabs(companies);
  renderCompareTable(compareData);
  document.getElementById("last-updated").textContent =
    "Updated " + new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  await selectTicker(activeTicker, companies);

  // Enter key triggers search
  document.getElementById("ticker-input").addEventListener("keydown", e => {
    if (e.key === "Enter") handleSearch();
  });
}

// ── Search ────────────────────────────────────────────────────────────────────
async function handleSearch() {
  const input = document.getElementById("ticker-input");
  const btn   = document.getElementById("search-btn");
  const status = document.getElementById("search-status");
  const ticker = input.value.trim().toUpperCase();

  if (!ticker) return;

  // UI: loading state
  btn.disabled = true;
  btn.textContent = "Fetching...";
  status.className = "search-status loading";
  status.textContent = `⟳ Fetching data for ${ticker} from Yahoo Finance...`;

  try {
    const res = await fetch(`${API}/fetch/${ticker}`, { method: "POST" });
    const data = await res.json();

    if (!res.ok) {
      status.className = "search-status error";
      status.textContent = `✗ ${data.detail || "Something went wrong"}`;
      return;
    }

    status.className = "search-status success";
    status.textContent = `✓ ${data.company} loaded — ${data.years_loaded} years of data in ${data.elapsed_seconds}s`;

    // Refresh companies + compare table
    const [companies, compareData] = await Promise.all([
      fetchJSON("/companies"),
      fetchJSON("/compare"),
    ]);
    allCompareData = compareData;
    renderTickerTabs(companies);
    renderCompareTable(compareData);

    // Switch to the new ticker
    await selectTicker(ticker);
    input.value = "";

  } catch (err) {
    status.className = "search-status error";
    status.textContent = `✗ Could not connect to API. Is it running?`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyse";
  }
}

// ── Fetch helper ──────────────────────────────────────────────────────────────
async function fetchJSON(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error(`API error: ${path}`);
  return res.json();
}

// ── Ticker tabs ───────────────────────────────────────────────────────────────
function renderTickerTabs(companies) {
  const container = document.getElementById("ticker-tabs");
  container.innerHTML = companies.map(c => `
    <button class="ticker-tab ${c.ticker === activeTicker ? "active" : ""}"
            onclick="selectTicker('${c.ticker}')">
      ${c.ticker}
    </button>
  `).join("");
}

async function selectTicker(ticker) {
  activeTicker = ticker;
  document.querySelectorAll(".ticker-tab").forEach(btn => {
    btn.classList.toggle("active", btn.textContent.trim() === ticker);
  });
  document.querySelectorAll("#compare-body tr").forEach(row => {
    row.classList.toggle("active-row", row.dataset.ticker === ticker);
  });

  const [company, kpis, trends] = await Promise.all([
    fetchJSON(`/companies/${ticker}`),
    fetchJSON(`/kpis/${ticker}/latest`),
    fetchJSON(`/trends/${ticker}`),
  ]);

  renderHero(company, kpis);
  renderKPIGrid(kpis);
  renderCharts(trends);
}

// ── Hero ──────────────────────────────────────────────────────────────────────
function renderHero(company, kpis) {
  document.getElementById("company-name").textContent = company.short_name || company.ticker;
  document.getElementById("company-sector").textContent = company.sector || "";
  document.getElementById("kpi-year").textContent = kpis.year;

  const heroItems = [
    { label: "Net Margin",     value: kpis.net_margin,         suffix: "%" },
    { label: "Revenue Growth", value: kpis.revenue_growth_yoy, suffix: "%" },
    { label: "ROE",            value: kpis.return_on_equity,   suffix: "%" },
    { label: "Current Ratio",  value: kpis.current_ratio,      suffix: "x" },
  ];

  document.getElementById("hero-kpis").innerHTML = heroItems.map(item => {
    const val = item.value != null ? item.value.toFixed(2) + item.suffix : "—";
    const cls = item.value == null ? "" : item.value >= 0 ? "positive" : "negative";
    return `
      <div class="hero-kpi-card">
        <div class="kpi-val ${cls}">${val}</div>
        <div class="kpi-name">${item.label}</div>
      </div>`;
  }).join("");
}

// ── KPI Grid ──────────────────────────────────────────────────────────────────
const KPI_META = [
  ["gross_margin",             "Gross Margin",          "Profitability", "%",  true ],
  ["operating_margin",         "Operating Margin",      "Profitability", "%",  true ],
  ["net_margin",               "Net Margin",            "Profitability", "%",  true ],
  ["ebitda_margin",            "EBITDA Margin",         "Profitability", "%",  true ],
  ["revenue_growth_yoy",       "Revenue Growth YoY",    "Growth",        "%",  true ],
  ["net_income_growth_yoy",    "Net Income Growth YoY", "Growth",        "%",  true ],
  ["current_ratio",            "Current Ratio",         "Liquidity",     "x",  true ],
  ["quick_ratio",              "Quick Ratio",           "Liquidity",     "x",  true ],
  ["debt_to_equity",           "Debt / Equity",         "Leverage",      "x",  false],
  ["debt_to_assets",           "Debt / Assets",         "Leverage",      "x",  false],
  ["return_on_assets",         "Return on Assets",      "Efficiency",    "%",  true ],
  ["return_on_equity",         "Return on Equity",      "Efficiency",    "%",  true ],
  ["operating_cashflow_margin","Operating CF Margin",   "Cash Flow",     "%",  true ],
  ["free_cashflow_margin",     "Free CF Margin",        "Cash Flow",     "%",  true ],
];

function renderKPIGrid(kpis) {
  document.getElementById("kpi-grid").innerHTML = KPI_META.map(([key, label, cat, suffix, higherBetter]) => {
    const raw = kpis[key];
    let valStr, cls;
    if (raw == null) { valStr = "—"; cls = "null"; }
    else {
      valStr = raw.toFixed(2) + suffix;
      cls = higherBetter ? (raw >= 0 ? "good" : "bad") : (raw <= 1 ? "good" : "bad");
    }
    return `
      <div class="kpi-card">
        <div class="kpi-category">${cat}</div>
        <div class="kpi-name">${label}</div>
        <div class="kpi-value ${cls}">${valStr}</div>
      </div>`;
  }).join("");
}

// ── Charts ────────────────────────────────────────────────────────────────────
const CHART_DEFAULTS = {
  responsive: true,
  plugins: { legend: { labels: { color: "#9ba3c0", font: { size: 11 } } } },
  scales: {
    x: { ticks: { color: "#6b7394" }, grid: { color: "#1c2030" } },
    y: { ticks: { color: "#6b7394" }, grid: { color: "#1c2030" } },
  },
};

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function makeChart(id, config) {
  destroyChart(id);
  charts[id] = new Chart(document.getElementById(id).getContext("2d"), config);
}

function renderCharts(trends) {
  const years = trends.map(t => t.year);
  const c = { gross: "#4f8ef7", net: "#38d9a9", op: "#f5a623", roe: "#38d9a9", fcf: "#f06595" };

  makeChart("chart-margins", {
    type: "line",
    data: { labels: years, datasets: [
      { label: "Gross Margin",     data: trends.map(t => t.gross_margin),     borderColor: c.gross, tension: 0.3, fill: false },
      { label: "Net Margin",       data: trends.map(t => t.net_margin),       borderColor: c.net,   tension: 0.3, fill: false },
      { label: "Operating Margin", data: trends.map(t => t.operating_margin), borderColor: c.op,    tension: 0.3, fill: false },
    ]},
    options: CHART_DEFAULTS,
  });

  makeChart("chart-growth", {
    type: "bar",
    data: { labels: years, datasets: [{
      label: "Revenue Growth %",
      data: trends.map(t => t.revenue_growth_yoy),
      backgroundColor: trends.map(t => t.revenue_growth_yoy >= 0 ? "#4f8ef760" : "#f0659560"),
      borderColor:     trends.map(t => t.revenue_growth_yoy >= 0 ? "#4f8ef7"   : "#f06595"),
      borderWidth: 2, borderRadius: 4,
    }]},
    options: CHART_DEFAULTS,
  });

  makeChart("chart-roe", {
    type: "line",
    data: { labels: years, datasets: [{
      label: "ROE %", data: trends.map(t => t.return_on_equity),
      borderColor: c.roe, backgroundColor: c.roe + "20", tension: 0.3, fill: true,
    }]},
    options: CHART_DEFAULTS,
  });

  makeChart("chart-fcf", {
    type: "line",
    data: { labels: years, datasets: [{
      label: "FCF Margin %", data: trends.map(t => t.free_cashflow_margin),
      borderColor: c.fcf, backgroundColor: c.fcf + "20", tension: 0.3, fill: true,
    }]},
    options: CHART_DEFAULTS,
  });
}

// ── Compare Table ─────────────────────────────────────────────────────────────
function renderCompareTable(data) {
  const keys = ["gross_margin","net_margin","revenue_growth_yoy",
                "return_on_equity","current_ratio","debt_to_equity","free_cashflow_margin"];
  const higherBetter = {
    gross_margin: true, net_margin: true, revenue_growth_yoy: true,
    return_on_equity: true, current_ratio: true, debt_to_equity: false, free_cashflow_margin: true,
  };
  const best = {}, worst = {};
  keys.forEach(k => {
    const vals = data.map(d => d[k]).filter(v => v != null);
    best[k]  = higherBetter[k] ? Math.max(...vals) : Math.min(...vals);
    worst[k] = higherBetter[k] ? Math.min(...vals) : Math.max(...vals);
  });

  document.getElementById("compare-body").innerHTML = data.map(row => `
    <tr data-ticker="${row.ticker}" onclick="selectTicker('${row.ticker}')">
      <td>${row.short_name || row.ticker}</td>
      ${keys.map(k => {
        const v = row[k];
        const cls = v == null ? "" : v === best[k] ? "best" : v === worst[k] ? "worst" : "";
        const display = v != null ? v.toFixed(2) + (k === "current_ratio" || k === "debt_to_equity" ? "x" : "%") : "—";
        return `<td class="${cls}">${display}</td>`;
      }).join("")}
    </tr>`).join("");
}

// ── Start ─────────────────────────────────────────────────────────────────────
init().catch(err => console.error("Init failed:", err));