# Specification: Telemetry Logs Copying & Raw Input/Output Visibility

## 1. Goal Description
To improve local debugging and analysis of agentic workflows:
1. Provide a **Copy Logs** button in the local telemetry viewer that copies the entire event log of the selected run as a formatted JSON string to the clipboard, allowing developers to paste it into external analysis tools.
2. Capture and show the actual input/output text (e.g. LLM system messages, user prompts, assistant responses, tool arguments, and tool outputs) in the telemetry viewer for each step, while ensuring secrets (API keys, authorization tokens) remain redacted.

---

## 2. Functional Requirements

### 2.1 Copy Logs Button
- A button labeled **Copy Logs** (or with a copy icon and text) must be added to the Event Timeline panel header in `/[lang]/dev/telemetry`.
- Clicking the button will serialize all events of the currently selected run into a JSON string and copy it to the clipboard.
- The button must display a feedback state (e.g., "Copied!") for 2 seconds after a successful copy operation.
- The button must only be visible/enabled when a run is selected and has one or more events.

### 2.2 Unsanitized Local Telemetry Storage
- The local in-memory telemetry store (`LocalTelemetryStore`) must retain the actual raw texts of inputs and outputs in local/testing environments.
- Secrets (matching keys like `authorization`, `api_key`, `apikey`, `anthropic`, `jwt`, `token`, `password`, `secret`) must **always** be redacted with `[REDACTED]`.
- Content-rich keys (`prompt`, `messages`, `response_content`, `file_content`, `raw_input_text_or_audio`, `document`, `tool_input`, `tool_output`) must remain readable (not hashed or shortened) in the local telemetry store.
- Structured logger (`logger.log` called by `log_event`) must continue to log hashed/redacted copies of raw content keys to ensure console/file logs remain clean and private.

### 2.3 LLM & Tool Telemetry Capture
- **LLM Calls**:
  - `llm_call_started` must capture `messages` (prompt messages list) and `system` (system instruction text).
  - `llm_call_completed` must capture `response_content` (the text returned by the model).
- **Tool Calls**:
  - `tool_call_started` must capture `tool_input` (the dictionary of tool arguments).
  - `tool_call_completed` must capture `tool_output` (the return value string from the tool).

### 2.4 Telemetry Flow Viewer UI Enhancements
- **LLM Events**: Display system prompt, user prompt, and model completion in formatted text blocks (e.g., collapsible panels or scroll areas).
- **Tool Events**: Display tool arguments and tool output.
- Non-essential fields (like hashes) can be hidden when raw values are present.

---

## 3. Non-Functional Requirements & Guardrails
- **Security**: Raw input/output text must never be persisted or logged to production console logs. The bypass must only apply to `LocalTelemetryStore` in `"local"` and `"test"` environments.
- **UI Responsiveness**: Large logs copied to clipboard must not block the main UI thread.
- **Styling Consistency**: The layout, colors, and styling of the new components must match the existing tailwind/shadcn-based UI of the telemetry page.

---

## 4. Acceptance Criteria
1. Clicking **Copy Logs** successfully copies the full JSON array of the selected run's events to the clipboard.
2. The UI shows a temporary "Copied!" confirmation.
3. In local telemetry viewer, clicking on an LLM completion event shows the raw prompt and completion text, rather than just hashes and lengths.
4. In local telemetry viewer, clicking on a tool execution event shows the actual input parameters and returned string.
5. All secrets (e.g., `authorization` header, `anthropic_api_key`) remain redacted in both raw and sanitized telemetry.
6. The backend tests pass, updating any assertions that expected redacted inputs/outputs locally to reflect the new local-viewer transparency.

---

## 5. Verification Plan
- **Automated Validation**:
  - Run `pytest tests/test_telemetry.py` to ensure telemetry capture is functioning.
  - Run frontend linting: `npm run lint` and `npm run type-check`.
- **Manual Verification**:
  - Run the backend, select a run in the dev telemetry viewer.
  - Verify that the inputs/outputs are visible and readable.
  - Click "Copy Logs" and verify the pasted JSON contains the full unsanitized logs.
