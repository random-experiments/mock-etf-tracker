# Mock ETF Tracker

A Streamlit research tool for building and analyzing synthetic equal-weight thematic ETF baskets across AI, semiconductor, nuclear, infrastructure, crypto/AI, memory, and related tech cohorts. Designed for research and education — not investment advice.

## What it does

You pick a starting basket value, a date range, and which tiers to include. The app fetches historical adjusted close prices from Yahoo Finance, constructs a fixed-share portfolio, and visualizes how each tier and the basket as a whole have performed over time.

Key behaviors:
- **Equal weight** per ticker or per tier (your choice)
- **Staged entry** — tickers without a price at the start date hold cash until their first available close, avoiding forward-fill bias
- **Ticker splicing** — KEEL's history is spliced from its prior symbol BITF
- **Reference overlays** — Reference groups show equal-weighted indexed price performance, not dollar allocations; they never contribute to the basket value
- **Cohort ordering** — reorder sleeves by dependency chain, canary fragility, valuation risk, cyclical amplitude, or financing fragility

## Tiers

| # | Name | Representative tickers |
|---|------|------------------------|
| 1 | Pre-revenue speculative | OKLO, SMR, NNE, LEU, RGTI, QBTS, QUBT, IONQ |
| 2 | Specialty silicon / optical microcaps | AXTI, POET, AAOI, MVIS, KOPN, AMBA, WOLF, AEHR, NVTS |
| 3 | Crypto-to-AI pivots | KEEL, BTDR, CLSK, HIVE, RIOT, MARA, CIFR, WULF, CORZ |
| 4 | AI-tagged small-cap software | BBAI, SOUN, AI, TEM, SERV, SYM, PATH |
| 5 | AI software — extreme multiples | PLTR, APP, SNOW, NET, DDOG, MDB, ESTC, GTLB, FROG, TTD, CRWD, NOW, ZS |
| 6 | AI infra — real but stretched | APLD, IREN, CRWV, NBIS, CLS |
| 7 | Silicon photonics / optical | LITE, COHR, TSEM, CRDO, ALAB, CIEN, MTSI |
| 8 | Memory cycle | MU, WDC, STX, SNDK, EWY |
| 9 | Server integrators | SMCI, DELL, HPE, PSTG |
| 10 | Cooling / power / networking | VRT, ETN, MOD, AAON, PH, TT, ANET, POWL, HUBB |
| 11 | Data center REITs | DLR, EQIX, IRM |
| 12 | Semi equipment | AMAT, LRCX, KLAC, NVMI, ONTO, ASML, TER |
| 13 | The Champ Chips | NVDA, AVGO, AMD, MRVL, ARM, INTC, MPWR, QCOM |
| 14 | Hyperscalers | AMZN, GOOGL, META, MSFT, ORCL |

### Reference groups _(overlay only — not counted in basket)_

| Name | Tickers |
|------|---------|
| Parabolic Seven | AVGO, AMD, MU, DELL, MRVL, INTC, SNDK |
| Semi's ETFs | SMH, SOXX |
| Indices ETFs | QQQ, DIA, SPY, IWM |

## Charts and outputs

- **Synthetic ETF value** — total basket over time
- **Tier sleeves** — per-cohort comparison (indexed or dollar value), ordered by your chosen axis
- **Faceted view** — each tier in its own subplot with an independent y-axis
- **Current sleeve weights** — bar chart of latest tier allocations
- **Holdings table** — start price, latest price, shares, value, weight, return %
- **Ticker drill-down** — individual ticker charts with three modes: indexed price return, raw price, or holding value

Three CSVs are available for download: holdings, daily basket value history, and underlying prices by cohort (includes volume where available).

## Run locally

```bash
pip install -r requirements.txt
python -m streamlit run mock_etf_streamlit_app.py
```

App runs at `http://localhost:8501`.

## Dev container / Codespaces

The repo includes a `.devcontainer` config. Open in GitHub Codespaces or VSCode with the Dev Containers extension and everything installs and launches automatically — Streamlit starts on port 8501, which Codespaces forwards for you.

## Sidebar options

| Option | Default | Description |
|--------|---------|-------------|
| Starting basket value | $10,000 | Total capital allocated at start date |
| Date range | 2022-10-14 → today | Historical window for price data |
| Weighting | Equal weight per ticker | Alternatively, equal weight per tier |
| Staged entry | On | Hold cash for tickers until their first available price |
| Log scale | Off | Toggle log scale on all charts |
| Tier sleeve chart value | Indexed | Show tier sleeves as indexed returns (start = 100) or raw dollar values |
| Order cohort sleeves by | As defined | Reorder tiers by dependency chain, canary fragility, valuation risk, cyclical amplitude, or financing fragility |
| Custom session tickers | — | Add any symbol to any tier for the current session |
| Tier inclusion | All | Select/deselect tiers; bulk select all or none |
| Exclusions | — | Remove specific tickers after tier selection |

## Disclaimer

This tool is for research and educational purposes only. It does not constitute financial advice. All data is sourced from Yahoo Finance via `yfinance` and may contain errors or gaps.
