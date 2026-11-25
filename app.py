
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Trading Scanner Agent",
    page_icon="📈",
    layout="wide"
)

# Mobile-friendly styling
st.markdown("""
<style>
.block-container {
    padding-top: 20px;
    padding-bottom: 15px;
}
[data-testid="stMetric"] {
    background-color: rgba(128,128,128,0.08);
    padding: 12px;
    border-radius: 12px;
}
h1 {
    font-size: 28px !important;
}
h2, h3 {
    font-size: 22px !important;
}
</style>
""", unsafe_allow_html=True)

st.title("📈 Trading Scanner Agent")
st.caption("Indian Cash Equity | Intraday & Swing Trading")

st.markdown("""
Upload your **Trading Scanner Excel Report** to view your scanner
results, trading levels and monitoring data.
""")

uploaded_file = st.file_uploader(
    "Upload Trading Scanner Excel Report",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Upload your Trading Scanner Excel file to view the dashboard.")
    st.stop()

try:
    excel = pd.ExcelFile(uploaded_file)
    sheets = {}

    for sheet in excel.sheet_names:
        sheets[sheet] = pd.read_excel(uploaded_file, sheet_name=sheet)

    df = pd.concat(
        [data for data in sheets.values() if not data.empty],
        ignore_index=True
    )

    if df.empty:
        st.warning("The uploaded Excel file contains no records.")
        st.stop()

except Exception as e:
    st.error(f"Unable to read Excel file: {e}")
    st.stop()

# Column identification
def find_column(data, candidates):
    for col in data.columns:
        if str(col).strip().lower() in candidates:
            return col
    return None

stock_col = find_column(df, ["stock", "symbol", "ticker", "name"])
signal_col = find_column(df, ["signal", "action", "recommendation"])
price_col = find_column(df, ["current_price", "current price", "ltp", "price"])
entry_col = find_column(df, ["entry", "entry_price", "entry price"])
stop_col = find_column(df, ["stop_loss", "stop loss", "sl"])
target_col = find_column(df, ["target", "target_1", "target1", "tp1"])
type_col = find_column(df, ["trade_type", "type", "category", "strategy"])

# Overview
st.header("📊 Overview")

total_stocks = len(df)

buy_count = 0
hold_count = 0

if signal_col:
    signals = df[signal_col].astype(str).str.upper()
    buy_count = signals.str.contains("BUY", na=False).sum()
    hold_count = signals.str.contains("HOLD", na=False).sum()

col1, col2, col3 = st.columns(3)

col1.metric("Stocks Scanned", total_stocks)
col2.metric("BUY Signals", int(buy_count))
col3.metric("HOLD Signals", int(hold_count))
sell_count = 0

if signal_col:
    sell_count = signals.str.contains("SELL", na=False).sum()

col4, col5 = st.columns(2)
col4.metric("SELL Signals", int(sell_count))
col5.metric("Other Signals", int(total_stocks - buy_count - hold_count - sell_count))
st.subheader("📊 Signal Distribution")

signal_chart = pd.DataFrame({
    "Signal": ["BUY", "HOLD", "SELL", "Other"],
    "Count": [int(buy_count), int(hold_count), int(sell_count),
              int(total_stocks - buy_count - hold_count - sell_count)]
})

st.bar_chart(signal_chart.set_index("Signal"))

st.subheader("⭐ BUY Signal Watchlist")
if signal_col:
    buy_display_cols = [
        col for col in [
            stock_col, signal_col, price_col, entry_col, stop_col, target_col
        ] if col is not None
    ]
    buy_rows = df.loc[
        signals.str.contains("BUY", na=False), buy_display_cols
    ]
    buy_search = st.text_input(
        "Search BUY stocks",
        placeholder="Enter a stock name or symbol",
        key="buy_watchlist_search"
    )
    if buy_search and stock_col:
        buy_rows = buy_rows[
            buy_rows[stock_col].astype(str).str.contains(
                buy_search, case=False, na=False
            )
        ]
    buy_rows = buy_rows.head(10)
    if buy_rows.empty:
        st.info("No BUY stocks match your search in the current scan.")
    else:
        st.dataframe(buy_rows, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download BUY Watchlist",
            data=buy_rows.to_csv(index=False).encode("utf-8"),
            file_name="BUY_Watchlist.csv",
            mime="text/csv"
        )
else:
    st.info("Signal column was not detected in the uploaded report.")

st.divider()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview",
    "Intraday",
    "Swing",
    "Trade Monitor",
    "Historical Performance"
])

