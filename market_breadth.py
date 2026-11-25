import time
import pandas as pd
import yfinance as yf


def analyze_breadth(universe, batch_size=40):
    rows = universe.to_dict("records") if hasattr(universe, "to_dict") else list(universe)
    tickers = []
    for row in rows:
        symbol = str(row.get("symbol", "")).strip()
        exchange = str(row.get("exchange", "NSE")).upper().strip()
        if symbol:
            tickers.append((symbol, symbol + (".NS" if exchange == "NSE" else ".BO")))
    results = []
    errors = []
    for start in range(0, len(tickers), batch_size):
        batch = tickers[start:start + batch_size]
        yf_symbols = [t[1] for t in batch]
        try:
            data = yf.download(yf_symbols, period="3mo", interval="1d", group_by="ticker", auto_adjust=True, progress=False, threads=False)
            for symbol, ticker in batch:
                try:
                    df = data[ticker] if len(yf_symbols) > 1 else data
                    close = df["Close"].dropna()
                    if len(close) < 55:
                        continue
                    price = float(close.iloc[-1])
                    sma20 = float(close.rolling(20).mean().iloc[-1])
                    sma50 = float(close.rolling(50).mean().iloc[-1])
                    change = float(price - close.iloc[-2])
                    results.append({"symbol": symbol, "price": price, "sma20": sma20, "sma50": sma50, "above_sma20": price > sma20, "above_sma50": price > sma50, "change": change})
                except Exception:
                    continue
        except Exception as exc:
            errors.append(f"Batch {start + 1}-{min(start + batch_size, len(tickers))}: {exc}")
        if start + batch_size < len(tickers):
            time.sleep(0.4)
    return pd.DataFrame(results), errors
