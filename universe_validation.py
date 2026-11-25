"""Validation helpers for the TraderPrp exchange-universe loader."""
import pandas as pd

REQUIRED_COLUMNS = {"symbol", "name", "isin", "exchange", "series"}

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
        if universe["symbol"].isna().any() or universe["symbol"].astype(str).str.strip().eq("").any():
            issues.append("Blank symbols detected.")
        if not universe["exchange"].isin(["NSE", "BSE"]).all():
            issues.append("Unexpected exchange values.")
        duplicates = universe.duplicated(["exchange", "symbol"]).sum()
        if duplicates:
            issues.append(f"{duplicates} duplicate exchange-symbol rows.")
        if "isin" in universe.columns:
            # Duplicate ISINs across exchanges are expected; duplicate rows are not.
            pass
    return not issues, issues
