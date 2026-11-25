import streamlit as st
import pandas as pd
from universe import load_full_universe
from scanner_engine import scan_universe

st.set_page_config(page_title="TraderPrp | Automatic Scanner", page_icon="🔎", layout="wide")
st.title("🔎 Automatic Stock Scanner")
st.caption("Daily-bar momentum and swing candidates across the loaded NSE/BSE universe. Not intraday live signals.")

@st.cache_data(ttl=3600, show_spinner=False)
def get_universe():
    return load_full_universe()

try:
    universe, source_errors = get_universe()
except Exception as e:
    st.error(f"Unable to load stock universe: {e}")
    st.stop()

if source_errors:
    st.warning("Some universe sources failed. Coverage may be partial; this is not a complete-market scan.")
    for err in source_errors:
        st.caption(err)

total_rows = len(universe)
st.metric("Loaded universe rows", total_rows)
exchanges = universe["exchange"].astype(str).str.upper().value_counts() if "exchange" in universe.columns else pd.Series(dtype=int)
cols = st.columns(2)
cols[0].metric("NSE rows", int(exchanges.get("NSE", 0)))
cols[1].metric("BSE rows", int(exchanges.get("BSE", 0)))
st.info("Universe row count is not the same as the number of stocks successfully analyzed. The scan may be incomplete if data providers reject or omit symbols.")

st.caption("This scanner uses daily candles for momentum/swing setups. True intraday scanning requires intraday data and will be built separately.")
if st.button("🔎 Scan Loaded Stock Universe", type="primary", use_container_width=True):
    with st.spinner(f"Scanning {total_rows} loaded listing rows. This may take several minutes…"):
        try:
            results = scan_universe(universe)
            st.session_state["scanner_results"] = results
            st.session_state["scanner_scan_time"] = pd.Timestamp.now().strftime("%d %b %Y, %I:%M %p")
            st.session_state["scanner_universe_count"] = total_rows
        except Exception as e:
            st.error(f"Scan failed: {e}")

results = st.session_state.get("scanner_results")
if results is not None:
    st.success(f"Candidate scan output last refreshed: {st.session_state.get('scanner_scan_time','')}")
    st.caption(f"Loaded rows at scan time: {st.session_state.get('scanner_universe_count', 'unknown')} • Candidate rows returned: {len(results)}. This does not certify every listing was successfully analyzed.")
    if results.empty:
        st.warning("No candidates passed the scanner's current rules. This does not mean every stock was successfully analyzed.")
    else:
        exchange_filter = st.selectbox("Exchange", ["All", "NSE", "BSE"])
        view = results.copy()
        if exchange_filter != "All" and "exchange" in view.columns:
            view = view[view["exchange"].astype(str).str.upper() == exchange_filter]
        st.metric("Candidates in current view", len(view))
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download scan results CSV", view.to_csv(index=False).encode("utf-8"), "TraderPrp_Scan_Results.csv", "text/csv", use_container_width=True)
        st.caption("Scores are rule-based screening indicators, not probability of profit or investment advice. ATR targets are scenarios, not forecasts.")
