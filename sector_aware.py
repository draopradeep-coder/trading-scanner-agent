import streamlit as st
import yfinance as yf
import pandas as pd

# Yahoo Finance sector labels are mapped only when a clear broad-sector match exists.
MAP={"Automotive":"Nifty Auto","Auto Manufacturers":"Nifty Auto","Banks":"Nifty Bank","Banking":"Nifty Bank","Financial Services":"Nifty Financial Services","Insurance":"Nifty Financial Services","Financial":"Nifty Financial Services","Consumer Defensive":"Nifty FMCG","Food & Beverage":"Nifty FMCG","Consumer Staples":"Nifty FMCG","Technology":"Nifty IT","Information Technology":"Nifty IT","Communication Services":"Nifty Media","Entertainment":"Nifty Media","Basic Materials":"Nifty Metal","Materials":"Nifty Metal","Pharmaceuticals":"Nifty Pharma","Healthcare":"Nifty Healthcare","Real Estate":"Nifty Realty","Energy":"Nifty Energy","Oil & Gas":"Nifty Oil & Gas","Utilities":"Nifty Energy","Industrial":"Nifty Infrastructure","Industrials":"Nifty Infrastructure"}

@st.cache_data(ttl=86400,show_spinner=False)
def _sector_for(ticker):
    try:
        info=yf.Ticker(ticker).get_info()
        raw=info.get("sector") or info.get("industry") or "Unknown"
        return raw,MAP.get(raw,"")
    except Exception:
        return "Unknown",""

@st.cache_data(ttl=1800,show_spinner=False)
def _sector_rotation():
    from sector_rotation import fetch_sector_rotation
    df,errors=fetch_sector_rotation()
    if df is None or df.empty: return {},errors
    return {str(r.sector):str(r.status) for r in df.itertuples()},errors

def apply_sector_context(candidates):
    out=candidates.copy()
    out["sector"] = "Unknown"; out["sector_status"] = "Unknown"; out["sector_bonus"] = 0
    if out.empty: return out
    # Keep lookups bounded; lower-ranked names retain neutral sector context.
    indices=out.sort_values("score",ascending=False).head(50).index
    status_map,errors=_sector_rotation()
    for idx in indices:
        row=out.loc[idx]
        raw,sector=_sector_for(str(row.get("ticker","")))
        if not sector:
            # Unknown classifications are not guessed.
            out.loc[idx,"sector"] = raw
            continue
        status=status_map.get(sector,"Unknown")
        bonus=8 if status=="Leading" else 4 if status=="Improving" else 0
        out.loc[idx,"sector"] = sector
        out.loc[idx,"sector_status"] = status
        out.loc[idx,"sector_bonus"] = bonus
    out["sector_bonus"] = pd.to_numeric(out["sector_bonus"],errors="coerce").fillna(0).astype(int)
    out["sector_rank_score"] = out["score"] + out["sector_bonus"]
    return out
