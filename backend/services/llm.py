"""LLM service: summarize search results into an answer. Uses LLM provider abstraction (OpenAI, Anthropic, Azure)."""
import os

from langchain_core.messages import HumanMessage, SystemMessage

from backend.services.diagnostics.recorder import invoke_llm
from backend.services.llm_provider import get_llm

DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant with access to a knowledge base. Answer the user's question using only the provided context from the knowledge base. If the context does not contain enough information, say so and suggest rephrasing or broader questions. Keep answers concise and professional."""


def _is_llm_configured() -> bool:
    """Check if current LLM provider has required config."""
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    if provider == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    if provider == "azure_openai":
        return bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"))
    return False


def summarize_with_llm(
    query: str,
    context_chunks: list[str],
    *,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Use configured LLM provider to generate an answer from query and retrieved chunks.

    Provider selected via LLM_PROVIDER (openai, anthropic, azure_openai).
    Optional overrides: system_prompt, temperature, max_tokens.
    """
    if not _is_llm_configured():
        return "LLM is not configured. Set OPENAI_API_KEY (or ANTHROPIC_API_KEY / AZURE_OPENAI_* for other providers) in .env to enable summarized answers."
    prompt = (
        system_prompt
        or os.getenv("OPENAI_SYSTEM_PROMPT")
        or DEFAULT_SYSTEM_PROMPT
    )
    try:
        llm = get_llm(temperature=temperature, max_tokens=max_tokens)
        context = "\n\n---\n\n".join(context_chunks[:10])  # limit tokens
        user_content = f"Context from knowledge base:\n\n{context}\n\nUser question: {query}"
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_content),
        ]
        response = invoke_llm(llm, messages, "chat", assessment_id=None)
        return response.content if hasattr(response, "content") else str(response) or "No response generated."
    except Exception as e:
        return f"LLM error: {str(e)}"
