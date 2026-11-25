"""Validation helpers for the TraderPrp exchange-universe loader."""
import pandas as pd

REQUIRED_COLUMNS = {"symbol", "name", "isin", "exchange", "series"}
REQUIRED_EXCHANGES = {"NSE", "BSE"}

def validate_universe(universe):
    issues = []
    if not isinstance(universe, pd.DataFrame):
        return False, ["Universe result is not a pandas DataFrame."]

    missing = REQUIRED_COLUMNS.difference(universe.columns)
    if missing:
        issues.append("Missing columns: " + ", ".join(sorted(missing)))

    if universe.empty:
        issues.append("Universe is empty.")

    if not missing and not universe.empty:
        symbols = universe["symbol"].astype(str).str.strip()
        if symbols.eq("").any() or symbols.eq("nan").any():
            issues.append("Blank symbols detected.")

        exchanges = universe["exchange"].astype(str).str.strip().str.upper()
        unexpected = sorted(set(exchanges.unique()) - REQUIRED_EXCHANGES)
        if unexpected:
            issues.append("Unexpected exchange values: " + ", ".join(unexpected))

        present = set(exchanges.unique())
        absent = sorted(REQUIRED_EXCHANGES - present)
        if absent:
            issues.append("Missing exchange coverage: " + ", ".join(absent))

        for exchange in sorted(REQUIRED_EXCHANGES):
            count = int(exchanges.eq(exchange).sum())
            if count == 0:
                issues.append(f"No {exchange} listings were loaded.")

        duplicates = universe.duplicated(["exchange", "symbol"]).sum()
        if duplicates:
            issues.append(f"{duplicates} duplicate exchange-symbol rows.")

    return not issues, issues
