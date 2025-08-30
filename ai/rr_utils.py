from typing import Literal


def round_to_tick(price: float, tick: float) -> float:
    """Round a price to the instrument tick size.

    Uses nearest rounding to the discrete grid and preserves decimal precision
    implied by the tick.
    """
    if tick <= 0:
        raise ValueError("tick must be > 0")
    steps = round(price / tick)
    rounded = steps * tick
    # Normalize floating error according to tick decimals
    tick_str = f"{tick:.12f}".rstrip("0").rstrip(".")
    decimals = len(tick_str.split(".")[-1]) if "." in tick_str else 0
    return round(rounded, decimals)


def rr_with_costs(
    entry: float,
    stop: float,
    target: float,
    side: Literal["long", "short"],
    tick: float,
    fees_bps: float,
    slippage_ticks: int,
) -> float:
    """Compute risk-reward including fees and slippage.

    - Applies slippage adversely on entry and exit.
    - Applies taker fees (bps) on both entry and exit notionals.
    Returns RR multiple (net_reward / net_risk). If risk is non-positive, returns 0.
    """
    if tick <= 0:
        raise ValueError("tick must be > 0")
    if fees_bps < 0:
        raise ValueError("fees_bps must be >= 0")
    if slippage_ticks < 0:
        raise ValueError("slippage_ticks must be >= 0")

    slip = slippage_ticks * tick

    if side == "long":
        entry_eff = entry + slip
        stop_eff = stop - slip
        target_eff = target - slip
        gross_risk = entry_eff - stop_eff
        gross_reward = target_eff - entry_eff
    else:  # short
        entry_eff = entry - slip
        stop_eff = stop + slip
        target_eff = target + slip
        gross_risk = stop_eff - entry_eff
        gross_reward = entry_eff - target_eff

    # Fees on notional at entry and exit
    fee_rate = fees_bps / 10000.0
    fees_entry = abs(entry_eff) * fee_rate
    fees_exit_target = abs(target_eff) * fee_rate
    fees_exit_stop = abs(stop_eff) * fee_rate

    net_risk = gross_risk + (fees_entry + fees_exit_stop)
    net_reward = gross_reward - (fees_entry + fees_exit_target)

    if net_risk <= 0:
        return 0.0
    return float(net_reward / net_risk)

