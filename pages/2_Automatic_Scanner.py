import streamlit as st
import pandas as pd
from universe import load_full_universe
from scanner_engine import scan_universe

st.set_page_config(page_title="TraderPrp | Automatic Scanner",page_icon="🔎",layout="wide")
st.title("🔎 Automatic Stock Scanner")
st.caption("Daily-bar momentum and swing candidates across the loaded NSE/BSE universe. Not intraday live signals.")

@st.cache_data(ttl=3600,show_spinner=False)
def get_universe():
    return load_full_universe()

try:
    universe, source_errors = get_universe()
except Exception as e:
    st.error(f"Unable to load stock universe: {e}")
    st.stop()
if source_errors:
    st.warning("Some sources failed; scan coverage may be partial.")
    for e in source_errors: st.caption(e)

st.metric("Universe rows",len(universe))
st.info("This first scanner uses daily candles for momentum/swing setups. True intraday scanning will be added separately with intraday data.")
if st.button("🚀 Scan Full Stock Universe",type="primary",use_container_width=True):
    with st.spinner(f"Scanning {len(universe):,} listing rows. This may take several minutes…"):
        try:
            results=scan_universe(universe)
            st.session_state["scanner_results"]=results
            st.session_state["scanner_scan_time"]=pd.Timestamp.now().strftime("%d %b %Y, %I:%M %p")
        except Exception as e:
            st.error(f"Scan failed: {e}")

results=st.session_state.get("scanner_results")
if results is not None:
    st.success(f"Scan results · {st.session_state.get('scanner_scan_time','')}")
    if results.empty:
        st.warning("No candidates passed the current scan filters.")
    else:
        exchange_filter=st.selectbox("Exchange",["All","NSE","BSE"])
        if exchange_filter!="All": results=results[results.exchange==exchange_filter]
        st.metric("Candidates",len(results))
        st.dataframe(results,use_container_width=True,hide_index=True)
        st.download_button("⬇️ Download scan results CSV",results.to_csv(index=False).encode("utf-8"),"TraderPrp_Scan_Results.csv","text/csv",use_container_width=True)
        st.caption("Setup scores are rule-based screening indicators, not probability of profit or investment advice. Targets are ATR-derived scenarios, not forecasts.")
