"""Cyber and data-security controls for the information system.

This is a research control plane, not a certified security product.
Version 0.48 expands secret patterns for Ethereum-style hex private keys,
additional BIP39 variants, more base58, and session patterns. Adds anomaly
detection on consecutive high-impact actions in the audit log. Strengthens
redaction and zero-trust notes with volume profile / ATR attestation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from crypto_intel.models import AuditEvent, ExecutionMode

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token|private[_-]?key|mnemonic|seed[_-]?phrase)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{8,}\b"),
    re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b[0-9a-fA-F]{64}\b"),  # Ethereum-style private keys (hex)
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b"),
    re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{87,88}\b"),
    re.compile(r"\b(?:abandon|ability|able|about|above|absent|absorb|abstract|absurd|abuse)\b(?:\s+\w+){11,23}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\b(?:ya29\.|1//)[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:xprv|xpub)[A-Za-z0-9]{100,}\b"),
    re.compile(r"\b(?:session[_-]?cookie|auth[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}", re.IGNORECASE),
    re.compile(r"\b(?:hardware[_-]?export|wallet[_-]?backup)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{64,88}\b"),  # Solana-style base58 private keys
    re.compile(r"(?i)(solana[_-]?key|private[_-]?key|eth[_-]?key)\s*[:=]\s*['\"]?[1-9A-HJ-NP-Za-km-z0-9]{32,}"),
    re.compile(r"\b0x[a-fA-F0-9]{64}\b"),  # Additional Ethereum hex private key pattern
)

WALLET_PATTERN = re.compile(r"\b0x[a-fA-F0-9]{40}\b")


@dataclass(frozen=True)
class DataClassification:
    field: str
    level: str
    retention: str


CLASSIFICATION = (
    DataClassification("symbol", "public", "research retention"),
    DataClassification("ohlcv", "public-market", "research retention"),
    DataClassification("exchange_api_key", "secret", "never stored"),
    DataClassification("wallet_address", "sensitive-identifier", "do not fixture"),
    DataClassification("account_email", "personal", "do not collect"),
    DataClassification("private_key", "secret", "never stored, never logged"),
    DataClassification("funding_rate", "public-market", "research retention"),
    DataClassification("seed_phrase", "secret", "never stored"),
    DataClassification("session_token", "secret", "never stored"),
    DataClassification("hardware_seed", "secret", "never stored"),
    DataClassification("jwt_token", "secret", "never stored"),
    DataClassification("hardware_export", "secret", "never stored"),
    DataClassification("session_cookie", "secret", "never stored"),
    DataClassification("bip39_seed", "secret", "never stored"),
    DataClassification("solana_key", "secret", "never stored"),
    DataClassification("ethereum_key", "secret", "never stored"),
    DataClassification("atr_derived", "derived-public", "research retention"),
    DataClassification("volume_profile", "derived-public", "research retention"),
)


def redact(text: str) -> str:
    cleaned = text
    for pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return WALLET_PATTERN.sub("[WALLET]", cleaned)


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS) or bool(WALLET_PATTERN.search(text))


def assert_paper_only(mode: ExecutionMode) -> None:
    if mode is not ExecutionMode.PAPER:
        raise PermissionError("live execution is disabled; this system is paper-only")


def hash_event(previous_hash: str, sequence: int, action: str, detail: str) -> str:
    material = f"{previous_hash}|{sequence}|{action}|{detail}".encode()
    return hashlib.sha256(material).hexdigest()


def integrity_digest(payload: str) -> str:
    """SHA-256 of a research payload for source attestation. Zero-trust input check."""
    return hashlib.sha256(payload.encode()).hexdigest()


def multi_hash_attest(payload: str) -> str:
    """Optional multi-hash (SHA-256 + truncated SHA-512) for stronger attestation."""
    h1 = hashlib.sha256(payload.encode()).hexdigest()
    h2 = hashlib.sha512(payload.encode()).hexdigest()[:32]
    return f"{h1}:{h2}"


def residency_stamp(region: str = "research-zone") -> str:
    """Simulated data residency tag for zero-trust lineage."""
    return f"residency={region}|ts={datetime.now(timezone.utc).isoformat(timespec='seconds')}"


def key_rotation_attest(old_digest: str, new_digest: str) -> str:
    """Simulated key-rotation attestation for research audit trails."""
    return f"rotation:{integrity_digest(old_digest + new_digest)}"


class AuditLog:
    """Append-only hash chain with simulated lineage and anomaly detection. Tampering changes the next digest."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._previous = "GENESIS"
        self._last_action = ""
        self._consecutive = 0
        self._anomaly_threshold = 5  # Flag if same high-impact action repeats too often

    def append(self, action: str, detail: str, lineage: str = "synthetic-fixture", sealed: bool = False, region: str = "research-zone") -> AuditEvent:
        safe_detail = redact(detail)
        if sealed:
            safe_detail = f"sealed:{multi_hash_attest(safe_detail)}"
        high_impact = action in ("kill_switch_clear", "catalog_change", "mode_change")
        if action == self._last_action:
            self._consecutive += 1
        else:
            self._consecutive = 1
            self._last_action = action
        anomaly = ""
        if high_impact and self._consecutive >= self._anomaly_threshold:
            anomaly = " | ANOMALY: consecutive high-impact"
        stamped = f"{safe_detail} | ts={datetime.now(timezone.utc).isoformat(timespec='seconds')} | lineage={lineage} | consec={self._consecutive}{anomaly} | {residency_stamp(region)}"
        sequence = len(self.events) + 1
        digest = hash_event(self._previous, sequence, action, stamped)
        event = AuditEvent(sequence, action, stamped, self._previous, digest)
        self.events.append(event)
        self._previous = digest
        return event

    def verify(self) -> bool:
        previous = "GENESIS"
        for event in self.events:
            expected = hash_event(previous, event.sequence, event.action, event.detail)
            if event.previous_hash != previous or event.digest != expected:
                return False
            previous = event.digest
        return True

    def has_anomaly(self) -> bool:
        """Check for any anomaly flags in recent events."""
        return any("ANOMALY" in event.detail for event in self.events[-10:])
