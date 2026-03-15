"""Approximate cost estimation from token counts (model-specific pricing)."""

# Per 1M tokens (input, output). Approximate; update from provider pricing pages.
MODEL_PRICING = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4-turbo": (10.00, 30.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-opus": (15.00, 75.00),
}


def estimate_cost_usd(model: str | None, input_tokens: int, output_tokens: int) -> float:
    """Return approximate cost in USD for the given model and token counts."""
    if not model:
        model = "gpt-4o-mini"
    # Normalize model name (e.g. strip deployment prefix)
    model_lower = (model or "").strip().lower()
    pricing = MODEL_PRICING.get(model_lower)
    if not pricing:
        for k in MODEL_PRICING:
            if k in model_lower:
                pricing = MODEL_PRICING[k]
                break
    if not pricing:
        pricing = MODEL_PRICING["gpt-4o-mini"]
    price_in, price_out = pricing
    return (input_tokens / 1e6 * price_in) + (output_tokens / 1e6 * price_out)
