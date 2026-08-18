"""Telemetry-aware registry for local and external tool calls."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict

from app.telemetry.ids import generate_id
from app.telemetry.logging import log_event


ToolHandler = Callable[..., str]


@dataclass(frozen=True)
class ToolDefinition:
    """Registered tool metadata."""

    name: str
    handler: ToolHandler
    source: str
    requires_untrusted_wrapping: bool
    description: str = ""


class ToolRegistry:
    """Central registry that records telemetry for tool invocations."""

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        *,
        name: str,
        handler: ToolHandler,
        source: str,
        requires_untrusted_wrapping: bool,
        description: str = "",
    ) -> None:
        """Register a telemetry-aware tool definition."""
        self._tools[name] = ToolDefinition(
            name=name,
            handler=handler,
            source=source,
            requires_untrusted_wrapping=requires_untrusted_wrapping,
            description=description,
        )

    def call(self, name: str, **kwargs: Any) -> str:
        """Invoke a registered tool and record sanitized local telemetry."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")

        definition = self._tools[name]
        tool_call_id = generate_id("tool")
        started_at = time.perf_counter()
        log_event(
            "tool_call_started",
            tool_call_id=tool_call_id,
            tool_name=name,
            tool_source=definition.source,
            requires_untrusted_wrapping=definition.requires_untrusted_wrapping,
            input_keys=sorted(kwargs.keys()),
            tool_input=kwargs,
        )
        try:
            output = definition.handler(**kwargs)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            output_wrapped = output.startswith("<untrusted_tool_output") and output.rstrip().endswith("</untrusted_tool_output>")
            if definition.requires_untrusted_wrapping and not output_wrapped:
                log_event(
                    "tool_output_wrapping_failed",
                    level="error",
                    tool_call_id=tool_call_id,
                    tool_name=name,
                    output_bytes=len(output.encode("utf-8")),
                )
            log_event(
                "tool_call_completed",
                tool_call_id=tool_call_id,
                tool_name=name,
                tool_source=definition.source,
                duration_ms=duration_ms,
                output_bytes=len(output.encode("utf-8")),
                output_wrapped=output_wrapped,
                tool_output=output,
            )
            return output
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            log_event(
                "tool_call_failed",
                level="error",
                tool_call_id=tool_call_id,
                tool_name=name,
                tool_source=definition.source,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
            )
            raise


tool_registry = ToolRegistry()

