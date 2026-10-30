"""Domain models for the paper-only crypto information system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AssetClass(str, Enum):
    MAJOR = "major"
    LARGE_CAP_ALT = "large_cap_alt"
    STABLECOIN = "stablecoin"
    DEFI = "defi"
    MEME = "meme"
    L2 = "l2"
    RWA = "rwa"
    PERPETUAL = "perpetual"


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"
    ALERT = "alert"


class ExecutionMode(str, Enum):
    PAPER = "paper"
    HALTED = "halted"


@dataclass(frozen=True)
class Candle:
    symbol: str
    asset_class: AssetClass
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    funding_rate: float = 0.0

    def __post_init__(self) -> None:
        if self.high < max(self.open, self.close, self.low):
            raise ValueError(f"high below range for {self.symbol} {self.timestamp}")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError(f"low above range for {self.symbol} {self.timestamp}")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")


@dataclass(frozen=True)
class Signal:
    symbol: str
    asset_class: AssetClass
    side: Side
    confidence: float
    reason: str
    stop_distance_pct: float
    size_fraction: float
    horizon_bars: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if self.size_fraction < 0:
            raise ValueError("size_fraction cannot be negative")


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    size_fraction: float
    reasons: tuple[str, ...]


@dataclass
class AuditEvent:
    sequence: int
    action: str
    detail: str
    previous_hash: str
    digest: str = ""


@dataclass
class PaperFill:
    symbol: str
    asset_class: AssetClass
    side: Side
    price: float
    size_fraction: float
    reason: str
    mode: ExecutionMode = ExecutionMode.PAPER
    notes: tuple[str, ...] = field(default_factory=tuple)
