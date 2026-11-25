import streamlit as st

st.set_page_config(page_title="TraderPrp | Trading Scanner", page_icon="📈", layout="wide")
st.markdown("""<style> .block-container{padding-top:2rem;} .hero{padding:2rem 1.5rem;border-radius:18px;background:linear-gradient(120deg,#101827,#263b58);color:white;} .hero h1{font-size:2.5rem;} .tile{padding:1rem;border:1px solid rgba(128,128,128,.3);border-radius:14px;} </style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>📈 TraderPrp Trading Scanner</h1><p>Indian cash-equity research • Daily momentum & swing setups</p><p>Market context first. Stock selection second. Risk awareness always.</p></div>',unsafe_allow_html=True)
st.write("")
st.subheader("Your research workspace")
cols=st.columns(3)
with cols[0]:
 st.markdown("### 🔎 Automatic Scanner\nFind daily-bar momentum and swing candidates across the available stock universe.")
with cols[1]:
 st.markdown("### 🌡️ Market Regime\nCheck broader market conditions before evaluating individual setups.")
with cols[2]:
 st.markdown("### 📊 Market Breadth & Sector Rotation\nExplore participation and relative strength across sectors.")
st.info("Use the navigation menu to open the scanner, market breadth, sector rotation and other research pages. The Excel-based dashboard is available as a separate page.")
st.markdown("---")
st.caption("TraderPrp • Educational research tool only, not financial advice. Verify data, prices and trade risk independently.")
