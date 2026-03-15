"""
Research Agent: KB search with confidence and explainability → Approach document.

Flow (see RESEARCH_FLOW_BLUEPRINT.md):
1. Build structured query from profile (origin/destination, workload, use case).
2. Search KB; keep full hits (score, file_path, application, content).
3. Compute KB confidence (0–1); if below threshold, later phases trigger official-doc research.
4. For each hit, compute "why_match" (explainability) from profile + hit content.
5. Synthesize approach document via LLM using KB context; include references.
6. Return ResearchResult (approach_document, kb_confidence, kb_hits, official_docs).

All external tools (e.g. Tavily for official docs) go through the Tool Gateway (Phase 3+).
LangSmith traces when LANGCHAIN_TRACING_V2=true.
"""

import os
import time
from pathlib import Path
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from backend.services.assessment.models import ApplicationProfile
from backend.services.assessment.research_models import (
    KBConfidence,
    KBHit,
    OfficialDocResult,
    ResearchResult,
)
from backend.services.diagnostics.recorder import invoke_llm
from backend.services.llm_provider import get_llm


# ─── Configuration (env with defaults) ───────────────────────────────────────
# Min relevance score to count a hit as "strong" for confidence.
RESEARCH_KB_MIN_SCORE = float(os.getenv("RESEARCH_KB_MIN_SCORE", "0.5"))
# Below this confidence we trigger official-doc research (Phase 4).
RESEARCH_KB_CONFIDENCE_LOW = float(os.getenv("RESEARCH_KB_CONFIDENCE_LOW", "0.35"))
# Set to "false" to disable official-doc web search even when confidence is below threshold.
RESEARCH_OFFICIAL_DOCS_ENABLED = os.getenv("RESEARCH_OFFICIAL_DOCS_ENABLED", "true").strip().lower() in ("true", "1", "yes")
# Max content length to keep per hit for preview and for LLM context (avoid token overflow).
CONTENT_PREVIEW_CHARS = 1200
# Max official-doc results to fetch and include (avoid token overflow in final doc).
OFFICIAL_DOCS_MAX_RESULTS = 5


def _get_project_index_namespace():
    """
    Get Pinecone index and namespace for the configured project directory.
    Returns (index, namespace) or (None, None) if project dir not set.
    """
    from backend.config import get_project_dir
    from backend.semantic_search import (
        INDEX_NAME,
        get_client,
        namespace_for_project,
    )

    project_dir = get_project_dir()
    if not project_dir:
        return None, None
    pc = get_client()
    index = pc.Index(INDEX_NAME)
    namespace = namespace_for_project(project_dir)
    return index, namespace


def _search_kb_full(query: str, top_k: int = 10) -> list[dict]:
    """
    Search the knowledge base and return full hit payload (score + metadata + content).

    Each item in the returned list is a dict with:
    - score: float (relevance)
    - file_path: str
    - application: str
    - category: str
    - content: str (full chunk; caller may truncate for preview)

    Returns empty list if project dir not set or search fails.
    """
    from backend.semantic_search import search_knowledge_base

    index, namespace = _get_project_index_namespace()
    if not index or not namespace or not query.strip():
        return []

    results = search_knowledge_base(index, namespace, query, top_k=top_k)
    hits = []
    # Pinecone returns result.hits; each hit has _score (dict key or attr) and .fields (metadata + content)
    for h in getattr(results.result, "hits", []) or []:
        score = getattr(h, "_score", None)
        if score is None and isinstance(h, dict):
            score = h.get("_score")
        if score is None:
            continue
        fields = getattr(h, "fields", None)
        if fields is None and isinstance(h, dict):
            fields = h.get("fields") or {}
        if not isinstance(fields, dict):
            fields = {}
        content = (fields.get("content") or "").strip()
        if not content:
            continue
        hits.append({
            "score": float(score),
            "file_path": fields.get("file_path") or "",
            "application": fields.get("application") or "",
            "category": fields.get("category") or "",
            "content": content,
        })
    return hits


