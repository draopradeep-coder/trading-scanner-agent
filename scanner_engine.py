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

def _scan_one_status(row):
    symbol = str(row.get("symbol", "")).strip()
    exchange = str(row.get("exchange", "")).upper()
    if not symbol:
        return {"status": "failed", "reason": "Missing symbol"}
    ticker = symbol + (".NS" if exchange == "NSE" else ".BO")
    try:
        df = yf.download(ticker, period="6mo", interval="1d", auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty or len(df) < 55:
            return {"status": "failed", "reason": "Insufficient or unavailable daily data"}
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]
        close = close.squeeze(); high = high.squeeze(); low = low.squeeze(); volume = volume.squeeze()
        last = float(close.iloc[-1])
        sma20 = float(close.rolling(20).mean().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        rsi = float(_rsi(close).iloc[-1])
        tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        avgvol = float(volume.rolling(20).mean().iloc[-1])
        vratio = float(volume.iloc[-1]/avgvol) if avgvol else 0
        prior_high = float(high.iloc[-21:-1].max())
        breakout = last > prior_high
        trend = last > sma20 > sma50
        score = int((25 if last>sma20 else 0)+(25 if sma20>sma50 else 0)+(20 if breakout else 0)+(15 if vratio>=1.5 else 0)+(15 if 50<=rsi<=70 else 0))
        entry=last; stop=entry-1.5*atr; risk=entry-stop
        rowout={"symbol":symbol,"exchange":exchange,"ticker":ticker,"price":round(last,2),"rsi14":round(rsi,1),"atr14":round(atr,2),"volume_ratio":round(vratio,2),"sma20":round(sma20,2),"sma50":round(sma50,2),"breakout20":bool(breakout),"trend_up":bool(trend),"score":score,"entry":round(entry,2),"stop_loss":round(stop,2),"target1":round(entry+risk,2),"target2":round(entry+2*risk,2),"target3":round(entry+3*risk,2),"setup":"Swing / momentum (daily data)"}
        return {"status":"analyzed","result":rowout,"candidate":score>=40}
    except Exception as e:
        return {"status":"failed","reason":str(e)[:180]}

def scan_universe_with_status(universe, limit=None, workers=6):
    """Return candidates and detailed scan status counts/records."""
    rows=universe.to_dict("records")
    if limit: rows=rows[:int(limit)]
    results=[]; status_rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(_scan_one_status,row) for row in rows]
        for row,f in zip(rows,futures):
            outcome=f.result()
            symbol=str(row.get("symbol","")); exch=str(row.get("exchange",""))
            status_rows.append({"symbol":symbol,"exchange":exch,"status":outcome["status"],"reason":outcome.get("reason","")})
            if outcome["status"]=="analyzed" and outcome.get("candidate"):
                results.append(outcome["result"])
    candidates=pd.DataFrame(results)
    if not candidates.empty:
        candidates=candidates.sort_values(["score","volume_ratio"],ascending=False).reset_index(drop=True)
    status=pd.DataFrame(status_rows)
    summary={"requested":len(rows),"analyzed":int((status["status"]=="analyzed").sum()) if not status.empty else 0,"failed":int((status["status"]=="failed").sum()) if not status.empty else 0,"candidates":len(candidates),"status_rows":status}
    return candidates,summary

def scan_universe(universe, limit=None, workers=6):
    """Backward-compatible candidate-only API."""
    results,_=scan_universe_with_status(universe,limit=limit,workers=workers)
    return results
