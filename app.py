import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="TraderPrp Trading Scanner", page_icon="📈", layout="wide")

st.title("📈 TraderPrp")
st.caption("Indian cash-equity scanner | Intraday + Swing | Powered by your existing Colab workbook")

st.sidebar.header("Connect your scanner")
uploaded = st.sidebar.file_uploader(
    "Upload Trading_Scanner_Complete_Report.xlsx",
    type=["xlsx"],
    help="Upload the Excel report exported by your existing Google Colab scanner."
)

if uploaded is None:
    st.info("Upload your existing Trading_Scanner_Complete_Report.xlsx to load your scanner data.")
    st.markdown("""
    **How to connect your existing Colab scanner**
    1. Run your existing scanner in Google Colab.
    2. Export `Trading_Scanner_Complete_Report.xlsx`.
    3. Upload that workbook here using the sidebar.
    4. Upload the refreshed workbook again whenever you update the scanner.
    """)
    st.stop()

try:
    xls = pd.ExcelFile(uploaded)
    sheets = {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}
except Exception as exc:
    st.error(f"Could not read this workbook: {exc}")
    st.stop()

def get_sheet(*names):
    for name in names:
        if name in sheets:
            return sheets[name].copy()
    return pd.DataFrame()

master = get_sheet("Master_Dashboard", "Master Dashboard")
monitor = get_sheet("Live_Monitor", "Live Monitor")
historical = get_sheet("Historical_Trades", "Historical Trades")
ranking = get_sheet("Stock_Ranking", "Stock Ranking")
outcomes = get_sheet("Outcome_Summary", "Outcome Summary")
intraday = get_sheet("Intraday_Signals", "Intraday", "Intraday_Scanner")

def find_col(df, candidates):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None

stock_col = find_col(master, ["Stock", "Symbol", "Ticker"])
if stock_col is None and not master.empty:
    possible = [c for c in master.columns if str(c).lower() in ("level_0", "index")]
    stock_col = possible[0] if possible else None

def numeric_value(row, candidates):
    col = find_col(pd.DataFrame([row]), candidates)
    if col is None:
        return None
    try:
        value = pd.to_numeric(row[col], errors="coerce")
        return None if pd.isna(value) else float(value)
    except Exception:
        return None

def metric_card(label, value):
    st.metric(label, value)

tab_overview, tab_intraday, tab_swing, tab_monitor, tab_history = st.tabs(
    ["Overview", "Intraday", "Swing", "Trade Monitor", "Historical Performance"]
)

with tab_overview:
    st.subheader("Scanner overview")
    c1, c2, c3, c4 = st.columns(4)
    stock_count = master[stock_col].nunique() if stock_col and not master.empty else len(master)
    metric_card("Stocks in dashboard", stock_count)
    metric_card("Historical trade records", len(historical))
    metric_card("Monitor records", len(monitor))
    metric_card("Workbook sheets", len(sheets))
    st.divider()
    st.subheader("Available scanner data")
    st.write(", ".join(sheets.keys()))
    if not master.empty:
        st.subheader("Master stock dashboard")
        st.dataframe(master, use_container_width=True, hide_index=True)
    else:
        st.warning("The workbook does not contain a populated Master_Dashboard sheet.")

with tab_intraday:
    st.subheader("Intraday scanner")
    if not intraday.empty:
        st.dataframe(intraday, use_container_width=True, hide_index=True)
    else:
        st.info(
            "Intraday data is not yet present in this workbook. Your existing report currently "
            "contains the daily/swing foundation. Once the Colab scanner exports an "
            "`Intraday_Signals` sheet, it will appear here automatically."
        )
        st.caption("Planned intraday fields: 15-minute signal, EMA 9/21, RSI, VWAP, ATR, entry, stop loss and targets.")

with tab_swing:
    st.subheader("Swing scanner")
    if not master.empty:
        rating_col = find_col(master, ["Scanner_Rating", "Signal", "Trade_Action"])
        if rating_col:
            choices = ["All"] + sorted(master[rating_col].dropna().astype(str).unique().tolist())
            selected = st.selectbox("Filter swing setups", choices, key="swing_filter")
            view = master if selected == "All" else master[master[rating_col].astype(str) == selected]
        else:
            view = master
        st.dataframe(view, use_container_width=True, hide_index=True)
        if stock_col:
            stock_options = sorted(master[stock_col].dropna().astype(str).unique().tolist())
            if stock_options:
                selected_stock = st.selectbox("Inspect a stock setup", stock_options, key="swing_stock")
                row_df = master[master[stock_col].astype(str) == selected_stock]
                if not row_df.empty:
                    row = row_df.iloc[0]
                    level_names = ["Stop_Loss", "Entry", "TP1", "TP2", "TP3"]
                    values = [numeric_value(row, [name]) for name in level_names]
                    valid = [(name, val) for name, val in zip(level_names, values) if val is not None]
                    if valid:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=[name.replace("_", " ") for name, _ in valid],
                            y=[val for _, val in valid],
                            mode="lines+markers+text",
                            text=[f"₹{val:.2f}" for _, val in valid],
                            textposition="top center",
                            name=selected_stock
                        ))
                        fig.update_layout(title=f"{selected_stock} — trade levels", yaxis_title="Price (₹)", height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.caption("Entry/Stop Loss/Target columns were not found for this stock.")
    else:
        st.warning("Master_Dashboard sheet is missing or empty.")

with tab_monitor:
    st.subheader("Trade monitoring")
    if not monitor.empty:
        st.dataframe(monitor, use_container_width=True, hide_index=True)
    else:
        st.info("No Live_Monitor sheet was found in this workbook.")

with tab_history:
    st.subheader("Historical performance")
    if not historical.empty:
        outcome_col = find_col(historical, ["Final_Outcome", "Outcome"])
        if outcome_col:
            counts = historical[outcome_col].fillna("Unknown").astype(str).value_counts().rename_axis("Outcome").reset_index(name="Trades")
            st.bar_chart(counts.set_index("Outcome"))
            st.dataframe(counts, use_container_width=True, hide_index=True)
        st.dataframe(historical, use_container_width=True, hide_index=True)
    else:
        st.info("No Historical_Trades sheet was found in this workbook.")

with st.sidebar:
    st.divider()
    st.caption("Data source: uploaded Colab Excel report")
    st.caption("This dashboard displays exported scanner results; it does not fetch live exchange prices or place orders.")
