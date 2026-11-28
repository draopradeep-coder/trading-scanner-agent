def simulate_portfolio(trades, starting_capital=100000.0, risk_pct=0.005, max_allocation_pct=0.20, max_positions=5):
    """Chronological cash-equity portfolio simulation from single-exit trades.

    Prevents same-symbol overlap, limits simultaneous positions, sizes risk to a
    fraction of equity, and caps each position at a fraction of equity/cash.
    No costs, taxes, slippage, dividends, or intra-day portfolio ordering.
    """
    import pandas as pd
    df=pd.DataFrame(trades)
    if df.empty or not {'signal_date','exit_date','entry','exit','stop','symbol'}.issubset(df.columns):
        return {'trades':[], 'summary':{'starting_capital':starting_capital,'ending_capital':starting_capital,'trade_count':0,'return_pct':0,'max_drawdown_pct':0}}
    df['signal_date']=pd.to_datetime(df['signal_date']); df['exit_date']=pd.to_datetime(df['exit_date'])
    df['entry_date']=pd.to_datetime(df['entry_date']) if 'entry_date' in df.columns else df['signal_date']
    df=df.sort_values(['entry_date','symbol']).reset_index(drop=True)
    cash=float(starting_capital); active=[]; closed=[]; equity_points=[]; symbols_active=set(); skipped=[]
    if starting_capital<=0 or not (0<risk_pct<=1) or not (0<max_allocation_pct<=1) or max_positions<1:
        raise ValueError('Invalid simulation settings: capital must be positive, risk/allocation in (0,1], and max_positions >= 1')
    for _,row in df.iterrows():
        entry_date=row['entry_date']
        still=[]
        for p in active:
            if p['exit_date']<=entry_date:
                cash+=p['capital_used']+p['pnl']; closed.append(p); symbols_active.discard(p['symbol'])
            else: still.append(p)
        active=still
        sym=str(row['symbol'])
        if sym in symbols_active:
            skipped.append({'symbol':sym,'entry_date':str(entry_date.date()),'reason':'same_symbol_position_active'}); continue
        if len(active)>=max_positions:
            skipped.append({'symbol':sym,'entry_date':str(entry_date.date()),'reason':'max_positions_reached'}); continue
        if cash<=0:
            skipped.append({'symbol':sym,'entry_date':str(entry_date.date()),'reason':'insufficient_cash'}); continue
        try:
            entry=float(row['entry']); stop=float(row['stop']); exit_price=float(row['exit'])
        except (TypeError,ValueError):
            skipped.append({'symbol':sym,'entry_date':str(entry_date.date()),'reason':'invalid_trade_values'}); continue
        if entry<=0 or stop<=0 or stop>=entry or exit_price<=0:
            skipped.append({'symbol':sym,'entry_date':str(entry_date.date()),'reason':'invalid_price_or_stop'}); continue
        equity=cash+sum(p['capital_used']+p['pnl'] for p in active)
        risk_cash=max(0,equity*risk_pct); risk_per_share=entry-stop
        qty=int(risk_cash/risk_per_share) if risk_per_share>0 else 0
        cap_limit=min(cash,equity*max_allocation_pct)
        qty=min(qty,int(cap_limit/entry))
        if qty<=0:
            skipped.append({'symbol':sym,'entry_date':str(entry_date.date()),'reason':'position_size_zero'}); continue
        capital_used=qty*entry; pnl=qty*(exit_price-entry)
        p={'symbol':sym,'signal_date':str(pd.Timestamp(row['signal_date']).date()),'entry_date':str(entry_date.date()),'exit_date':pd.Timestamp(row['exit_date']),'entry':entry,'exit':exit_price,'stop':stop,'quantity':qty,'capital_used':round(capital_used,2),'pnl':round(pnl,2),'status':row.get('status','')}
        cash-=capital_used; active.append(p); symbols_active.add(sym)
    for p in active:
        cash+=p['capital_used']+p['pnl']; closed.append(p)
    ending=cash; total_return=(ending-starting_capital)/starting_capital*100 if starting_capital else 0
    for p in closed: p['exit_date']=str(pd.Timestamp(p['exit_date']).date())
    # Build a realized-equity ledger grouped by exit date, so trades exiting on
    # the same date are treated as one event rather than arbitrarily sequenced.
    grouped={}
    for p in closed:
        d=str(pd.Timestamp(p['exit_date']).date())
        grouped[d]=grouped.get(d,0.0)+float(p['pnl'])
    curve=[float(starting_capital)]; curve_dates=['Start']; running=float(starting_capital)
    for d in sorted(grouped):
        running+=grouped[d]; curve.append(round(running,2)); curve_dates.append(d)
    peak=curve[0]; maxdd=0.0
    for val in curve:
        peak=max(peak,val)
        if peak>0: maxdd=min(maxdd,(val-peak)/peak*100)
    curve_reconciles=bool(curve) and abs(curve[-1]-ending)<=0.01
    if not curve_reconciles: raise ValueError('Realized equity curve does not reconcile to ending capital')
    wins=[p['pnl'] for p in closed if p['pnl']>0]; losses=[p['pnl'] for p in closed if p['pnl']<0]
    summary={'starting_capital':round(starting_capital,2),'ending_capital':round(ending,2),'trade_count':len(closed),'return_pct':round(total_return,2),'win_rate_pct':round(len(wins)/len(closed)*100,2) if closed else 0,'profit_factor':round(sum(wins)/abs(sum(losses)),2) if losses else (float('inf') if wins else 0),'max_drawdown_pct':round(maxdd,2),'net_pnl':round(ending-starting_capital,2),'equity_curve_reconciles':curve_reconciles,'max_drawdown_method':'realized exit dates grouped','skipped_trade_count':len(skipped),'skip_reasons':{k:sum(1 for s in skipped if s['reason']==k) for k in sorted(set(s['reason'] for s in skipped))}}
    if abs(ending-(starting_capital+sum(p['pnl'] for p in closed)))>0.01: raise ValueError('Portfolio accounting reconciliation failed')
    return {'trades':closed,'skipped_trades':skipped,'summary':summary,'equity_curve':{'date':curve_dates,'equity':curve},'engine_version':'3'}
