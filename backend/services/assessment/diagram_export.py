"""
Export target-state architecture: save Mermaid source to .mmd file and render to PNG.

Flow:
1. Build Mermaid code (from target_architecture_diagram).
2. Save editable source to data/assessment_diagrams/{assessment_id}/target_architecture.mmd.
3. Render to PNG via mermaid.ink API and save to target_architecture.png.
4. Report and DOCX reference this image so the diagram is visible as a proper image.

References: https://mermaid.ink (render Mermaid to image via URL).
"""

import base64
import logging
import ssl
import urllib.request
from pathlib import Path

import certifi

logger = logging.getLogger(__name__)

# Base URL for mermaid.ink image rendering (no auth required)
MERMAID_INK_IMG = "https://mermaid.ink/img"


def _diagrams_dir(assessment_id: str) -> Path:
    """Directory for generated diagram artifacts: .mmd and .png."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    d = root / "data" / "assessment_diagrams" / assessment_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def clear_diagram_artifacts(assessment_id: str) -> None:
    """Remove generated diagram folder for this assessment (e.g. when re-running research)."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    d = root / "data" / "assessment_diagrams" / assessment_id
    if d.exists():
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def _mermaid_to_png_url(mermaid_code: str) -> str:
    """Return mermaid.ink URL for the given Mermaid code (PNG image)."""
    encoded = base64.urlsafe_b64encode(mermaid_code.strip().encode("utf-8")).decode("ascii")
    return f"{MERMAID_INK_IMG}/{encoded}.png"


def _ssl_context() -> ssl.SSLContext:
    """SSL context using certifi CA bundle (e.g. for macOS)."""
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(certifi.where())
    return ctx


def _fetch_png_from_mermaid_ink(mermaid_code: str) -> bytes | None:
    """Fetch PNG bytes from mermaid.ink for the given Mermaid code. Returns None on failure."""
    url = _mermaid_to_png_url(mermaid_code)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AssessmentReport/1.0"})
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:  # nosec B310 - URL always https://mermaid.ink (hardcoded constant), never user-supplied
            return resp.read()
    except Exception as e:
        logger.warning("Failed to fetch diagram from mermaid.ink: %s", e)
        return None


def export_target_diagram(assessment_id: str, mermaid_code: str) -> dict:
    """
    Save Mermaid source to .mmd file and render to PNG. Creates/overwrites files in
    data/assessment_diagrams/{assessment_id}/.

    When mermaid.ink PNG fetch fails, we still return mermaid_ink_url so the report
    can embed that image (mermaid.ink serves the diagram via URL). This avoids blank
    diagrams in the report when our PNG is missing.

    Returns:
        {
            "mmd_path": Path to .mmd file,
            "png_path": Path to .png file (if render succeeded),
            "image_url": URL for report embedding: our PNG API path if we have PNG,
                         else mermaid.ink direct URL so the diagram still displays,
            "mermaid_ink_url": Direct mermaid.ink image URL (always set when we have code),
        }
    """
    code = (mermaid_code or "").strip()
    if not code:
        return {"mmd_path": None, "png_path": None, "image_url": None, "mermaid_ink_url": None}

    dir_path = _diagrams_dir(assessment_id)
    mmd_file = dir_path / "target_architecture.mmd"
    png_file = dir_path / "target_architecture.png"

    mmd_file.write_text(code, encoding="utf-8")

    mermaid_ink_url = _mermaid_to_png_url(code)

    png_bytes = _fetch_png_from_mermaid_ink(code)
    if png_bytes:
        png_file.write_bytes(png_bytes)
        image_url = f"/api/assessment/{assessment_id}/diagram/target?format=png"
        return {"mmd_path": mmd_file, "png_path": png_file, "image_url": image_url, "mermaid_ink_url": mermaid_ink_url}

    # Fallback: use mermaid.ink URL in report so the diagram is not blank (e.g. if fetch failed or returned error image)
    return {"mmd_path": mmd_file, "png_path": None, "image_url": mermaid_ink_url, "mermaid_ink_url": mermaid_ink_url}
