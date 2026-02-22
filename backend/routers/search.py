"""Search API: query the knowledge base."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import get_project_dir

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    category: str | None = None
    application: str | None = None
    top_k: int = 5

# Lazy import after path is set
def _get_search_deps():
    from semantic_search import (
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
    return index, namespace


@router.post("/search")
def search(body: SearchRequest):
    index, namespace = _get_search_deps()
    results = search_knowledge_base(
        index, namespace, body.query,
        category_filter=body.category,
        application_filter=body.application,
        top_k=body.top_k,
    )
    hits = results.result.hits
    return {
        "query": body.query,
        "hits": [
            {
                "id": h["_id"],
                "score": h["_score"],
                "content": h.fields.get("content", ""),
                "file_path": h.fields.get("file_path", ""),
                "category": h.fields.get("category", ""),
                "application": h.fields.get("application", ""),
            }
            for h in hits
        ],
    }
