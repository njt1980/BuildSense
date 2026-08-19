# Specification: Fix Test Hangs, Test Crashes, Filter Worker Messages, and Optimize Tool Latency

## 1. Goal Description
The purpose of this specification is to:
1. Eliminate hangs in the test suite by ensuring no unit tests make actual, unmocked network calls to external APIs.
2. Fix a `TypeError` crash in `test_confirmed_intake_is_required_before_execution` within `tests/test_analyst_behavior.py`.
3. Filter worker persona and tool messages out of the user-visible chat history, preventing internal assistant logs and raw JSON reasoning signatures from being displayed in the chat window.
4. Reduce latency in the `market_signal` tool by executing external calls concurrently in a thread pool and lowering connection timeouts.
5. Mock the network requests in `test_market_signal_mcp_containment` to prevent slow external dependencies from affecting test runs.

---

## 2. Functional Requirements

### 2.1 Filter Worker Persona and Tool Messages
- Modify `_save_intermediate_state` in `apps/api/app/core/orchestrator.py`:
  - Filter out `assistant` messages whose `name` is not `None` and is not `"BuildSense Intelligence"`.
  - Filter out all messages with `role == "tool"`.
  - This ensures that background process analysts and automation architects' intermediate thought processes and tool results are not saved to the user-facing database.
- Modify `run_pipeline` in `apps/api/app/core/orchestrator.py`:
  - Perform the same filtering on the returned `SessionState.messages` before returning it to the API route, preventing worker persona outputs and JSON thinking blocks from leaking into the immediate HTTP response.

### 2.2 Fix Test Suite Hang in Checkpointer Persistence Test
- Modify `test_langgraph_checkpoint_persistence_and_resumption` in `tests/test_langgraph.py` to run inside a `with patch("app.core.orchestrator.HAS_ANTHROPIC", False):` block.
- This ensures the checkpointer test runs in local mock simulation mode instead of executing live Anthropic SDK calls, preventing connection hangs when a fake key is present in `.env`.

### 2.3 Fix TypeError Crash in Analyst Behavior Test
- Modify `complete_execution_loop` inside `test_confirmed_intake_is_required_before_execution` in `tests/test_analyst_behavior.py` to accept arbitrary positional and keyword arguments (`*args: Any, **kwargs: Any`).
- This prevents `TypeError` when `_node_execute_tools` calls the mocked `_execute_mock_simulation_loop` with keyword arguments (like `task=local_task`).

### 2.4 Optimize market_signal Tool Latency & Parallelize Requests
- Refactor `market_signal_mcp` in `apps/api/app/mcp/tools.py`:
  - Run the HackerNews and Reddit HTTP searches concurrently using a thread pool (e.g. `concurrent.futures.ThreadPoolExecutor`).
  - Reduce the timeout for each `httpx.get` request from `5.0` seconds to `1.0` second.
  - If both calls timeout or fail, gracefully fall back to the local simulated signals as before.
  - This reduces the maximum network blocking time from `10.0` seconds to `1.0` second.

### 2.5 Mock Network in market_signal Unit Test
- Update `test_market_signal_mcp_containment` in `tests/test_mcp_tools.py` to mock `httpx.get` (or mock `market_signal_mcp` network dependencies) to guarantee zero real network traffic during test collection and execution.

---

## 3. Non-Functional Requirements & Latency Targets
- **Test Suite Execution Time**: Reduce total test execution time by avoiding network timeouts and live API connection attempts.
- **Tool Latency**: Worst-case execution latency for `market_signal` tool must be capped at 1.0 second (down from 10.0 seconds).

---

## 4. Acceptance Criteria
1. Background worker persona messages (e.g., `Process Analyst Persona`, `Automation Architect Persona`) and raw JSON thinking/reasoning blocks are not visible in the chat history returned to the client or saved in the database.
2. The test `test_confirmed_intake_is_required_before_execution` passes without throwing a `TypeError`.
3. The checkpointer persistence test `test_langgraph_checkpoint_persistence_and_resumption` runs and completes in under 2 seconds without hanging.
4. The tool test `test_market_signal_mcp_containment` passes without making real HTTP calls to Reddit or HackerNews.
5. All automated unit tests in `pytest tests/ -v` pass successfully.

---

## 5. Verification Plan
- Run unit tests: `pytest tests/ -v`
