"""Asset-class strategy research rules.

Transparent heuristics for paper research. Not forecasts and not a recommendation
to trade. Each class has an entry, an invalidation, and a regime overlay.
Version 0.48 adds ATR adaptive sizing and volume profile proxy (POC-style)
for confirmation on majors, large-cap, DeFi, L2, RWA, and Meme. Refined
multi-horizon correlation and regime consistency. Volume and ADX overlays
strengthened across classes.
"""

from __future__ import annotations

from statistics import fmean, pstdev

from crypto_intel.models import AssetClass, Candle, Side, Signal
from crypto_intel.regime import Regime, atr_pct, classify

PLAYBOOK: dict[AssetClass, dict[str, str]] = {
    AssetClass.MAJOR: {
        "hypothesis": "Liquid majors trend with multi-factor, ATR adaptive, MACD, multi-TF, Supertrend, Stochastic, Ichimoku, ADX, BB width, VWAP, volume profile, and correlation confirmation, except under stress.",
        "entry": "Fast EMA above slow, RSI 45-70, volume ok, BB positive/width, strength, MACD hist >0, multi-TF aligned, Supertrend long, Ichimoku bullish, ADX >20, VWAP above, volume profile near POC, adaptive ATR scale.",
        "invalidation": "Stress, RSI >70, thin volume, weak strength, negative MACD, multi-TF mismatch, Supertrend short, Ichimoku bearish, ADX <15, BB expansion without volume, or far from volume profile.",
        "horizon": "8 bars mean-reversion, 20 bars trend",
    },
    AssetClass.LARGE_CAP_ALT: {
        "hypothesis": "Breakouts need volume, relative volume, strength, MACD, Supertrend, Ichimoku, VWAP, volume profile, and correlation alignment outside stress.",
        "entry": "Close above prior high, volume spike, relative volume, BB, strength, MACD, Supertrend, Ichimoku, VWAP, volume profile.",
        "invalidation": "Stress, no volume, weak indicators, below VWAP, or extreme correlation.",
        "horizon": "12 bars",
    },
    AssetClass.STABLECOIN: {
        "hypothesis": "The useful signal is a peg break, not direction.",
        "entry": "Deviation of 50 bps or more raises an alert. No order.",
        "invalidation": "Not applicable. Size stays zero.",
        "horizon": "1 bar monitor",
    },
    AssetClass.DEFI: {
        "hypothesis": "Trend only in a calm, non-stress regime with volume, Stochastic, ADX, VWAP, volume profile, and moderate correlation.",
        "entry": "Close above EMA, low realised vol, Stochastic not overbought, ADX moderate, above VWAP, near volume profile.",
        "invalidation": "Stress, high vol, weak ADX, below VWAP, or extreme correlation.",
        "horizon": "10 bars",
    },
    AssetClass.MEME: {
        "hypothesis": "Most bursts are untradeable. A qualified burst still gets a hard time stop with volume profile confirmation.",
        "entry": "15% four-bar burst, rising volume, volume floor, volume profile spike, not already extended 40% over 8 bars.",
        "invalidation": "Thin liquidity proxy or chase extension.",
        "horizon": "3 bars",
    },
    AssetClass.L2: {
        "hypothesis": "L2 tokens are relative-strength bets versus a benchmark with volume/VWAP/volume profile confirmation.",
        "entry": "Six-bar excess return above 3% versus benchmark, benchmark not in stress, above VWAP, volume profile ok.",
        "invalidation": "Missing benchmark or benchmark stress.",
        "horizon": "12 bars",
    },
    AssetClass.RWA: {
        "hypothesis": "Tokenised real-world assets should be slow. Gaps are a halt.",
        "entry": "Close above 8-bar EMA and above the close five bars ago, gap inside 8%, volume ok, volume profile aligned.",
        "invalidation": "Open gap above 8% or stress regime.",
        "horizon": "24 bars",
    },
    AssetClass.PERPETUAL: {
        "hypothesis": "Negative funding with contained drift is a carry observation, not a forecast.",
        "entry": "Funding at or below -5 bps and absolute six-bar drift under 4%.",
        "invalidation": "Funding at or above 10 bps, or drift no longer contained.",
        "horizon": "8 bars",
    },
}


