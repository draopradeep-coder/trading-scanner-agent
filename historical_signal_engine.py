"""Point-in-time historical signals for NSE/BSE cash equities.
Only bars through the signal date are used for indicators; entry is next session open.
"""
import numpy as np
import pandas as pd

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

def historical_signal(daily, signal_pos):
    """Return signal/next-open trade levels, or None. daily requires OHLCV."""
    if daily is None or signal_pos < 54 or signal_pos + 1 >= len(daily): return None
    bars=daily.iloc[:signal_pos+1].copy()
    if isinstance(bars.columns,pd.MultiIndex): bars.columns=bars.columns.get_level_values(0)
    close,high,low,volume=[bars[c].squeeze() for c in ("Close","High","Low","Volume")]
    price=float(close.iloc[-1]); sma20=float(close.rolling(20).mean().iloc[-1]); sma50=float(close.rolling(50).mean().iloc[-1])
    rsi=float(_rsi(close).iloc[-1])
    tr=pd.concat([high-low,(high-close.shift()).abs(),(low-close.shift()).abs()],axis=1).max(axis=1)
    atr=float(tr.rolling(14).mean().iloc[-1]); avgvol=float(volume.rolling(20).mean().iloc[-1])
    volratio=float(volume.iloc[-1]/avgvol) if avgvol and np.isfinite(avgvol) else 0.0
    prior_high=float(high.iloc[-21:-1].max()); breakout=price>prior_high
    score=int((25 if price>sma20 else 0)+(25 if sma20>sma50 else 0)+(20 if breakout else 0)+(15 if volratio>=1.5 else 0)+(15 if 50<=rsi<=70 else 0))
    if score < 40 or not np.isfinite(atr) or atr<=0: return None
    nextbar=daily.iloc[signal_pos+1]
    if isinstance(nextbar,pd.DataFrame): nextbar=nextbar.iloc[0]
    entry=float(nextbar["Open"]); risk=1.5*atr
    stop=entry-risk
    return {"signal_date":str(bars.index[-1].date()),"entry_date":str(daily.index[signal_pos+1].date()),"signal_close":round(price,2),"entry":round(entry,2),"atr14_signal":round(atr,2),"score":score,"tier":_tier(score),"rsi14":round(rsi,1),"volume_ratio":round(volratio,2),"breakout20":bool(breakout),"sma20":round(sma20,2),"sma50":round(sma50,2),"stop_loss":round(stop,2),"target1":round(entry+risk,2),"target2":round(entry+2*risk,2),"target3":round(entry+3*risk,2)}
