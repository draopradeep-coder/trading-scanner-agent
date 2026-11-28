def simulate_staged_portfolio(trades, starting_capital=100000.0, risk_pct=0.005, max_allocation_pct=0.20, max_positions=5):
    import pandas as pd
    from monitoring_engine import monitor_trade
    rows=pd.DataFrame(trades)
    if rows.empty: return {'summary':{'starting_capital':starting_capital,'ending_capital':starting_capital,'trade_count':0,'net_pnl':0},'trades':[],'equity_curve':[]}
    rows['entry_date']=pd.to_datetime(rows['entry_date'],errors='coerce'); rows=rows.sort_values(['entry_date','symbol'],kind='stable')
    cash=float(starting_capital); active=[]; results=[]; curve=[{'date':'Start','equity':cash}]
    for _,row in rows.iterrows():
        ed=row['entry_date']; sym=str(row['symbol'])
        released=[]; remain=[]
        for p in active:
            if p['end_date']<=ed: cash+=p['capital']+p['pnl']; released.append(p); results.append(p)
            else: remain.append(p)
        active=remain
        if pd.isna(ed) or any(p['symbol']==sym for p in active) or len(active)>=max_positions: continue
        try: entry=float(row['entry']); stop=float(row['stop']);
        except: continue
        if entry<=stop or entry<=0: continue
        equity=cash+sum(p['capital'] for p in active); qty=min(int(equity*risk_pct/(entry-stop)),int(min(cash,equity*max_allocation_pct)/entry))
        if qty<1: continue
        path=pd.DataFrame(row.get('staged_bar_path',[]) or [])
        if path.empty: continue
        if 'Date' not in path: continue
        outcome=monitor_trade(ed,entry,stop,[float(row['target1']),float(row['target2']),float(row['target3'])],path,quantities=[int(qty/3),int(qty/3),qty-2*int(qty/3)])
        ev=outcome.get('events',[]); pnl=float(outcome.get('realized_pnl',0))+float(outcome.get('unrealized_pnl',0)); end_date=pd.to_datetime(path['Date']).max()
        if ev: end_date=pd.to_datetime(ev[-1]['date'])
        p={'symbol':sym,'entry_date':str(ed.date()),'end_date':str(end_date.date()),'entry':entry,'stop':stop,'quantity':qty,'capital':qty*entry,'realized_pnl':outcome.get('realized_pnl',0),'unrealized_pnl':outcome.get('unrealized_pnl',0),'net_pnl':round(pnl,2),'status':outcome.get('status'),'events':ev,'targets_hit':outcome.get('targets_hit')}
        cash-=qty*entry; active.append({**p,'end_date':end_date,'pnl':pnl});
    results+=active
    ending=starting_capital+sum(p['net_pnl'] for p in results); wins=[p['net_pnl'] for p in results if p['net_pnl']>0]; losses=[p['net_pnl'] for p in results if p['net_pnl']<0]
    return {'trades':results,'summary':{'starting_capital':round(starting_capital,2),'ending_capital':round(ending,2),'net_pnl':round(ending-starting_capital,2),'return_pct':round((ending-starting_capital)/starting_capital*100,2),'trade_count':len(results),'win_rate_pct':round(100*len(wins)/len(results),2) if results else 0,'profit_factor':round(sum(wins)/abs(sum(losses)),2) if losses else (float('inf') if wins else 0),'method':'staged partial exits; approximate concurrency, no costs'},'equity_curve':curve}
