"""Technical scanner for NSE/BSE cash equities using Yahoo Finance daily bars."""
import concurrent.futures
import pandas as pd
import numpy as np
import yfinance as yf


def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _scan_one(row):
    symbol, exchange = str(row.get("symbol", "")).strip(), str(row.get("exchange", "")).upper()
    if not symbol:
        return None
    ticker = symbol + (".NS" if exchange == "NSE" else ".BO")
    try:
        df = yf.download(ticker, period="6mo", interval="1d", auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty or len(df) < 55:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]
        close = close.squeeze(); high = high.squeeze(); low = low.squeeze(); volume = volume.squeeze()
        last = float(close.iloc[-1]); sma20 = float(close.rolling(20).mean().iloc[-1]); sma50 = float(close.rolling(50).mean().iloc[-1])
        rsi = float(_rsi(close).iloc[-1]) if pd.notna(_rsi(close).iloc[-1]) else 50.0
        tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        avgvol = float(volume.rolling(20).mean().iloc[-1]); vratio = float(volume.iloc[-1]/avgvol) if avgvol else 0
        prior_high = float(high.iloc[-21:-1].max()); breakout = last > prior_high
        trend = last > sma20 > sma50
        score = int((25 if last > sma20 else 0)+(25 if sma20 > sma50 else 0)+(20 if breakout else 0)+(15 if vratio >= 1.5 else 0)+(15 if 50 <= rsi <= 70 else 0))
        if score < 40:
            return None
        entry = last
        stop = entry - 1.5*atr
        risk = entry-stop
        return {"symbol":symbol,"exchange":exchange,"ticker":ticker,"price":round(last,2),"rsi14":round(rsi,1),"atr14":round(atr,2),"volume_ratio":round(vratio,2),"sma20":round(sma20,2),"sma50":round(sma50,2),"breakout20":breakout,"trend_up":trend,"score":score,"entry":round(entry,2),"stop_loss":round(stop,2),"target1":round(entry+risk,2),"target2":round(entry+2*risk,2),"target3":round(entry+3*risk,2),"setup":"Swing / momentum (daily data)"}
    except Exception:
        return None


def scan_universe(universe, limit=None, workers=8):
    """Scan listing rows; optionally limit rows for testing. Returns sorted DataFrame."""
    rows = universe.to_dict("records")
    if limit:
        rows = rows[:int(limit)]
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(_scan_one, rows):
            if result:
                results.append(result)
    out=pd.DataFrame(results)
    if not out.empty:
        out=out.sort_values(["score","volume_ratio"],ascending=False).reset_index(drop=True)
    return out
