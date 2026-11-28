def simulate_portfolio(trades, starting_capital=100000.0, risk_pct=0.005, max_allocation_pct=0.20, max_positions=5):
    """Daily-close mark-to-market portfolio simulation, research only."""
    import pandas as pd
    df=pd.DataFrame(trades)
    if df.empty or not {'signal_date','exit_date','entry','exit','stop','symbol'}.issubset(df.columns):
        return {'trades':[], 'summary':{'starting_capital':starting_capital,'ending_capital':starting_capital,'trade_count':0,'return_pct':0,'max_drawdown_pct':0},'equity_curve':{'date':['Start'],'equity':[starting_capital]}}
    df['signal_date']=pd.to_datetime(df['signal_date'],errors='coerce'); df['exit_date']=pd.to_datetime(df['exit_date'],errors='coerce')
    df['entry_date']=pd.to_datetime(df['entry_date'],errors='coerce') if 'entry_date' in df.columns else df['signal_date']
    df=df.sort_values(['entry_date','symbol','signal_date'],kind='stable').reset_index(drop=True)
    if starting_capital<=0 or not (0<risk_pct<=1) or not (0<max_allocation_pct<=1) or max_positions<1: raise ValueError('Invalid simulation settings')
    def path_for(row):
        vals={}
        for item in row.get('price_path',[]) or []:
            try:
                d=pd.Timestamp(item['date']).normalize(); v=float(item['close'])
                if v>0: vals[d]=v
            except Exception: pass
        return vals
    cash=float(starting_capital); active=[]; closed=[]; skipped=[]
    for _,row in df.iterrows():
        ed=row['entry_date']; xd=row['exit_date']; sym=str(row['symbol'])
        if pd.isna(ed) or pd.isna(xd) or xd<ed: skipped.append({'symbol':sym,'reason':'invalid_date_order'}); continue
        still=[]
        for p in active:
            if p['exit_date']<=ed: cash+=p['capital_used']+p['pnl']; closed.append(p)
            else: still.append(p)
        active=still
        if any(p['symbol']==sym for p in active): skipped.append({'symbol':sym,'entry_date':str(ed.date()),'reason':'same_symbol_position_active'}); continue
        if len(active)>=max_positions: skipped.append({'symbol':sym,'entry_date':str(ed.date()),'reason':'max_positions_reached'}); continue
        try: entry=float(row['entry']); stop=float(row['stop']); exit_price=float(row['exit'])
        except Exception: skipped.append({'symbol':sym,'reason':'invalid_trade_values'}); continue
        if entry<=0 or stop<=0 or stop>=entry or exit_price<=0: skipped.append({'symbol':sym,'reason':'invalid_price_or_stop'}); continue
        for p in active:
            prior=[(d,v) for d,v in p['price_path'].items() if d<=ed.normalize()]
            if prior: p['last_price']=max(prior,key=lambda z:z[0])[1]
        mtm=sum(p['quantity']*p['last_price'] for p in active); equity=cash+mtm
        qty=int(max(0,equity*risk_pct)/(entry-stop)); qty=min(qty,int(min(cash,equity*max_allocation_pct)/entry))
        if qty<=0: skipped.append({'symbol':sym,'entry_date':str(ed.date()),'reason':'position_size_zero'}); continue
        capital_used=qty*entry; pnl=qty*(exit_price-entry); px=path_for(row)
        p={'symbol':sym,'signal_date':str(pd.Timestamp(row['signal_date']).date()),'entry_date':ed.normalize(),'exit_date':xd.normalize(),'entry':entry,'exit':exit_price,'stop':stop,'quantity':qty,'capital_used':round(capital_used,2),'pnl':round(pnl,2),'status':row.get('status',''),'price_path':px,'last_price':entry}
        cash-=capital_used; active.append(p)
    selected=active+closed; all_dates=set()
    for p in selected: all_dates.update(p['price_path'].keys()); all_dates.add(p['entry_date']); all_dates.add(p['exit_date'])
    all_dates=sorted(all_dates); curve_dates=['Start']; curve=[float(starting_capital)]; cash_curve=float(starting_capital); open_positions={}; entries={}; exits={}
    for p in selected: entries.setdefault(p['entry_date'],[]).append(p); exits.setdefault(p['exit_date'],[]).append(p)
    for d in all_dates:
        for p in entries.get(d,[]): cash_curve-=p['capital_used']; open_positions[p['symbol']]=p
        for p in open_positions.values():
            if d in p['price_path']: p['last_price']=p['price_path'][d]
        for p in exits.get(d,[]): cash_curve+=p['capital_used']+p['pnl']; open_positions.pop(p['symbol'],None)
        curve_dates.append(str(d.date())); curve.append(round(cash_curve+sum(p['quantity']*p['last_price'] for p in open_positions.values()),2))
    ending=float(curve[-1]); peak=curve[0]; maxdd=0.0
    for v in curve: peak=max(peak,v); maxdd=min(maxdd,(v-peak)/peak*100 if peak>0 else 0)
    pnl_sum=sum(p['pnl'] for p in selected); reconciles=abs(ending-(starting_capital+pnl_sum))<=0.01
    if not reconciles: raise ValueError('MTM equity curve failed final accounting reconciliation')
    for p in selected: p.pop('price_path',None); p.pop('last_price',None)
    wins=[p['pnl'] for p in selected if p['pnl']>0]; losses=[p['pnl'] for p in selected if p['pnl']<0]
    summary={'starting_capital':round(starting_capital,2),'ending_capital':round(ending,2),'trade_count':len(selected),'return_pct':round((ending-starting_capital)/starting_capital*100,2),'win_rate_pct':round(len(wins)/len(selected)*100,2) if selected else 0,'profit_factor':round(sum(wins)/abs(sum(losses)),2) if losses else (float('inf') if wins else 0),'max_drawdown_pct':round(maxdd,2),'net_pnl':round(ending-starting_capital,2),'equity_curve_reconciles':reconciles,'max_drawdown_method':'daily close mark-to-market; exit dates use exit fills','skipped_trade_count':len(skipped),'skip_reasons':{k:sum(1 for s in skipped if s['reason']==k) for k in sorted(set(s['reason'] for s in skipped))}}
    return {'trades':selected,'skipped_trades':skipped,'summary':summary,'equity_curve':{'date':curve_dates,'equity':curve},'engine_version':'4'}
