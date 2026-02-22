"""LLM service: summarize search results into an answer (OpenAI)."""
import os
from openai import OpenAI

SYSTEM_PROMPT = """You are a helpful assistant with access to a knowledge base. Answer the user's question using only the provided context from the knowledge base. If the context does not contain enough information, say so and suggest rephrasing or broader questions. Keep answers concise and professional."""


def summarize_with_llm(query: str, context_chunks: list[str]) -> str:
    """Use OpenAI to generate an answer from query and retrieved chunks. Returns error message if not configured."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "LLM is not configured. Set OPENAI_API_KEY in .env to enable summarized answers."
    try:
        client = OpenAI(api_key=api_key)
        context = "\n\n---\n\n".join(context_chunks[:10])  # limit tokens
        user_content = f"Context from knowledge base:\n\n{context}\n\nUser question: {query}"
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1024,
        )
        return resp.choices[0].message.content or "No response generated."
    except Exception as e:
        return f"LLM error: {str(e)}"
