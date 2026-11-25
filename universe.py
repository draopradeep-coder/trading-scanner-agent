"""Automatic NSE + BSE listed-equity universe loader for TraderPrp."""
from io import BytesIO
import zipfile
import pandas as pd
import requests

UNIVERSE_BUILD = "BSE headers v3 · 2026-11-25"

NSE_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
BSE_API_URL = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
BSE_MASTER_URL = "https://api.infinn.in/BSE_symbols.txt.zip"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123 Safari/537.36",
    "Accept": "text/csv,application/octet-stream,*/*",
    "Referer": "https://www.nseindia.com/",
}
BSE_HEADERS = {
    "Host": "api.bseindia.com",
    "Referer": "https://www.bseindia.com/",
    "Origin": "https://www.bseindia.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    "Sec-CH-UA": '"Google Chrome";v="155", "Chromium";v="155", "Not?A_Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
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

def _parse_bse_api_payload(payload):
    if isinstance(payload, dict):
        payload = payload.get("Table", payload.get("data", payload.get("Data", [])))
    if not isinstance(payload, list) or not payload:
        raise ValueError("BSE API returned an empty or unexpected securities response.")
    df = _clean_columns(pd.DataFrame(payload))
    symbol_col = next((c for c in ("SCRIP_CD", "SCRIP_CODE", "SC_CODE", "CODE") if c in df.columns), None)
    name_col = next((c for c in ("ISSUER_NAME", "SCRIP_NAME", "NAME") if c in df.columns), None)
    isin_col = next((c for c in ("ISIN_NUMBER", "ISIN", "ISIN_CODE") if c in df.columns), None)
    group_col = next((c for c in ("GROUP", "SCRIP_GROUP") if c in df.columns), None)
    if not symbol_col:
        raise ValueError("BSE scrip-code field not found in API response: " + ", ".join(df.columns))
    out = pd.DataFrame({
        "symbol": df[symbol_col].astype(str).str.strip(),
        "name": df[name_col].astype(str).str.strip() if name_col else "",
        "isin": df[isin_col].astype(str).str.strip() if isin_col else "",
        "exchange": "BSE",
        "series": df[group_col].astype(str).str.strip() if group_col else "",
    })
    out = out[out["symbol"].ne("") & out["symbol"].ne("NAN")]
    return out.drop_duplicates(["exchange", "symbol"]).reset_index(drop=True)


def _fetch_bse_master_fallback():
    """Load BSE cash-equity scrip codes from the daily instrument-master mirror."""
    response = requests.get(BSE_MASTER_URL, timeout=35)
    response.raise_for_status()
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith((".csv", ".txt"))]
        if not csv_names:
            raise ValueError("BSE fallback archive contains no CSV/TXT master file.")
        df = pd.read_csv(archive.open(csv_names[0]), dtype=str)
    required = {"Token", "Symbol", "Instrument"}
    if not required.issubset(df.columns):
        raise ValueError("BSE fallback master has an unexpected schema.")
    token = pd.to_numeric(df["Token"], errors="coerce")
    instrument = df["Instrument"].fillna("").astype(str).str.strip().str.upper()
    # BSE equity scrip codes are in the 500000-599999 range. Exclude the
    # F-coded debt instruments present in the same consolidated master.
    equity = df[token.between(500000, 599999) & ~instrument.isin(["F", "G"])].copy()
    equity["Token"] = token.loc[equity.index].astype("int64").astype(str)
    out = pd.DataFrame({
        "symbol": equity["Token"].str.strip(),
        "name": equity["Symbol"].fillna("").astype(str).str.strip(),
        "isin": "",
        "exchange": "BSE",
        "series": equity["Instrument"].fillna("").astype(str).str.strip(),
    })
    out = out[out["symbol"].ne("") & out["name"].ne("")]
    out = out.drop_duplicates(["exchange", "symbol"]).reset_index(drop=True)
    if len(out) < 1000:
        raise ValueError(f"BSE fallback master returned only {len(out)} eligible equity scrips.")
    return out


def fetch_bse_universe():
    """Prefer the daily BSE cash-equity instrument master; use BSE API only as backup."""
    try:
        # Streamlit Cloud may receive 403 responses from BSE. The instrument
        # master is the primary source so normal scans do not depend on that API.
        return _fetch_bse_master_fallback()
    except Exception as fallback_error:
        try:
            response = requests.get(
                BSE_API_URL,
                headers=BSE_HEADERS,
                params={"Group": "", "Scripcode": "", "industry": "", "segment": "Equity", "status": "Active"},
                timeout=30,
            )
            response.raise_for_status()
            api_data = _parse_bse_api_payload(response.json())
            api_data.attrs["source_warning"] = (
                "BSE instrument-master fallback unavailable (" + str(fallback_error)[:120] +
                "); loaded " + str(len(api_data)) + " BSE equity scrips from the BSE API backup."
            )
            return api_data
        except Exception as api_error:
            raise RuntimeError(
                "BSE instrument-master fallback failed: " + str(fallback_error)[:160] +
                "; BSE API backup also failed: " + str(api_error)[:160]
            ) from api_error

def load_full_universe():
    """Load both exchanges; raises if both sources fail, tolerates one source failure."""
    results, errors = [], []
    for loader in (fetch_nse_universe, fetch_bse_universe):
        try:
            loaded = loader()
            results.append(loaded)
            source_warning = loaded.attrs.get("source_warning")
            if source_warning:
                errors.append(source_warning)
        except Exception as exc:
            errors.append(f"{loader.__name__}: {exc}")
    if not results:
        raise RuntimeError("Unable to load exchange universe. " + " | ".join(errors))
    universe = pd.concat(results, ignore_index=True)
    universe["isin"] = universe["isin"].replace({"nan": "", "None": ""}).fillna("").str.strip()
    universe["symbol"] = universe["symbol"].astype(str).str.strip()
    universe["name"] = universe["name"].astype(str).str.strip()
    universe = universe.drop_duplicates(["exchange", "symbol"]).reset_index(drop=True)
    return universe, errors
