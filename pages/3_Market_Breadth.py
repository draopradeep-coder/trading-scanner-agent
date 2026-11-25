import streamlit as st
import pandas as pd
from universe import load_full_universe
from market_breadth import analyze_breadth

st.set_page_config(page_title="TraderPrp | Market Breadth", page_icon="📊", layout="wide")
st.title("📊 Market Breadth Analysis")
st.caption("Market participation across the deduplicated cash-equity universe using daily adjusted prices.")

@st.cache_data(ttl=3600, show_spinner=False)
def load_universe():
    return load_full_universe()

try:
    universe, source_errors = load_universe()
except Exception as exc:
    st.error(f"Unable to load stock universe: {exc}")
    st.stop()
if source_errors:
    st.warning("Universe coverage may be partial because some sources failed.")
    for err in source_errors:
        st.caption(str(err))

listing_count = len(universe)
# Prefer NSE rows when the same ISIN is listed on both exchanges; use symbol fallback where ISIN is absent.
clean = universe.copy()
clean["_isin_key"] = clean.get("isin", pd.Series("", index=clean.index)).astype(str).str.strip().str.upper()
clean["_symbol_key"] = clean["symbol"].astype(str).str.strip().str.upper()
clean["_key"] = clean["_isin_key"].where(clean["_isin_key"].ne(""), clean["_symbol_key"])
clean["_exchange_rank"] = clean["exchange"].astype(str).str.upper().eq("NSE").map({True: 0, False: 1})
clean = clean.sort_values("_exchange_rank").drop_duplicates("_key", keep="first").drop(columns=["_isin_key", "_symbol_key", "_key", "_exchange_rank"])
universe = clean.reset_index(drop=True)
unique_count = len(universe)
st.metric("Listings loaded", f"{listing_count:,}")
st.metric("Unique stocks for breadth", f"{unique_count:,}", f"{listing_count-unique_count:,} duplicates/alternate listings removed")

CHUNK_SIZE = 120
if "breadth_state" not in st.session_state or st.session_state.breadth_state.get("total") != unique_count:
    st.session_state.breadth_state = {"offset": 0, "rows": [], "errors": [], "total": unique_count, "complete": False}
state = st.session_state.breadth_state

if not state.get("complete"):
    progress_label = "Progress: {:,} / {:,} unique stocks attempted".format(state["offset"], state["total"])
    st.progress(min(state["offset"] / max(state["total"], 1), 1.0), text=progress_label)
    label = "🔄 Calculate / Continue Market Breadth" if state["offset"] else "🔄 Calculate Market Breadth"
    if st.button(label, type="primary", use_container_width=True):
        end = min(state["offset"] + CHUNK_SIZE, len(universe))
        batch_universe = universe.iloc[state["offset"]:end]
        batch_label = "Calculating unique-stock batch {:,}–{:,} of {:,}...".format(state["offset"] + 1, end, len(universe))
        with st.spinner(batch_label):
            data, errors = analyze_breadth(batch_universe, batch_size=40)
        state["rows"].extend(data.to_dict("records"))
        state["errors"].extend(errors)
        state["offset"] = end
        state["complete"] = end >= len(universe)
        if state["complete"]:
            st.session_state.breadth_time = pd.Timestamp.now().strftime("%d %b %Y %H:%M")
        st.session_state.breadth_state = state
        st.rerun()
else:
    st.success("Market Breadth processing completed for the deduplicated stock universe.")
    if st.button("Start a fresh calculation", use_container_width=True):
        st.session_state.breadth_state = {"offset": 0, "rows": [], "errors": [], "total": unique_count, "complete": False}
        st.rerun()

data = pd.DataFrame(state["rows"])
if not data.empty:
    total = len(data)
    n20 = int(data["above_sma20"].sum())
    n50 = int(data["above_sma50"].sum())
    pct20 = n20 / total * 100
    pct50 = n50 / total * 100
    adv = int((data["change"] > 0).sum())
    dec = int((data["change"] < 0).sum())
    unchanged = total - adv - dec
    ratio = adv / dec if dec else float("inf")
    if pct20 >= 65 and pct50 >= 60 and adv > dec:
        pulse, note = "🟢 STRONG BREADTH", "Broad participation is supportive, though not a guarantee of continued gains."
    elif pct20 >= 45 or pct50 >= 45 or adv > dec:
        pulse, note = "🟡 MIXED BREADTH", "Participation is mixed. Prefer selective setups and risk control."
    else:
        pulse, note = "🔴 WEAK BREADTH", "Participation is weak across the sampled universe; be selective."
    st.subheader(pulse)
    st.write(note)
    coverage = total / max(unique_count, 1) * 100
    st.metric("Data coverage", f"{total:,}/{unique_count:,} unique stocks", f"{coverage:.1f}% usable price history")
    a,b,c,d=st.columns(4)
    a.metric("Above SMA20", f"{n20}/{total}", f"{pct20:.1f}%")
    b.metric("Above SMA50", f"{n50}/{total}", f"{pct50:.1f}%")
    c.metric("Advancing", adv, f"Declining: {dec}")
    d.metric("Advance/Decline", f"{ratio:.2f}" if ratio != float("inf") else "∞", f"Unchanged: {unchanged}")
    st.progress(pct20 / 100, text=f"SMA20 participation: {pct20:.1f}%")
    st.progress(pct50 / 100, text=f"SMA50 participation: {pct50:.1f}%")
    st.caption("Usable stocks: {:,} · Attempted: {:,}/{:,} unique stocks".format(total, state["offset"], state["total"]))
    if state["complete"]:
        st.caption("Last calculated: {}".format(st.session_state.get("breadth_time", "")))
    st.subheader("Stock participation data")
    view=data.sort_values("change", ascending=False).copy()
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download breadth data CSV", view.to_csv(index=False).encode("utf-8"), "TraderPrp_Market_Breadth.csv", "text/csv", use_container_width=True)
for error in state.get("errors", []):
    st.warning(error)
st.caption("Uses daily adjusted data from Yahoo Finance. Source availability, failed ticker batches and market holidays may affect coverage. This is a screening tool, not financial advice.")
