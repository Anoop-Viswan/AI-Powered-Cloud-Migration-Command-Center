"""
Pinecone spend guardrail: track estimated usage and block when over limit
unless user has given explicit permission (PINECONE_ALLOW_OVER_LIMIT=yes or --allow-over-limit).

Usage is persisted in .pinecone_usage.json (read_units, write_units from this app's operations).
Pricing (serverless Standard, approximate): $8.25/1M read units, $2/1M write units.
"""

import json
import os
from pathlib import Path

# Serverless Standard pricing (approximate)
DOLLARS_PER_1M_READ_UNITS = 8.25
DOLLARS_PER_1M_WRITE_UNITS = 2.0


def _usage_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return Path(base) / ".pinecone_usage.json"


def _load():
    p = _usage_path()
    if not p.exists():
        return {"read_units": 0, "write_units": 0}
    try:
        with open(p) as f:
            data = json.load(f)
        return {
            "read_units": int(data.get("read_units", 0)),
            "write_units": int(data.get("write_units", 0)),
        }
    except Exception:
        return {"read_units": 0, "write_units": 0}


def _save(data):
    p = _usage_path()
    with open(p, "w") as f:
        json.dump(data, f, indent=2)


def estimate_dollars(read_units=0, write_units=0):
    """Estimate cost in USD from read and write units (serverless Standard)."""
    ru_cost = (read_units / 1_000_000) * DOLLARS_PER_1M_READ_UNITS
    wu_cost = (write_units / 1_000_000) * DOLLARS_PER_1M_WRITE_UNITS
    return round(ru_cost + wu_cost, 4)


def add_read_units(n):
    data = _load()
    data["read_units"] = data["read_units"] + n
    _save(data)


def add_write_units(n):
    data = _load()
    data["write_units"] = data["write_units"] + n
    _save(data)


def get_estimated_spend():
    """Return (estimated_dollars, read_units, write_units)."""
    data = _load()
    ru, wu = data["read_units"], data["write_units"]
    return estimate_dollars(ru, wu), ru, wu


def get_spend_limit():
    """Spend limit in dollars from env; default 10."""
    try:
        return float(os.getenv("PINECONE_SPEND_LIMIT", "10"))
    except ValueError:
        return 10.0


def is_over_limit_allowed():
    """True if user has explicitly allowed going over the spend limit."""
    v = os.getenv("PINECONE_ALLOW_OVER_LIMIT", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def check_spend_guardrail(allow_over_limit_flag=False):
    """
    If estimated spend >= PINECONE_SPEND_LIMIT and user has not allowed over limit,
    raise SystemExit with a clear message. Otherwise return (estimated_dollars, limit).
    """
    limit = get_spend_limit()
    estimated, ru, wu = get_estimated_spend()
    if allow_over_limit_flag or is_over_limit_allowed():
        return estimated, limit
    if estimated >= limit:
        print(
            f"\n*** PINECONE SPEND GUARDRAIL ***\n"
            f"Estimated usage from this app: ${estimated:.2f} (read_units={ru}, write_units={wu}).\n"
            f"Your limit is ${limit:.2f}.\n\n"
            f"To allow usage beyond this limit, you must give explicit permission:\n"
            f"  1. Set in .env:  PINECONE_ALLOW_OVER_LIMIT=yes\n"
            f"  2. Or run with:  --allow-over-limit\n\n"
            f"Otherwise no further Pinecone operations will run from this script.\n"
        )
        raise SystemExit(1)
    return estimated, limit


def report_usage():
    """Print current estimated usage and limit."""
    estimated, ru, wu = get_estimated_spend()
    limit = get_spend_limit()
    print(f"Estimated spend (this app): ${estimated:.2f}  (read_units={ru}, write_units={wu})")
    print(f"Spend limit: ${limit:.2f}")
    if estimated >= limit:
        print("Status: AT OR ABOVE LIMIT — set PINECONE_ALLOW_OVER_LIMIT=yes or use --allow-over-limit to proceed.")
    else:
        print(f"Status: under limit (${limit - estimated:.2f} remaining)")
