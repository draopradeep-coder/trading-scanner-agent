import streamlit as st
import pandas as pd
from universe import load_full_universe
from scanner_engine import scan_batch, load_progress, clear_progress

st.set_page_config(page_title="TraderPrp | Automatic Scanner",page_icon="🔎",layout="wide")
st.title("🔎 Automatic Stock Scanner")
st.caption("Daily-bar momentum and swing candidates across the loaded NSE/BSE universe. Not intraday live signals.")

@st.cache_data(ttl=3600,show_spinner=False)
def get_universe():
    return load_full_universe()

try:
    universe,source_errors=get_universe()
except Exception as e:
    st.error(f"Unable to load universe: {e}")
    st.stop()
if source_errors:
    st.warning("Some sources failed; scan coverage may be partial.")
    for error in source_errors: st.caption(str(error))
total=len(universe)
st.metric("Universe loaded",total)
st.caption("Universe size is not the same as completed scan coverage. Progress is stored locally while this app instance remains available.")
progress=load_progress()
if progress and progress.get("records"):
    st.info(f"Saved progress: {len(progress['records'])} stock records. Resume, retry failed stocks, or start fresh.")
c1,c2,c3=st.columns(3)
with c1: resume=st.button("▶️ Resume / Scan Next Batch",type="primary",use_container_width=True)
with c2: retry=st.button("🔁 Retry Failed Stocks",use_container_width=True)
with c3: fresh=st.button("🧹 Start Fresh Scan",use_container_width=True)
if fresh:
    clear_progress()
    st.success("Progress cleared. Press Resume to begin.")
if resume or retry:
    with st.spinner("Scanning daily stock data..."):
        try:
            candidates,summary,status=scan_batch(universe,batch_size=40,retry_failed=retry)
            st.session_state["scan_candidates"]=candidates
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
    st.progress(min(1.0,len(records)/max(total,1)))
    st.caption(f"Last saved: {progress.get('updated','unknown')} · Batch size: 40")
candidates=st.session_state.get("scan_candidates")
if candidates is None and progress:
    candidates=pd.DataFrame([x.get("result") for x in progress.get("records",{}).values() if x.get("status")=="analyzed" and x.get("candidate") and x.get("result")])
if candidates is not None and not candidates.empty:
    if "tier" not in candidates.columns:
        candidates["tier"]=candidates["score"].apply(lambda x:"A+" if x>=85 else "A" if x>=70 else "B" if x>=55 else "C")
    candidates=candidates.sort_values(["score","volume_ratio"],ascending=False).reset_index(drop=True)
    st.subheader("🏆 Ranked candidates")
    st.caption("Tier labels summarize indicator confluence—not win probability or financial advice.")
    tier_filter=st.multiselect("Show tiers",["A+","A","B","C"],default=["A+","A","B","C"])
    exchange=st.selectbox("Exchange filter",["All","NSE","BSE"])
    view=candidates[candidates["tier"].isin(tier_filter)]
    if exchange!="All": view=view[view["exchange"]==exchange]
    st.metric("Candidates shown",len(view))
    st.dataframe(view,use_container_width=True,hide_index=True)
    st.download_button("⬇️ Download candidates CSV",view.to_csv(index=False).encode("utf-8"),"TraderPrp_Candidates.csv","text/csv",use_container_width=True)
else:
    st.info("No qualifying candidates yet. Scan additional batches.")
if progress and progress.get("records"):
    status_df=pd.DataFrame([{k:v for k,v in rec.items() if k!="result"} for rec in progress["records"].values()])
    if not status_df.empty:
        with st.expander("Stock scan status"):
            st.dataframe(status_df,use_container_width=True,hide_index=True)
            st.download_button("Download scan status CSV",status_df.to_csv(index=False).encode("utf-8"),"TraderPrp_Scan_Status.csv","text/csv")
st.caption("Daily candles are used for swing/momentum screening, not live intraday signals. Scores and tiers are screening metrics, not probabilities or financial advice.")
