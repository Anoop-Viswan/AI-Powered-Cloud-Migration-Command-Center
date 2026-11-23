"""Guards for the reachability assumptions behind our dependency-risk decisions.

When we judge a CVE "not reachable" (or accept residual risk), the judgment rests on
how the app uses the library. These tests turn that assumption into a check, so a
future change that makes the vulnerable code path reachable fails CI and forces a
fresh look, instead of quietly invalidating an old risk call.
"""

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"


def _imports() -> list[tuple[str, str]]:
    """(file, imported name) for every import in backend/."""
    found = []
    for py in BACKEND.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found += [(str(py), a.name) for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.append((str(py), node.module))
                found += [(str(py), f"{node.module}.{a.name}") for a in node.names]
    return found


def test_langgraph_used_in_process_only_no_remote_sdk():
    """GHSA-3fx2-cqw9-xr3c (Nov 2026) hit langgraph-sdk streaming and RemoteGraph.

    We patched anyway (langgraph 1.2.14), but our exposure was nil because we only
    run StateGraph in-process. If you add RemoteGraph or the SDK client, validate
    thread_id/assistant_id inputs and revisit the advisory history first.
    """
    remote = [
        (f, name) for f, name in _imports()
        if name.startswith("langgraph_sdk") or name.endswith("RemoteGraph") or "pregel.remote" in name
    ]
    assert remote == [], f"Remote LangGraph usage introduced, see docstring: {remote}"


def test_pypdf_entry_point_is_single_guarded_extractor():
    """All PDF parsing goes through document_extractors._extract_pdf, which catches every
    exception. pypdf CVEs are mostly DoS on crafted files, so a second, unguarded
    parsing path would widen the blast radius."""
    users = sorted({Path(f).name for f, name in _imports() if name.split(".")[0] == "pypdf"})
    assert users == ["document_extractors.py"], users
