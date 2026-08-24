"""Offline compatibility checks for the pinned Anthropic messages API.

This module validates the local SDK contract only; it deliberately makes no
network request and never requires a provider secret.
"""

import inspect

import anthropic
import pytest


@pytest.mark.anthropic_compat
def test_pinned_anthropic_messages_create_contract() -> None:
    """Verify the pinned SDK exposes the keyword contract used by BuildSense."""
    from anthropic import AsyncAnthropic

    signature = inspect.signature(AsyncAnthropic(api_key="test").messages.create)
    parameters = signature.parameters

    assert anthropic.__version__ == "0.43.0"
    assert {"max_tokens", "messages", "model", "system"}.issubset(parameters)
    assert "temperature" in parameters


@pytest.mark.anthropic_compat
@pytest.mark.asyncio
async def test_unsupported_messages_create_keyword_fails_loudly() -> None:
    """Ensure a contract mismatch raises instead of being silently discarded."""

    async def strict_create(*, max_tokens: int, messages: list[dict[str, str]], model: str) -> object:
        """Represent a provider SDK version with a narrower request contract."""
        return {"max_tokens": max_tokens, "messages": messages, "model": model}

    with pytest.raises(TypeError, match="temperature"):
        await strict_create(
            max_tokens=32,
            messages=[{"role": "user", "content": "hello"}],
            model="claude-3-haiku",
            temperature=0.0,  # type: ignore[call-arg]
        )
