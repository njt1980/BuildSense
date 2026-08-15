# Telemetry Design

## 1. Architecture

The local telemetry system is implemented inside the existing FastAPI and Next.js apps.

```text
FastAPI middleware
  -> contextvars request context
  -> structured event helper
  -> bounded in-memory event store
  -> dev-only API routes
  -> Next.js local dashboard
```

Agent flow events are emitted from LangGraph node wrappers, the LLM wrapper, and the tool registry.

## 2. Backend Modules

Telemetry code lives under:

```text
apps/api/app/telemetry/
```

Module responsibilities:

| Module | Responsibility |
| --- | --- |
| `ids.py` | Generate request, run, step, LLM, and tool IDs. |
| `context.py` | Store request-scoped context using `contextvars`. |
| `privacy.py` | Redact secrets and hash sensitive content. |
| `dev_store.py` | Keep bounded in-memory telemetry events. |
| `logging.py` | Emit structured events into the local store. |
| `middleware.py` | Assign request IDs and record request lifecycle events. |
| `dev_routes.py` | Expose local inspection APIs. |
| `nodes.py` | Wrap LangGraph nodes. |
| `llm.py` | Wrap Anthropic calls. |
| `tools.py` | Register and call tools with telemetry. |

## 3. Configuration

Settings are loaded through `app.core.config.Settings`.

```text
ENVIRONMENT=local
SERVICE_NAME=buildsense-api
TELEMETRY_ENABLED=true
LOCAL_TELEMETRY_VIEWER_ENABLED=true
LOCAL_TELEMETRY_MAX_EVENTS=1000
LOCAL_TELEMETRY_MAX_RUNS=100
```

The dev telemetry API is enabled only when:

```text
ENVIRONMENT in ["local", "test"]
LOCAL_TELEMETRY_VIEWER_ENABLED=true
```

## 4. Event Shape

Events stored in memory use this shape:

```json
{
  "timestamp": "2026-08-14T10:30:00.000Z",
  "level": "info",
  "event": "llm_call_completed",
  "request_id": "req_...",
  "environment": "local",
  "service": "buildsense-api",
  "user_id": "user_...",
  "company_id": "company_...",
  "project_id": "project_...",
  "session_id": "session_...",
  "run_id": "run_...",
  "attributes": {
    "llm_call_id": "llm_...",
    "llm_model": "claude...",
    "duration_ms": 420,
    "input_tokens": 1000,
    "output_tokens": 250,
    "cost_usd": 0.003
  }
}
```

Context fields are top-level. Event-specific details go under `attributes`.

## 5. Request Flow

For each request:

1. Middleware reads `X-Request-ID`.
2. If absent or unsafe, middleware generates a new request ID.
3. Middleware sets base context.
4. Middleware records `request_started`.
5. Route handlers enrich context with user/project/session IDs.
6. Middleware records `request_completed` or `request_failed`.
7. Response includes `X-Request-ID`.

## 6. Orchestration Flow

For `/api/v1/orchestrate`:

1. Route records `orchestration_request_received`.
2. Route loads or creates project/session state.
3. Route generates `run_id`.
4. Route records `orchestration_started`.
5. LangGraph executes instrumented nodes.
6. Route records `orchestration_paused`, `orchestration_completed`, or `orchestration_failed`.

## 7. Node Wrapper

`instrument_node(node_name, handler)` wraps async LangGraph node handlers.

It records:

- `orchestrator_node_started`
- `orchestrator_node_completed`
- `orchestrator_node_failed`

It captures:

- `step_id`
- `node_name`
- `status_before`
- `status_after`
- `duration_ms`
- `steps_taken`
- `budget_spent_usd`
- `update_keys`

## 8. LLM Wrapper

`traced_anthropic_messages_create(...)` wraps `client.messages.create(...)`.

It records:

- `llm_call_started`
- `llm_call_completed`
- `llm_call_failed`

It captures:

- `llm_call_id`
- provider
- model
- purpose
- BYOK flag
- duration
- input/output tokens
- cache tokens
- estimated cost
- stop reason
- prompt hash
- response hash

The wrapper estimates cost for local visibility. Existing budget accounting remains the source of session budget state.

## 9. Tool Registry

Tools are registered once with metadata:

```python
tool_registry.register(
    name="market_signal",
    handler=market_signal_mcp,
    source="local_mcp_style",
    requires_untrusted_wrapping=True,
)
```

Calls go through:

```python
tool_registry.call("market_signal", query=query)
```

The registry records:

- `tool_call_started`
- `tool_call_completed`
- `tool_call_failed`
- `tool_output_wrapping_failed`

It captures:

- `tool_call_id`
- tool name
- source
- duration
- input keys
- output byte size
- output wrapping status
- error type

## 10. Local Store

`LocalTelemetryStore` uses:

```python
deque(maxlen=settings.local_telemetry_max_events)
```

It provides:

- `append`
- `list_events`
- `list_runs`
- `get_by_field`
- `clear`

It uses a lock around read/write operations.

## 11. Dev API

Routes:

```text
GET /api/dev/telemetry/events
GET /api/dev/telemetry/runs
GET /api/dev/telemetry/runs/{run_id}
GET /api/dev/telemetry/requests/{request_id}
GET /api/dev/telemetry/sessions/{session_id}
DELETE /api/dev/telemetry
```

Routes return `404` when local telemetry is disabled.

## 12. Frontend Dashboard

The dashboard route is:

```text
apps/web/src/app/[lang]/dev/telemetry/page.tsx
```

It:

- fetches recent runs
- fetches selected run events
- performs lookup by run/request/session
- renders event timelines
- renders event attributes as JSON
- clears local telemetry
- filters recent runs by all, manual, or eval

## 13. Local Eval Metadata

Eval runners should set context values before invoking orchestration:

```python
update_context(
    is_eval=True,
    eval_suite="agent_quality",
    eval_case_id="...",
)
```

Manual local runs should use `is_eval=False` or omit eval fields.

The dashboard supports a coarse all/manual/eval filter. Fine-grained filtering by `eval_suite` and `eval_case_id` is deferred.

## 14. Privacy Implementation

`sanitize_mapping` applies these rules:

- redact secret-like keys
- preserve token count fields
- hash prompt-like string values
- store content lengths
- summarize lists by length
- recursively sanitize dictionaries

The dashboard only renders sanitized event payloads.

## 15. Tests

Focused tests live in:

```text
apps/api/tests/test_telemetry.py
```

Coverage:

- request ID generation
- request ID preservation
- sanitization
- dev route gating
- node wrapper events
- tool registry events
- LLM usage/cost events

## 16. Future Extensions

Deferred work:

- DB/Redis event instrumentation.
- Fine-grained dashboard filtering by `eval_suite` and `eval_case_id`.
- LangSmith metadata propagation.
- OpenTelemetry export.
- Sentry or equivalent exception tracking.
- Production dashboard/runbook.