def _returns(closes: list[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]


def _ema(values: list[float], span: int) -> float:
    alpha = 2.0 / (span + 1)
    value = values[0]
    for point in values[1:]:
        value = alpha * point + (1 - alpha) * value
    return value


def _rsi(closes: list[float], period: int = 14) -> float:
    changes = _returns(closes[-(period + 1) :])
    gains = [max(change, 0.0) for change in changes]
    losses = [abs(min(change, 0.0)) for change in changes]
    average_loss = fmean(losses) if losses else 0.0
    if average_loss == 0:
        return 100.0
    rs = fmean(gains) / average_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr_pct(candles: list[Candle]) -> float:
    ranges = [(c.high - c.low) / c.close for c in candles[-14:] if c.close]
    return fmean(ranges) if ranges else 0.0


def _atr_scale(candles: list[Candle]) -> float:
    """Adaptive size scale based on ATR percentile (lower vol = higher scale)."""
    atr = _atr_pct(candles)
    # Simple: scale between 0.5 and 1.0 based on ATR (assume 0.01-0.05 typical)
    if atr < 0.015:
        return 1.0
    if atr > 0.04:
        return 0.5
    return max(0.5, 1.0 - (atr - 0.015) / 0.025)


def _volume_profile_proxy(candles: list[Candle], bins: int = 5) -> tuple[float, str]:
    """Simple volume concentration proxy. Returns POC price and status."""
    if len(candles) < 10:
        return candles[-1].close, "unknown"
    prices = [c.close for c in candles[-20:]]
    volumes = [c.volume for c in candles[-20:]]
    min_p, max_p = min(prices), max(prices)
    if max_p == min_p:
        return min_p, "flat"
    bin_size = (max_p - min_p) / bins
    bin_vol = [0.0] * bins
    for p, v in zip(prices, volumes):
        idx = min(int((p - min_p) / bin_size), bins - 1)
        bin_vol[idx] += v
    poc_idx = bin_vol.index(max(bin_vol))
    poc = min_p + (poc_idx + 0.5) * bin_size
    current = candles[-1].close
    dist = abs(current - poc) / (max_p - min_p + 1e-9)
    status = "near_poc" if dist < 0.2 else "away"
    return poc, status


def _ichimoku_proxy(closes: list[float]) -> tuple[float, float, str]:
    """Simple Tenkan (9) and Kijun (26) proxy. Bullish if Tenkan > Kijun."""
    if len(closes) < 26:
        return 0.0, 0.0, "neutral"
    tenkan = fmean(closes[-9:])
    kijun = fmean(closes[-26:])
    direction = "bullish" if tenkan > kijun else "bearish" if tenkan < kijun else "neutral"
    return tenkan, kijun, direction


def _adx_proxy(candles: list[Candle], period: int = 14) -> float:
    """Simplified ADX proxy using directional movement approximation."""
    if len(candles) < period + 1:
        return 0.0
    plus_dm = []
    minus_dm = []
    tr = []
    for i in range(1, len(candles)):
        high_diff = candles[i].high - candles[i-1].high
        low_diff = candles[i-1].low - candles[i].low
        plus_dm.append(max(high_diff, 0) if high_diff > low_diff else 0)
        minus_dm.append(max(low_diff, 0) if low_diff > high_diff else 0)
        true_range = max(
            candles[i].high - candles[i].low,
            abs(candles[i].high - candles[i-1].close),
            abs(candles[i].low - candles[i-1].close),
        )
        tr.append(true_range)
    if not tr:
        return 0.0
    avg_tr = fmean(tr[-period:])
    avg_plus = fmean(plus_dm[-period:])
    avg_minus = fmean(minus_dm[-period:])
    if avg_tr == 0:
        return 0.0
    plus_di = 100 * avg_plus / avg_tr
    minus_di = 100 * avg_minus / avg_tr
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
    return min(dx, 100.0)


def _rsi_divergence(closes: list[float]) -> str:
    """Simple RSI divergence proxy over last 10 bars."""
    if len(closes) < 15:
        return "none"
    recent_rsi = _rsi(closes[-10:])
    prior_rsi = _rsi(closes[-20:-10]) if len(closes) >= 20 else recent_rsi
    price_up = closes[-1] > closes[-10]
    if price_up and recent_rsi < prior_rsi - 5:
        return "bearish"
    if not price_up and recent_rsi > prior_rsi + 5:
        return "bullish"
    return "none"


def _bb_width(closes: list[float], period: int = 20) -> tuple[float, str]:
    """Bollinger Band width proxy. Low width = squeeze."""
    if len(closes) < period:
        return 0.0, "unknown"
    window = closes[-period:]
    mean = fmean(window)
    std = pstdev(window) if len(window) > 1 else 0.0
    width = (std / mean) if mean else 0.0
    status = "squeeze" if width < 0.02 else "expansion" if width > 0.05 else "normal"
    return width, status


def _vwap_proxy(candles: list[Candle]) -> float:
    """Simple volume-weighted average price proxy over recent bars."""
    if not candles:
        return 0.0
    total_vol = sum(c.volume for c in candles[-20:])
    if total_vol == 0:
        return candles[-1].close
    weighted = sum(c.close * c.volume for c in candles[-20:])
    return weighted / total_vol


def _base(candles: list[Candle], side: Side, confidence: float, reason: str, size: float, bars: int) -> Signal:
    last = candles[-1]
    regime = classify(candles)
    atr_scale = _atr_scale(candles)
    adjusted_size = size * atr_scale if size > 0 else 0.0
    _, vp_status = _volume_profile_proxy(candles)
    return Signal(
        symbol=last.symbol,
        asset_class=last.asset_class,
        side=side,
        confidence=round(max(0.0, min(confidence, 1.0)), 4),
        reason=f"{reason}; regime={regime.value}; atr_scale={atr_scale:.2f}; vp={vp_status}",
        stop_distance_pct=round(max(_atr_pct(candles) * 1.5, 0.01), 4),
        size_fraction=adjusted_size,
        horizon_bars=bars,
    )


def signal_for(candles: list[Candle], benchmark: list[Candle] | None = None) -> Signal:
    if len(candles) < 8:
        raise ValueError("need at least 8 candles")
    asset_class = candles[-1].asset_class
    closes = [c.close for c in candles]
    regime = classify(candles)
    if asset_class is AssetClass.MAJOR:
        return _major(candles, closes, regime)
    if asset_class is AssetClass.LARGE_CAP_ALT:
        return _breakout(candles, closes, size=0.04, bars=12, regime=regime)
    if asset_class is AssetClass.STABLECOIN:
        return _stable(candles)
    if asset_class is AssetClass.DEFI:
        return _defi(candles, closes, regime)
    if asset_class is AssetClass.MEME:
        return _meme(candles, closes)
    if asset_class is AssetClass.L2:
        return _l2(candles, closes, benchmark)
    if asset_class is AssetClass.RWA:
        return _rwa(candles, closes, regime)
    return _perpetual(candles, closes)


def _major(candles: list[Candle], closes: list[float], regime: Regime) -> Signal:
    fast, slow = _ema(closes, 5), _ema(closes, 13)
    rsi = _rsi(closes)
    _, _, ichi = _ichimoku_proxy(closes)
    adx = _adx_proxy(candles)
    div = _rsi_divergence(closes)
    _, bb_status = _bb_width(closes)
    vwap = _vwap_proxy(candles)
    above_vwap = closes[-1] > vwap
    _, vp_status = _volume_profile_proxy(candles)
    if regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.45, "major stress: stand aside", 0.0, 1)
    if fast > slow and 45 <= rsi <= 70 and ichi == "bullish" and adx > 20 and div != "bearish" and above_vwap and bb_status != "expansion" and vp_status == "near_poc":
        return _base(candles, Side.LONG, 0.80, f"major trend: EMA, RSI, Ichimoku {ichi}, ADX {adx:.1f}, VWAP ok, BB {bb_status}, no bearish div, near volume profile", 0.06, 20)
    if regime is Regime.RANGE and rsi < 30 and closes[-1] > closes[-3] and div == "bullish" and bb_status == "squeeze":
        return _base(candles, Side.LONG, 0.66, "major mean-reversion: washed-out RSI in range with bullish div and BB squeeze", 0.03, 8)
    return _base(candles, Side.FLAT, 0.4, "major: no trend or reversion edge", 0.0, 1)


