import pandas as pd

def build_trade_plan(df, atr_period=14, stop_atr=1.5, entry_buffer_atr=0.25):
    """Build a cash-equity swing plan from OHLC daily bars. Returns a dict."""
    if df is None or len(df) < atr_period + 2:
        return {"status": "Unavailable", "reason": "Insufficient OHLC history"}
    cols = {str(c).lower(): c for c in df.columns}
    needed = ["high", "low", "close"]
    if not all(c in cols for c in needed):
        return {"status": "Unavailable", "reason": "Requires High, Low, Close columns"}
    high, low, close = (pd.to_numeric(df[cols[c]], errors="coerce") for c in needed)
    tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean().iloc[-1]
    price = close.iloc[-1]
    if pd.isna(atr) or pd.isna(price) or atr <= 0 or price <= 0:
        return {"status": "Unavailable", "reason": "Invalid price/ATR"}
    entry_low = round(float(price - entry_buffer_atr*atr), 2)
    entry_high = round(float(price + entry_buffer_atr*atr), 2)
    entry = float(price)
    stop = round(entry - stop_atr*float(atr), 2)
    risk = entry-stop
    return {
        "status": "Plan generated (not a signal)",
        "reference_price": round(float(price), 2),
        "entry_zone_low": entry_low, "entry_zone_high": entry_high,
        "stop_loss": stop, "risk_per_share": round(risk, 2),
        "target_1": round(entry+risk, 2),
        "target_2": round(entry+2*risk, 2),
        "target_3": round(entry+3*risk, 2),
        "atr_14": round(float(atr), 2),
        "method": f"ATR({atr_period}) stop at {stop_atr}x ATR; targets 1R/2R/3R",
        "warning": "Daily-bar estimate only; confirm price, liquidity and risk before trading."
    }
