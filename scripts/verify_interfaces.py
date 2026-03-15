#!/usr/bin/env python3
"""
Run interface connectivity checks and print a detailed report.

For one-time setup verification (required vs optional, step-by-step fix instructions),
use instead:  python scripts/verify_setup.py   (see docs/Setup-and-Reference/One-Time-Setup.md).

This script runs the same checks and exits 0 if all pass, 1 if any fail.
Use before push or deploy. Loads .env from the project root.

Usage (from project root):
  python scripts/verify_interfaces.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
except ImportError:
    pass

from tests.interface_checks import run_all_checks


def main() -> int:
    results = run_all_checks()
    failed = []
    for r in results:
        status = "PASS" if r["ok"] else "FAIL"
        name = r["name"]
        msg = r["message"]
        detail = r.get("detail") or ""
        steps = r.get("setup_steps") or []
        print(f"[{status}] {name}: {msg}")
        if detail:
            print(f"       → {detail}")
        if steps:
            for i, s in enumerate(steps, 1):
                print(f"       {i}. {s}")
        if not r["ok"]:
            failed.append(name)
    if failed:
        print(f"\nFailed: {', '.join(failed)}. Fix the issues above. See docs/Setup-and-Reference/One-Time-Setup.md.")
        return 1
    print("\nAll interface checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
