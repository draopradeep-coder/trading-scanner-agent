import streamlit as st
from market_regime import detect_market_regime

@st.cache_data(ttl=900, show_spinner=False)
def load_regime():
    return detect_market_regime()

st.markdown("""<style>.block-container{padding-top:1.4rem}.hero{padding:1.5rem;border-radius:18px;background:linear-gradient(120deg,#101827,#263b58);color:white}</style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>📈 TraderPrp Trading Scanner</h1><p>Indian cash-equity research • Daily momentum & swing setups</p><p>Market context first. Stock selection second. Risk awareness always.</p></div>',unsafe_allow_html=True)
st.subheader("🌡️ Market overview")
if st.button("🔄 Refresh market overview", key="home_market_overview_refresh_v2"): load_regime.clear()
with st.spinner("Loading benchmark context..."): result=load_regime()
regime=result.get("regime","UNKNOWN")
st.metric("Market Regime • NIFTY 50 + Bank Nifty confirmation",regime)
details=result.get("details",{})
cols=st.columns(2)
for col,name in zip(cols,["NIFTY 50","BANK NIFTY"]):
 with col:
  d=details.get(name)
  if d:
   st.markdown(f"**{name}**"); st.metric("Latest close (daily data)",f"{d['price']:,.2f}",f"20-session change: {d['change20']*100:+.2f}%"); st.caption(f"SMA20 {d['sma20']:,.2f} · SMA50 {d['sma50']:,.2f}")
  else: st.warning(f"{name}: unavailable")
st.caption(result.get("message",""))
if result.get("issues"): st.warning("Data issues: "+"; ".join(result["issues"]))
st.subheader("🛡️ Market Risk Meter")
n=details.get("NIFTY 50"); b=details.get("BANK NIFTY")
if n:
 score=int(n["price"]>n["sma20"])+int(n["price"]>n["sma50"])+int(n["sma50"]>n["sma50_prev"])
 if b: score+=int(b["price"]>b["sma20"]>b["sma50"]); score+=int(b["price"]>b["sma50"])
 maxscore=5 if b else 3
 if score>=maxscore-1: label="FAVORABLE"; guidance="Trend conditions are supportive. Still validate individual setups and risk."
 elif score>=maxscore//2: label="CAUTIOUS"; guidance="Mixed conditions. Prefer stronger setups and avoid chasing extended prices."
 else: label="DEFENSIVE"; guidance="Weak trend conditions. Tighten selectivity and prioritize capital preservation."
 st.metric("Rule-based risk status",label,f"Trend score {score}/{maxscore}")
 st.write(guidance)
 st.caption("Score uses NIFTY price vs SMA20/SMA50 and SMA50 direction, with Bank Nifty trend confirmation when data is available. It is a heuristic—not a forecast or probability.")
else: st.warning("Risk Meter unavailable because NIFTY data could not be loaded.")

# Optional breadth snapshot; on-demand to keep Home fast.
st.subheader("📊 Market Breadth Snapshot")
st.caption("Participation across the loaded cash-equity universe. Optional scan; may take several minutes.")
@st.cache_data(ttl=3600, show_spinner=False)
def load_breadth_snapshot():
 from universe import load_full_universe
 from market_breadth import analyze_breadth
 universe, source_errors = load_full_universe()
 data, errors = analyze_breadth(universe)
 return data, source_errors, errors, len(universe)
if st.button("🔄 Calculate / Refresh Breadth", use_container_width=True, key="home_refresh_market_breadth"):
 load_breadth_snapshot.clear()
 st.session_state.pop("home_breadth_error",None)
 with st.spinner("Scanning daily prices for market participation..."):
  try: st.session_state["home_breadth"] = load_breadth_snapshot()
  except Exception as exc: st.session_state["home_breadth_error"] = str(exc)
if st.session_state.get("home_breadth_error"): st.warning("Breadth unavailable: "+st.session_state["home_breadth_error"])
snapshot=st.session_state.get("home_breadth")
if snapshot:
 data,source_errors,scan_errors,universe_count=snapshot
 if data is not None and not data.empty:
  total=len(data); n20=int(data["above_sma20"].sum()); n50=int(data["above_sma50"].sum())
  pct20=n20/total*100; pct50=n50/total*100; adv=int((data["change"]>0).sum()); dec=int((data["change"]<0).sum())
  cols=st.columns(3)
  cols[0].metric("Above SMA20",f"{pct20:.1f}%",f"{n20}/{total}")
  cols[1].metric("Above SMA50",f"{pct50:.1f}%",f"{n50}/{total}")
  cols[2].metric("Advancing / Declining",f"{adv} / {dec}")
  st.progress(pct20/100,text=f"SMA20 participation: {pct20:.1f}%")
  st.progress(pct50/100,text=f"SMA50 participation: {pct50:.1f}%")
  if pct20>=60 and pct50>=55 and adv>dec: st.success("Broad participation is supportive.")
  elif pct20<40 and pct50<40 and dec>=adv: st.warning("Participation looks weak. Be selective.")
  else: st.info("Breadth is mixed. Prioritize stronger setups and risk control.")
  st.caption(f"Usable data: {total} of {universe_count} loaded rows. Coverage may be partial.")
 else: st.warning("No usable breadth data returned.")
 for issue in list(source_errors or [])+list(scan_errors or []): st.caption("Data issue: "+str(issue))
st.subheader("Research workflow")
c1,c2,c3=st.columns(3)
with c1: st.markdown("### 🔎 Stock research"); st.write("Explore the stock universe and daily-bar momentum candidates.")
with c2: st.markdown("### 📊 Market participation"); st.write("Check market breadth before individual stocks.")
with c3: st.markdown("### 🏭 Sector strength"); st.write("Review sector rotation and relative strength.")
st.info("Suggested workflow: Market Regime → Market Breadth → Sector Rotation → Automatic Scanner.")
st.caption("Educational research tool only—not financial advice. Verify data and risk independently.")
