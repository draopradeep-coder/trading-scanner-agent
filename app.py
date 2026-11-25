
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

# Upload summary
st.success(f"Loaded **{uploaded_file.name}** successfully")
summary_col1, summary_col2, summary_col3 = st.columns(3)
summary_col1.metric("Excel Sheets", len(sheets))
summary_col2.metric("Rows Loaded", len(df))
summary_col3.metric("Columns Found", len(df.columns))
st.caption("The dashboard combines all non-empty sheets from the uploaded workbook.")

with st.expander("📑 View Excel Sheet Breakdown"):
    sheet_summary = pd.DataFrame([
        {
            "Sheet": sheet_name,
            "Rows": len(sheet_data),
            "Columns": len(sheet_data.columns),
            "Status": "Loaded" if not sheet_data.empty else "Empty (not included)"
        }
        for sheet_name, sheet_data in sheets.items()
    ])
    st.dataframe(sheet_summary, use_container_width=True, hide_index=True)
    st.caption("Empty sheets are listed for visibility but are not included in the combined dashboard data.")

# Column identification
def normalize_header(value):
    return "".join(character for character in str(value).strip().lower() if character.isalnum())


def find_column(data, candidates):
    normalized_candidates = {normalize_header(candidate) for candidate in candidates}
    for col in data.columns:
        if normalize_header(col) in normalized_candidates:
            return col
    return None


stock_col = find_column(df, ["stock", "stock name", "symbol", "ticker", "trading symbol", "tradingsymbol", "name"])
signal_col = find_column(df, ["signal", "trade signal", "action", "recommendation", "buy sell", "side"])
price_col = find_column(df, ["current_price", "current price", "ltp", "last traded price", "price"])
entry_col = find_column(df, ["entry", "entry_price", "entry price"])
stop_col = find_column(df, ["stop_loss", "stop loss", "sl"])
target_col = find_column(df, ["target", "target_1", "target1", "target price", "tp1"])
type_col = find_column(df, ["trade_type", "trade type", "type", "category", "strategy"])

# Manual fallback for unrecognized Excel headers
missing_mappings = [
    ("Stock Name / Symbol", "stock_col", stock_col),
    ("Signal", "signal_col", signal_col),
    ("Current Price", "price_col", price_col),
    ("Entry Price", "entry_col", entry_col),
    ("Stop Loss", "stop_col", stop_col),
    ("Target", "target_col", target_col),
    ("Trade Type", "type_col", type_col),
]
if any(column is None for _, _, column in missing_mappings):
    with st.expander("🛠️ Manually Map Missing Columns", expanded=False):
        st.caption("If an Excel header was not recognized, select the correct column below. Your original Excel file is not changed.")
        available_columns = ["(leave unmapped)"] + list(df.columns)
        for field_label, field_key, detected_column in missing_mappings:
            if detected_column is None:
                selected_column = st.selectbox(
                    f"Choose Excel column for {field_label}",
                    available_columns,
                    key=f"manual_map_{field_key}"
                )
                if selected_column != "(leave unmapped)":
                    if field_key == "stock_col":
                        stock_col = selected_column
                    elif field_key == "signal_col":
                        signal_col = selected_column
                    elif field_key == "price_col":
                        price_col = selected_column
                    elif field_key == "entry_col":
                        entry_col = selected_column
                    elif field_key == "stop_col":
                        stop_col = selected_column
                    elif field_key == "target_col":
                        target_col = selected_column
                    elif field_key == "type_col":
                        type_col = selected_column

# Detected column guide
with st.expander("🔎 View Detected Excel Columns", expanded=False):
    detected_columns = pd.DataFrame([
        {"Dashboard Field": label, "Detected Excel Column": column if column is not None else "Not detected", "Status": "Ready" if column is not None else "Needs attention"}
        for label, column in [
            ("Stock Name / Symbol", stock_col),
            ("Signal", signal_col),
            ("Current Price", price_col),
            ("Entry Price", entry_col),
            ("Stop Loss", stop_col),
            ("Target", target_col),
            ("Trade Type", type_col),
        ]
    ])
    st.dataframe(detected_columns, use_container_width=True, hide_index=True)
    st.caption("Header matching ignores spaces, underscores, hyphens and capitalization. Common alternatives include Stock Name, Trading Symbol, Trade Signal, Buy/Sell, Last Traded Price and Target Price. If a field is missing, use the Manually Map Missing Columns section above or rename the Excel header.")

