"""Shared market-regime classifier for asset-class research rules."""

from __future__ import annotations

from enum import Enum
from statistics import fmean

from crypto_intel.models import Candle


class Regime(str, Enum):
    TREND = "trend"
    RANGE = "range"
    STRESS = "stress"


def atr_pct(candles: list[Candle], bars: int = 8) -> float:
    window = candles[-bars:]
    ranges = [(c.high - c.low) / c.close for c in window if c.close]
    return fmean(ranges) if ranges else 0.0


def classify(candles: list[Candle]) -> Regime:
    """Stress first, then trend versus range. Research label, not a forecast."""
    if len(candles) < 8:
        raise ValueError("need at least 8 candles")
    width = atr_pct(candles)
    if width >= 0.035:
        return Regime.STRESS
    closes = [c.close for c in candles]
    span = closes[-1] / closes[-8] - 1.0
    if abs(span) >= 0.025:
        return Regime.TREND
    return Regime.RANGE
