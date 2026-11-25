"""Daily technical scanner for NSE/BSE cash equities; resumable local progress."""
import json, os, time
import pandas as pd
import numpy as np
import yfinance as yf

STATE_FILE = "scanner_progress.json"

def _rsi(close, period=14):
    delta=close.diff()
    gain=delta.clip(lower=0).rolling(period).mean()
    loss=-delta.clip(upper=0).rolling(period).mean()
    rs=gain/loss.replace(0,np.nan)
    return 100-(100/(1+rs))

def _tier(score):
    if score >= 85: return "A+"
    if score >= 70: return "A"
    if score >= 55: return "B"
    return "C"

def _scan_one_status(row):
    symbol=str(row.get("symbol","")).strip()
    exchange=str(row.get("exchange","")).upper()
    if not symbol: return {"status":"failed","reason":"Missing symbol"}
    ticker=symbol+(".NS" if exchange=="NSE" else ".BO")
    df=None; last_error=""
    for attempt in range(3):
        try:
            df=yf.download(ticker,period="6mo",interval="1d",auto_adjust=True,progress=False,threads=False)
            if df is not None and not df.empty and len(df)>=55: break
            last_error="Insufficient or unavailable daily data"
        except Exception as e:
            last_error=str(e)[:180]
        if attempt<2: time.sleep(1.5*(2**attempt))
    if df is None or df.empty or len(df)<55:
        return {"status":"failed","reason":last_error or "Insufficient data"}
    try:
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        close,high,low,volume=[df[c].squeeze() for c in ("Close","High","Low","Volume")]
        price=float(close.iloc[-1]); sma20=float(close.rolling(20).mean().iloc[-1]); sma50=float(close.rolling(50).mean().iloc[-1])
        rsi=float(_rsi(close).iloc[-1])
        tr=pd.concat([high-low,(high-close.shift()).abs(),(low-close.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1]); avgvol=float(volume.rolling(20).mean().iloc[-1])
        volratio=float(volume.iloc[-1]/avgvol) if avgvol and np.isfinite(avgvol) else 0
        prior_high=float(high.iloc[-21:-1].max()); breakout=price>prior_high; trend=price>sma20>sma50
        score=int((25 if price>sma20 else 0)+(25 if sma20>sma50 else 0)+(20 if breakout else 0)+(15 if volratio>=1.5 else 0)+(15 if 50<=rsi<=70 else 0))
        entry=price; stop=entry-1.5*atr; risk=entry-stop
        result={"symbol":symbol,"exchange":exchange,"ticker":ticker,"price":round(price,2),"rsi14":round(rsi,1),"atr14":round(atr,2),"volume_ratio":round(volratio,2),"sma20":round(sma20,2),"sma50":round(sma50,2),"breakout20":bool(breakout),"trend_up":bool(trend),"score":score,"tier":_tier(score),"entry":round(entry,2),"stop_loss":round(stop,2),"target1":round(entry+risk,2),"target2":round(entry+2*risk,2),"target3":round(entry+3*risk,2),"setup":"Swing / momentum (daily data)"}
        return {"status":"analyzed","result":result,"candidate":score>=40}
    except Exception as e:
        return {"status":"failed","reason":str(e)[:180]}

def load_progress():
    try:
        with open(STATE_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def clear_progress():
    try: os.remove(STATE_FILE)
    except FileNotFoundError: pass

def scan_batch(universe,batch_size=40,retry_failed=False):
    rows=universe.to_dict("records")
    state=load_progress() or {"records":{},"universe_total":len(rows)}
    records=state.get("records",{}); state["universe_total"]=len(rows); pending=[]
    for i,row in enumerate(rows):
        key=f'{str(row.get("exchange","")).upper()}:{str(row.get("symbol","")).strip()}'
        existing=records.get(key)
        if existing and existing.get("status")=="analyzed": continue
        if existing and existing.get("status")=="failed" and not retry_failed: continue
        pending.append((i,key,row))
    pending=pending[:max(1,int(batch_size))]
    for n,(i,key,row) in enumerate(pending):
        outcome=_scan_one_status(row)
        records[key]={"symbol":str(row.get("symbol","")),"exchange":str(row.get("exchange","")),"status":outcome["status"],"reason":outcome.get("reason",""),"candidate":bool(outcome.get("candidate",False)),"result":outcome.get("result")}
        if n<len(pending)-1: time.sleep(.35)
    state["records"]=records; state["updated"]=pd.Timestamp.now().isoformat()
    with open(STATE_FILE,"w",encoding="utf-8") as f: json.dump(state,f,ensure_ascii=False)
    results=[v["result"] for v in records.values() if v.get("status")=="analyzed" and v.get("candidate") and v.get("result")]
    candidates=pd.DataFrame(results)
    if not candidates.empty: candidates=candidates.sort_values(["score","volume_ratio"],ascending=False).reset_index(drop=True)
    status=pd.DataFrame([{k:v for k,v in rec.items() if k!="result"} for rec in records.values()])
    summary={"requested":len(rows),"processed":len(records),"analyzed":sum(v.get("status")=="analyzed" for v in records.values()),"failed":sum(v.get("status")=="failed" for v in records.values()),"candidates":len(candidates),"pending":max(0,len(rows)-len(records)),"updated":state["updated"]}
    return candidates,summary,status

def scan_universe_with_status(universe,limit=None,workers=6):
    rows=universe if limit is None else universe.head(int(limit))
    clear_progress()
    candidates,summary,status=scan_batch(rows,batch_size=len(rows),retry_failed=True)
    summary["status_rows"]=status
    return candidates,summary

def scan_universe(universe,limit=None,workers=6):
    return scan_universe_with_status(universe,limit,workers)[0]
