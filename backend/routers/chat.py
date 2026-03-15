"""Chat API: query KB and summarize with LLM."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import get_project_dir
from backend.services.llm import summarize_with_llm

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    category: str | None = None
    application: str | None = None
    top_k: int = 5
    # Optional LLM overrides (otherwise use .env: OPENAI_SYSTEM_PROMPT, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS)
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


def _search_kb(query: str, category: str | None = None, application: str | None = None, top_k: int = 5):
    from backend.semantic_search import (
        get_client,
        namespace_for_project,
        search_knowledge_base,
        INDEX_NAME,
    )
    project_dir = get_project_dir()
    if not project_dir:
        raise HTTPException(status_code=503, detail="PINECONE_PROJECT_DIR not configured")
    pc = get_client()
    index = pc.Index(INDEX_NAME)
    namespace = namespace_for_project(project_dir)
    results = search_knowledge_base(
        index, namespace, query,
        category_filter=category,
        application_filter=application,
        top_k=top_k,
    )
    return [h.fields.get("content", "") for h in results.result.hits]


@router.post("/chat")
def chat(body: ChatRequest):
    chunks = _search_kb(
        body.query,
        category=body.category,
        application=body.application,
        top_k=body.top_k,
    )
    answer = summarize_with_llm(
        body.query,
        chunks,
        system_prompt=body.system_prompt,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    return {
        "query": body.query,
        "answer": answer,
        "sources_used": len(chunks),
    }