with tab1:
    st.subheader("Scanner Overview")

    if stock_col:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Stock name column was not detected.")
        st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("⚡ Intraday Scanner")

    if type_col:
        intraday = df[
            df[type_col].astype(str).str.lower().str.contains("intraday", na=False)
        ].copy()
    else:
        intraday = df.copy()

    if stock_col:
        search_stock = st.text_input("🔎 Search Intraday Stock")
        if search_stock:
            intraday = intraday[
                intraday[stock_col].astype(str).str.contains(
                    search_stock, case=False, na=False
                )
            ]

    if signal_col:
        signal_filter = st.selectbox(
            "Filter by Signal",
            ["All", "BUY", "HOLD", "SELL"]
        )

        if signal_filter != "All":
            intraday = intraday[
                intraday[signal_col].astype(str).str.upper().str.contains(
                    signal_filter, na=False
                )
            ]

    st.caption(f"Showing {len(intraday)} matching Intraday stocks.")

    if intraday.empty:
        st.info("No stocks found for this filter in the current scan.")
    else:
        st.dataframe(intraday, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download Intraday Results",
            data=intraday.to_csv(index=False).encode("utf-8"),
            file_name="Intraday_Results.csv",
            mime="text/csv",
            key="download_intraday_results"
        )

with tab3:
    st.subheader("📈 Swing Scanner")

    if type_col:
        swing = df[
            df[type_col].astype(str).str.lower().str.contains("swing", na=False)
        ].copy()
    else:
        swing = df.copy()

    if stock_col:
        search_stock = st.text_input("🔎 Search Swing Stock")
        if search_stock:
            swing = swing[
                swing[stock_col].astype(str).str.contains(
                    search_stock, case=False, na=False
                )
            ]

    if signal_col:
        swing_signal_filter = st.selectbox(
            "Filter Swing by Signal",
            ["All", "BUY", "HOLD", "SELL"],
            key="swing_signal_filter"
        )
        if swing_signal_filter != "All":
            swing = swing[
                swing[signal_col].astype(str).str.upper().str.contains(
                    swing_signal_filter, na=False
                )
            ]

    st.caption(f"Showing {len(swing)} matching Swing stocks.")

    if swing.empty:
        st.info("No stocks found for this filter in the current scan.")
    else:
        st.dataframe(swing, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download Swing Results",
            data=swing.to_csv(index=False).encode("utf-8"),
            file_name="Swing_Results.csv",
            mime="text/csv",
            key="download_swing_results"
        )

with tab4:
    st.subheader("🎯 Trade Monitor")

    st.caption("Review trade levels from the uploaded report. Live TP/SL outcome tracking is not enabled yet.")

    monitor_df = df.copy()

    if signal_col:
        monitor_signal_filter = st.selectbox(
            "Filter monitored trades by Signal",
            ["All", "BUY", "HOLD", "SELL"],
            key="monitor_signal_filter"
        )
        if monitor_signal_filter != "All":
            monitor_df = monitor_df[
                monitor_df[signal_col].astype(str).str.upper().str.contains(
                    monitor_signal_filter, na=False
                )
            ]

    monitor_cols = [
        c for c in [
            stock_col, signal_col, entry_col, price_col,
            stop_col, target_col
        ] if c is not None
    ]

    if monitor_df.empty:
        st.info("No trades found for this filter in the uploaded report.")
    elif monitor_cols:
        st.dataframe(
            monitor_df[monitor_cols],
            use_container_width=True,
            hide_index=True
        )
        st.download_button(
            "⬇️ Download Trade Monitor",
            data=monitor_df[monitor_cols].to_csv(index=False).encode("utf-8"),
            file_name="Trade_Monitor.csv",
            mime="text/csv",
            key="download_trade_monitor"
        )
    else:
        st.dataframe(monitor_df, use_container_width=True)
        st.download_button(
            "⬇️ Download Trade Monitor",
            data=monitor_df.to_csv(index=False).encode("utf-8"),
            file_name="Trade_Monitor.csv",
            mime="text/csv",
            key="download_trade_monitor"
        )

with tab5:
    st.subheader("📜 Historical Performance")

    st.info("Historical TP1, TP2 and Stop Loss outcome tracking is not available yet. This tab currently shows the uploaded scanner report, not verified historical performance.")

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Download Full Scanner Report",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="Full_Scanner_Report.csv",
        mime="text/csv",
        key="download_full_scanner_report"
    )

st.divider()

st.caption(
    "TraderPrp | Educational tool only. Not financial advice. "
    "Always verify prices and manage risk."
    )