# Data quality checks
st.subheader("🧹 Data Quality Check")
quality_col1, quality_col2, quality_col3 = st.columns(3)
def count_missing_values(series):
    return int((series.isna() | series.astype(str).str.strip().eq("")).sum())

missing_stock_names = count_missing_values(df[stock_col]) if stock_col else 0
missing_signals = count_missing_values(df[signal_col]) if signal_col else 0
if stock_col:
    stock_names = df[stock_col].astype(str).str.strip()
    valid_stock_names = stock_names[~df[stock_col].isna() & stock_names.ne("")]
    duplicate_stocks = int(valid_stock_names.duplicated().sum())
else:
    duplicate_stocks = 0
quality_col1.metric("Missing Stock Names", missing_stock_names)
quality_col2.metric("Missing Signals", missing_signals if signal_col else "N/A")
quality_col3.metric("Duplicate Stock Rows", duplicate_stocks if stock_col else "N/A")

if signal_col:
    normalized_signals = df[signal_col].fillna("").astype(str).str.strip().str.upper()
    valid_signal_mask = normalized_signals.str.contains(r"BUY|HOLD|SELL|AVOID|WAIT", regex=True, na=False)
    unexpected_signals = sorted(normalized_signals[
        normalized_signals.ne("") & ~valid_signal_mask
    ].unique().tolist())
    st.metric("Unrecognized Signal Labels", len(normalized_signals[
        normalized_signals.ne("") & ~valid_signal_mask
    ]))
    if unexpected_signals:
        st.warning("Unrecognized signal labels found: " + ", ".join(unexpected_signals[:10]))
        with st.expander("🔍 View unrecognized signal counts", expanded=False):
            unexpected_counts = (
                normalized_signals[normalized_signals.ne("") & ~valid_signal_mask]
                .value_counts()
                .rename_axis("Signal Label")
                .reset_index(name="Rows")
            )
            st.dataframe(unexpected_counts, use_container_width=True, hide_index=True)
            st.caption("These labels are shown for review only. The dashboard does not assume what they mean or convert them into BUY, HOLD, SELL, AVOID or WAIT.")

trade_level_fields = [
    ("Current Price", price_col),
    ("Entry", entry_col),
    ("Stop Loss", stop_col),
    ("Target", target_col),
]
available_trade_fields = [(label, col) for label, col in trade_level_fields if col is not None]
if available_trade_fields:
    st.caption("Missing values in detected trade-level columns:")
    level_cols = st.columns(len(available_trade_fields))
    for level_col, (label, column) in zip(level_cols, available_trade_fields):
        level_col.metric(f"Missing {label}", count_missing_values(df[column]))

    st.caption("Non-numeric values in trade-level columns (currency symbols and commas are ignored):")
    numeric_cols = st.columns(len(available_trade_fields))
    for numeric_col, (label, column) in zip(numeric_cols, available_trade_fields):
        cleaned_values = df[column].astype(str).str.replace(r"[₹,\s]", "", regex=True)
        parsed_values = pd.to_numeric(cleaned_values, errors="coerce")
        invalid_values = int((~df[column].isna() & df[column].astype(str).str.strip().ne("") & parsed_values.isna()).sum())
        numeric_col.metric(f"Invalid {label}", invalid_values)

if not stock_col:
    st.warning("Stock name/symbol column was not detected. Please check your Excel headings.")
elif duplicate_stocks:
    st.info("Some stock names or symbols appear more than once. Review them before using the report.")



# Downloadable data quality report
quality_issues = []

