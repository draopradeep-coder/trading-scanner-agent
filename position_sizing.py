def calculate_position_size(capital, risk_pct, entry, stop, max_allocation_pct=100):
    """Calculate equity-share quantity constrained by risk and capital."""
    values = [capital, risk_pct, entry, stop, max_allocation_pct]
    if any(v is None for v in values):
        return {"status": "Invalid", "reason": "Missing inputs"}
    capital, risk_pct, entry, stop, max_allocation_pct = map(float, values)
    if capital <= 0 or entry <= 0 or stop <= 0 or risk_pct <= 0 or max_allocation_pct <= 0:
        return {"status": "Invalid", "reason": "Inputs must be positive"}
    if stop >= entry:
        return {"status": "Invalid", "reason": "For long trades, stop must be below entry"}
    risk_budget = capital * risk_pct / 100
    risk_per_share = entry - stop
    qty_risk = int(risk_budget // risk_per_share)
    allocation_cap = capital * max_allocation_pct / 100
    qty_capital = int(allocation_cap // entry)
    qty = max(0, min(qty_risk, qty_capital))
    cost = round(qty * entry, 2)
    actual_risk = round(qty * risk_per_share, 2)
    return {
        "status": "Calculated",
        "quantity": qty,
        "risk_budget": round(risk_budget, 2),
        "risk_per_share": round(risk_per_share, 2),
        "capital_required": cost,
        "capital_remaining": round(capital-cost, 2),
        "actual_risk": actual_risk,
        "allocation_pct": round(cost/capital*100, 2),
        "quantity_by_risk": qty_risk,
        "quantity_by_capital": qty_capital,
        "limiting_factor": "Risk" if qty_risk <= qty_capital else "Capital",
        "warning": "Cash-equity sizing estimate; excludes fees, slippage and gaps."
    }