def _compute_confidence(hits: list[dict], min_score: float) -> KBConfidence:
    """
    Compute a single 0–1 KB confidence from the list of hits.

    Simple formula:
    - No hits or all below min_score → 0, label "low", below_threshold True.
    - Otherwise: use top score (normalized by clamping to [0,1]) and a small boost
      for number of strong hits (score >= min_score). Label by value bands.
    """
    strong = [h for h in hits if h["score"] >= min_score]
    if not strong:
        return KBConfidence(
            value=0.0,
            label="low",
            below_threshold=True,
        )
    top_score = max(h["score"] for h in hits)
    # Normalize: assume scores are typically in a range (e.g. 0–1 or 0–2 after rerank).
    # Clamp to [0, 1] and optionally scale; keep it simple.
    normalized = min(1.0, max(0.0, top_score))
    # Slight boost for multiple strong hits (more coverage)
    n_strong = len(strong)
    if n_strong >= 3:
        normalized = min(1.0, normalized + 0.1)
    elif n_strong >= 1:
        normalized = min(1.0, normalized + 0.05)

    if normalized >= 0.6:
        label = "high"
    elif normalized >= 0.35:
        label = "medium"
    else:
        label = "low"

    return KBConfidence(
        value=round(normalized, 3),
        label=label,
        below_threshold=normalized < RESEARCH_KB_CONFIDENCE_LOW,
    )


def _explain_why_match(hit: dict, profile: ApplicationProfile) -> str:
    """
    Rule-based explainability: why does this KB hit match the request?

    We compare profile fields to the hit's content and metadata:
    - Origin/destination: e.g. "on-prem to Azure" in content and profile.
    - Target environment: Azure, AWS, GCP, Snowflake in content.
    - Tech stack / DB: overlap between profile.tech_stack, profile.database_types and content.
    - Application: hit.application matches or content mentions similar app.

    Returns a short 1–2 sentence explanation for the Architect.
    """
    content_lower = (hit.get("content") or "")[:800].lower()
    file_path = (hit.get("file_path") or "").lower()
    reasons = []

    # Origin/destination pattern
    origin = (profile.current_environment or "").lower()
    target = (profile.target_environment or "").lower()
    if origin and target:
        pattern = f"{origin}"
        if "azure" in target and ("azure" in content_lower or "azure" in file_path):
            reasons.append(f"Target environment (Azure) matches; origin {origin}")
        elif "aws" in target and ("aws" in content_lower or "amazon" in content_lower):
            reasons.append(f"Target environment (AWS) matches; origin {origin}")
        elif "snowflake" in content_lower or "snowflake" in file_path:
            reasons.append("Snowflake migration content")
        elif target in content_lower or target in file_path:
            reasons.append(f"Target ({target}) and origin ({origin}) pattern matches")

    # Tech stack / database overlap
    for tech in (profile.tech_stack or [])[:5]:
        if tech and tech.lower() in content_lower:
            reasons.append(f"Tech stack: {tech}")
            break
    for db in (profile.database_types or [])[:3]:
        if db and db.lower() in content_lower:
            reasons.append(f"Database: {db}")
            break

    # Application name in content or path
    app_name = (profile.application_name or "").strip()
    if app_name and (app_name.lower() in content_lower or app_name.lower() in file_path):
        reasons.append(f"Application context: {app_name}")

    if not reasons:
        reasons.append("Relevant migration or architecture content (semantic match)")
    return "; ".join(reasons[:3])  # Cap at 3 reasons to keep it short


def _build_official_doc_queries(profile: ApplicationProfile) -> list[tuple[str, list[str] | None]]:
    """
    Build (query, include_domains) for official-documentation web search.

    Target platform rules:
    - Azure → query "Azure migration guide" and optionally restrict to learn.microsoft.com.
    - Snowflake (from tech_stack or profile) → "Snowflake migration guide".
    - AWS / GCP → analogous. include_domains helps focus on official sources.
    Returns a list of (query_string, domains_or_None). None means no domain filter.
    """
    target = (profile.target_environment or "").lower()
    tech_stack = [t.lower() for t in (profile.tech_stack or [])]
    queries: list[tuple[str, list[str] | None]] = []

    if target == "azure":
        queries.append(("Azure cloud migration guide best practices", ["learn.microsoft.com"]))
        if profile.contains_database_migration == "yes" or any("sql" in t for t in tech_stack):
            queries.append(("Azure SQL migration guide", ["learn.microsoft.com"]))
    elif target == "aws":
        queries.append(("AWS migration guide best practices", ["docs.aws.amazon.com"]))
    elif target == "gcp":
        queries.append(("Google Cloud migration guide", ["cloud.google.com"]))
    if "snowflake" in " ".join(tech_stack):
        queries.append(("Snowflake migration guide best practices", ["docs.snowflake.com"]))

    if not queries:
        # Fallback: generic migration with no domain filter
        queries.append((f"{profile.current_environment or 'on-prem'} to {profile.target_environment or 'cloud'} migration guide", None))
    return queries


