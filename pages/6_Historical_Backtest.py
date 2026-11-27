import streamlit as st
import pandas as pd
import yfinance as yf
from historical_signal_engine import historical_signal
from backtest_engine import simulate_trade, summarize_backtest

st.title("🧪 Historical Strategy Backtest")
st.caption("Research-only backtest for NSE/BSE cash equities. Upload a symbol universe; data availability and survivorship bias limit conclusions.")
up=st.file_uploader("Upload stock universe CSV or Excel (symbol, exchange columns)",type=["csv","xlsx","xls"])
if up:
        uni=pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
        uni.columns=[str(c).strip().lower() for c in uni.columns]
        if 'symbol' not in uni.columns: st.error("Universe must contain a symbol column.")
        else:
            if 'exchange' not in uni: uni['exchange']='NSE'
            uni=uni[['symbol','exchange']].dropna().drop_duplicates()
            limit=st.number_input("Maximum symbols for this run",min_value=1,max_value=300,value=min(30,len(uni)))
            st.write(f"Universe rows: {len(uni)}")
            if st.button("Run historical test",type="primary"):
                outcomes=[]; signals=[]; progress=st.progress(0)
                for ix,row in uni.head(int(limit)).iterrows():
                    sym=str(row['symbol']).strip(); exch=str(row['exchange']).upper().strip(); ticker=sym+('.NS' if exch=='NSE' else '.BO')
                    try:
                        df=yf.download(ticker,period='5y',interval='1d',auto_adjust=True,progress=False,threads=False)
                        if df is not None and not df.empty:
                            if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                            df=df.dropna(subset=['Open','High','Low','Close','Volume'])
                            for pos in range(54,len(df)-1):
                                sig=historical_signal(df,pos)
                                if not sig: continue
                                sig['symbol']=sym; sig['exchange']=exch
                                signals.append(sig)
                                fwd=df.iloc[pos+2:].reset_index()
                                datecol=fwd.columns[0]; fwd=fwd.rename(columns={datecol:'Date'})
                                result=simulate_trade(sig['entry_date'],sig['entry'],sig['stop_loss'],[sig['target1'],sig['target2'],sig['target3']],fwd,max_bars=60)
                                if result.get('status') not in ('INVALID','INVALID_DATA','NO_FORWARD_DATA'):
                                    result.update({'symbol':sym,'exchange':exch,'score':sig['score'],'tier':sig['tier'],'target1':sig['target1'],'target2':sig['target2'],'target3':sig['target3']})
                                    outcomes.append(result)
                    except Exception as e: pass
                    progress.progress(min(1,(len(outcomes)+len(signals))/max(1,int(limit)*10)))
                st.session_state['bt_signals']=signals; st.session_state['bt_outcomes']=outcomes
                st.success(f"Completed: {len(signals)} signals | {len(outcomes)} simulated trades")
if 'bt_outcomes' in st.session_state:
    trades=pd.DataFrame(st.session_state['bt_outcomes']); sigs=pd.DataFrame(st.session_state.get('bt_signals',[]))
    if trades.empty: st.warning("No trade outcomes available in this run.")
    else:
        stats=summarize_backtest(trades.to_dict('records'))
        c=st.columns(4); c[0].metric("Trades",stats['trades']); c[1].metric("Win rate",f"{stats['win_rate_pct']}%"); c[2].metric("Profit factor",stats['profit_factor']); c[3].metric("Per-share P&L sum",stats['total_pnl_per_share_sum'])
        st.caption("P&L sums per-share outcomes across trades (not portfolio returns). Fees, slippage, position sizing, overlapping trades and dividends are excluded.")
        st.subheader("Outcome distribution")
        st.bar_chart(trades['status'].value_counts())
        st.subheader("Trades")
        st.dataframe(trades,hide_index=True,use_container_width=True)
        st.download_button("Download trade results CSV",trades.to_csv(index=False),file_name="historical_backtest_results.csv")
        if not sigs.empty: st.subheader("Generated signals"); st.dataframe(sigs,hide_index=True,use_container_width=True); st.download_button("Download signals CSV",sigs.to_csv(index=False),file_name="historical_signals.csv")
else:
    st.info("Upload a universe file to start. Use modest symbol batches first; Yahoo historical data may be incomplete.")
