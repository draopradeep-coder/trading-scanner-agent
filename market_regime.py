"""Simple market regime classifier using daily benchmark index data."""
import yfinance as yf
import pandas as pd

def detect_market_regime():
    symbols={"NIFTY 50":"^NSEI","BANK NIFTY":"^NSEBANK"}
    data={}
    issues=[]
    for name,ticker in symbols.items():
        try:
            df=yf.download(ticker,period="6mo",interval="1d",auto_adjust=True,progress=False,threads=False)
            if df is None or df.empty or len(df)<55:
                issues.append(f"{name}: insufficient data")
                continue
            close=df["Close"]
            if isinstance(close,pd.DataFrame): close=close.iloc[:,0]
            data[name]={
                "price":float(close.iloc[-1]),
                "sma20":float(close.rolling(20).mean().iloc[-1]),
                "sma50":float(close.rolling(50).mean().iloc[-1]),
                "sma50_prev":float(close.rolling(50).mean().iloc[-6]),
                "change20":float(close.iloc[-1]/close.iloc[-21]-1)
            }
        except Exception as e:
            issues.append(f"{name}: {str(e)[:100]}")
    if "NIFTY 50" not in data:
        return {"regime":"UNKNOWN","details":data,"issues":issues,"message":"Nifty benchmark data unavailable; candidate gating disabled."}
    n=data["NIFTY 50"]
    bullish=n["price"]>n["sma20"]>n["sma50"] and n["sma50"]>n["sma50_prev"]
    bearish=n["price"]<n["sma20"]<n["sma50"] and n["sma50"]<n["sma50_prev"]
    bank=data.get("BANK NIFTY")
    bank_bull=bool(bank and bank["price"]>bank["sma20"]>bank["sma50"])
    bank_bear=bool(bank and bank["price"]<bank["sma20"]<bank["sma50"])
    if bullish and (bank_bull or not bank): regime="BULLISH"
    elif bearish and (bank_bear or not bank): regime="BEARISH"
    else: regime="SIDEWAYS / MIXED"
    return {"regime":regime,"details":data,"issues":issues,"message":"Classification uses benchmark price, 20/50-day averages and SMA50 direction. Bank Nifty is a confirmation, not a prediction."}
