import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="TraderPrp Trading Scanner",
    page_icon="📈",
    layout="wide"
)

st.title("📈 TraderPrp")
st.caption("Indian Cash Equity Scanner | Intraday + Swing")

st.sidebar.header("Connect Scanner")
uploaded = st.sidebar.file_uploader(
    "Upload Trading_Scanner_Complete_Report.xlsx",
    type=["xlsx"]
)

if uploaded is None:
    st.info("Upload your scanner Excel report to view dashboard data.")
    st.markdown("""
    ### How to connect your scanner
    1. Run your scanner in Google Colab.
    2. Export `Trading_Scanner_Complete_Report.xlsx`.
    3. Upload the workbook here.
    4. Explore the dashboard tabs.
    """)
    st.stop()

try:
    xls = pd.ExcelFile(uploaded)
    sheets = {
        name: pd.read_excel(xls, sheet_name=name)
        for name in xls.sheet_names
    }
except Exception as e:
    st.error(f"Could not read workbook: {e}")
    st.stop()


def get_sheet(*names):
    for name in names:
        if name in sheets:
            return sheets[name].copy()
    return pd.DataFrame()


def find_col(df, candidates):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def metric_card(label, value):
    st.metric(label, value)


master = get_sheet("Master_Dashboard", "Master Dashboard")
monitor = get_sheet("Live_Monitor", "Live Monitor")
historical = get_sheet("Historical_Trades", "Historical Trades")
ranking = get_sheet("Stock_Ranking", "Stock Ranking")
outcomes = get_sheet("Outcome_Summary", "Outcome Summary")
intraday = get_sheet(
    "Intraday_Signals", "Intraday", "Intraday_Scanner"
)

stock_col = find_col(master, ["Stock", "Symbol", "Ticker"])
signal_col = find_col(master, ["Signal", "Trade_Action", "Trade Action"])
rating_col = find_col(master, ["Scanner_Rating", "Scanner Rating", "Rating"])
outcome_col = find_col(historical, ["Final_Outcome", "Outcome"])

tabs = st.tabs([
    "🏠 Overview",
    "⚡ Intraday",
    "📊 Swing",
    "🎯 Trade Monitor",
    "📈 Historical Performance"
])

# ================= OVERVIEW =================

with tabs[0]:
    st.subheader("Smart Overview")

    total_stocks = (
        master[stock_col].nunique()
        if stock_col and not master.empty
        else len(master)
    )

    buy_count = 0
    hold_count = 0
    other_count = 0

    if signal_col and not master.empty:
        signal_values = master[signal_col].astype(str).str.upper()
        buy_count = signal_values.str.contains("BUY", na=False).sum()
        hold_count = signal_values.str.contains("HOLD", na=False).sum()
        other_count = len(master) - buy_count - hold_count

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("Stocks Scanned", total_stocks)

    with c2:
        metric_card("BUY Signals", int(buy_count))

    with c3:
        metric_card("HOLD Signals", int(hold_count))

    with c4:
        metric_card("Monitor Records", len(monitor))

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Signal Distribution")

        if signal_col and not master.empty:
            counts = master[signal_col].astype(str).value_counts()
            st.bar_chart(counts)
        else:
            st.info("Signal data unavailable.")

    with c2:
        st.subheader("Scanner Information")

        metric_card("Historical Trades", len(historical))
        metric_card("Workbook Sheets", len(sheets))

        if rating_col and not master.empty:
            st.write("**Scanner Ratings**")
            st.write(master[rating_col].value_counts())

    st.divider()

    st.subheader("Top Scanner Results")

    if not master.empty:
        st.dataframe(
            master,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Master Dashboard sheet is missing or empty.")

    st.subheader("Available Workbook Sheets")
    st.write(", ".join(sheets.keys()))

# ================= INTRADAY =================

with tabs[1]:
    st.subheader("Intraday Scanner")

    if not intraday.empty:
        st.dataframe(
            intraday,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(
            "Intraday data is not available in this workbook. "
            "Your scanner needs to export an Intraday_Signals sheet."
        )

    st.caption(
        "Planned scanner fields: 15-minute signals, EMA 9/21, "
        "RSI, VWAP, ATR, Entry, Stop Loss and Targets."
    )

# ================= SWING =================

with tabs[2]:
    st.subheader("Swing Scanner")

    if not master.empty:
        view = master.copy()

        if rating_col:
            choices = ["All"] + sorted(
                view[rating_col].dropna().astype(str).unique().tolist()
            )
            selected = st.selectbox("Filter by rating", choices)

            if selected != "All":
                view = view[view[rating_col].astype(str) == selected]

        if signal_col:
            signals = ["All"] + sorted(
                view[signal_col].dropna().astype(str).unique().tolist()
            )
            selected_signal = st.selectbox("Filter by signal", signals)

            if selected_signal != "All":
                view = view[view[signal_col].astype(str) == selected_signal]

        st.dataframe(
            view,
            use_container_width=True,
            hide_index=True
        )

        if stock_col:
            stock_options = view[stock_col].dropna().astype(str).unique().tolist()

            if stock_options:
                selected_stock = st.selectbox(
                    "Inspect trade levels",
                    stock_options
                )

                row_df = view[view[stock_col].astype(str) == selected_stock]

                if not row_df.empty:
                    row = row_df.iloc[0]

                    level_names = [
                        "Stop_Loss", "Entry", "TP1", "TP2", "TP3"
                    ]

                    values = []
                    labels = []

                    for name in level_names:
                        col = find_col(view, [name, name.replace("_", " ")])
                        if col:
                            val = pd.to_numeric(
                                pd.Series([row[col]]),
                                errors="coerce"
                            ).iloc[0]

                            if pd.notna(val):
                                values.append(float(val))
                                labels.append(name)

                    if values:
                        fig = go.Figure()

                        fig.add_trace(go.Scatter(
                            x=labels,
                            y=values,
                            mode="lines+markers+text",
                            text=[f"₹{v:.2f}" for v in values],
                            textposition="top center"
                        ))

                        fig.update_layout(
                            title=f"{selected_stock} — Trade Levels",
                            yaxis_title="Price (₹)",
                            height=400
                        )

                        st.plotly_chart(
                            fig,
                            use_container_width=True
                        )
    else:
        st.info("Master Dashboard data unavailable.")

# ================= MONITOR =================

with tabs[3]:
    st.subheader("Trade Monitoring")

    if not monitor.empty:
        st.dataframe(
            monitor,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No Live_Monitor sheet found in the workbook.")

# ================= HISTORY =================

with tabs[4]:
    st.subheader("Historical Performance")

    if not historical.empty:

        if outcome_col:
            counts = (
                historical[outcome_col]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
            )

            st.subheader("Trade Outcome Distribution")
            st.bar_chart(counts)

        st.dataframe(
            historical,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No Historical_Trades sheet found.")

# ================= FOOTER =================

st.sidebar.divider()
st.sidebar.caption("Data source: Uploaded scanner Excel report")
st.sidebar.caption(
    "This dashboard displays exported scanner data. "
    "It does not independently fetch live prices or place orders."
)
st.sidebar.warning(
    "For educational purposes only. Not financial advice."
)
