"""Research Agent: KB search + LLM synthesis → Approach document. Standalone, traceable via LangSmith."""

import os
import sys
from pathlib import Path

# Ensure project root on path for semantic_search
_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from langchain_core.messages import HumanMessage, SystemMessage

from backend.services.assessment.models import ApplicationProfile
from backend.services.llm_provider import get_llm


def _search_kb(query: str, top_k: int = 8) -> list[str]:
    """Search Knowledge Base; returns list of content chunks."""
    from backend.config import get_project_dir
    from semantic_search import (
        INDEX_NAME,
        get_client,
        namespace_for_project,
        search_knowledge_base,
    )

    project_dir = get_project_dir()
    if not project_dir:
        return []
    pc = get_client()
    index = pc.Index(INDEX_NAME)
    namespace = namespace_for_project(project_dir)
    results = search_knowledge_base(index, namespace, query, top_k=top_k)
    return [h.fields.get("content", "") for h in results.result.hits if h.fields.get("content")]


def run_research(profile: ApplicationProfile) -> str:
    """
    Produce approach document from application profile.
    Uses KB search + LLM synthesis. LangSmith traces when LANGCHAIN_TRACING_V2=true.
    """
    # Build search query from profile
    terms = [profile.application_name, profile.business_purpose or profile.description]
    terms.extend(profile.tech_stack)
    terms.extend(profile.database_types)
    terms.append(profile.target_environment)
    terms.append("migration")
    query = " ".join(t for t in terms if t)

    # KB search
    chunks = _search_kb(query, top_k=8) if query else []
    context = "\n\n---\n\n".join(chunks[:10]) if chunks else "(No relevant documents found in knowledge base.)"

    # LLM synthesis (uses get_llm for provider-agnostic switching; LangSmith traces when enabled)
    llm = get_llm(temperature=0.3)

    system_prompt = """You are a migration architect. Given an application profile (with architecture pillars: overview, data, DR, cost, security, timeline) and context from a knowledge base, produce an APPROACH DOCUMENT with:
1. Recommended migration strategy (lift-and-shift, refactor, or re-platform) with brief rationale
2. Key steps and phases
3. Best practices to follow
4. Pitfalls to avoid
5. References to any relevant prior migrations from the context

Consider RTO/RPO, data volume, security requirements, and budget when making recommendations. Be concise and professional. Output in markdown."""

    profile_text = profile.to_context_text()
    user_content = f"""## Application Profile (Architecture Pillars)
{profile_text}

## Context from Knowledge Base
{context}

Produce the approach document."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = llm.invoke(messages)
    return response.content if hasattr(response, "content") else str(response)
