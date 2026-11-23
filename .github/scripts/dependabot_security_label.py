"""Decide whether a Dependabot PR is a genuine security fix.

Why this exists
---------------
`dependabot/fetch-metadata` only fills its `ghsa-id` output when `alert-lookup: true`
is set, and that lookup needs a PAT with Dependabot-alert read access. The workflow
`GITHUB_TOKEN` can't read Dependabot alerts. Without it, `ghsa-id` is always empty,
so the old labeler *removed* the `security` label from every PR, real CVE fixes
included (#204 pypdf and #208 langgraph, Oct/Nov 2026).

This script asks the public GitHub Advisory Database instead. For each updated
dependency it compares the advisories affecting the OLD version with those affecting
the NEW version. If the bump clears at least one advisory, the PR is a security fix.
No PAT needed, and it also covers stale bumps (a PR whose target still leaves the
package vulnerable shows up as "partial").

Input:  env UPDATED_DEPS_JSON = fetch-metadata's `updated-dependencies-json` output.
Output: writes `verdict=security|not-security|unknown` and `ghsa_ids=...` to
        $GITHUB_OUTPUT. On any API error the verdict is `unknown` and the workflow
        leaves labels untouched, so a hiccup never strips a real security label.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Callable, Iterable

ADVISORY_API = "https://api.github.com/advisories"

# Dependabot package-ecosystem -> GitHub Advisory DB ecosystem.
ECOSYSTEM_MAP = {
    "pip": "pip",
    "npm_and_yarn": "npm",
    "npm": "npm",
    "github_actions": "actions",
    "maven": "maven",
    "gradle": "maven",
    "nuget": "nuget",
    "bundler": "rubygems",
    "composer": "composer",
    "go_modules": "go",
    "cargo": "rust",
    "pub": "pub",
    "swift": "swift",
}

# fetch(ecosystem, package, version) -> set of GHSA ids affecting that version.
Fetcher = Callable[[str, str, str], set]


def advisory_ids_affecting(ecosystem: str, package: str, version: str, token: str | None = None) -> set:
    """Query the public advisory DB for advisories that affect package@version."""
    query = urllib.parse.urlencode(
        {"ecosystem": ecosystem, "affects": f"{package}@{version}", "per_page": 100}
    )
    req = urllib.request.Request(
        f"{ADVISORY_API}?{query}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    # Host is the hardcoded https://api.github.com constant; only the query string varies.
    with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310 - fixed https host, not user input
        return {a["ghsa_id"] for a in json.load(resp)}


def classify(deps: Iterable[dict], fetch: Fetcher) -> tuple[str, list[str], list[str]]:
    """Return (verdict, fixed_ghsa_ids, still_open_ghsa_ids).

    verdict is "security" if any dependency's bump clears at least one advisory,
    otherwise "not-security". Unknown ecosystems or missing versions are skipped.
    Exceptions from `fetch` propagate; the caller maps them to "unknown".
    """
    fixed: set = set()
    still_open: set = set()
    for dep in deps:
        ecosystem = ECOSYSTEM_MAP.get(dep.get("packageEcosystem", ""))
        name, prev, new = dep.get("dependencyName"), dep.get("prevVersion"), dep.get("newVersion")
        if not (ecosystem and name and prev and new):
            continue
        before = fetch(ecosystem, name, prev)
        if not before:
            continue
        after = fetch(ecosystem, name, new)
        fixed |= before - after
        still_open |= before & after
    verdict = "security" if fixed else "not-security"
    return verdict, sorted(fixed), sorted(still_open)


def main() -> int:
    raw = os.environ.get("UPDATED_DEPS_JSON", "").strip()
    token = os.environ.get("GITHUB_TOKEN")
    out_path = os.environ.get("GITHUB_OUTPUT")

    try:
        deps = json.loads(raw) if raw else []
        verdict, fixed, still_open = classify(
            deps, lambda e, p, v: advisory_ids_affecting(e, p, v, token)
        )
    except Exception as exc:  # network/API/parse failure -> don't touch labels
        print(f"::warning::advisory lookup failed, leaving labels unchanged: {exc}")
        verdict, fixed, still_open = "unknown", [], []

    print(f"verdict={verdict} fixed={fixed} still_open={still_open}")
    if still_open:
        print(f"::warning::bump leaves advisories open (stale target version?): {still_open}")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(f"verdict={verdict}\n")
            fh.write(f"ghsa_ids={','.join(fixed)}\n")
            fh.write(f"still_open={','.join(still_open)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
