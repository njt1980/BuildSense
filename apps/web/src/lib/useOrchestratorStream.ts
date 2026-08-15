import { useState, useCallback } from "react";
import { getApiBaseUrl } from "./api";
import { supabase } from "./supabase";

/**
 * Interface representing a standard chat message in the session state.
 */
export interface Message {
  /** The role of the message author (e.g. system, user, assistant, tool) */
  role: string;
  /** The raw text content of the message */
  content: string;
  /** Optional sender name */
  name: string | null;
  /** Optional tool call identifier */
  tool_call_id: string | null;
}

/**
 * Interface representing the complete serialized session state returned by the backend.
 */
export interface SessionState {
  /** Unique UUID string identifying the active session */
  session_id: string;
  /** Active operational mode of the session */
  mode: "OPTIMIZER";
  /** Current state machine pipeline status */
  status:
    | "ROUTING"
    | "PLANNING"
    | "EXECUTING"
    | "AWAITING_CLARIFICATION"
    | "SYNTHESIZING"
    | "COMPLETED"
    | "FAILED";
  /** Accumulated cost spent in USD */
  budget_spent_usd: number;
  /** Maximum spending cap before loop termination */
  max_budget_usd: number;
  /** Number of execution loop steps taken */
  steps_taken: number;
  /** Maximum allowed execution loop steps */
  max_steps: number;
  /** List of chat history messages */
  messages: Message[];
  /** Pending questions waiting for human responses */
  clarification_questions: string[];
  /** Responses provided by the user for pending questions */
  clarification_responses: Record<string, string>;
  /** Structured plan tasks for agent worker personas */
  dag_plan: Array<Record<string, unknown>>;
  /** Additional metadata and final report compilation values */
  metadata: Record<string, unknown>;
}

/**
 * Deduplicate messages by role+content key. Keeps the last occurrence for each unique key.
 */
function dedupeMessages(messages: Message[] | undefined): Message[] {
  if (!messages || messages.length === 0) return [];
  const map = new Map<string, Message>();
  for (const m of messages) {
    const key = `${m.role}|${(m.content || "").trim().slice(0, 500)}`;
    // last-wins to allow final payload to overwrite intermediate chunks
    map.set(key, m);
  }
  return Array.from(map.values());
}

/**
 * Custom React hook managing the Server-Sent Events (SSE) or JSON connection stream
 * to the FastAPI orchestrate endpoint, handling progress, logs, and pauses.
 *
 * @returns State properties and callbacks for starting and resuming pipeline sessions.
 */
