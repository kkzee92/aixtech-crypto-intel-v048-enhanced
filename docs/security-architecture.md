# Security architecture notes for v0.48

See docs/v48-enhanced-atr-volume-and-cyber.md for full details.

- Zero-trust: All inputs attested with multi-hash before evaluation.
- Redaction expanded for Ethereum hex keys, additional seeds, etc.
- Anomaly detection on consecutive high-impact audit actions.
- Paper-only enforced at every entry point.
- No secrets stored; gitleaks recommended in CI.