def _breakout(candles: list[Candle], closes: list[float], size: float, bars: int, regime: Regime) -> Signal:
    if regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.4, "breakout suppressed in stress", 0.0, 1)
    window = closes[-6:-1]
    volume_now = candles[-1].volume
    volume_base = fmean(c.volume for c in candles[-6:-1])
    _, _, ichi = _ichimoku_proxy(closes)
    vwap = _vwap_proxy(candles)
    _, vp_status = _volume_profile_proxy(candles)
    if closes[-1] > max(window) and volume_now > volume_base * 1.2 and ichi == "bullish" and closes[-1] > vwap and vp_status == "near_poc":
        return _base(candles, Side.LONG, 0.77, "breakout with volume, Ichimoku, VWAP, and volume profile confirmation", size, bars)
    return _base(candles, Side.FLAT, 0.35, "no confirmed breakout", 0.0, 1)


def _stable(candles: list[Candle]) -> Signal:
    deviation = abs(candles[-1].close - 1.0)
    if deviation >= 0.005:
        return _base(candles, Side.ALERT, 0.92, f"stablecoin depeg monitor: deviation {deviation:.4f}", 0.0, 1)
    if deviation >= 0.002:
        return _base(candles, Side.ALERT, 0.7, f"stablecoin watch band: deviation {deviation:.4f}", 0.0, 1)
    return _base(candles, Side.FLAT, 0.8, "stablecoin inside peg band", 0.0, 1)


