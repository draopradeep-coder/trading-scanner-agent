import pandas as pd

JOURNAL_COLUMNS = [
    "date","symbol","setup","side","entry","exit","quantity","stop_loss",
    "target1","target2","target3","status","notes"
]

def create_trade_journal():
    """Create an empty journal DataFrame for cash-equity swing trades."""
    return pd.DataFrame(columns=JOURNAL_COLUMNS)

def analyze_trade_journal(journal):
    """Summarize recorded trades. P&L is computed from entry/exit and quantity."""
    if journal is None or journal.empty:
        return {"trades":0,"wins":0,"losses":0,"win_rate_pct":0.0,
                "total_pnl":0.0,"average_win":0.0,"average_loss":0.0,
                "profit_factor":None,"message":"Journal is empty."}
    df=journal.copy()
    for col in ["entry","exit","quantity"]:
        if col not in df.columns:
            return {"message":f"Missing required column: {col}"}
        df[col]=pd.to_numeric(df[col],errors="coerce")
    df=df.dropna(subset=["entry","exit","quantity"])
    df=df[(df["entry"]>0)& (df["quantity"]>0)]
    if df.empty:
        return {"message":"No valid closed trades found."}
    df["pnl"]=(df["exit"]-df["entry"])*df["quantity"]
    wins=df[df["pnl"]>0]["pnl"]
    losses=df[df["pnl"]<0]["pnl"]
    gross_profit=float(wins.sum())
    gross_loss=float(abs(losses.sum()))
    return {
        "trades":int(len(df)),
        "wins":int((df["pnl"]>0).sum()),
        "losses":int((df["pnl"]<0).sum()),
        "breakeven":int((df["pnl"]==0).sum()),
        "win_rate_pct":round(float((df["pnl"]>0).mean()*100),2),
        "total_pnl":round(float(df["pnl"].sum()),2),
        "average_win":round(float(wins.mean()),2) if len(wins) else 0.0,
        "average_loss":round(float(losses.mean()),2) if len(losses) else 0.0,
        "profit_factor":round(gross_profit/gross_loss,2) if gross_loss else (float("inf") if gross_profit else 0.0),
        "gross_profit":round(gross_profit,2),
        "gross_loss":round(gross_loss,2),
        "message":"P&L excludes brokerage, taxes, slippage and dividends."
    }

def export_trade_journal_csv(journal, path="trade_journal.csv"):
    journal.to_csv(path,index=False)
    return path
