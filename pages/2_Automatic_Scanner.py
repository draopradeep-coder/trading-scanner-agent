import streamlit as st
import pandas as pd
from universe import load_full_universe
from scanner_engine import scan_batch, load_progress, clear_progress

st.set_page_config(page_title="TraderPrp | Automatic Scanner",page_icon="🔎",layout="wide")
st.title("🔎 Automatic Stock Scanner")
st.caption("Daily-bar momentum and swing candidates across NSE/BSE cash equities. Not intraday live signals.")

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
st.caption("Universe size is not the same as completed scan coverage. Progress is stored locally while this app instance remains available.")
progress=load_progress()
if progress and progress.get("records"):
    st.info(f"Saved progress: {len(progress['records'])} stock records. Resume, retry failed stocks, or start fresh.")
col1,col2,col3=st.columns(3)
with col1: resume=st.button("▶️ Resume / Scan Next Batch",type="primary",use_container_width=True)
with col2: retry=st.button("🔁 Retry Failed Stocks",use_container_width=True)
with col3: fresh=st.button("🆕 Start Fresh Scan",use_container_width=True)
if fresh:
    clear_progress()
    st.success("Progress cleared. Start the scan with Resume.")
if resume or retry:
    with st.spinner("Scanning daily stock data..."):
        try:
            candidates,summary,status=scan_batch(universe,batch_size=40,retry_failed=retry)
            st.session_state["scan_results"]=candidates
            st.session_state["scan_summary"]=summary
            st.session_state["scan_status"]=status
        except Exception as e:
            st.error(f"Scan failed: {e}")
summary=st.session_state.get("scan_summary")
progress=load_progress()
if progress:
    records=progress.get("records",{})
    analyzed=sum(x.get("status")=="analyzed" for x in records.values())
    failed=sum(x.get("status")=="failed" for x in records.values())
    remaining=max(0,total-len(records))
    a,b,c,d=st.columns(4)
    a.metric("Recorded",len(records),f"of {total}")
    b.metric("Analyzed",analyzed)
    c.metric("Failed",failed)
    d.metric("Remaining",remaining)
    st.progress(min(1,len(records)/max(total,1)))
    st.caption(f"Last saved: {progress.get('updated','unknown')}. Batch size: 40 stocks.")
    candidates=pd.DataFrame([x.get("result") for x in records.values() if x.get("status")=="analyzed" and x.get("candidate") and x.get("result")])
    if not candidates.empty:
        candidates=candidates.sort_values(["score","volume_ratio"],ascending=False).reset_index(drop=True)
        exchange=st.selectbox("Exchange filter",["All","NSE","BSE"])
        view=candidates if exchange=="All" else candidates[candidates["exchange"]==exchange]
        st.metric("Candidates",len(view))
        st.dataframe(view,use_container_width=True,hide_index=True)
        st.download_button("⬇️ Download candidates CSV",view.to_csv(index=False).encode("utf-8"),"TraderPrp_Candidates.csv","text/csv",use_container_width=True)
    else: st.warning("No qualifying candidates yet. Scan more batches.")
    status_df=pd.DataFrame([{k:v for k,v in rec.items() if k!="result"} for rec in records.values()])
    if not status_df.empty:
        with st.expander("Stock scan status"):
            st.dataframe(status_df,use_container_width=True,hide_index=True)
            st.download_button("Download scan status CSV",status_df.to_csv(index=False).encode("utf-8"),"TraderPrp_Scan_Status.csv","text/csv")
else:
    st.info("No saved scan progress yet. Press Resume / Scan Next Batch to start.")
st.caption("Daily candles are used for swing/momentum screening, not live intraday signals. Scores are screening indicators, not probabilities or financial advice.")
