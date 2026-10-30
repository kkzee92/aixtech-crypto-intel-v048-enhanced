# Minimal CLI entry for demo (extend as needed)

from crypto_intel.security import AuditLog, assert_paper_only
from crypto_intel.models import ExecutionMode
import json
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m crypto_intel <command> [file]")
        return
    cmd = sys.argv[1]
    log = AuditLog()
    log.append("startup", "v0.48 enhanced system initialized", sealed=True)
    print(f"Audit chain verified: {log.verify()}")
    print("Paper-only mode enforced.")
    assert_paper_only(ExecutionMode.PAPER)
    if cmd == "demo":
        print("Demo complete. Research only.")
    else:
        print(f"Command {cmd} acknowledged. Full CLI in source.")

if __name__ == "__main__":
    main()
