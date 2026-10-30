# v0.48 enhancements: ATR adaptive sizing, volume profile proxies, refined multi-factor strategies, and strengthened zero-trust cyber architecture with anomaly detection

Research only. Paper-only. Not financial, legal, or security advice.

## Strategy upgrades (per asset class)

- **ATR adaptive sizing**: Dynamic size scaling based on recent ATR percentile. High volatility reduces size proportionally across directional classes (Major, Large-cap, DeFi, L2, Meme). Integrated into base signal construction.
- **Volume profile proxy**: Simple Point-of-Control (POC)-style volume concentration heuristic over recent bars. Signals preferred when price is near high-volume nodes for confirmation on Majors, Large-cap, DeFi, L2, RWA, and Meme bursts.
- **Refined multi-horizon correlation and regime**: Correlation filter now uses multi-horizon (short/medium) consistency. Extreme positive correlation in stress suppresses size more aggressively. Regime consistency score further modulates confidence.
- **Class-specific refinements**:
  - Major: ATR-scaled size; volume profile confirmation preferred for trend entries; stand-aside if self-correlation breaks.
  - Large-cap alt: Relative volume vs major + volume profile + correlation filter required for breakout.
  - DeFi / L2: Prefer moderate correlation and volume profile alignment; ATR scale applied.
  - Meme: Burst qualification requires volume profile spike confirmation and correlation decay.
  - Stablecoin / RWA / Perpetual: Volume profile light monitoring for alerts; ATR not applied to zero-size classes.
- **All classes**: Reasons list includes ATR scale factor, volume profile status, multi-horizon correlation/regime scores for audit transparency. Shared stress overlay and prior multi-factor layers retained.

All rules remain transparent heuristics on synthetic candles. No edge or future-return claim is made. Scores describe the fixture only.

## Cyber / data security upgrades

- Strengthened zero-trust data plane: Source attestation includes multi-hash sealed digest over fixture label + quality metrics + correlation proxy + volume profile snapshot. Inputs must pass before any strategy evaluation.
- Expanded redaction patterns: Additional coverage for Ethereum-style private keys (hex), partial seed phrases, hardware wallet fragments, session tokens, and more base58 variants.
- Anomaly detection in audit log: Flags consecutive high-impact actions (e.g., repeated kill-switch or catalog changes) for dual-control review simulation.
- Simulated dual-control for high-impact actions retained with operator + auditor acknowledgment note.
- Data classification updated to treat volume-profile and ATR-derived features as derived public market data (synthetic-only).
- Feed integrity, hash-chain, and correlation-jump retained; added volume-spike anomaly as secondary integrity signal.

## Threat model additions

| Threat | Control |
|---|---|
| Volatility-driven oversized risk | ATR adaptive size scaling + class caps |
| Volume profile manipulation via fixture | Source attestation + synthetic label + multi-hash |
| Oversized correlated risk in stress | Refined multi-horizon correlation filter + adaptive size |
| Partial secret paste (Ethereum key, seed fragment) | Expanded redaction + gitleaks CI |
| Audit without dual review or anomaly on kill-switch | Simulated multi-factor acknowledgment + consecutive anomaly detection |
| Derived feature injection | Quality gate + attestation before strategy |

## Operating notes

- Still no order router, no trade/withdrawal keys, no live mode. `assert_paper_only` and `refuse_trade_secret` unchanged.
- Human review required before any kill-switch clear. Dual acknowledgment and anomaly check preferred.
- PDPA tripwire, gitleaks CI, paper-only constraints, and AI-disclosure trail unchanged.
- Inspired by the process in zeekiankok92/aixtech-agent-harness-demo and prior aixtech-crypto-intel versions.
- Promote any signal only via a separate, human-approved system.

See also docs/v47-enhanced-correlation-and-cyber.md and earlier version notes.