for row_index, (_, row) in enumerate(df.iterrows(), start=1):
    stock_name = str(row[stock_col]).strip() if stock_col and pd.notna(row[stock_col]) else ""
    if stock_col and not stock_name:
        quality_issues.append({
            "Dashboard Row": row_index,
            "Stock": "",
            "Issue": "Missing stock name/symbol",
            "Column": str(stock_col),
            "Value": ""
        })
    if signal_col:
        signal_value = str(row[signal_col]).strip() if pd.notna(row[signal_col]) else ""
        if not signal_value:
            quality_issues.append({
                "Dashboard Row": row_index,
                "Stock": stock_name,
                "Issue": "Missing signal",
                "Column": str(signal_col),
                "Value": ""
            })
        elif not any(label in signal_value.upper() for label in ["BUY", "HOLD", "SELL", "AVOID", "WAIT"]):
            quality_issues.append({
                "Dashboard Row": row_index,
                "Stock": stock_name,
                "Issue": "Unrecognized signal label",
                "Column": str(signal_col),
                "Value": signal_value
            })
    for label, column in available_trade_fields:
        value = row[column]
        if pd.isna(value) or str(value).strip() == "":
            quality_issues.append({
                "Dashboard Row": row_index,
                "Stock": stock_name,
                "Issue": f"Missing {label}",
                "Column": str(column),
                "Value": ""
            })
        else:
            cleaned_value = str(value).replace("₹", "").replace(",", "").strip()
            if pd.to_numeric(cleaned_value, errors="coerce") is pd.NA or pd.isna(pd.to_numeric(cleaned_value, errors="coerce")):
                quality_issues.append({
                    "Dashboard Row": row_index,
                    "Stock": stock_name,
                    "Issue": f"Invalid {label}",
                    "Column": str(column),
                    "Value": str(value)
                })

if stock_col:
    seen_stock_names = set()
    for row_position, stock_value in enumerate(df[stock_col].tolist(), start=1):
        if pd.isna(stock_value):
            continue
        normalized_stock = str(stock_value).strip().casefold()
        if not normalized_stock:
            continue
        if normalized_stock in seen_stock_names:
            quality_issues.append({
                "Dashboard Row": row_position,
                "Stock": str(stock_value),
                "Issue": "Duplicate stock name/symbol",
                "Column": str(stock_col),
                "Value": str(stock_value)
            })
        else:
            seen_stock_names.add(normalized_stock)

if quality_issues:
    quality_report = pd.DataFrame(quality_issues)
    st.caption(f"{len(quality_report)} data-quality issue(s) identified. Dashboard Row refers to the row position in the combined report.")
    with st.expander("Preview data-quality issues", expanded=False):
        st.dataframe(quality_report.head(20), use_container_width=True, hide_index=True)
        if len(quality_report) > 20:
            st.caption(f"Showing first 20 of {len(quality_report)} issues. Download the CSV for the complete list.")
    st.download_button(
        "⬇️ Download Data Quality Issues",
        data=quality_report.to_csv(index=False).encode("utf-8"),
        file_name="Data_Quality_Issues.csv",
        mime="text/csv",
        key="download_data_quality_issues"
    )
else:
    st.success("No data-quality issues detected in the checked fields.")


# Overview
st.header("📊 Overview")

total_stocks = len(df)

buy_count = 0
hold_count = 0
sell_count = 0
avoid_count = 0
wait_count = 0

if signal_col:
    signals = df[signal_col].astype(str).str.upper().str.strip()
    buy_count = signals.str.contains(r"\bBUY\b", regex=True, na=False).sum()
    hold_count = signals.str.contains(r"\bHOLD\b", regex=True, na=False).sum()
    sell_count = signals.str.contains(r"\bSELL\b", regex=True, na=False).sum()
    avoid_count = signals.str.contains(r"\bAVOID\b", regex=True, na=False).sum()
    wait_count = signals.str.contains(r"\bWAIT\b", regex=True, na=False).sum()

other_count = max(0, total_stocks - buy_count - hold_count - sell_count - avoid_count - wait_count)
scan_denominator = max(total_stocks, 1)

col1, col2, col3 = st.columns(3)
col1.metric("Stocks Scanned", total_stocks)
col2.metric("BUY Signals", int(buy_count), delta=f"{buy_count / scan_denominator * 100:.1f}% of scan")
col3.metric("HOLD Signals", int(hold_count), delta=f"{hold_count / scan_denominator * 100:.1f}% of scan")

col4, col5, col6 = st.columns(3)
col4.metric("SELL Signals", int(sell_count), delta=f"{sell_count / scan_denominator * 100:.1f}% of scan")
col5.metric("AVOID Signals", int(avoid_count), delta=f"{avoid_count / scan_denominator * 100:.1f}% of scan")
col6.metric("WAIT Signals", int(wait_count), delta=f"{wait_count / scan_denominator * 100:.1f}% of scan")