export function useOrchestratorStream() {
  const [activeSessionState, setActiveSessionState] = useState<SessionState | null>(null);
  const [isOrchestratorLoopActive, setIsOrchestratorLoopActive] = useState<boolean>(false);
  const [orchestratorLogs, setOrchestratorLogs] = useState<string[]>([]);
  const [errorDetails, setErrorDetails] = useState<string | null>(null);

  /**
   * Hydrates the hook with persisted session state without starting orchestration.
   *
   * @param state - Previously saved backend session state, or null to clear it.
   */
  const hydrateOrchestratorSession = useCallback((state: SessionState | null) => {
    if (!state) {
      setActiveSessionState(null);
      return;
    }

    const dedupedMessages = dedupeMessages(state.messages || []);
    setActiveSessionState({ ...state, messages: dedupedMessages });
  }, []);

  /**
   * Starts or resumes a BuildSense session pipeline step.
   * Uses native ReadableStream over HTTP fetch POST to capture execution logs.
   *
   * @param params - Configuration inputs including prompt details and session keys.
   */
  const executeOrchestratorRequest = useCallback(async (params: {
    prompt?: string;
    mode?: "OPTIMIZER";
    motivation?: string;
    session_id?: string;
    clarification_responses?: Record<string, string>;
    file_name?: string;
    file_content?: string;
    user_constraints?: string[];
    lang?: string;
    user_persona?: string;
    industry_vertical?: string;
    company_id?: string;
  }) => {
    setIsOrchestratorLoopActive(true);
    setErrorDetails(null);

    // Initial mock logs to show live execution start
    setOrchestratorLogs((previousLogs) => [
      ...previousLogs,
      `[CLIENT] Connecting to BuildSense core pipeline...`,
    ]);

    try {
      const userApiKey = typeof window !== "undefined" ? localStorage.getItem("buildsense_user_api_key") || "" : "";
      
      // Get the token from local mock storage or Supabase
      let jwtToken = "";
      if (typeof window !== "undefined") {
        const mockSessionStr = localStorage.getItem("buildsense_mock_session");
        if (mockSessionStr) {
          try {
            const mockSession = JSON.parse(mockSessionStr);
            jwtToken = mockSession.token || "";
          } catch {}
        }
      }
      
      if (!jwtToken) {
        try {
          const { data } = await supabase.auth.getSession();
          jwtToken = data.session?.access_token || "";
        } catch {}
      }

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (userApiKey) {
        headers["X-User-Anthropic-Key"] = userApiKey;
      }
      if (jwtToken) {
        headers["Authorization"] = `Bearer ${jwtToken}`;
      }

      const apiBaseUrl = getApiBaseUrl();
      const response = await fetch(`${apiBaseUrl}/api/v1/orchestrate`, {
        method: "POST",
        headers,
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        let errorMessageBody = `HTTP Error ${response.status}`;
        try {
          const errorJson = await response.json();
          if (errorJson.detail) {
            errorMessageBody = errorJson.detail;
          }
        } catch {
          // Fallback to default message
        }
        throw new Error(errorMessageBody);
      }

      // Check if response contains streaming headers or standard JSON body
      const contentType = response.headers.get("content-type") || "";
      
      if (contentType.includes("application/json")) {
        const resultState: SessionState = await response.json();
        // Deduplicate incoming messages by role+content to avoid rendering duplicates
        const deduped = dedupeMessages(resultState.messages || []);
        setActiveSessionState({ ...resultState, messages: deduped });

        // Populate logs dynamically from steps state
        const generatedLogs: string[] = [
          `[ROUTING] Completed classification checks.`,
        ];

        if (resultState.status === "AWAITING_CLARIFICATION") {
          generatedLogs.push(`[HITL] Paused. Awaiting human input clarification.`);
        } else if (resultState.status === "COMPLETED") {
          generatedLogs.push(`[COMPLETED] Pipeline execution finished successfully.`);
        } else if (resultState.status === "FAILED") {
          generatedLogs.push(`[FAILED] Pipeline terminated. Spend: $${resultState.budget_spent_usd.toFixed(3)}`);
        } else {
          generatedLogs.push(`[EXECUTING] Processed ${resultState.steps_taken} steps in tool loop.`);
        }

        setOrchestratorLogs((previousLogs) => [...previousLogs, ...generatedLogs]);
      } else {
        // Stream reader fallback for text/event-stream chunks
        const responseBodyReader = response.body?.getReader();
        if (responseBodyReader) {
          const stringDecoder = new TextDecoder();
          let streamDone = false;

          while (!streamDone) {
            const { value: streamChunk, done: isChunkDone } = await responseBodyReader.read();
            streamDone = isChunkDone;
            if (streamChunk) {
              const decodedChunkString = stringDecoder.decode(streamChunk);
              
              // Process event chunks line-by-line
              const rawLines = decodedChunkString.split("\n");
              for (const line of rawLines) {
                const trimmedLine = line.trim();
                if (trimmedLine.startsWith("data:")) {
                  const eventDataContent = trimmedLine.replace("data:", "").trim();
                  try {
                    const parsedEventState: SessionState = JSON.parse(eventDataContent);
                    // Deduplicate messages before updating state
                    const dedupedStream = dedupeMessages(parsedEventState.messages || []);
                    setActiveSessionState({ ...parsedEventState, messages: dedupedStream });
                    setOrchestratorLogs((previousLogs) => [
                      ...previousLogs,
                      `[SYSTEM] State update: ${parsedEventState.status}`,
                    ]);
                  } catch {
                    // Log raw thought string if not JSON state
                    setOrchestratorLogs((previousLogs) => [
                      ...previousLogs,
                      `[THOUGHT] ${eventDataContent}`,
                    ]);
                  }
                }
              }
            }
          }
        }
      }
    } catch (networkError: unknown) {
      const parsedErrorMessage = networkError instanceof Error ? networkError.message : String(networkError);
      setErrorDetails(parsedErrorMessage);
      setOrchestratorLogs((previousLogs) => [
        ...previousLogs,
        `[ERROR] Connection failed: ${parsedErrorMessage}`,
      ]);
    } finally {
      setIsOrchestratorLoopActive(false);
    }
  }, []);

  /**
   * Resets the active session and logs context.
   */
  const resetOrchestratorSession = useCallback(() => {
    setActiveSessionState(null);
    setOrchestratorLogs([]);
    setErrorDetails(null);
  }, []);

  return {
    activeSessionState,
    isOrchestratorLoopActive,
    orchestratorLogs,
    errorDetails,
    executeOrchestratorRequest,
    hydrateOrchestratorSession,
    resetOrchestratorSession,
  };
}
