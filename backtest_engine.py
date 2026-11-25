def simulate_trade(signal_date, entry, stop, targets, daily_bars, max_bars=60):
    """Simulate a long cash-equity trade from post-signal daily OHLC bars.
    If stop and target are both touched on one bar, assume stop first (conservative).
    daily_bars must contain Date, High, Low, Close columns and be after signal_date.
    """
    import pandas as pd
    try:
        entry=float(entry); stop=float(stop); targets=[float(x) for x in targets]
    except (TypeError,ValueError):
        return {"status":"INVALID"}
    if entry<=0 or stop<=0 or stop>=entry or not targets:
        return {"status":"INVALID"}
    bars=daily_bars.copy()
    required={"Date","High","Low","Close"}
    if not required.issubset(bars.columns):
        return {"status":"INVALID_DATA","reason":"Requires Date, High, Low, Close"}
    bars["Date"]=pd.to_datetime(bars["Date"])
    start=pd.to_datetime(signal_date)
    bars=bars[bars["Date"]>start].sort_values("Date").head(max_bars)
    if bars.empty:
        return {"status":"NO_FORWARD_DATA"}
    levels=sorted(targets)
    booked=0
    exit_price=None
    exit_date=None
    status="OPEN"
    for _,bar in bars.iterrows():
        low=float(bar["Low"]); high=float(bar["High"])
        # Conservative stop-first handling when both stop and a target are hit.
        if low<=stop:
            exit_price=stop; exit_date=bar["Date"]; status="STOP"
            break
        reached=[t for t in levels if high>=t]
        if reached:
            exit_price=max(reached); exit_date=bar["Date"]; status=f"TARGET_{levels.index(exit_price)+1}"
            break
    if status=="OPEN":
        last=bars.iloc[-1]
        exit_price=float(last["Close"]); exit_date=last["Date"]
        status="TIME_EXIT"
    pnl=exit_price-entry
    return {
        "signal_date":str(start.date()),"exit_date":str(pd.Timestamp(exit_date).date()),
        "entry":round(entry,2),"stop":round(stop,2),"exit":round(exit_price,2),
        "status":status,"pnl_per_share":round(pnl,2),
        "return_pct":round(pnl/entry*100,2),"bars_held":int(len(bars)),
        "note":"Simplified single-exit simulation. No fees, slippage, partial exits, dividends or portfolio overlap. Stop-first rule used for same-bar ambiguity."
    }

def summarize_backtest(results):
    """Aggregate dictionaries returned by simulate_trade."""
    import pandas as pd
    df=pd.DataFrame(results)
    if df.empty or "pnl_per_share" not in df:
        return {"trades":0,"win_rate_pct":0,"total_return_pct_sum":0,"message":"No results"}
    pnl=pd.to_numeric(df["pnl_per_share"],errors="coerce").dropna()
    winners=pnl[pnl>0]; losers=pnl[pnl<0]
    gp=float(winners.sum()); gl=float(abs(losers.sum()))
    return {
        "trades":int(len(pnl)),"wins":int((pnl>0).sum()),
        "losses":int((pnl<0).sum()),"breakeven":int((pnl==0).sum()),
        "win_rate_pct":round(float((pnl>0).mean()*100),2) if len(pnl) else 0,
        "average_win_per_share":round(float(winners.mean()),2) if len(winners) else 0,
        "average_loss_per_share":round(float(losers.mean()),2) if len(losers) else 0,
        "profit_factor":round(gp/gl,2) if gl else (float("inf") if gp else 0),
        "total_pnl_per_share_sum":round(float(pnl.sum()),2),
        "message":"Research helper only; not a validated portfolio backtest. P&L sums per-share results across trades."
    }
