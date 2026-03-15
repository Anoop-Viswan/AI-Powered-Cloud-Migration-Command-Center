#!/usr/bin/env python3
"""
One-time setup verification for new environments and open-source users.

Runs all interface checks (Pinecone, LLM, LangSmith, Tavily, Mermaid.ink) and
prints a clear report: what passed, what failed, and for each failure **why** and
**what to do** (step-by-step). Use after editing .env so you can fix issues before
starting the app or deploying.

Required (must pass): Pinecone, LLM.
Optional (warn if missing, fail if configured but invalid): LangSmith, Tavily, Mermaid.ink.

Exit 0 = all required checks passed (optional may be missing or fail).
Exit 1 = one or more required checks failed.

Usage (from project root):
  python scripts/verify_setup.py

See docs/Setup-and-Reference/One-Time-Setup.md for the one-time setup guide.
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

# Required: must pass for the app to work in a new environment.
REQUIRED = {"Pinecone", "LLM (openai)", "LLM (anthropic)", "LLM (azure_openai)"}

# Optional: app works without them; we warn if missing, fail if configured but invalid.
OPTIONAL = {"LangSmith", "Tavily", "Mermaid.ink"}


def _is_required(result: dict) -> bool:
    name = result.get("name", "")
    if name == "Pinecone":
        return True
    if name.startswith("LLM ("):
        return True
    return False


def main() -> int:
    print("One-time setup verification")
    print("=" * 50)
    print("Checking required and optional interfaces. Required must pass for the app to work.")
    print("See docs/Setup-and-Reference/One-Time-Setup.md for setup steps.\n")

    results = run_all_checks()
    required_failed = []
    optional_failed = []

    for r in results:
        name = r.get("name", "?")
        ok = r.get("ok", False)
        message = r.get("message", "")
        detail = r.get("detail")
        steps = r.get("setup_steps") or []

        if ok:
            print(f"  [PASS] {name}: {message}")
            continue

        # Failed
        if _is_required(r):
            required_failed.append(r)
            print(f"  [FAIL] {name}: {message}")
            if detail:
                print(f"         {detail}")
            if steps:
                print("         What to do:")
                for i, s in enumerate(steps, 1):
                    print(f"           {i}. {s}")
            print()
        else:
            optional_failed.append(r)
            print(f"  [WARN] {name}: {message}")
            if detail:
                print(f"         {detail}")
            if steps:
                for i, s in enumerate(steps, 1):
                    print(f"           {i}. {s}")
            print()

    if required_failed:
        print("=" * 50)
        print("REQUIRED CHECKS FAILED – fix the issues above before starting the app or deploying.")
        print("Run this script again after updating .env or creating the Pinecone index.")
        print("Full guide: docs/Setup-and-Reference/One-Time-Setup.md")
        return 1

    if optional_failed:
        print("=" * 50)
        print("All required checks passed. Some optional services are not configured or failed.")
        print("The app will run; optional features (e.g. official-doc search, tracing) may be limited.")
    else:
        print("=" * 50)
        print("All checks passed. You can start the app or deploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
