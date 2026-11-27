import streamlit as st
import pandas as pd
import yfinance as yf
from historical_signal_engine import historical_signal
from backtest_engine import simulate_trade, summarize_backtest
from portfolio_engine import simulate_portfolio

st.title("🧪 Historical Strategy Backtest")
st.caption("Research-only backtest for NSE/BSE cash equities. Data availability and survivorship bias limit conclusions.")
up=st.file_uploader("Upload stock universe CSV or Excel (or scanner report)",type=["csv","xlsx","xls"])
if up:
    frames = {'CSV': pd.read_csv(up)} if up.name.lower().endswith('.csv') else pd.read_excel(up, sheet_name=None)
    aliases = ['symbol','ticker','tradingsymbol','trading symbol','stock symbol','scrip','scrip code','stock','stocks']
    found=[]
    for sheet, frame in frames.items():
        frame.columns=[str(c).strip().lower().replace('_',' ').replace('-',' ') for c in frame.columns]
        col=next((c for c in frame.columns if c in aliases),None)
        if col:
            excol=next((c for c in frame.columns if c in ['exchange','exch']),None)
            temp=pd.DataFrame({'symbol':frame[col]})
            temp['exchange']=frame[excol] if excol else 'NSE'
            found.append(temp)
    if not found:
        st.error("No recognizable stock-symbol column found. Expected Symbol, Ticker, Trading Symbol, or Scrip.")
    else:
        uni=pd.concat(found,ignore_index=True)
        uni['symbol']=uni['symbol'].astype(str).str.strip().str.upper()
        uni['exchange']=uni['exchange'].astype(str).str.strip().str.upper()
        uni.loc[~uni['exchange'].isin(['NSE','BSE']),'exchange']='NSE'
        uni=uni[~uni['symbol'].isin(['', 'NAN', 'NONE', 'NULL', '<NA>'])].drop_duplicates()
        st.success(f"Recognized {len(uni)} symbols across uploaded sheet(s).")
        with st.expander("Preview detected symbols"):
            st.dataframe(uni.head(30),hide_index=True,use_container_width=True)
        limit=st.number_input("Maximum symbols for this run",min_value=1,max_value=300,value=min(30,len(uni)))
        if st.button("Run historical test",type="primary"):
            outcomes=[]; signals=[]; failures=[]; progress=st.progress(0); batch=uni.head(int(limit))
            for ix,row in enumerate(batch.itertuples(index=False),start=1):
                sym=str(row.symbol).strip().upper(); exch=str(row.exchange).upper().strip(); base_sym=sym.removesuffix('.NS').removesuffix('.BO'); tickers=[base_sym+('.NS' if exch=='NSE' else '.BO'),base_sym+('.BO' if exch=='NSE' else '.NS')]
                try:
                    df=None; download_errors=[]
                    for ticker in tickers:
                        try:
                            candidate=yf.download(ticker,period='5y',interval='1d',auto_adjust=True,progress=False,threads=False)
                            if candidate is not None and not candidate.empty:
                                df=candidate; break
                        except Exception as de: download_errors.append(f'{ticker}: {str(de)[:90]}')
                    if df is not None and not df.empty:
                        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                        df=df.dropna(subset=['Open','High','Low','Close','Volume'])
                        for pos in range(54,len(df)-1):
                            sig=historical_signal(df,pos)
                            if not sig: continue
                            sig['symbol']=sym; sig['exchange']=exch; signals.append(sig)
                            fwd=df.iloc[pos+2:].reset_index(); fwd=fwd.rename(columns={fwd.columns[0]:'Date'})
                            result=simulate_trade(sig['entry_date'],sig['entry'],sig['stop_loss'],[sig['target1'],sig['target2'],sig['target3']],fwd,max_bars=60)
                            if result.get('status') not in ('INVALID','INVALID_DATA','NO_FORWARD_DATA'):
                                result.update({'symbol':sym,'exchange':exch,'score':sig['score'],'tier':sig['tier'],'target1':sig['target1'],'target2':sig['target2'],'target3':sig['target3']}); outcomes.append(result)
                    else: failures.append(f'{sym} ({exch}): no data from tickers {tickers}')
                except Exception as e: failures.append(f'{sym} ({exch}): {str(e)[:180]}')
                progress.progress(ix/int(limit))
            st.session_state['bt_signals']=signals; st.session_state['bt_outcomes']=outcomes; st.session_state['bt_failures']=failures
            st.success(f"Completed: {len(signals)} signals | {len(outcomes)} simulated trades | {len(failures)} failures")
if st.session_state.get('bt_failures'):
    with st.expander('View data failures'):
        st.write(st.session_state['bt_failures'])
if 'bt_outcomes' in st.session_state:
    trades=pd.DataFrame(st.session_state['bt_outcomes']); sigs=pd.DataFrame(st.session_state.get('bt_signals',[]))
    if trades.empty: st.warning("No trade outcomes available in this run.")
    else:
        stats=summarize_backtest(trades.to_dict('records'))
        c=st.columns(4); c[0].metric("Trades",stats['trades']); c[1].metric("Win rate",f"{stats['win_rate_pct']}%"); c[2].metric("Profit factor",stats['profit_factor']); c[3].metric("Per-share P&L sum",stats['total_pnl_per_share_sum'])
        st.caption("P&L sums per-share outcomes across trades (not portfolio returns). Fees, slippage, position sizing, overlapping trades and dividends are excluded.")
        st.warning("Signals may overlap in time, including multiple trades in the same stock. These results are signal-level research, not portfolio performance.")
        st.subheader("Portfolio simulation (non-overlapping, risk-sized)")
        capital=st.number_input("Starting capital (₹)",min_value=10000,value=100000,step=10000,key="bt_capital")
        risk=st.slider("Risk per trade (% of equity)",min_value=0.1,max_value=2.0,value=0.5,step=0.1,key="bt_risk")
        alloc=st.slider("Max allocation per trade (% of equity)",min_value=5,max_value=50,value=20,step=5,key="bt_alloc")
        maxpos=st.slider("Maximum simultaneous positions",min_value=1,max_value=10,value=5,key="bt_maxpos")
        port=simulate_portfolio(trades.to_dict("records"),starting_capital=float(capital),risk_pct=float(risk)/100,max_allocation_pct=float(alloc)/100,max_positions=int(maxpos))
        ps=port["summary"]; pm=st.columns(4); pm[0].metric("Ending capital",f"₹{ps['ending_capital']:,.0f}"); pm[1].metric("Portfolio return",f"{ps['return_pct']}%"); pm[2].metric("Portfolio PF",ps['profit_factor']); pm[3].metric("Max drawdown",f"{ps['max_drawdown_pct']}%")
        st.caption("Approximate portfolio simulation: one active trade per symbol, risk-sized, capped position allocation and concurrent positions. No fees, taxes, slippage or dividends. Exit-time event ordering is simplified.")
        if port["trades"]: st.dataframe(pd.DataFrame(port["trades"]),hide_index=True,use_container_width=True)
        st.subheader("Outcome distribution")
        st.bar_chart(trades['status'].value_counts())
        st.subheader("Trades")
        st.dataframe(trades,hide_index=True,use_container_width=True)
        st.download_button("Download trade results CSV",trades.to_csv(index=False),file_name="historical_backtest_results.csv")
        if not sigs.empty: st.subheader("Generated signals"); st.dataframe(sigs,hide_index=True,use_container_width=True); st.download_button("Download signals CSV",sigs.to_csv(index=False),file_name="historical_signals.csv")
else:
    st.info("Upload a universe file to start. Use modest symbol batches first; Yahoo historical data may be incomplete.")
