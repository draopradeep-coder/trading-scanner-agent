import pandas as pd

def evaluate_trade_setup(df, min_rr=1.5, max_extension_pct=8.0, max_risk_pct=8.0):
    """Filter stock setups using price, entry, stop and target columns where present."""
    out=df.copy()
    def pick(cols):
        for c in cols:
            if c in out.columns:return c
        return None
    entry=pick(["entry","entry_price","buy_price","close","Close"])
    stop=pick(["stop_loss","sl","stop","Stop Loss"])
    target=pick(["target1","target_1","target","t1","Target 1"])
    if not entry or not stop or not target:
        out["setup_quality"] = "Not evaluated"
        out["quality_reason"] = "Entry/stop/target fields unavailable"
        out["risk_reward"] = pd.NA
        out["risk_pct"] = pd.NA
        out["extension_pct"] = pd.NA
        return out, "missing fields"
    e=pd.to_numeric(out[entry],errors="coerce"); s=pd.to_numeric(out[stop],errors="coerce"); t=pd.to_numeric(out[target],errors="coerce")
    risk=e-s; reward=t-e
    out["risk_pct"]=(risk/e*100).round(2)
    out["risk_reward"]=(reward/risk).round(2)
    out["extension_pct"] = pd.to_numeric(out.get("extension_pct",0),errors="coerce").fillna(0)
    valid=(e>0)&(s>0)&(t>e)&(s<e)&(risk>0)
    rr_ok=out["risk_reward"]>=min_rr
    risk_ok=out["risk_pct"]<=max_risk_pct
    extension_ok=out["extension_pct"]<=max_extension_pct
    out["setup_quality"] = "Reject"
    out.loc[valid & rr_ok & risk_ok & extension_ok,"setup_quality"] = "Pass"
    reasons=[]
    for i in out.index:
        r=[]
        if not bool(valid.loc[i]):r.append("invalid entry/stop/target geometry")
        if not bool(rr_ok.loc[i]):r.append(f"RR below {min_rr}:1")
        if not bool(risk_ok.loc[i]):r.append(f"risk exceeds {max_risk_pct}%")
        if not bool(extension_ok.loc[i]):r.append(f"extension exceeds {max_extension_pct}%")
        reasons.append("; ".join(r) if r else "All checks passed")
    out["quality_reason"] = reasons
    return out, "evaluated"
