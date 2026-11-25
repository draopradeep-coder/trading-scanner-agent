import streamlit as st
import pandas as pd
from sector_rotation import fetch_sector_rotation

st.set_page_config(page_title="TraderPrp | Sector Rotation",page_icon="🏭",layout="wide")
st.title("🏭 Sector Strength & Rotation")
st.caption("Ranks Indian sector indices by 20- and 50-session performance and trend alignment.")
if st.button("🔄 Refresh Sector Analysis",type="primary",use_container_width=True):
    with st.spinner("Fetching sector index daily data..."):
        df,errors=fetch_sector_rotation(); st.session_state["sector_data"]=df; st.session_state["sector_errors"]=errors; st.session_state["sector_time"]=pd.Timestamp.now().strftime("%d %b %Y %H:%M")
df=st.session_state.get("sector_data")
if df is not None and not df.empty:
    leaders=df[df.status=="Leading"]
    a,b,c=st.columns(3); a.metric("Sector indices covered",len(df)); b.metric("Leading sectors",len(leaders)); c.metric("Top sector",df.iloc[0].sector)
    st.subheader("Ranked sector rotation")
    st.caption("Ranks combine relative 20- and 50-session returns; classifications are descriptive, not forecasts.")
    st.dataframe(df[["rank","sector","return_20d_pct","return_50d_pct","above_sma20","above_sma50","status"]],use_container_width=True,hide_index=True)
    st.subheader("Strongest sectors")
    st.write(", ".join(leaders.sector.tolist()) if not leaders.empty else "No sectors currently meet the leading criteria.")
    st.download_button("⬇️ Download sector data CSV",df.to_csv(index=False).encode("utf-8"),"TraderPrp_Sector_Rotation.csv","text/csv",use_container_width=True)
    st.caption(f"Last refreshed: {st.session_state.get('sector_time','')}")
    for e in st.session_state.get("sector_errors",[]): st.warning(e)
else: st.info("Press Refresh Sector Analysis to load rankings.")
st.caption("Yahoo Finance sector-index data may be delayed, unavailable, or incomplete. This is a cash-equity research tool, not financial advice.")
