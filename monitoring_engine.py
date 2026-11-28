def monitor_trade(entry_date, entry, stop, targets, daily_bars, quantities=None, move_stop_to_breakeven=True):
    """Monitor a long cash-equity trade through OHLC bars using staged exits.
    Stop-first ambiguity is conservative. Target allocations default to thirds.
    Returns event log, realized P&L, remaining shares and final status.
    """
    import pandas as pd
    try: entry=float(entry); stop=float(stop); targets=[float(x) for x in targets]
    except Exception: return {'status':'INVALID','events':[]}
    if entry<=0 or stop<=0 or stop>=entry or len(targets)!=3 or any(x<=entry for x in targets): return {'status':'INVALID','events':[]}
    bars=daily_bars.copy(); required={'Date','Open','High','Low','Close'}
    if not required.issubset(bars.columns): return {'status':'INVALID_DATA','events':[]}
    bars['Date']=pd.to_datetime(bars['Date'],errors='coerce'); bars=bars[bars['Date']>pd.to_datetime(entry_date)].sort_values('Date')
    alloc=quantities if quantities is not None else [1/3,1/3,1/3]
    if len(alloc)!=3 or sum(alloc)<=0 or any(x<0 for x in alloc): return {'status':'INVALID_ALLOCATIONS','events':[]}
    alloc=[float(x)/sum(alloc) for x in alloc]; total=int(10000 if quantities is None else sum(quantities)); remaining=int(total); portions=[int(total*x) for x in alloc]; portions[-1]=total-sum(portions[:-1])
    events=[]; realized=0.0; active_stop=float(stop); hit=[False]*3; status='OPEN'
    for _,bar in bars.iterrows():
        if remaining<=0: status='CLOSED'; break
        op=float(bar['Open']); hi=float(bar['High']); lo=float(bar['Low']); date=str(bar['Date'].date())
        if op<=active_stop or lo<=active_stop:
            fill=op if op<=active_stop else active_stop; pnl=(fill-entry)*remaining; realized+=pnl
            events.append({'date':date,'event':'STOP','fill_price':round(fill,2),'quantity':round(remaining,4),'pnl':round(pnl,2),'stop':round(active_stop,2)})
            remaining=0; status='STOP'; break
        for i,target in enumerate(targets):
            if not hit[i] and hi>=target and remaining>0:
                q=min(remaining,int(portions[i])); fill=op if op>=target else target; pnl=(fill-entry)*q; realized+=pnl; remaining-=q; hit[i]=True
                events.append({'date':date,'event':f'TP{i+1}','fill_price':round(fill,2),'quantity':round(q,4),'pnl':round(pnl,2)})
                if i==0 and move_stop_to_breakeven: active_stop=max(active_stop,entry)
        if remaining<=1e-8: status='TARGETS_COMPLETED'; break
    if remaining>0 and len(bars):
        last=bars.iloc[-1]; mark=float(last['Close']); status='OPEN';
    else: mark=entry if remaining<=0 else entry
    return {'status':status,'events':events,'realized_pnl':round(realized,2),'remaining_quantity':round(remaining,4),'remaining_mark':round(mark,2),'unrealized_pnl':round((mark-entry)*remaining,2),'stop_current':round(active_stop,2),'targets_hit':hit,'breakeven_after_tp1':bool(move_stop_to_breakeven),'note':'Partial exits modeled; OHLC stop-first ambiguity; allocations are approximate fractions. No costs, slippage or taxes.'}