st.metric("Other Signals", int(other_count))
st.subheader("📊 Signal Distribution")

signal_chart = pd.DataFrame({
    "Signal": ["BUY", "HOLD", "SELL", "AVOID", "WAIT", "Other"],
    "Count": [int(buy_count), int(hold_count), int(sell_count),
              int(avoid_count), int(wait_count), int(other_count)]
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

    overview_df = df.copy()
    if stock_col:
        overview_search = st.text_input(
            "🔎 Search All Stocks",
            placeholder="Enter a stock name or symbol",
            key="overview_stock_search"
        )
        if overview_search:
            overview_df = overview_df[
                overview_df[stock_col].astype(str).str.contains(
                    overview_search, case=False, na=False
                )
            ]
        if signal_col:
            overview_signal_filter = st.selectbox(
                "Filter Overview by Signal",
                ["All", "BUY", "HOLD", "SELL", "AVOID", "WAIT"],
                key="overview_signal_filter"
            )
            if overview_signal_filter != "All":
                overview_df = overview_df[
                    overview_df[signal_col].astype(str).str.upper().str.contains(
                        overview_signal_filter, na=False
                    )
                ]
        overview_sort = st.selectbox(
            "Sort Overview Stocks",
            ["Original order", "Stock name A-Z", "Stock name Z-A"],
            key="overview_stock_sort"
        )
        if overview_sort == "Stock name A-Z":
            overview_df = overview_df.sort_values(
                by=stock_col, key=lambda col: col.astype(str).str.lower()
            )
        elif overview_sort == "Stock name Z-A":
            overview_df = overview_df.sort_values(
                by=stock_col, key=lambda col: col.astype(str).str.lower(),
                ascending=False
            )
        st.caption(f"Showing {len(overview_df)} of {total_stocks} stocks.")
        if overview_df.empty:
            st.info("No stocks match your search in the current scan.")
        else:
            # Keep the main Overview table compact on mobile; full fields remain below.
            mobile_priority_columns = [stock_col, signal_col, entry_col, stop_col, target_col]
            mobile_priority_columns = list(dict.fromkeys(
                column for column in mobile_priority_columns
                if column is not None and column in overview_df.columns
            ))
            overview_mobile_df = overview_df[mobile_priority_columns].copy()
            st.caption("📱 Compact view: showing Stock, Signal, Entry, Stop Loss and TP1 where available. Select a stock below for every available field.")
            st.dataframe(
                overview_mobile_df,
                use_container_width=True,
                hide_index=True
            )
            st.download_button(
                "⬇️ Download Overview Results",
                data=overview_df.to_csv(index=False).encode("utf-8"),
                file_name="Overview_Results.csv",
                mime="text/csv",
                key="download_overview_results"
            )
            st.markdown("#### 📋 View Full Stock Details")
            detail_options = overview_df[stock_col].dropna().astype(str).unique().tolist()
            if detail_options:
                selected_detail_stock = st.selectbox(
                    "Select a stock to see all available fields",
                    detail_options,
                    key="overview_detail_stock"
                )
                selected_detail = overview_df[
                    overview_df[stock_col].astype(str) == selected_detail_stock
                ].iloc[0]
                snapshot_fields = [
                    ("Signal", signal_col),
                    ("Current Price", price_col),
                    ("Entry", entry_col),
                    ("Stop Loss", stop_col),
                    ("Target", target_col)
                ]
                snapshot_fields = [
                    (label, col) for label, col in snapshot_fields
                    if col is not None and col in selected_detail.index
                    and pd.notna(selected_detail[col])
                ]
                if snapshot_fields:
                    st.markdown("#### 🎯 Quick Trade Snapshot")
                    snapshot_cols = st.columns(2)
                    for i, (label, col) in enumerate(snapshot_fields):
                        snapshot_cols[i % 2].metric(
                            label, str(selected_detail[col])
                        )
                st.markdown("#### All Available Stock Information")
                st.dataframe(
                    selected_detail.rename("Value").to_frame(),
                    use_container_width=True
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
            ["All", "BUY", "HOLD", "SELL", "AVOID", "WAIT"]
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
            ["All", "BUY", "HOLD", "SELL", "AVOID", "WAIT"],
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
            ["All", "BUY", "HOLD", "SELL", "AVOID", "WAIT"],
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
