"""Unit tests for .github/scripts/dependabot_security_label.py (the PR labeler).

The advisory lookup is injected, so these run offline. Cases mirror real PRs:
#208 langgraph (security), #204 pypdf (security but stale), routine bumps (not).
"""

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "dependabot_security_label.py"
_spec = importlib.util.spec_from_file_location("dependabot_security_label", _SCRIPT)
label = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(label)


def _fake_db(table: dict):
    """table: {(ecosystem, package, version): {ghsa ids}}; records calls."""
    calls = []

    def fetch(eco, pkg, ver):
        calls.append((eco, pkg, ver))
        return set(table.get((eco, pkg, ver), set()))

    fetch.calls = calls
    return fetch


def _dep(name, prev, new, eco="pip"):
    return {"dependencyName": name, "prevVersion": prev, "newVersion": new, "packageEcosystem": eco}


def test_bump_that_clears_advisory_is_security():
    fetch = _fake_db({("pip", "langgraph", "1.2.9"): {"GHSA-3fx2-cqw9-xr3c"}})
    verdict, fixed, still_open = label.classify([_dep("langgraph", "1.2.9", "1.2.14")], fetch)
    assert verdict == "security"
    assert fixed == ["GHSA-3fx2-cqw9-xr3c"]
    assert still_open == []


def test_plain_version_bump_is_not_security():
    fetch = _fake_db({})
    verdict, fixed, _ = label.classify([_dep("fastapi", "0.140.1", "0.141.0")], fetch)
    assert verdict == "not-security"
    assert fixed == []
    # Clean old version -> no need to look up the new one.
    assert fetch.calls == [("pip", "fastapi", "0.140.1")]


def test_stale_partial_fix_is_security_and_reports_still_open():
    """#204 pattern: target version fixes old CVEs but newer ones still affect it."""
    fetch = _fake_db({
        ("pip", "pypdf", "6.18.1"): {"GHSA-old-1", "GHSA-new-1"},
        ("pip", "pypdf", "6.21.2"): {"GHSA-new-1"},
    })
    verdict, fixed, still_open = label.classify([_dep("pypdf", "6.18.1", "6.21.2")], fetch)
    assert verdict == "security"
    assert fixed == ["GHSA-old-1"]
    assert still_open == ["GHSA-new-1"]


def test_bump_that_fixes_nothing_is_not_security():
    """Vulnerable before AND after (no advisory cleared) is not a security fix."""
    fetch = _fake_db({
        ("npm", "react-router-dom", "6.30.6"): {"GHSA-x"},
        ("npm", "react-router-dom", "6.30.7"): {"GHSA-x"},
    })
    verdict, fixed, still_open = label.classify(
        [_dep("react-router-dom", "6.30.6", "6.30.7", eco="npm_and_yarn")], fetch
    )
    assert verdict == "not-security"
    assert still_open == ["GHSA-x"]


def test_grouped_pr_is_security_if_any_member_fixes_something():
    fetch = _fake_db({("pip", "pypdf", "6.21.2"): {"GHSA-p"}})
    deps = [_dep("fastapi", "0.140.1", "0.141.0"), _dep("pypdf", "6.21.2", "6.21.4")]
    verdict, fixed, _ = label.classify(deps, fetch)
    assert verdict == "security"
    assert fixed == ["GHSA-p"]


@pytest.mark.parametrize("dependabot_eco, advisory_eco", [
    ("pip", "pip"), ("npm_and_yarn", "npm"), ("github_actions", "actions"),
])
def test_ecosystem_names_are_mapped_to_advisory_db(dependabot_eco, advisory_eco):
    fetch = _fake_db({})
    label.classify([_dep("pkg", "1.0.0", "1.0.1", eco=dependabot_eco)], fetch)
    assert fetch.calls == [(advisory_eco, "pkg", "1.0.0")]


@pytest.mark.parametrize("dep", [
    _dep("pkg", "1.0.0", "1.0.1", eco="unknown_eco"),
    {"dependencyName": "pkg", "packageEcosystem": "pip", "prevVersion": "", "newVersion": "1.0.1"},
    {"packageEcosystem": "pip", "prevVersion": "1.0.0", "newVersion": "1.0.1"},
])
def test_incomplete_or_unknown_entries_are_skipped(dep):
    fetch = _fake_db({})
    assert label.classify([dep], fetch)[0] == "not-security"
    assert fetch.calls == []


def _run_main(monkeypatch, tmp_path, deps_json, fetch_impl):
    out = tmp_path / "gh_output"
    monkeypatch.setenv("UPDATED_DEPS_JSON", deps_json)
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setattr(label, "advisory_ids_affecting", fetch_impl)
    assert label.main() == 0
    return dict(line.split("=", 1) for line in out.read_text().splitlines())


def test_main_writes_security_verdict_and_ids(monkeypatch, tmp_path):
    deps = json.dumps([_dep("langgraph", "1.2.9", "1.2.14")])
    out = _run_main(
        monkeypatch, tmp_path, deps,
        lambda e, p, v, t=None: {"GHSA-a", "GHSA-b"} if v == "1.2.9" else set(),
    )
    assert out == {"verdict": "security", "ghsa_ids": "GHSA-a,GHSA-b", "still_open": ""}


def test_main_api_failure_yields_unknown_so_labels_are_left_alone(monkeypatch, tmp_path):
    """Fail-safe: a network/API error must never strip a real security label."""
    def boom(*_a, **_k):
        raise OSError("api down")

    deps = json.dumps([_dep("pypdf", "6.21.2", "6.21.4")])
    out = _run_main(monkeypatch, tmp_path, deps, boom)
    assert out["verdict"] == "unknown"


def test_main_malformed_metadata_yields_unknown(monkeypatch, tmp_path):
    out = _run_main(monkeypatch, tmp_path, "{not json", lambda *a, **k: set())
    assert out["verdict"] == "unknown"


def test_main_empty_metadata_is_not_security(monkeypatch, tmp_path):
    out = _run_main(monkeypatch, tmp_path, "", lambda *a, **k: set())
    assert out["verdict"] == "not-security"


def test_workflow_no_longer_depends_on_empty_ghsa_id_output():
    """Regression guard: fetch-metadata's ghsa-id is always empty without a PAT."""
    wf = (_SCRIPT.parents[1] / "workflows" / "dependabot-labels.yml").read_text()
    assert "outputs.ghsa-id" not in wf
    assert "dependabot_security_label.py" in wf
    # pull_request_target + write token: must never check out the PR head.
    assert "github.event.pull_request.head" not in wf
