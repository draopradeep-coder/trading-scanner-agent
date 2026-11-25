import streamlit as st
import pandas as pd
from universe import load_full_universe
from scanner_engine import scan_batch, load_progress, clear_progress

st.set_page_config(page_title="TraderPrp | Automatic Scanner",page_icon="📈",layout="wide")
st.title("🔎 Automatic Stock Scanner")
st.caption("Daily-bar momentum and swing candidates across NSE/BSE cash equities. Not intraday signals.")

@st.cache_data(ttl=3600,show_spinner=False)
def get_universe():
    return load_full_universe()

try:
    universe,source_errors=get_universe()
except Exception as e:
    st.error(f"Unable to load universe: {e}")
    st.stop()
if source_errors:
    st.warning("Some universe sources failed; scan coverage may be partial.")
    for err in source_errors: st.caption(str(err))

total=len(universe)
st.metric("Universe loaded",total)
st.caption("Loaded universe size is not the same as completed scan coverage. Scan progress is saved in a local progress file while this app instance remains available.")

progress=load_progress()
if progress and progress.get("records"):
    st.info(f"Saved scan progress detected: {len(progress['records'])} stocks recorded. Continue the scan or reset it.")
c1,c2=st.columns(2)
with c1:
    resume=st.button("▶️ Resume / Scan Next Batch",type="primary",use_container_width=True)
with c2:
    fresh=st.button("🧹 Start Fresh Scan",use_container_width=True)
if fresh:
    clear_progress()
    progress=None
    st.success("Saved scan progress cleared. Press Resume / Scan Next Batch to start.")
if resume or fresh:
    with st.spinner("Scanning the next batch of daily stock data..."):
        try:
            results,summary,status=scan_batch(universe,batch_size=40,retry_failed=bool(fresh))
            st.session_state["scan_results"]=results
            st.session_state["scan_summary"]=summary
            st.session_state["scan_status"]=status
        except Exception as e:
            st.error(f"Scan batch failed: {e}")

summary=st.session_state.get("scan_summary")
results=st.session_state.get("scan_results")
status=st.session_state.get("scan_status")
progress=load_progress()
if progress:
    recs=progress.get("records",{})
    analyzed=sum(x.get("status")=="analyzed" for x in recs.values())
    failed=sum(x.get("status")=="failed" for x in recs.values())
    pending=max(0,total-len(recs))
    candidates=pd.DataFrame([x.get("result") for x in recs.values() if x.get("status")=="analyzed" and x.get("candidate") and x.get("result")])
    if not candidates.empty: candidates=candidates.sort_values(["score","volume_ratio"],ascending=False).reset_index(drop=True)
    a,b,c,d=st.columns(4)
    a.metric("Recorded",len(recs),f"of {total}")
    b.metric("Analyzed",analyzed)
    c.metric("Failed",failed)
    d.metric("Remaining",pending)
    st.progress(min(1.0,len(recs)/max(1,total)))
    st.caption(f"Saved progress updated: {progress.get('updated','unknown')}. Remaining stocks can be scanned in batches of 40. Failed stocks are skipped during resume; reset to retry them.")
    if not candidates.empty:
        exch=st.selectbox("Exchange",["All","NSE","BSE"])
        view=candidates.copy()
        if exch!="All": view=view[view["exchange"]==exch]
        st.metric("Candidates",len(view))
        st.dataframe(view,use_container_width=True,hide_index=True)
        st.download_button("⬇️ Download candidates CSV",view.to_csv(index=False).encode("utf-8"),"TraderPrp_Candidates.csv","text/csv",use_container_width=True)
    else: st.warning("No qualifying candidates yet. Continue scanning more batches.")
    status_df=pd.DataFrame([{k:v for k,v in rec.items() if k!="result"} for rec in recs.values()])
    if not status_df.empty:
        with st.expander("Stock scan status"):
            st.dataframe(status_df,use_container_width=True,hide_index=True)
            st.download_button("Download scan status CSV",status_df.to_csv(index=False).encode("utf-8"),"TraderPrp_Scan_Status.csv","text/csv")
else:
    st.info("No saved scan progress yet. Start scanning to analyze the universe in batches.")

st.caption("Daily candles are used for swing/momentum screening, not intraday live signals. Scores are screening indicators, not probabilities or financial advice.")
