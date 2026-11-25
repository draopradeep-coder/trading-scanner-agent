import pandas as pd

def apply_multifactor(df):
    out=df.copy()
    if out.empty: return out
    base=pd.to_numeric(out.get("score",0),errors="coerce").fillna(0).clip(0,100)*0.70
    trend=out.get("trend_up",False).astype(bool).astype(int)*10
    breakout=out.get("breakout20",False).astype(bool).astype(int)*8
    vol=pd.to_numeric(out.get("volume_ratio",0),errors="coerce").fillna(0)
    volume_factor=vol.apply(lambda x: 6 if x>=2 else 4 if x>=1.5 else 2 if x>=1 else 0)
    rsi=pd.to_numeric(out.get("rsi14",0),errors="coerce").fillna(0)
    rsi_factor=rsi.apply(lambda x: 6 if 55<=x<=68 else 3 if 50<=x<55 or 68<x<=72 else 0)
    # Sector context is a small additional ranking overlay (maximum 8 points).
    sec=pd.to_numeric(out.get("sector_bonus",0),errors="coerce").fillna(0).clip(0,8)
    total=(base+trend+breakout+volume_factor+rsi_factor+sec).round().astype(int)
    out["factor_rank_score"]=total
    out["factor_breakdown"]=[f"Base {int(b)} / 70 · Trend {int(t)} / 10 · Breakout {int(br)} / 8 · Volume {int(v)} / 6 · RSI {int(r)} / 6 · Sector {int(s)} / 8" for b,t,br,v,r,s in zip(base,trend,breakout,volume_factor,rsi_factor,sec)]
    return out
