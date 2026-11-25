"""Automatic NSE + BSE listed-equity universe loader for TraderPrp.

Downloads exchange security masters, normalizes common columns, and combines
records while retaining exchange, symbol, ISIN and security name.
"""
from io import BytesIO
import pandas as pd
import requests

NSE_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
BSE_URL = "https://www.bseindia.com/downloads1/EquityList.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123 Safari/537.36",
    "Accept": "text/csv,application/octet-stream,*/*",
    "Referer": "https://www.nseindia.com/",
}

def _download_csv(url):
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    return pd.read_csv(BytesIO(response.content))

def _clean_columns(df):
    df.columns = [str(c).strip().upper().replace(" ", "_") for c in df.columns]
    return df

def fetch_nse_universe():
    df = _clean_columns(_download_csv(NSE_URL))
    symbol_col = next((c for c in ("SYMBOL", "TICKER") if c in df.columns), None)
    name_col = next((c for c in ("NAME_OF_COMPANY", "COMPANY_NAME") if c in df.columns), None)
    isin_col = next((c for c in ("ISIN", "ISIN_NUMBER") if c in df.columns), None)
    series_col = next((c for c in ("SERIES",) if c in df.columns), None)
    if not symbol_col:
        raise ValueError("NSE symbol column not found in downloaded master.")
    out = pd.DataFrame({
        "symbol": df[symbol_col].astype(str).str.strip(),
        "name": df[name_col].astype(str).str.strip() if name_col else "",
        "isin": df[isin_col].astype(str).str.strip() if isin_col else "",
        "exchange": "NSE",
        "series": df[series_col].astype(str).str.strip() if series_col else "EQ",
    })
    if series_col:
        out = out[out["series"].isin(["EQ", "BE", "BZ"])]
    out = out[out["symbol"].ne("") & out["symbol"].ne("NAN")]
    return out.drop_duplicates(["exchange", "symbol"]).reset_index(drop=True)

def fetch_bse_universe():
    df = _clean_columns(_download_csv(BSE_URL))
    symbol_col = next((c for c in ("SCRIP_CODE", "SC_CODE", "CODE") if c in df.columns), None)
    name_col = next((c for c in ("ISSUER_NAME", "SCRIP_NAME", "NAME") if c in df.columns), None)
    isin_col = next((c for c in ("ISIN_NUMBER", "ISIN") if c in df.columns), None)
    group_col = next((c for c in ("GROUP", "SCRIP_GROUP") if c in df.columns), None)
    if not symbol_col:
        raise ValueError("BSE scrip-code column not found in downloaded master.")
    out = pd.DataFrame({
        "symbol": df[symbol_col].astype(str).str.strip(),
        "name": df[name_col].astype(str).str.strip() if name_col else "",
        "isin": df[isin_col].astype(str).str.strip() if isin_col else "",
        "exchange": "BSE",
        "series": df[group_col].astype(str).str.strip() if group_col else "",
    })
    out = out[out["symbol"].ne("") & out["symbol"].ne("NAN")]
    return out.drop_duplicates(["exchange", "symbol"]).reset_index(drop=True)

def load_full_universe():
    """Load both exchanges; raises if both sources fail, tolerates one source failure."""
    results, errors = [], []
    for loader in (fetch_nse_universe, fetch_bse_universe):
        try:
            results.append(loader())
        except Exception as exc:
            errors.append(f"{loader.__name__}: {exc}")
    if not results:
        raise RuntimeError("Unable to load exchange universe. " + " | ".join(errors))
    universe = pd.concat(results, ignore_index=True)
    universe["isin"] = universe["isin"].replace({"nan": "", "None": ""}).fillna("").str.strip()
    universe["symbol"] = universe["symbol"].astype(str).str.strip()
    universe["name"] = universe["name"].astype(str).str.strip()
    universe = universe.drop_duplicates(["exchange", "symbol"]).reset_index(drop=True)
    # Companies traded on both exchanges remain represented on both exchange rows.
    return universe, errors
