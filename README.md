# AIxTech crypto intel v0.48: enhanced paper-only trading information system

Research harness for automated cryptocurrency **information** and paper strategy evaluation. It does not place live orders, does not store exchange secrets, and is not financial advice.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![version](https://img.shields.io/badge/version-0.48.0-blue)
![mode](https://img.shields.io/badge/execution-paper%20only-orange)
![Licence](https://img.shields.io/badge/licence-MIT-green)

## What it does

- Classifies markets into eight asset classes and applies refined multi-factor research rules to each.
- Labels each series trend, range, or stress, and stands aside in stress.
- Scores a signal with multi-factor confirmation plus adaptive ATR volatility scaling, volume profile proxy, refined cross-asset correlation, multi-horizon regime consistency, trend-strength, MACD-style, Supertrend, Stochastic, Ichimoku, ADX, RSI divergence, BB width, VWAP, adaptive MTF (v0.48), then a risk gate that can shrink or refuse it.
- Applies a declared round-trip cost by asset class in the paper backtest.
- Writes a hash-chained audit log with UTC timestamps, lineage stamp (multi-hash sealed digest), consecutive-action counter, residency stamp, anomaly detection on consecutive high-impact actions, attests fixture sources, and redacts secret-like strings (expanded for extended keys, session cookies, hardware exports, BIP39, Solana/Ethereum-style keys, on-chain patterns, and partial seed fragments).
- Backtests on **synthetic** candles only. Network access is injectable and unused by default.

| Asset class | Research rule | Risk cap | Cost |
|---|---|---|---|
| Major (BTC, ETH) | Multi-factor EMA + ATR adaptive size + strength + MACD + multi-TF + Supertrend + Ichimoku + ADX + BB width + VWAP + volume profile + adaptive MTF + volume-flow + correlation-adjusted outside stress; range-only RSI + Stochastic + BB + divergence reversion | 8% | 8 bps |
| Large-cap alt | Breakout with volume, relative volume vs major, BB, strength, MACD, Supertrend, Ichimoku, VWAP, volume profile, adaptive MTF, and correlation filter, suppressed in stress | 4% | 14 bps |
| Stablecoin | 20 bp watch, 50 bp depeg alert. No order | 0% | n/a |
| DeFi | Trend only in a calm, non-stress regime with volume, Stochastic, ADX, VWAP, volume profile, adaptive MTF, and moderate correlation | 2% | 22 bps |
| Meme | Qualified burst with volume spike vs longer avg, chase filter, volume-flow proxy, correlation decay, volume profile confirmation, 3-bar horizon | 0.5% | 45 bps |
| L2 | Relative strength versus a non-stress benchmark with volume/VWAP/volume profile, adaptive MTF, and correlation confirmation | 3% | 16 bps |
| RWA | Slow trend; halt on an 8% gap or stress, with volume filter and volume profile | 2% | 12 bps |
| Perpetual | Negative-funding carry if drift contained; crowded or flipping funding is an alert; light correlation monitor | 2% | 10 bps |

Full notes: [docs/asset-class-strategies.md](docs/asset-class-strategies.md).
Security design: [docs/security-architecture.md](docs/security-architecture.md).
Latest enhancements: [docs/v48-enhanced-atr-volume-and-cyber.md](docs/v48-enhanced-atr-volume-and-cyber.md).

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/make_fixtures.py
PYTHONPATH=src python -m crypto_intel scan fixtures/candles_synthetic.json
PYTHONPATH=src python -m crypto_intel brief fixtures/candles_synthetic.json
PYTHONPATH=src python -m crypto_intel posture fixtures/candles_synthetic.json
PYTHONPATH=src python -m crypto_intel demo fixtures/candles_synthetic.json
```

The fixture is labelled `SYNTHETIC` and is not a market history.

## Controls

1. Paper-only execution. `HALTED` and any live mode raise `PermissionError`.
2. Trade and withdrawal credential names are refused. No role can place an order.
3. Class size caps, confidence floors, kill switch, drawdown halt, RWA gap halt, stress overlay, multi-factor, ATR adaptive, volume profile, MACD, multi-TF, Supertrend, Stochastic, Ichimoku, ADX, RSI divergence, BB width, VWAP, adaptive MTF, volume-flow, cross-asset correlation, and adaptive filters.
4. Hash-chained audit log with timestamps, lineage (multi-hash sealed), consecutive counter, residency stamp, anomaly detection, source attestation, feed jump and staleness checks, correlation-jump signal.
5. PDPA-style tripwire over fixtures and docs.
6. Ruff lint (including bandit-style `S` rules), format, pytest coverage floor, gitleaks in CI.

## Honesty

- No live exchange connector is included. Do not add trade keys to this tree.
- Strategy scores describe the synthetic fixture, not future returns.
- This is not legal, compliance, or investment advice.
- Process inspired by zeekiankok92/aixtech-agent-harness-demo and prior versions of aixtech-crypto-intel.
