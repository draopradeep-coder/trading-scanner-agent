import streamlit as st
import pandas as pd

from universe import load_full_universe
from universe_validation import validate_universe

st.set_page_config(page_title="TraderPrp | Stock Universe", page_icon="📚", layout="wide")
st.title("📚 NSE + BSE Stock Universe")
st.caption("Exchange listings and validation — universe foundation, not live trading signals.")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_universe():
    return load_full_universe()

if st.button("🔄 Refresh Stock Universe", type="primary"):
    st.cache_data.clear()

with st.spinner("Fetching exchange listings. This may take a moment..."):
    try:
        universe, source_errors = fetch_universe()
    except Exception as exc:
        st.error(f"Universe download failed: {exc}")
        st.info("The exchange sources may temporarily block or change their download format. Please retry later.")
        st.stop()

valid, issues = validate_universe(universe)

if source_errors:
    st.warning("Some exchange sources reported errors; results may be partial.")
    for error in source_errors:
        st.caption(str(error))

c1, c2, c3 = st.columns(3)
c1.metric("Total Listing Rows", len(universe))
c2.metric("NSE Rows", int(universe["exchange"].astype(str).str.upper().eq("NSE").sum()) if "exchange" in universe else 0)
c3.metric("BSE Rows", int(universe["exchange"].astype(str).str.upper().eq("BSE").sum()) if "exchange" in universe else 0)

if valid:
    st.success("Validation passed")
else:
    st.warning("Validation returned issues")
if issues:
    for issue in issues:
        st.write("•", issue)

st.subheader("Listing Data")
search = st.text_input("Search symbol, company name or ISIN")
filtered = universe.copy()
if search:
    mask = pd.Series(False, index=filtered.index)
    for col in ["symbol", "name", "isin"]:
        if col in filtered:
            mask |= filtered[col].astype(str).str.contains(search, case=False, na=False)
    filtered = filtered[mask]
exchange_choice = st.selectbox("Exchange", ["All", "NSE", "BSE"])
if exchange_choice != "All" and "exchange" in filtered:
    filtered = filtered[filtered["exchange"].astype(str).str.upper().eq(exchange_choice)]
st.caption(f"Showing {len(filtered)} rows")
st.dataframe(filtered, use_container_width=True, hide_index=True)
st.download_button("⬇️ Download Universe CSV", data=filtered.to_csv(index=False).encode("utf-8"), file_name="TraderPrp_Stock_Universe.csv", mime="text/csv")
st.caption("Listings are fetched from source files and cached for one hour. Confirm listing eligibility before trading.")
