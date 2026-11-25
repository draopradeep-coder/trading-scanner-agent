import streamlit as st
import pandas as pd
from universe import load_full_universe
from scanner_engine import scan_universe_with_status

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
st.info("Universe row count is not the same as the number of stocks successfully analyzed.")

st.caption("Daily candles are used for swing/momentum screening. This is not intraday live data.")
if st.button("🔎 Scan Loaded Stock Universe", type="primary", use_container_width=True):
    with st.spinner(f"Analyzing {total_rows} listing rows… This may take several minutes."):
        try:
            results, scan_summary = scan_universe_with_status(universe)
            st.session_state["scanner_results"] = results
            st.session_state["scanner_summary"] = scan_summary
            st.session_state["scanner_scan_time"] = pd.Timestamp.now().strftime("%d %b %Y, %I:%M %p")
            st.session_state["scanner_universe_count"] = total_rows
        except Exception as e:
            st.error(f"Scan failed: {e}")

results = st.session_state.get("scanner_results")
summary = st.session_state.get("scanner_summary")
if results is not None and summary is not None:
    st.success(f"Scan refreshed: {st.session_state.get('scanner_scan_time','')}")
    st.caption(f"Attempted: {summary['requested']} | Successfully analyzed: {summary['analyzed']} | Failed: {summary['failed']} | Candidates: {summary['candidates']}")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Attempted",summary["requested"])
    c2.metric("Analyzed",summary["analyzed"])
    c3.metric("Failed",summary["failed"])
    c4.metric("Candidates",summary["candidates"])
    status_df=summary["status_rows"]
    if not status_df.empty:
        with st.expander("📋 Scan status by stock", expanded=False):
            st.dataframe(status_df,use_container_width=True,hide_index=True)
            st.download_button("Download scan status CSV",status_df.to_csv(index=False).encode("utf-8"),"TraderPrp_Scan_Status.csv","text/csv")
    if results.empty:
        st.warning("No candidates passed the scanner rules. See scan status above for data failures.")
    else:
        exchange_filter=st.selectbox("Exchange",["All","NSE","BSE"])
        view=results.copy()
        if exchange_filter!="All" and "exchange" in view.columns:
            view=view[view["exchange"].astype(str).str.upper()==exchange_filter]
        st.metric("Candidates in current view",len(view))
        st.dataframe(view,use_container_width=True,hide_index=True)
        st.download_button("⬇️ Download candidate results CSV",view.to_csv(index=False).encode("utf-8"),"TraderPrp_Scan_Results.csv","text/csv",use_container_width=True)
    st.caption("A failed fetch is not treated as an analyzed stock. A successfully analyzed stock that did not pass rules is not shown among candidates. Scores are screening indicators, not probabilities.")
