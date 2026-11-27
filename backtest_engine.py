def simulate_trade(signal_date, entry, stop, targets, daily_bars, max_bars=60):
    """Conservative long cash-equity single-exit simulation.

    Entry is supplied by the caller (historical signal workflows should use
    the next session open). Bars must be strictly after signal_date. If stop
    and a target are touched on the same session, stop is assumed first.
    This is a level-touch test, not a partial-exit portfolio simulation.
    """
    import pandas as pd
    try:
        entry=float(entry); stop=float(stop); targets=[float(x) for x in targets]
    except (TypeError, ValueError):
        return {"status":"INVALID"}
    if entry<=0 or stop<=0 or stop>=entry or not targets or any(t<=entry for t in targets):
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
    levels=sorted(set(targets))
    status="OPEN"; exit_price=None; exit_date=None; bars_held=0
    target_hits={f"TP{i}":False for i in range(1,4)}
    first_target=None
    for bars_held, (_, bar) in enumerate(bars.iterrows(), start=1):
        low=float(bar["Low"]); high=float(bar["High"])
        open_price=float(bar["Open"]) if "Open" in bar and pd.notna(bar["Open"]) else None
        # Gap through stop: fill at session open, not at the stop level.
        if open_price is not None and open_price<=stop:
            exit_price=open_price; exit_date=bar["Date"]; status="STOP_GAP"; break
        # Same-day stop/target ambiguity resolved conservatively.
        if low<=stop:
            exit_price=stop; exit_date=bar["Date"]; status="STOP"; break
        for i, target in enumerate(levels, start=1):
            if high>=target:
                target_hits[f"TP{i}"]=True
                if first_target is None:
                    first_target=target
                    status=f"TARGET_{i}"
                    exit_price=open_price if open_price is not None and open_price>=target else target
                    exit_date=bar["Date"]
        if first_target is not None:
            break
    if status=="OPEN":
        last=bars.iloc[-1]
        exit_price=float(last["Close"]); exit_date=last["Date"]; status="TIME_EXIT"
    pnl=float(exit_price)-entry
    return {
        "signal_date":str(start.date()),"exit_date":str(pd.Timestamp(exit_date).date()),
        "entry":round(entry,2),"stop":round(stop,2),"exit":round(float(exit_price),2),
        "status":status,"pnl_per_share":round(pnl,2),
        "return_pct":round(pnl/entry*100,2),"bars_held":bars_held,
        **{f"{k}_hit":v for k,v in target_hits.items()},
        "note":"Single-exit level-touch simulation; no fees, slippage, partial exits, dividends or overlapping portfolio constraints. Conservative stop-first rule for same-session ambiguity."
    }

def summarize_backtest(results):
    """Aggregate single-exit results; values are per-share, not portfolio returns."""
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
        "message":"Research helper only. P&L sums per-share results across trades; no portfolio sizing or costs."
    }