def _run_official_doc_search(profile: ApplicationProfile) -> list[OfficialDocResult]:
    """
    When KB confidence is below threshold, call the Tool Gateway web_search to fetch
    official-documentation results. Returns a list of OfficialDocResult (title, url, snippet, rationale).
    Rationale is left empty here; we could add a single LLM call later to generate one sentence per result.
    """
    from backend.services.tool_gateway import get_gateway

    gateway = get_gateway()
    seen_urls: set[str] = set()
    all_results: list[OfficialDocResult] = []
    queries = _build_official_doc_queries(profile)
    max_total = OFFICIAL_DOCS_MAX_RESULTS

    for query, include_domains in queries:
        if len(all_results) >= max_total:
            break
        try:
            params: dict = {"query": query, "max_results": max_total - len(all_results)}
            if include_domains:
                params["include_domains"] = include_domains
            raw = gateway.invoke("web_search", params)
        except KeyError:
            # Tool not registered (e.g. web_search missing)
            raw = []
        # Let TavilySearchError and other API/network errors propagate so the user sees the exact error
        if not isinstance(raw, list):
            raw = []
        for r in raw:
            if len(all_results) >= max_total:
                break
            if not isinstance(r, dict):
                continue
            url = (r.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            all_results.append(OfficialDocResult(
                title=(r.get("title") or "").strip() or "(No title)",
                url=url,
                snippet=(r.get("content") or r.get("snippet") or "").strip()[:500],
                rationale="",  # Optional: one LLM call to add "why follow this" per result
            ))
    return all_results


def _build_queries(profile: ApplicationProfile) -> list[str]:
    """
    Build one or more search queries from the profile for KB search.

    We use:
    1. A combined "origin to target migration" + workload query (main).
    2. Optionally a second query for coverage (e.g. tech stack + "migration").
    Returns a list of query strings; the first is the primary, rest can be used for coverage.
    """
    origin = profile.current_environment or "on-prem"
    target = profile.target_environment or "azure"
    main_terms = [
        f"{origin} to {target}",
        "migration",
        profile.application_name or "",
        profile.business_purpose or "",
    ]
    main_terms.extend(profile.tech_stack or [])
    main_terms.extend(profile.database_types or [])
    query_main = " ".join(t for t in main_terms if t and str(t).strip())
    if not query_main.strip():
        query_main = "cloud migration assessment"
    return [query_main]


def run_research(
    profile: ApplicationProfile,
    event_callback: Callable[[str, dict], None] | None = None,
) -> ResearchResult:
    """
    Run the full research flow: KB search → confidence → explainability → LLM synthesis.

    If event_callback is provided, it is called with (event_type, payload) at each phase
    for live updates (e.g. SSE). Event types: "phase", "kb_results", "confidence",
    "official_search_skipped", "official_search_results", "key_results", "phase", "done", "error".

    Returns a ResearchResult with:
    - approach_document: markdown for storage and display.
    - kb_confidence: value, label, below_threshold.
    - kb_hits: list of KBHit with score, file_path, application, content_preview, why_match.
    - official_docs: empty in Phase 1/2; filled in Phase 4 when below_threshold and web search enabled.
    """
    def emit(event_type: str, payload: dict) -> None:
        if event_callback:
            event_callback(event_type, payload)

    total_start = time.perf_counter()

    # ─── 0. Thinking / start ─────────────────────────────────────────────────
    emit("phase", {"message": "Thinking…", "step": "start"})

    # ─── 0b. Check KB availability ───────────────────────────────────────────
    index, namespace = _get_project_index_namespace()
    if not index or not namespace:
        emit("phase", {
            "message": "Knowledge base not available: PINECONE_PROJECT_DIR not set or Pinecone not configured. Search will return no hits. Set PINECONE_PROJECT_DIR (and PINECONE_API_KEY) in .env. See docs/ENV_REFERENCE.md.",
        })

    # ─── 1. Retrieve from KB (with timing) ───────────────────────────────────
    emit("phase", {"message": "Retrieving from knowledge base…", "step": "kb"})
    t_kb = time.perf_counter()
    queries = _build_queries(profile)
    query = queries[0] if queries else "migration assessment"
    raw_hits = _search_kb_full(query, top_k=10)
    kb_elapsed = time.perf_counter() - t_kb
    emit("phase", {"message": f"KB retrieval took {kb_elapsed:.1f}s", "step": "kb_done", "duration_seconds": round(kb_elapsed, 1)})

    # ─── 2. Compute KB confidence ───────────────────────────────────────────
    emit("phase", {"message": "Computing confidence from KB hits…", "step": "confidence"})
    t_conf = time.perf_counter()
    kb_confidence = _compute_confidence(raw_hits, RESEARCH_KB_MIN_SCORE)
    conf_elapsed = time.perf_counter() - t_conf
    emit("confidence", {**kb_confidence.model_dump(), "duration_seconds": round(conf_elapsed, 1)})
    emit("phase", {"message": f"Confidence: {kb_confidence.label} ({kb_confidence.value:.0%}) (took {conf_elapsed:.1f}s)", "step": "confidence_done", "duration_seconds": round(conf_elapsed, 1)})

    # ─── 3. Build KBHit list with explainability (why_match) ──────────────────
    kb_hits: list[KBHit] = []
    for h in raw_hits:
        why = _explain_why_match(h, profile)
        content = h.get("content") or ""
        preview = content[:CONTENT_PREVIEW_CHARS] + ("..." if len(content) > CONTENT_PREVIEW_CHARS else "")
        kb_hits.append(KBHit(
            score=round(h["score"], 4),
            file_path=h.get("file_path") or "",
            application=h.get("application") or "",
            category=h.get("category") or "",
            content_preview=preview,
            why_match=why,
        ))
    # Emit KB results for transparency (file_path, score, why_match) with duration
    emit("kb_results", {
        "count": len(raw_hits),
        "query": query,
        "hits": [{"file_path": h.file_path, "score": h.score, "why_match": h.why_match} for h in kb_hits],
        "duration_seconds": round(kb_elapsed, 1),
        "message": f"Retrieved {len(raw_hits)} KB hit(s) in {kb_elapsed:.1f}s",
    })

    # ─── 4. If confidence below threshold, retrieve from Tavily (with timing) ───
    official_docs: list[OfficialDocResult] = []
    official_search_skip_reason: str | None = None
    tavily_elapsed: float = 0.0
    if kb_confidence.below_threshold:
        if not RESEARCH_OFFICIAL_DOCS_ENABLED:
            official_search_skip_reason = (
                "Official-documentation search is disabled (RESEARCH_OFFICIAL_DOCS_ENABLED=false). "
                "Set RESEARCH_OFFICIAL_DOCS_ENABLED=true in .env to enable. See docs/ENV_REFERENCE.md."
            )
            emit("official_search_skipped", {"reason": official_search_skip_reason})
        elif not (os.getenv("TAVILY_API_KEY") or "").strip():
            official_search_skip_reason = (
                "Official-documentation search was skipped: TAVILY_API_KEY is not set. "
                "Add TAVILY_API_KEY to .env (get key from https://app.tavily.com/) to enable. See docs/ENV_REFERENCE.md."
            )
            emit("official_search_skipped", {"reason": official_search_skip_reason})
        else:
            emit("phase", {"message": "Retrieving from official documentation (Tavily)…", "step": "tavily"})
            t_tavily = time.perf_counter()
            official_docs = _run_official_doc_search(profile)
            tavily_elapsed = time.perf_counter() - t_tavily
            emit("phase", {"message": f"Tavily retrieval took {tavily_elapsed:.1f}s", "step": "tavily_done", "duration_seconds": round(tavily_elapsed, 1)})
            emit("official_search_results", {
                "count": len(official_docs),
                "results": [
                    {"title": d.title, "url": d.url, "snippet_preview": (d.snippet or "")[:200]}
                    for d in official_docs
                ],
                "duration_seconds": round(tavily_elapsed, 1),
                "message": f"Retrieved {len(official_docs)} official doc(s) in {tavily_elapsed:.1f}s",
            })
            if not official_docs:
                official_search_skip_reason = (
                    "Official-documentation search completed but found no results for this query. "
                    "You have quota (see https://app.tavily.com/). Try different search terms or run research again."
                )
                emit("official_search_skipped", {"reason": official_search_skip_reason})

    # ─── 5. Build context string for LLM (KB + optional official-doc snippets) ─
    if kb_hits:
        context_parts = []
        for i, hit in enumerate(kb_hits[:10], 1):
            ref = f"[Source {i}: {hit.file_path} (app: {hit.application}, score: {hit.score})]"
            context_parts.append(f"{ref}\n{hit.content_preview}")
        context = "\n\n---\n\n".join(context_parts)
    else:
        context = "(No relevant documents found in knowledge base.)"

    if official_docs:
        context += "\n\n---\n\n## Official documentation (from web search)\n\n"
        for i, doc in enumerate(official_docs[:5], 1):
            context += f"[Official {i}: {doc.title}]({doc.url})\n{doc.snippet}\n\n"

    # ─── 5b. Emit "Got these key results" for full transparency ───────────────
    kb_summary = ", ".join(h.file_path or "(unknown)" for h in kb_hits[:5]) if kb_hits else "none"
    off_summary = "; ".join(d.title or d.url for d in official_docs[:5]) if official_docs else "none"
    key_results_msg = f"KB: {len(kb_hits)} source(s) ({kb_summary}). Official docs: {len(official_docs)} result(s) ({off_summary})."
    emit("key_results", {
        "message": f"Got these key results: {key_results_msg}",
        "kb_count": len(kb_hits),
        "official_count": len(official_docs),
        "kb_sources": [h.file_path for h in kb_hits[:5]],
        "official_titles": [d.title for d in official_docs[:5]],
    })

    # ─── 6. LLM synthesis: approach document (with timing) ─────────────────────
    n_kb, n_off = len(kb_hits), len(official_docs)
    emit("phase", {
        "message": "Summarizing approach with LLM (using KB + official docs, aligned to migration pillars)…",
        "step": "llm_synthesis",
    })
    t_llm = time.perf_counter()
    llm = get_llm(temperature=0.3)
    system_prompt = """You are a migration architect. Given an application profile and context from a knowledge base, produce an APPROACH DOCUMENT in markdown with:
1. Recommended migration strategy (lift-and-shift, refactor, or re-platform) with brief rationale
2. Key steps and phases
3. Best practices to follow
4. Pitfalls to avoid
5. References to the provided KB sources (use "Source 1", "Source 2" as in the context) where relevant

Consider RTO/RPO, data volume, security requirements, and budget. Be concise and professional."""

    profile_text = profile.to_context_text()
    user_content = f"""## Application Profile (Architecture Pillars)
{profile_text}

## Context from Knowledge Base
{context}

Produce the approach document. Where you use prior migrations or docs, cite the source (e.g. "per Source 1" or "see Source 2")."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = invoke_llm(llm, messages, "research", assessment_id=None)
    approach_document = response.content if hasattr(response, "content") else str(response)
    llm_elapsed = time.perf_counter() - t_llm
    emit("phase", {
        "message": f"Synthesis complete (LLM took {llm_elapsed:.1f}s)",
        "step": "llm_done",
        "duration_seconds": round(llm_elapsed, 1),
    })

    # ─── 7. Prepend KB summary and optional official-doc section ─────────────────
    summary_lines = [
        "## KB search summary",
        f"- **Confidence:** {kb_confidence.label} ({kb_confidence.value:.0%})",
        f"- **Hits:** {len(kb_hits)}",
    ]
    if kb_hits:
        summary_lines.append("- **Top sources:** " + ", ".join(h.file_path or "(unknown)" for h in kb_hits[:5]))
    if kb_confidence.below_threshold:
        if official_docs:
            summary_lines.append("- **Note:** Confidence below threshold; official-documentation search was run (see below).")
        elif official_search_skip_reason:
            summary_lines.append(f"- **Note:** {official_search_skip_reason}")
        else:
            summary_lines.append("- **Note:** Confidence is below threshold; official-documentation research can be run to supplement (set TAVILY_API_KEY and ensure RESEARCH_OFFICIAL_DOCS_ENABLED). See docs/ENV_REFERENCE.md.")
    summary_lines.append("")

    # Append an "Official documentation" section when we have web search results
    if official_docs:
        summary_lines.append("## Official documentation (references)")
        for doc in official_docs:
            summary_lines.append(f"- **[{doc.title}]({doc.url})**")
            if doc.snippet:
                summary_lines.append(f"  {doc.snippet[:300]}{'...' if len(doc.snippet) > 300 else ''}")
            if doc.rationale:
                summary_lines.append(f"  *Rationale:* {doc.rationale}")
        summary_lines.append("")

    full_approach = "\n".join(summary_lines) + approach_document

    result = ResearchResult(
        approach_document=full_approach,
        kb_confidence=kb_confidence,
        kb_hits=kb_hits,
        official_docs=official_docs,
    )
    total_elapsed = time.perf_counter() - total_start
    emit("done", {
        "approach_document": result.approach_document,
        "kb_confidence": result.kb_confidence.model_dump(),
        "kb_hits": [h.model_dump() for h in result.kb_hits],
        "official_docs": [d.model_dump() for d in result.official_docs],
        "duration_seconds": round(total_elapsed, 1),
        "message": f"Done. Total research took {total_elapsed:.1f}s.",
    })
    return result
