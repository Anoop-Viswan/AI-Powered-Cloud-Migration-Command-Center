"""
LLM provider abstraction: seamless switching between OpenAI, Anthropic, Azure OpenAI.

All LLM calls (Chat, Research Agent, Summarizer Agent) use get_llm() for a unified,
provider-agnostic interface. Switch providers via LLM_PROVIDER env var.
"""

import os
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_llm(
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """
    Return a LangChain ChatModel based on LLM_PROVIDER.

    Supported providers:
    - openai (default): OPENAI_API_KEY, OPENAI_MODEL
    - anthropic: ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    - azure_openai: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT

    All providers support optional overrides: model, temperature, max_tokens.
    """
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    temp = temperature if temperature is not None else _float_env("OPENAI_TEMPERATURE", 0.3)
    max_tok = max_tokens if max_tokens is not None else _int_env("OPENAI_MAX_TOKENS", 4096)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=temp,
            max_tokens=max_tok,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "LLM_PROVIDER=anthropic requires langchain-anthropic. "
                "Install with: pip install langchain-anthropic"
            )
        return ChatAnthropic(
            model=model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            temperature=temp,
            max_tokens=max_tok,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    if provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            temperature=temp,
            max_tokens=max_tok,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER={provider}. "
        "Supported: openai, anthropic, azure_openai"
    )
