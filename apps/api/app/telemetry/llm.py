"""Telemetry wrappers for LLM provider calls."""

from __future__ import annotations

import time
from typing import Any

from app.telemetry.ids import generate_id
from app.telemetry.logging import log_event
from app.telemetry.privacy import stable_hash


def _estimate_cost(model: str, input_tokens: int, output_tokens: int, cache_read_tokens: int = 0, cache_creation_tokens: int = 0) -> float:
    """Estimate Anthropic call cost using BuildSense's current model rates."""
    if "haiku" in model:
        input_rate = 0.80 / 1_000_000
        output_rate = 4.00 / 1_000_000
        cache_write_rate = 1.00 / 1_000_000
        cache_read_rate = 0.08 / 1_000_000
    else:
        input_rate = 3.00 / 1_000_000
        output_rate = 15.00 / 1_000_000
        cache_write_rate = 3.75 / 1_000_000
        cache_read_rate = 0.30 / 1_000_000

    # Subtract cached tokens from base input token calculation
    base_input_tokens = max(0, input_tokens - cache_read_tokens - cache_creation_tokens)
    return (
        (base_input_tokens * input_rate)
        + (output_tokens * output_rate)
        + (cache_creation_tokens * cache_write_rate)
        + (cache_read_tokens * cache_read_rate)
    )


def _payload_hash(payload: Any) -> str:
    """Return a short stable hash for privacy-safe payload correlation."""
    return stable_hash(repr(payload))


async def traced_anthropic_messages_create(
    client: Any,
    *,
    model: str,
    purpose: str,
    is_byok: bool,
    **kwargs: Any,
) -> Any:
    """Call Anthropic messages.create while recording sanitized local telemetry."""
    llm_call_id = generate_id("llm")
    started_at = time.perf_counter()
    log_event(
        "llm_call_started",
        llm_call_id=llm_call_id,
        llm_provider="anthropic",
        llm_model=model,
        llm_purpose=purpose,
        is_byok=is_byok,
        prompt_hash=_payload_hash(kwargs.get("messages")),
        system_hash=_payload_hash(kwargs.get("system")) if kwargs.get("system") is not None else None,
        messages=kwargs.get("messages"),
        system=kwargs.get("system"),
    )
    try:
        response = await client.messages.create(model=model, **kwargs)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        cache_read_tokens = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        cache_creation_tokens = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        cost_usd = _estimate_cost(model, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens)
        
        response_content = None
        if hasattr(response, "content"):
            content_blocks = response.content
            if isinstance(content_blocks, list):
                response_content = "".join(
                    getattr(block, "text", "")
                    for block in content_blocks
                    if getattr(block, "type", "text") == "text"
                )
            elif isinstance(content_blocks, str):
                response_content = content_blocks

        log_event(
            "llm_call_completed",
            llm_call_id=llm_call_id,
            llm_provider="anthropic",
            llm_model=model,
            llm_purpose=purpose,
            is_byok=is_byok,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cost_usd=round(cost_usd, 8),
            stop_reason=getattr(response, "stop_reason", None),
            response_hash=_payload_hash(getattr(response, "content", "")),
            response_content=response_content,
        )
        return response
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_event(
            "llm_call_failed",
            level="error",
            llm_call_id=llm_call_id,
            llm_provider="anthropic",
            llm_model=model,
            llm_purpose=purpose,
            is_byok=is_byok,
            duration_ms=duration_ms,
            error_type=type(exc).__name__,
        )
        raise

