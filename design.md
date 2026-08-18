# System Design: Telemetry Logs Copying & Raw Input/Output Visibility

## 1. Architecture & Telemetry Data Flow

We are updating the telemetry capture flow in local/test environments to retain raw developer inputs and outputs in memory, while maintaining production privacy through standard logging sanitization.

```text
Backend Execution (LLM / Tool)
  │
  ├─► Structured Logger (log_event) ──► sanitize_mapping(redact_raw=True) ──► Console/File (Hashed/Redacted)
  │
  └─► Local telemetry store (record_event) ──► sanitize_mapping(redact_raw=False) ──► In-Memory Store (Raw text preserved)
                                                                                            ▲
                                                                                            │ (HTTP GET)
                                                                                            │
                                                                                    Frontend UI Tab
                                                                                      - Event Timeline Viewer
                                                                                      - Copy Logs (Clipboard)
```

---

## 2. Component Design & Changes

### 2.1 Backend: `privacy.py` and `dev_store.py`
- `sanitize_mapping` is updated with `redact_raw: bool = True`.
- When `redact_raw` is `False`, content-rich keys (e.g. `messages`, `prompt`, `response_content`, `tool_input`, `tool_output`, `file_content`) are preserved exactly as-is without hashing or length replacement.
- Secrets (`authorization`, API keys, etc.) are **always** redacted, even if `redact_raw` is `False`.

### 2.2 Backend: `llm.py` and `tools.py`
- LLM calls will capture the raw `messages` parameters and the text content of responses, logging them as `messages`, `system`, and `response_content`.
- Tool calls will capture the input parameters as `tool_input` and the returned string as `tool_output`.

### 2.3 Frontend: `page.tsx`
- Add a **Copy Logs** button using Tailwind styling next to the "Event Timeline" header.
- Create an implementation utilizing the `navigator.clipboard.writeText` API to copy the formatted JSON string representing all events of the selected run.
- Enhance event list item rendering:
  - If the event is an LLM call or has `messages`, `system`, or `response_content` attributes, display them in neat code blocks/panels.
  - If the event is a Tool call, render `tool_input` and `tool_output` properties inside readable tables or text blocks.

---

## 3. Atomic Implementation Steps

### Step 1: Update Backend Privacy Sanitization
- **Read/Modify file**: [`privacy.py`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/telemetry/privacy.py)
- **Action**: Add `tool_input` and `tool_output` to `_RAW_CONTENT_KEYS`. Add `redact_raw` parameter to `sanitize_mapping` and support raw bypass.

### Step 2: Update Logging and Store Dispatch
- **Read/Modify file**: [`logging.py`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/telemetry/logging.py)
- **Read/Modify file**: [`dev_store.py`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/telemetry/dev_store.py)
- **Action**:
  - In `logging.py`, pass original `attributes` to `record_event`.
  - In `dev_store.py`, call `sanitize_mapping(attributes, redact_raw=False)` in `LocalTelemetryStore.append`.

### Step 3: Update LLM and Tool Instrumentation
- **Read/Modify file**: [`llm.py`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/telemetry/llm.py)
- **Read/Modify file**: [`tools.py`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/telemetry/tools.py)
- **Action**:
  - In `llm.py`, pass raw messages and system fields to `log_event`. Extract completion text from `response.content` and pass it as `response_content`.
  - In `tools.py`, pass `tool_input` and `tool_output` to `log_event`.

### Step 4: Update Backend Telemetry Tests
- **Read/Modify file**: [`test_telemetry.py`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/tests/test_telemetry.py)
- **Action**: Update `test_local_telemetry_events_are_sanitized` to verify secret redaction while checking that the prompt text is preserved in local storage.

### Step 5: Update Frontend UI for Copying Logs & Displaying Raw IO
- **Read/Modify file**: [`page.tsx`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/web/src/app/[lang]/dev/telemetry/page.tsx)
- **Action**: Implement "Copy Logs" button in `LocalTelemetryPage`. Render raw prompts, responses, tool inputs, and tool outputs.

---

## 4. Verification & Testing Design

### 4.1 Automated Validation
- Run backend tests: `pytest apps/api/tests/test_telemetry.py -v`
- Run frontend type check and linting:
  - `npm run type-check`
  - `npm run lint`

### 4.2 Manual Verification
- Verify that copying logs copies all selected run events to the clipboard.
- Verify that raw LLM instructions/prompts/responses and Tool arguments/returns are displayed when inspecting events.
