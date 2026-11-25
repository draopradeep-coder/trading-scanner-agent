import streamlit as st
from market_regime import detect_market_regime

st.set_page_config(page_title="TraderPrp | Trading Scanner", page_icon="📈", layout="wide")
pages = {"Home": [st.Page("app.py", title="Home", icon="🏠", default=True)],"Stock Research": [st.Page("pages/1_Stock_Universe.py", title="Stock Universe", icon="📚"), st.Page("pages/2_Automatic_Scanner.py", title="Automatic Scanner", icon="🔎")],"Market Intelligence": [st.Page("pages/3_Market_Breadth.py", title="Market Breadth", icon="📊"), st.Page("pages/4_Sector_Rotation.py", title="Sector Rotation", icon="🏭")],"Tools": [st.Page("pages/5_Excel_Dashboard.py", title="Excel Dashboard", icon="📁")] }
page=st.navigation(pages)
@st.cache_data(ttl=900,show_spinner=False)
def load_regime(): return detect_market_regime()
if page==pages["Home"][0]:
 st.markdown("""<style>.block-container{padding-top:1.4rem}.hero{padding:1.5rem;border-radius:18px;background:linear-gradient(120deg,#101827,#263b58);color:white}</style>""",unsafe_allow_html=True)
 st.markdown('<div class="hero"><h1>📈 TraderPrp Trading Scanner</h1><p>Indian cash-equity research • Daily momentum & swing setups</p><p>Market context first. Stock selection second. Risk awareness always.</p></div>',unsafe_allow_html=True)
 st.subheader("🌡️ Market overview")
 if st.button("🔄 Refresh market overview"): load_regime.clear()
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
 st.subheader("Research workflow")
 c1,c2,c3=st.columns(3)
 with c1: st.markdown("### 🔎 Stock research"); st.write("Explore the stock universe and daily-bar momentum candidates.")
 with c2: st.markdown("### 📊 Market participation"); st.write("Check market breadth before individual stocks.")
 with c3: st.markdown("### 🏭 Sector strength"); st.write("Review sector rotation and relative strength.")
 st.info("Suggested workflow: Market Regime → Market Breadth → Sector Rotation → Automatic Scanner.")
 st.caption("Educational research tool only—not financial advice. Verify data and risk independently.")
page.run()
