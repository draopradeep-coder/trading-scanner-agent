import streamlit as st
import pandas as pd
from universe import load_full_universe
from scanner_engine import scan_batch, load_progress, clear_progress
from market_regime import detect_market_regime

st.set_page_config(page_title="TraderPrp | Automatic Scanner",page_icon="🔎",layout="wide")
st.title("🔎 Automatic Stock Scanner")
st.caption("Daily-bar momentum and swing candidates across the loaded NSE/BSE cash-equity universe. Not intraday live signals.")
st.caption("Scanner build: BSE fallback v2")

@st.cache_data(ttl=3600,show_spinner=False)
def get_universe():
    return load_full_universe()

@st.cache_data(ttl=1800,show_spinner=False)
def get_regime():
    return detect_market_regime()

try:
    regime=get_regime()
    st.subheader("🌦️ Market Regime")
    name=regime.get("regime","UNKNOWN")
    if name=="BULLISH": st.success("Market Regime: BULLISH — scanner will show qualifying candidates.")
    elif name=="BEARISH": st.error("Market Regime: BEARISH — new candidate recommendations are suppressed.")
    elif name=="SIDEWAYS / MIXED": st.warning("Market Regime: SIDEWAYS / MIXED — only stronger A+/A tier candidates will be shown.")
    else: st.info("Market regime unavailable — filtering will not be applied.")
    detail=regime.get("details",{})
    if detail:
        cols=st.columns(len(detail))
        for col,(idx,values) in zip(cols,detail.items()):
            col.metric(idx,f"{values['price']:,.2f}",f"20d: {values['change20']*100:+.2f}%")
            col.caption(f"SMA20 {values['sma20']:,.2f} · SMA50 {values['sma50']:,.2f}")
    st.caption(regime.get("message",""))
    if regime.get("issues"):
        for issue in regime["issues"]: st.caption(issue)
except Exception as e:
    regime={"regime":"UNKNOWN","details":{},"issues":[str(e)]}
    st.warning(f"Market regime detection failed: {e}")

@st.cache_data(ttl=3600,show_spinner=False)
def get_universe_data(cache_version="bse-fallback-v2"):
    # cache_version intentionally invalidates older NSE-only universe cache entries.
    return load_full_universe()

try:
    universe,source_errors=get_universe_data("bse-fallback-v2")
except Exception as e:
    st.error(f"Unable to load universe: {e}")
    st.stop()
if source_errors:
    fallback_notes=[str(error) for error in source_errors if "fallback." in str(error)]
    other_errors=[str(error) for error in source_errors if "fallback." not in str(error)]
    if fallback_notes:
        st.info("BSE primary API was unavailable, but the alternate daily BSE equity master loaded successfully.")
        for note in fallback_notes: st.caption(note)
    if other_errors:
        st.warning("Some exchange sources failed; scan coverage may be partial.")
        for error in other_errors: st.caption(error)
