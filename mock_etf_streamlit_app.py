"""
Mock Thematic ETF Tracker

Run locally:
  pip install streamlit yfinance pandas plotly
  streamlit run mock_etf_streamlit_app.py

What it does:
- Builds a synthetic ETF from the tickers below.
- Defaults to equal-dollar weighting by ticker at the selected start date.
- Preserves the tier structure as sleeves.
- Tracks historical value using adjusted close data from Yahoo Finance via yfinance.
- Defaults the historical start date to 2024-01-01 and starts the basket with tickers that had data at that date.

This is for research/watchlist use, not investment advice.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

TIERS: Dict[str, List[str]] = {
    "Tier 1 — Pre-revenue speculative, highest canary value": [
        "OKLO", "SMR", "NNE", "LEU", "RGTI", "QBTS", "QUBT", "IONQ"
    ],
    "Tier 2 — Specialty silicon/optical micro-caps, AXTI archetype": [
        "AXTI", "POET", "AAOI", "MVIS", "KOPN", "AMBA", "WOLF", "AEHR", "NVTS"
    ],
    "Tier 3 — Crypto-to-AI pivots, no AI revenue yet": [
        "KEEL", "BTDR", "CLSK", "HIVE", "RIOT", "MARA", "CIFR", "WULF", "CORZ"
    ],
    "Tier 4 — AI-tagged small-cap software, valuation/revenue mismatch": [
        "BBAI", "SOUN", "AI", "TEM", "SERV", "SYM", "PATH"
    ],
    "Tier 5 — AI-software extreme multiples, real revenue": [
        "PLTR", "APP", "SNOW", "NET", "DDOG", "MDB", "CFLT", "ESTC", "GTLB", "FROG", "TTD",
        "CRWD", "NOW", "ZS"
    ],
    "Tier 6 — AI infra real-but-stretched, AI-priced multiples": [
        "APLD", "IREN", "CRWV", "NBIS", "CLS"
    ],
    "Tier 7 — Silicon photonics/optical established": [
        "LITE", "COHR", "TSEM", "CRDO", "ALAB", "CIEN", "MTSI"
    ],
    "Tier 8 — Memory cycle": [
        "MU", "WDC", "STX", "SNDK," "EWY"
    ],
    "Tier 9 — AI-utility plays, contracted revenue cushion": [
        "VST", "CEG", "TLN", "NRG", "NEE", "GEV", "D"
    ],
    "Tier 10 — Server integrators, track NVIDIA cadence": [
        "SMCI", "DELL", "HPE", "PSTG"
    ],
    "Tier 11 — Cooling/power/networking infrastructure, backlog cushion": [
        "VRT", "ETN", "MOD", "AAON", "PH", "TT", "ANET", "POWL", "HUBB"
    ],
    "Tier 12 — Data center REITs, lease-contract support": [
        "DLR", "EQIX", "IRM"
    ],
    "Tier 13 — Semi cap equipment, diversified end-markets": [
        "AMAT", "LRCX", "KLAC", "NVMI", "ONTO", "ASML", "TER"
    ],
    "Tier 14 — The Champ Chips": [
        "NVDA", "AVGO", "AMD", "MRVL", "ARM", "INTC", "MPWR", "QCOM"
    ],
    "Tier 15 — Hyperscalers": [
        "AMZN", "GOOGL", "META", "MSFT", "ORCL"
    ],
}


ALL_TICKERS = [ticker for tickers in TIERS.values() for ticker in tickers]
TICKER_TO_TIER = {ticker: tier for tier, tickers in TIERS.items() for ticker in tickers}


@dataclass
class BasketResult:
    prices: pd.DataFrame
    shares: pd.Series
    value_by_ticker: pd.DataFrame
    value_by_tier: pd.DataFrame
    total_value: pd.Series
    start_prices: pd.Series
    included_tickers: List[str]
    excluded_tickers: List[str]


st.set_page_config(page_title="Mock ETF Tracker for AI-fueled ticker cohorts", page_icon="📈", layout="wide")

st.title("Mock ETF Tracker for AI-fueled ticker cohorts")

DEFAULT_SUBTITLE = (
    "As much as I love AI, all bubbles break, usually in tiers/cohorts. Tiers are organized in the order they are expect to fall apart."
    "This app builds a synthetic equal-dollar basket from user-defined AI-related ticker cohorts. "
    "It downloads adjusted historical prices, creates fixed-share holdings from the selected start date, "
    "tracks total basket value, compares cohort sleeves, displays current sleeve weights, and exports the underlying price data. "
    "Research/watchlist tool only; not investment advice."
)

st.caption(DEFAULT_SUBTITLE)


@st.cache_data(show_spinner=False, ttl=60 * 60)
def download_one_ticker(ticker: str, start: dt.date, end: dt.date) -> pd.Series:
    """Download adjusted close history. Special handling for KEEL/BITF history."""
    end_plus_one = end + dt.timedelta(days=1)

    def fetch(symbol: str) -> pd.Series:
        data = yf.download(
            symbol,
            start=start.isoformat(),
            end=end_plus_one.isoformat(),
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if data.empty:
            return pd.Series(dtype="float64", name=ticker)

        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close.name = ticker
        close.index = pd.to_datetime(close.index).tz_localize(None)
        return close.dropna()

    if ticker == "KEEL":
        keel = fetch("KEEL")
        bitf = fetch("BITF")
        combined = pd.concat([bitf, keel]).sort_index()
        combined = combined[~combined.index.duplicated(keep="last")]
        combined.name = "KEEL"
        return combined

    return fetch(ticker)


@st.cache_data(show_spinner=False, ttl=60 * 60)
def download_prices(tickers: Tuple[str, ...], start: dt.date, end: dt.date) -> pd.DataFrame:
    series = []
    for ticker in tickers:
        s = download_one_ticker(ticker, start, end)
        if not s.empty:
            series.append(s)

    if not series:
        return pd.DataFrame()

    prices = pd.concat(series, axis=1).sort_index()
    prices = prices.ffill()
    return prices


def build_basket(
    prices: pd.DataFrame,
    selected_tickers: List[str],
    base_value: float,
    weighting_mode: str,
) -> BasketResult:
    clean = prices[selected_tickers].copy()

    # Start on the first trading day in the requested window.
    # Do NOT wait for every ticker to have history. Newer IPOs / ticker changes
    # would otherwise move the whole basket start date forward.
    clean = clean.dropna(how="all").ffill()
    if clean.empty:
        raise ValueError("No usable prices found for the selected basket.")

    actual_start_date = clean.index.min()
    start_row = clean.loc[actual_start_date]

    # Include only tickers that already had price data at the basket start.
    # This preserves a true equal-dollar basket from the beginning date.
    included = start_row.dropna().index.tolist()
    excluded = [t for t in selected_tickers if t not in included]

    if not included:
        raise ValueError("No selected tickers had usable prices at the basket start date.")

    clean = clean[included].loc[actual_start_date:].ffill()
    start_prices = clean.iloc[0]

    if weighting_mode == "Equal weight each ticker":
        allocation = pd.Series(base_value / len(included), index=included)
    else:
        active_tiers = sorted({TICKER_TO_TIER[t] for t in included})
        tier_allocation = base_value / len(active_tiers)
        allocation = pd.Series(index=included, dtype="float64")
        for tier in active_tiers:
            tier_tickers = [t for t in included if TICKER_TO_TIER[t] == tier]
            allocation.loc[tier_tickers] = tier_allocation / len(tier_tickers)

    shares = allocation / start_prices
    value_by_ticker = clean.multiply(shares, axis=1)
    total_value = value_by_ticker.sum(axis=1)

    tier_frames = []
    for tier in TIERS:
        tier_tickers = [t for t in value_by_ticker.columns if TICKER_TO_TIER[t] == tier]
        if tier_tickers:
            tier_frames.append(value_by_ticker[tier_tickers].sum(axis=1).rename(tier))
    value_by_tier = pd.concat(tier_frames, axis=1)

    return BasketResult(
        prices=clean,
        shares=shares,
        value_by_ticker=value_by_ticker,
        value_by_tier=value_by_tier,
        total_value=total_value,
        start_prices=start_prices,
        included_tickers=included,
        excluded_tickers=excluded,
    )


with st.sidebar:
    st.header("Basket setup")
    base_value = st.number_input("Starting basket value", min_value=100.0, value=10_000.0, step=1_000.0)

    today = dt.date.today()
    default_start = dt.date(2022, 10, 14)
    start_date = st.date_input("Historical start date", value=default_start)
    end_date = st.date_input("Historical end date", value=today)

    weighting_mode = st.radio(
        "Weighting method",
        ["Equal weight each ticker", "Equal weight each tier"],
        index=0,
    )

    st.header("Include tiers")

    # Initialize editable tier checkbox state once.
    for tier in TIERS:
        state_key = f"tier_selected_{tier}"
        if state_key not in st.session_state:
            st.session_state[state_key] = True

    bulk_col1, bulk_col2 = st.columns(2)
    with bulk_col1:
        if st.button("Select all tiers", use_container_width=True):
            for tier in TIERS:
                st.session_state[f"tier_selected_{tier}"] = True
    with bulk_col2:
        if st.button("Select no tiers", use_container_width=True):
            for tier in TIERS:
                st.session_state[f"tier_selected_{tier}"] = False

    selected_tiers = []
    st.caption("Use the buttons for bulk changes, then adjust individual tiers below.")

    for tier in TIERS:
        checked = st.checkbox(
            tier,
            key=f"tier_selected_{tier}",
        )
        if checked:
            selected_tiers.append(tier)

    selected_tickers = [ticker for tier in selected_tiers for ticker in TIERS[tier]]

    st.header("Optional exclusions")
    excluded = st.multiselect("Remove tickers", selected_tickers, default=[])
    selected_tickers = [t for t in selected_tickers if t not in excluded]


if not selected_tickers:
    st.warning("Select at least one ticker.")
    st.stop()

if start_date >= end_date:
    st.warning("Start date must be before end date.")
    st.stop()

with st.spinner("Downloading price history..."):
    prices = download_prices(tuple(selected_tickers), start_date, end_date)

if prices.empty:
    st.error("No price data returned. Try a different date range or fewer tickers.")
    st.stop()

try:
    basket = build_basket(prices, selected_tickers, base_value, weighting_mode)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

latest_value = basket.total_value.iloc[-1]
start_value = basket.total_value.iloc[0]
absolute_return = latest_value - start_value
percent_return = latest_value / start_value - 1

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current mock ETF value", f"${latest_value:,.2f}", f"{percent_return:.2%}")
c2.metric("Starting value", f"${start_value:,.2f}")
c3.metric("Dollar P/L", f"${absolute_return:,.2f}")
c4.metric("Included tickers", len(basket.included_tickers))

if basket.excluded_tickers:
    st.warning(
        "Excluded because they did not have price data at the basket start date: "
        + ", ".join(basket.excluded_tickers)
    )

st.subheader("Synthetic ETF value")
plot_df = basket.total_value.rename("Mock ETF value").reset_index().rename(columns={"index": "Date"})
fig = px.line(plot_df, x="Date", y="Mock ETF value")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Tier sleeves")
tier_plot = basket.value_by_tier.reset_index()
tier_plot = tier_plot.rename(columns={tier_plot.columns[0]: "Date"})
tier_long = tier_plot.melt(id_vars="Date", var_name="Tier", value_name="Value")
fig_tier = px.line(tier_long, x="Date", y="Value", color="Tier")
st.plotly_chart(fig_tier, use_container_width=True)

st.subheader("Tier sleeves — faceted view")
st.caption("Each selected sleeve gets its own chart; charts wrap three per row.")
facet_rows = max(1, (basket.value_by_tier.shape[1] + 2) // 3)
fig_tier_faceted = px.line(
    tier_long,
    x="Date",
    y="Value",
    facet_col="Tier",
    facet_col_wrap=3,
    height=max(420, 280 * facet_rows),
)
# Force each facet to use its own independent y-axis scale.
fig_tier_faceted.update_yaxes(matches=None, showticklabels=True)
for axis_name in fig_tier_faceted.layout:
    if axis_name.startswith("yaxis"):
        fig_tier_faceted.layout[axis_name].matches = None

fig_tier_faceted.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
st.plotly_chart(fig_tier_faceted, use_container_width=True)

st.subheader("Current sleeve weights")
latest_tiers = basket.value_by_tier.iloc[-1].sort_values(ascending=False)
weights = (latest_tiers / latest_tiers.sum()).rename("Weight").reset_index()
weights.columns = ["Tier", "Weight"]
fig_weights = px.bar(weights, x="Tier", y="Weight")
st.plotly_chart(fig_weights, use_container_width=True)

st.subheader("Holdings")
holdings = pd.DataFrame({
    "Tier": [TICKER_TO_TIER[t] for t in basket.included_tickers],
    "Start price": basket.start_prices,
    "Shares held": basket.shares,
    "Latest price": basket.prices.iloc[-1],
    "Latest value": basket.value_by_ticker.iloc[-1],
})
holdings["Latest weight"] = holdings["Latest value"] / holdings["Latest value"].sum()
holdings["Ticker return"] = holdings["Latest price"] / holdings["Start price"] - 1
holdings = holdings.sort_values("Latest value", ascending=False)
st.dataframe(
    holdings.style.format({
        "Start price": "${:,.2f}",
        "Shares held": "{:,.4f}",
        "Latest price": "${:,.2f}",
        "Latest value": "${:,.2f}",
        "Latest weight": "{:.2%}",
        "Ticker return": "{:.2%}",
    }),
    use_container_width=True,
)

st.subheader("Individual ticker charts")
chart_tickers = st.multiselect(
    "Select holdings to chart",
    options=holdings.index.tolist(),
    default=holdings.index.tolist()[: min(9, len(holdings.index))],
)

chart_mode = st.radio(
    "Chart type",
    ["Indexed price return", "Price", "Holding value"],
    horizontal=True,
)

if chart_tickers:
    if chart_mode == "Indexed price return":
        chart_data = basket.prices[chart_tickers] / basket.prices[chart_tickers].iloc[0] * 100
        y_label = "Indexed value, start = 100"
    elif chart_mode == "Price":
        chart_data = basket.prices[chart_tickers]
        y_label = "Price"
    else:
        chart_data = basket.value_by_ticker[chart_tickers]
        y_label = "Holding value"

    chart_df = chart_data.reset_index().rename(columns={"index": "Date"})
    chart_long = chart_df.melt(id_vars="Date", var_name="Ticker", value_name=y_label)
    fig_tickers = px.line(chart_long, x="Date", y=y_label, color="Ticker")
    st.plotly_chart(fig_tickers, use_container_width=True)
else:
    st.info("Select one or more holdings to view individual charts.")

st.download_button(
    "Download holdings CSV",
    holdings.to_csv(index=True).encode("utf-8"),
    file_name="mock_etf_holdings.csv",
    mime="text/csv",
)

st.download_button(
    "Download value history CSV",
    basket.total_value.rename("mock_etf_value").to_csv().encode("utf-8"),
    file_name="mock_etf_value_history.csv",
    mime="text/csv",
)

# Long-format export of underlying price data.
# reset_index() may name the date column "index", "Date", or something else
# depending on the DataFrame index name, so rename the first column explicitly.
underlying_prices_wide = basket.prices.reset_index()
underlying_prices_wide = underlying_prices_wide.rename(
    columns={underlying_prices_wide.columns[0]: "date"}
)

underlying_prices = underlying_prices_wide.melt(
    id_vars="date",
    var_name="ticker",
    value_name="closing_price",
)
underlying_prices["cohort"] = underlying_prices["ticker"].map(TICKER_TO_TIER)
underlying_prices = underlying_prices[["date", "ticker", "cohort", "closing_price"]]
underlying_prices = underlying_prices.sort_values(["date", "cohort", "ticker"])
underlying_prices["date"] = pd.to_datetime(underlying_prices["date"]).dt.strftime("%Y-%m-%d")

st.download_button(
    "Download underlying price data CSV",
    underlying_prices.to_csv(index=False).encode("utf-8"),
    file_name="mock_etf_underlying_prices_by_cohort.csv",
    mime="text/csv",
)
