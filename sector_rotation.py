import pandas as pd
import yfinance as yf

SECTORS = {
    "Nifty Auto": "^CNXAUTO", "Nifty Bank": "^NSEBANK", "Nifty Financial Services": "^CNXFINANCE",
    "Nifty FMCG": "^CNXFMCG", "Nifty IT": "^CNXIT", "Nifty Media": "^CNXMEDIA",
    "Nifty Metal": "^CNXMETAL", "Nifty Pharma": "^CNXPHARMA", "Nifty Realty": "^CNXREALTY",
    "Nifty Energy": "^CNXENERGY", "Nifty PSU Bank": "^CNXPSUBANK", "Nifty Infrastructure": "^CNXINFRA",
    "Nifty Oil & Gas": "^CNXOG", "Nifty Consumer Durables": "^CNXCONSUM", "Nifty Healthcare": "^CNXHEALTH"
}

def fetch_sector_rotation():
    data = yf.download(list(SECTORS.values()), period="6mo", interval="1d", auto_adjust=True, group_by="ticker", progress=False, threads=False)
    rows=[]; errors=[]
    for name,ticker in SECTORS.items():
        try:
            close=data[ticker]["Close"].dropna()
            if len(close)<55: raise ValueError("Insufficient history")
            latest=float(close.iloc[-1]); r20=(latest/float(close.iloc[-21])-1)*100; r50=(latest/float(close.iloc[-51])-1)*100
            sma20=float(close.rolling(20).mean().iloc[-1]); sma50=float(close.rolling(50).mean().iloc[-1])
            rows.append({"sector":name,"index":ticker,"price":latest,"return_20d_pct":r20,"return_50d_pct":r50,"above_sma20":latest>sma20,"above_sma50":latest>sma50})
        except Exception as e: errors.append(f"{name}: {e}")
    df=pd.DataFrame(rows)
    if not df.empty:
        df["rank"]=(df["return_20d_pct"].rank(ascending=False)+df["return_50d_pct"].rank(ascending=False))/2
        df=df.sort_values("rank").reset_index(drop=True)
        df["status"] = df.apply(lambda r: "Leading" if r.return_20d_pct>0 and r.return_50d_pct>0 and r.above_sma20 and r.above_sma50 else "Improving" if r.return_20d_pct>0 else "Weakening",axis=1)
    return df,errors
