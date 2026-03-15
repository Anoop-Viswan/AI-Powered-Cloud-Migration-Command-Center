"""
Research flow – data structures for KB hits, confidence, and official-doc results.

Used by the Research Agent to return structured data to the API and UI:
- KB hits with scores and explainability (why_match)
- KB confidence (0–1, label, below_threshold)
- Official-doc results (Phase 4) with URL and rationale

All fields are optional where appropriate so we can extend without breaking clients.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ─── KB hit (one search result from Pinecone) ─────────────────────────────────


class KBHit(BaseModel):
    """
    A single knowledge-base search hit with score, source, and explainability.

    - score: Relevance score from Pinecone (rerank or vector).
    - file_path: Source file path in the project (e.g. "docs/azure-migration.md").
    - application: Application name from metadata (or "default").
    - category: File type (e.g. "pdf", "md").
    - content_preview: First N chars of content for display (avoid sending huge chunks).
    - why_match: Short explanation of why this hit is relevant (origin/destination, features).
    """

    score: float = Field(description="Relevance score from search")
    file_path: str = Field(default="", description="Source file path")
    application: str = Field(default="", description="Application from metadata")
    category: str = Field(default="", description="File category/type")
    content_preview: str = Field(default="", description="Short preview of content")
    why_match: str = Field(default="", description="Why this hit matches the request (explainability)")


# ─── KB confidence (aggregate) ───────────────────────────────────────────────


class KBConfidence(BaseModel):
    """
    Aggregate confidence that the KB supports this migration request.

    - value: 0.0–1.0 (or think of as 0–100%).
    - label: "high" | "medium" | "low" for display.
    - below_threshold: True if we should run official-doc research (e.g. value < 0.35).
    """

    value: float = Field(ge=0.0, le=1.0, description="Confidence score 0–1")
    label: Literal["high", "medium", "low"] = Field(description="Human-readable label")
    below_threshold: bool = Field(
        default=False,
        description="True when confidence is below configured low threshold (trigger official-doc research)",
    )


# ─── Official-doc result (Phase 4: from Tavily or other web search) ───────────


class OfficialDocResult(BaseModel):
    """
    One result from official-documentation search (e.g. Microsoft Learn, Snowflake docs).

    - title: Page or document title.
    - url: Source URL for reference.
    - snippet: Short excerpt or summary.
    - rationale: Why the Architect should follow this recommendation (1–2 sentences).
    """

    title: str = Field(default="", description="Document title")
    url: str = Field(default="", description="Source URL")
    snippet: str = Field(default="", description="Excerpt or summary")
    rationale: str = Field(default="", description="Why this step should be followed")


# ─── Full research result (what run_research returns) ─────────────────────────


class ResearchResult(BaseModel):
    """
    Full result of the Research Agent run.

    - approach_document: The main markdown output (stored in DB and shown in UI).
    - kb_confidence: Aggregate KB confidence (value, label, below_threshold).
    - kb_hits: List of KB hits with scores and why_match (for explainability in UI).
    - official_docs: List of official-doc results (empty until Phase 4 / when below_threshold).
    """

    approach_document: str = Field(description="Generated approach document (markdown)")
    kb_confidence: KBConfidence = Field(description="KB confidence score and label")
    kb_hits: list[KBHit] = Field(default_factory=list, description="KB hits with explainability")
    official_docs: list[OfficialDocResult] = Field(
        default_factory=list,
        description="Official-documentation results (when confidence below threshold)",
    )
