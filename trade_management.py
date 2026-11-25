def update_trade_status(entry, stop, targets, ltp, remaining_qty=None, stop_moved_to=None):
    """Evaluate long cash-equity trade levels using supplied LTP (not live feed)."""
    try:
        entry, stop, ltp = float(entry), float(stop), float(ltp)
        targets = [float(x) for x in targets]
    except (TypeError, ValueError):
        return {"status":"Invalid inputs"}
    if entry <= 0 or stop <= 0 or ltp <= 0 or stop >= entry or not targets:
        return {"status":"Invalid trade geometry or price"}
    risk = entry-stop
    hit_targets = [i+1 for i,t in enumerate(targets) if ltp >= t]
    stop_hit = ltp <= stop
    if stop_hit:
        status = "STOP LOSS HIT"
        action = "Review exit; stop level reached based on supplied price."
    elif len(hit_targets) >= 3:
        status = "TARGET 3 REACHED"
        action = "Review final profit booking or trailing rules."
    elif len(hit_targets) == 2:
        status = "TARGET 2 REACHED"
        action = "Review second partial booking and trailing stop."
    elif len(hit_targets) == 1:
        status = "TARGET 1 REACHED"
        action = "Review partial profit booking and moving stop toward breakeven."
    else:
        status = "IN TRADE"
        action = "Continue monitoring; no target or stop level reached."
    breakeven = round(entry,2)
    trailing = round(max(stop, ltp-risk),2)
    return {
        "status":status,
        "ltp":round(ltp,2),
        "targets_reached":hit_targets,
        "stop_loss":round(stop,2),
        "breakeven_stop_suggestion":breakeven,
        "atr_like_1R_trailing_reference":trailing,
        "remaining_qty":remaining_qty,
        "action_guidance":action,
        "warning":"Level checks use only the LTP supplied; gaps, intraday sequencing and fees are not accounted for. Suggestions are not orders."
    }
