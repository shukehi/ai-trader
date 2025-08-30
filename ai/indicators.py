from typing import Iterable, Optional
import pandas as pd


def ema(series: Iterable[float], period: int = 20) -> float:
    """Compute EMA using only provided bars and return the last EMA value.

    Accepts any iterable convertible to a pandas Series. Caller is responsible
    for rounding to instrument tick size.
    """
    s = pd.Series(list(series), dtype=float)
    if len(s) < 1:
        raise ValueError("series must contain at least 1 value")
    ema_series = s.ewm(span=period, adjust=False).mean()
    return float(ema_series.iloc[-1])