total=len(universe)
st.metric("Universe loaded",total)
st.caption("Universe size is not completed scan coverage. Progress is stored locally while this app instance remains available.")
progress=load_progress()
if progress and progress.get("records"): st.info(f"Saved progress: {len(progress['records'])} records. Resume, retry failed stocks, or start fresh.")
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
        except Exception as e: st.error(f"Scan failed: {e}")
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
    st.caption("Tier labels reflect indicator confluence, not probability.")
    f1,f2=st.columns(2)
    tier_filter=f1.multiselect("Show tiers",["A+","A","B","C"],default=["A+","A","B","C"])
    exchange=f2.selectbox("Exchange filter",["All","NSE","BSE"])
    view=candidates[candidates["tier"].isin(tier_filter)].copy()
    if exchange!="All": view=view[view["exchange"]==exchange]
    regime_name=regime.get("regime","UNKNOWN")
    if regime_name=="BEARISH":
        st.warning("Bearish market filter: candidate recommendations are hidden. You can still inspect scan progress.")
        view=view.iloc[0:0]
    elif regime_name=="SIDEWAYS / MIXED":
        view=view[view["tier"].isin(["A+","A"])]
        st.info("Sideways/mixed market: showing A+/A tier only.")
    st.subheader("💰 Position sizing & risk planner")
    capital=st.number_input("Total trading capital available (₹)",min_value=1000,value=100000,step=5000)
    risk_pct=st.slider("Risk budget per trade (% of capital)",min_value=0.25,max_value=3.0,value=1.0,step=0.25)
    risk_budget=capital*risk_pct/100
    st.metric("Risk budget per trade",f"₹{risk_budget:,.2f}")
    view["risk_per_share"]=(view["entry"]-view["stop_loss"]).clip(lower=0)
    view["risk_budget"]=risk_budget
    view["risk_qty"]=view.apply(lambda r:int(risk_budget/r["risk_per_share"]) if r["risk_per_share"]>0 else 0,axis=1)
    view["capital_qty"]=view.apply(lambda r:int(capital/r["entry"]) if r["entry"]>0 else 0,axis=1)
    view["suggested_qty"]=view[["risk_qty","capital_qty"]].min(axis=1).astype(int)
    view["capital_required"]=view["suggested_qty"]*view["entry"]
    view["actual_risk"]=view["suggested_qty"]*view["risk_per_share"]
    view["profit_T1"]=view["suggested_qty"]*(view["target1"]-view["entry"])
    view["profit_T2"]=view["suggested_qty"]*(view["target2"]-view["entry"])
    view["profit_T3"]=view["suggested_qty"]*(view["target3"]-view["entry"])
    st.caption("Share quantity is capped by both the selected risk budget and available capital (single-stock illustrative sizing).")
    st.metric("Candidates shown",len(view))
    columns=["symbol","exchange","tier","score","price","entry","stop_loss","target1","target2","target3","risk_per_share","suggested_qty","capital_required","actual_risk","profit_T1","profit_T2","profit_T3","rsi14","volume_ratio"]
    st.dataframe(view[[x for x in columns if x in view.columns]],use_container_width=True,hide_index=True)
    st.subheader("🧠 Why was this stock selected?")
    if not view.empty:
        choice=st.selectbox("Choose a candidate to explain",view["symbol"].astype(str).tolist())
        row=view[view["symbol"].astype(str)==choice].iloc[0]
        with st.expander(f"Setup breakdown: {choice}",expanded=True):
            st.markdown(f"**Score:** {int(row['score'])}/100 · **Tier:** {row['tier']}")
            checks=[
                ("Price above SMA20",bool(row.get("trend_up",False)), "Price above its 20-day average supports short-term trend."),
                ("SMA20 above SMA50",bool(row.get("trend_up",False)), "Trend alignment is a medium-term momentum confirmation."),
                ("20-day breakout",bool(row.get("breakout20",False)), "Price is above the previous 20-session high."),
                ("Relative volume ≥ 1.5",float(row.get("volume_ratio",0))>=1.5, f"Current daily volume is {float(row.get('volume_ratio',0)):.2f}× the 20-day average."),
                ("RSI in 50–70 zone",50<=float(row.get("rsi14",0))<=70, f"RSI(14): {float(row.get('rsi14',0)):.1f}."),
            ]
            for label,passed,detail in checks:
                st.write(("✅ " if passed else "⚪ "),label,"—",detail)
            st.write(f"**ATR(14):** ₹{float(row.get('atr14',row.get('atr',0))):.2f} where available")
            st.write(f"**Planned risk per share:** ₹{float(row['risk_per_share']):.2f} · **Quantity:** {int(row['suggested_qty'])}")
            st.caption("These checks describe the scanner's indicator confluence; they are not a forecast or guarantee. Trend fields and indicators reflect the latest available daily data.")
    st.download_button("⬇️ Download position plans CSV",view.to_csv(index=False).encode("utf-8"),"TraderPrp_Position_Plans.csv","text/csv",use_container_width=True)
else: st.info("No qualifying candidates yet. Scan additional batches.")
if progress and progress.get("records"):
    status_df=pd.DataFrame([{k:v for k,v in rec.items() if k!="result"} for rec in progress["records"].values()])
    if not status_df.empty:
        with st.expander("Stock scan status"):
            st.dataframe(status_df,use_container_width=True,hide_index=True)
            st.download_button("Download scan status CSV",status_df.to_csv(index=False).encode("utf-8"),"TraderPrp_Scan_Status.csv","text/csv")
st.caption("Daily candles for swing/momentum screening, not live intraday signals. Risk estimates exclude brokerage, slippage, taxes and gap risk. Scores are not probabilities or financial advice.")