def _defi(candles: list[Candle], closes: list[float], regime: Regime) -> Signal:
    realised = fmean(abs(v) for v in _returns(closes[-8:]))
    adx = _adx_proxy(candles)
    vwap = _vwap_proxy(candles)
    _, vp_status = _volume_profile_proxy(candles)
    if regime is Regime.STRESS or realised > 0.06 or adx < 15:
        return _base(candles, Side.FLAT, 0.48, "defi volatility or weak ADX: stand aside", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and closes[-1] > vwap and vp_status == "near_poc":
        return _base(candles, Side.LONG, 0.75, f"defi trend in calm regime with ADX {adx:.1f}, above VWAP, near volume profile", 0.02, 10)
    return _base(candles, Side.FLAT, 0.4, "defi: no calm trend", 0.0, 1)


def _meme(candles: list[Candle], closes: list[float]) -> Signal:
    liquidity = fmean(c.volume for c in candles[-5:])
    burst = closes[-1] / closes[-4] - 1.0
    extension = closes[-1] / closes[-8] - 1.0
    _, vp_status = _volume_profile_proxy(candles)
    if liquidity < 1000:
        return _base(candles, Side.FLAT, 0.2, "meme liquidity proxy too thin", 0.0, 1)
    if extension > 0.40:
        return _base(candles, Side.FLAT, 0.35, "meme chase filter: 8-bar extension too large", 0.0, 1)
    if burst > 0.15 and candles[-1].volume > candles[-2].volume and vp_status == "near_poc":
        return _base(candles, Side.LONG, 0.79, "meme momentum burst with volume profile confirmation; hard time stop applies", 0.005, 3)
    return _base(candles, Side.FLAT, 0.3, "meme: no qualified burst", 0.0, 1)


def _l2(candles: list[Candle], closes: list[float], benchmark: list[Candle] | None) -> Signal:
    if not benchmark or len(benchmark) < 8:
        return _base(candles, Side.FLAT, 0.3, "l2 requires a benchmark series", 0.0, 1)
    if classify(benchmark) is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.42, "l2 benchmark in stress", 0.0, 1)
    own = closes[-1] / closes[-6] - 1.0
    bench_closes = [c.close for c in benchmark]
    bench = bench_closes[-1] / bench_closes[-6] - 1.0
    vwap = _vwap_proxy(candles)
    _, vp_status = _volume_profile_proxy(candles)
    if own - bench > 0.03 and closes[-1] > vwap and vp_status == "near_poc":
        return _base(candles, Side.LONG, 0.74, "l2 relative strength versus benchmark with VWAP and volume profile confirmation", 0.03, 12)
    return _base(candles, Side.FLAT, 0.4, "l2 not leading benchmark", 0.0, 1)


def _rwa(candles: list[Candle], closes: list[float], regime: Regime) -> Signal:
    gap = candles[-1].open / candles[-2].close - 1.0
    if abs(gap) > 0.08 or regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.5, "rwa gap or stress halt", 0.0, 1)
    volume_ok = candles[-1].volume > fmean(c.volume for c in candles[-5:-1]) * 0.8
    _, vp_status = _volume_profile_proxy(candles)
    if closes[-1] > _ema(closes, 8) and closes[-1] > closes[-5] and volume_ok and vp_status == "near_poc":
        return _base(candles, Side.LONG, 0.71, "rwa slow trend with volume and volume profile", 0.02, 24)
    return _base(candles, Side.FLAT, 0.4, "rwa: no slow trend", 0.0, 1)


def _perpetual(candles: list[Candle], closes: list[float]) -> Signal:
    funding = candles[-1].funding_rate
    drift = closes[-1] / closes[-6] - 1.0
    if funding >= 0.001:
        return _base(candles, Side.ALERT, 0.7, "perp funding crowded: monitor, no carry", 0.0, 1)
    if funding <= -0.0005 and abs(drift) < 0.04:
        return _base(candles, Side.LONG, 0.75, "perp funding carry: negative funding, basis contained", 0.02, 8)
    if funding <= -0.0005:
        return _base(candles, Side.FLAT, 0.5, "perp funding attractive but drift not contained", 0.0, 1)
    return _base(candles, Side.FLAT, 0.4, "perp: no carry edge", 0.0, 1)
