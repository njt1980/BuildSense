# Telemetry Specification

## 1. Purpose

BuildSense must provide a low-cost local telemetry experience for development and local evaluations. A developer should be able to run the app locally, submit or evaluate a workflow, and inspect the request flow, agent steps, LLM calls, tool calls, costs, errors, and final status without Docker or a paid always-on observability stack.

## 2. Scope

In scope:

- Local app runs.
- Local evaluation runs.
- Local dashboard for telemetry inspection.
- Request, orchestration, node, LLM, and tool telemetry.
- Cost and token visibility for local debugging.
- Privacy-safe storage of recent telemetry events in memory.

Out of scope for this phase:

- Production observability.
- OpenTelemetry export.
- Required LangSmith usage.
- Long-term telemetry retention.
- Docker-based observability stacks.
- Alerting.

## 3. Operating Modes

Telemetry must distinguish:

```text
environment=local
is_eval=false
```

from:

```text
environment=local
is_eval=true
```

Manual local app usage should use `is_eval=false`. Local evaluation runs should use `is_eval=true` and include eval metadata when available.

## 4. Required IDs

Telemetry must support correlation through these IDs:

- `request_id`: one HTTP request.
- `user_id`: authenticated user, when available.
- `company_id`: active company, when available.
- `project_id`: active project, when available.
- `session_id`: orchestration session.
- `run_id`: one orchestration attempt.
- `step_id`: one orchestrator node execution.
- `llm_call_id`: one LLM call.
- `tool_call_id`: one tool call.

The app must return `X-Request-ID` for local API requests.

## 5. Required Local Dashboard Behavior

The local dashboard must let a developer:

- view recent runs
- search by `request_id`
- search by `session_id`
- search by `run_id`
- inspect ordered event timelines
- see request start/completion/failure
- see orchestration start/pause/completion/failure
- see node start/completion/failure
- see LLM model, purpose, duration, token counts, estimated cost, and BYOK flag
- see tool name, duration, output size, and untrusted wrapping status
- clear retained local telemetry

## 6. Required Events

The telemetry system must record these event categories:

- Request lifecycle.
- Session/project lifecycle.
- Orchestration lifecycle.
- LangGraph node lifecycle.
- LLM call lifecycle.
- Tool call lifecycle.
- Sanitization/redaction failures.
- Tool output wrapping failures.

## 7. Local Evaluation Requirements

Local eval telemetry must support these fields:

- `is_eval`
- `eval_suite`
- `eval_case_id`
- `dataset_version`, when available
- `model_version`, when available
- `prompt_version`, when available

The local dashboard must support at least a basic manual/eval run filter. More specific filters for `eval_suite` and `eval_case_id` can be added later.

## 8. Privacy Requirements

Telemetry must not store:

- JWTs
- API keys
- BYOK keys
- database credentials
- Redis credentials
- raw uploaded file content
- full prompts by default
- full LLM responses by default
- full untrusted external tool output by default

Telemetry may store:

- IDs
- event names
- status
- duration
- error type
- model name
- token counts
- estimated cost
- prompt hash
- response hash
- content lengths
- output byte size
- output wrapping status

## 9. Retention Requirements

Local telemetry must be:

- bounded in memory
- cleared on backend restart
- clearable manually
- unavailable as a production persistence mechanism

## 10. Acceptance Criteria

The phase is complete when:

1. Local API responses include `X-Request-ID`.
2. The local dashboard lists recent orchestration runs.
3. A run timeline includes request, orchestration, node, LLM, and tool events.
4. LLM events show model, purpose, duration, tokens, estimated cost, and BYOK flag.
5. Tool events show name, duration, output size, and wrapping status.
6. Node events show name, status before/after, duration, and step ID.
7. Secrets and raw sensitive content are redacted.
8. Local telemetry remains bounded and non-durable.
9. Local eval events can be tagged with `is_eval=true`.
10. The implementation does not require Docker, LangSmith, or OTel export for normal local use.
