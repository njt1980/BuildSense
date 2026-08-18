"use client";

import React from "react";
import { getApiBaseUrl } from "@/lib/api";

/**
 * Attribute map attached to a local telemetry event.
 */
interface TelemetryAttributes {
  [key: string]: string | number | boolean | null | undefined | TelemetryAttributes;
}

/**
 * Local telemetry event returned by the development-only backend API.
 */
interface TelemetryEvent {
  timestamp: string;
  level: string;
  event: string;
  request_id?: string;
  session_id?: string;
  run_id?: string;
  step_id?: string;
  http_method?: string;
  http_route?: string;
  attributes?: TelemetryAttributes;
  is_eval?: boolean;
  eval_suite?: string;
  eval_case_id?: string;
}

/**
 * Compact run summary returned by the local telemetry API.
 */
interface RunSummary {
  run_id: string;
  request_id?: string;
  session_id?: string;
  started_at?: string;
  last_event_at?: string;
  event_count: number;
  status: string;
  is_eval?: boolean;
  eval_suite?: string;
  eval_case_id?: string;
  total_cost_usd?: number;
}

const apiBaseUrl = getApiBaseUrl();

/**
 * Development-only page for inspecting recent local telemetry flow.
 */
export default function LocalTelemetryPage(): React.JSX.Element {
  const [runs, setRuns] = React.useState<RunSummary[]>([]);
  const [events, setEvents] = React.useState<TelemetryEvent[]>([]);
  const [selectedRunId, setSelectedRunId] = React.useState<string>("");
  const [lookupValue, setLookupValue] = React.useState<string>("");
  const [lookupMode, setLookupMode] = React.useState<"runs" | "requests" | "sessions">("runs");
  const [runFilter, setRunFilter] = React.useState<"all" | "manual" | "eval">("all");
  const [errorText, setErrorText] = React.useState<string>("");
  const [isLoading, setIsLoading] = React.useState<boolean>(false);
  const [showRawJson, setShowRawJson] = React.useState<Record<string, boolean>>({});
  const [copyFeedback, setCopyFeedback] = React.useState<boolean>(false);

  const handleCopyLogs = React.useCallback(async (): Promise<void> => {
    if (events.length === 0) return;
    try {
      const logsJson = JSON.stringify(events, null, 2);
      await navigator.clipboard.writeText(logsJson);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    } catch (err) {
      console.error("Failed to copy telemetry logs", err);
    }
  }, [events]);

  const visibleRuns = React.useMemo(() => {
    if (runFilter === "eval") return runs.filter((run) => run.is_eval);
    if (runFilter === "manual") return runs.filter((run) => !run.is_eval);
    return runs;
  }, [runFilter, runs]);

  /**
   * Fetches recent run summaries from the backend telemetry API.
   */
  const loadRuns = React.useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setErrorText("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/dev/telemetry/runs`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Telemetry API returned ${response.status}`);
      }
      const data = (await response.json()) as RunSummary[];
      setRuns(data);
      if (data.length > 0 && !selectedRunId) {
        setSelectedRunId(data[0].run_id);
      }
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Failed to load local telemetry.");
    } finally {
      setIsLoading(false);
    }
  }, [selectedRunId]);

  /**
   * Fetches events for the selected run ID.
   */
  const loadSelectedRun = React.useCallback(async (): Promise<void> => {
    if (!selectedRunId) {
      setEvents([]);
      return;
    }
    setIsLoading(true);
    setErrorText("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/dev/telemetry/runs/${selectedRunId}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Telemetry API returned ${response.status}`);
      }
      setEvents((await response.json()) as TelemetryEvent[]);
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Failed to load run events.");
    } finally {
      setIsLoading(false);
    }
  }, [selectedRunId]);

  React.useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  React.useEffect(() => {
    void loadSelectedRun();
  }, [loadSelectedRun]);

  /**
   * Looks up events by request, session, or run identifier.
   */
  const handleLookup = async (): Promise<void> => {
    const trimmedValue = lookupValue.trim();
    if (!trimmedValue) return;

    setIsLoading(true);
    setErrorText("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/dev/telemetry/${lookupMode}/${trimmedValue}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Telemetry API returned ${response.status}`);
      }
      setEvents((await response.json()) as TelemetryEvent[]);
      if (lookupMode === "runs") {
        setSelectedRunId(trimmedValue);
      }
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Lookup failed.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Clears local telemetry events from the backend process.
   */
  const handleClear = async (): Promise<void> => {
    setIsLoading(true);
    setErrorText("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/dev/telemetry`, { method: "DELETE" });
      if (!response.ok) {
        throw new Error(`Telemetry API returned ${response.status}`);
      }
      setRuns([]);
      setEvents([]);
      setSelectedRunId("");
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Clear failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#03060d] text-slate-100 px-6 py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col gap-4 border-b border-slate-900 pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-400">Local Development</p>
            <h1 className="mt-2 text-3xl font-bold text-slate-50">Telemetry Flow Viewer</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              Inspect recent request, run, node, LLM, and tool events retained by the local backend process.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void loadRuns()}
              className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-amber-500/40"
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={() => void handleClear()}
              className="rounded-md border border-rose-900/60 bg-rose-950/30 px-3 py-2 text-xs font-semibold text-rose-200 hover:border-rose-500/60"
            >
              Clear
            </button>
          </div>
        </header>

        {errorText && (
          <div className="rounded-md border border-rose-900/70 bg-rose-950/30 px-4 py-3 text-sm text-rose-200">
            {errorText}
          </div>
        )}

        <section className="grid gap-5 lg:grid-cols-[360px_1fr]">
          <aside className="space-y-4">
            <div className="rounded-lg border border-slate-900 bg-[#0b0f19] p-4">
              <h2 className="text-sm font-bold text-slate-100">Lookup</h2>
              <div className="mt-3 grid grid-cols-[110px_1fr] gap-2">
                <select
                  value={lookupMode}
                  onChange={(event) => setLookupMode(event.target.value as "runs" | "requests" | "sessions")}
                  className="rounded-md border border-slate-800 bg-slate-950 px-2 py-2 text-xs text-slate-200"
                >
                  <option value="runs">Run</option>
                  <option value="requests">Request</option>
                  <option value="sessions">Session</option>
                </select>
                <input
                  value={lookupValue}
                  onChange={(event) => setLookupValue(event.target.value)}
                  placeholder="Paste ID"
                  className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 outline-none focus:border-amber-500/60"
                />
              </div>
              <button
                type="button"
                onClick={() => void handleLookup()}
                className="mt-3 w-full rounded-md bg-amber-500 px-3 py-2 text-xs font-bold text-slate-950 hover:bg-amber-400"
              >
                Search
              </button>
            </div>

            <div className="rounded-lg border border-slate-900 bg-[#0b0f19]">
              <div className="border-b border-slate-900 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-bold text-slate-100">Recent Runs</h2>
                    <p className="mt-1 text-xs text-slate-500">{visibleRuns.length} shown / {runs.length} retained</p>
                  </div>
                  <select
                    value={runFilter}
                    onChange={(event) => setRunFilter(event.target.value as "all" | "manual" | "eval")}
                    className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
                  >
                    <option value="all">All</option>
                    <option value="manual">Manual</option>
                    <option value="eval">Eval</option>
                  </select>
                </div>
              </div>
              <div className="max-h-[560px] overflow-y-auto">
                {visibleRuns.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-slate-500">No local runs captured yet.</p>
                ) : (
                  visibleRuns.map((run) => (
                    <button
                      key={run.run_id}
                      type="button"
                      onClick={() => setSelectedRunId(run.run_id)}
                      className={`block w-full border-b border-slate-900 px-4 py-3 text-left hover:bg-slate-950/70 ${
                        selectedRunId === run.run_id ? "bg-amber-500/10" : ""
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="truncate font-mono text-xs text-slate-200">{run.run_id}</span>
                        <div className="flex items-center gap-1.5">
                          {run.total_cost_usd !== undefined && run.total_cost_usd > 0 && (
                            <span className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded px-1 py-0.5 text-[9px] font-mono font-bold">
                              ${run.total_cost_usd.toFixed(4)}
                            </span>
                          )}
                          <span className={`rounded border px-1.5 py-0.5 text-[9px] uppercase font-bold ${
                            run.status === "completed" ? "border-emerald-900/50 text-emerald-400 bg-emerald-950/25" :
                            run.status === "failed" ? "border-rose-900/50 text-rose-400 bg-rose-950/25" :
                            run.status === "paused" ? "border-amber-900/50 text-amber-400 bg-amber-950/25" :
                            "border-slate-800 text-slate-400 bg-slate-900/20"
                          }`}>
                            {run.status}
                          </span>
                        </div>
                      </div>
                      <p className="mt-2 truncate font-mono text-[11px] text-slate-500">{run.session_id || "no session"}</p>
                      <div className="mt-2 flex flex-wrap items-center justify-between text-[11px] text-slate-500">
                        <span>{run.event_count} events</span>
                        <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase font-semibold ${
                          run.is_eval ? "border-sky-800/40 text-sky-400 bg-sky-950/15" : "border-slate-800 text-slate-400"
                        }`}>
                          {run.is_eval ? "Eval" : "Manual"}
                        </span>
                      </div>
                      {run.is_eval && (
                        <p className="mt-1 truncate font-mono text-[10px] text-sky-400">
                          {run.eval_suite || "eval"} / {run.eval_case_id || "case"}
                        </p>
                      )}
                    </button>
                  ))
                )}
              </div>
            </div>
          </aside>

          <section className="rounded-lg border border-slate-900 bg-[#0b0f19]">
            <div className="flex flex-col gap-2 border-b border-slate-900 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-100">Event Timeline</h2>
                <p className="mt-1 font-mono text-xs text-slate-500">{selectedRunId || "Select a run"}</p>
              </div>
              <div className="flex items-center gap-2">
                {events.length > 0 && (
                  <button
                    type="button"
                    onClick={() => void handleCopyLogs()}
                    className="rounded-md border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:border-amber-500/40 transition-all flex items-center gap-1.5"
                  >
                    {copyFeedback ? (
                      <>
                        <span className="text-emerald-400">✓</span>
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <span>📋</span>
                        <span>Copy Logs</span>
                      </>
                    )}
                  </button>
                )}
                {isLoading && <span className="text-xs text-amber-400">Loading...</span>}
              </div>
            </div>

            <div className="max-h-[720px] overflow-y-auto p-4">
              {events.length === 0 ? (
                <p className="py-10 text-center text-sm text-slate-500">No events selected.</p>
              ) : (
                <div className="space-y-3">
                  {events.map((event, index) => (
                    <article key={`${event.timestamp}-${event.event}-${index}`} className="rounded-md border border-slate-900 bg-slate-950/50 p-4">
                      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                        <div>
                          <h3 className="font-mono text-sm font-bold text-slate-100">{event.event}</h3>
                          <p className="mt-1 text-xs text-slate-500">{new Date(event.timestamp).toLocaleString()}</p>
                        </div>
                        <span className="w-fit rounded border border-slate-800 px-2 py-1 text-[10px] uppercase text-slate-400">
                          {event.level}
                        </span>
                      </div>

                      <div className="mt-3 grid gap-2 text-[11px] text-slate-400 md:grid-cols-3">
                        <p className="truncate font-mono">request: {event.request_id || "-"}</p>
                        <p className="truncate font-mono">session: {event.session_id || "-"}</p>
                        <p className="truncate font-mono">run: {event.run_id || "-"}</p>
                      </div>

                      {event.is_eval && (
                        <div className="mt-3 rounded border border-sky-900/60 bg-sky-950/20 px-3 py-2 text-[11px] text-sky-200">
                          Eval: <span className="font-mono">{event.eval_suite || "unknown_suite"}</span>
                          <span className="mx-2 text-sky-700">/</span>
                          <span className="font-mono">{event.eval_case_id || "unknown_case"}</span>
                        </div>
                      )}

                      {event.event === "llm_call_completed" && event.attributes && (
                        <div className="mt-3 bg-[#03060d]/80 border border-slate-900 rounded-lg p-3 space-y-3">
                          <div className="flex flex-wrap gap-2 text-[10px] font-bold">
                            {event.attributes.cost_usd !== undefined && (
                              <span className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded px-2 py-0.5 font-mono">
                                💰 Cost: ${Number(event.attributes.cost_usd).toFixed(5)}
                              </span>
                            )}
                            {event.attributes.duration_ms !== undefined && (
                              <span className="bg-sky-500/10 border border-sky-500/20 text-sky-400 rounded px-2 py-0.5 font-mono">
                                🕒 Duration: {(Number(event.attributes.duration_ms) / 1000).toFixed(2)}s
                              </span>
                            )}
                            {event.attributes.llm_model && (
                              <span className="bg-slate-900 border border-slate-850 text-slate-350 rounded px-2 py-0.5 font-mono">
                                🤖 {String(event.attributes.llm_model)} ({String(event.attributes.llm_purpose || "LLM")})
                              </span>
                            )}
                          </div>
                          
                          {Number(event.attributes.input_tokens || 0) > 0 && (
                            <div className="space-y-2">
                              <div className="flex items-center justify-between text-[9px] font-extrabold text-slate-500 uppercase tracking-wider">
                                <span>Cache & Token breakdown</span>
                                <span className="font-mono">Total: {Number(event.attributes.input_tokens || 0) + Number(event.attributes.output_tokens || 0)} tokens</span>
                              </div>
                              
                              {/* Caching Horizontal Bar Stack */}
                              {(() => {
                                const inT = Number(event.attributes.input_tokens || 0);
                                const outT = Number(event.attributes.output_tokens || 0);
                                const cRead = Number(event.attributes.cache_read_tokens || 0);
                                const cCreate = Number(event.attributes.cache_creation_tokens || 0);
                                const baseIn = Math.max(0, inT - cRead - cCreate);
                                const total = inT + outT;
                                
                                return (
                                  <>
                                    <div className="h-3.5 bg-slate-950 rounded border border-slate-900 overflow-hidden flex text-[8px] font-bold font-mono">
                                      {cRead > 0 && (
                                        <div 
                                          className="bg-cyan-500 text-cyan-950 flex items-center justify-center transition-all h-full"
                                          style={{ width: `${(cRead / total) * 100}%` }}
                                          title={`Cached Read: ${cRead} tokens`}
                                        >
                                          {((cRead / total) * 100) > 12 && "Read"}
                                        </div>
                                      )}
                                      {cCreate > 0 && (
                                        <div 
                                          className="bg-indigo-500 text-indigo-100 flex items-center justify-center transition-all h-full"
                                          style={{ width: `${(cCreate / total) * 100}%` }}
                                          title={`Cache Write: ${cCreate} tokens`}
                                        >
                                          {((cCreate / total) * 100) > 12 && "Write"}
                                        </div>
                                      )}
                                      {baseIn > 0 && (
                                        <div 
                                          className="bg-slate-700 text-slate-205 flex items-center justify-center transition-all h-full"
                                          style={{ width: `${(baseIn / total) * 100}%` }}
                                          title={`Base Input: ${baseIn} tokens`}
                                        >
                                          {((baseIn / total) * 100) > 12 && "Input"}
                                        </div>
                                      )}
                                      {outT > 0 && (
                                        <div 
                                          className="bg-emerald-500 text-emerald-950 flex items-center justify-center transition-all h-full"
                                          style={{ width: `${(outT / total) * 100}%` }}
                                          title={`Output: ${outT} tokens`}
                                        >
                                          {((outT / total) * 100) > 12 && "Output"}
                                        </div>
                                      )}
                                    </div>
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[9px] text-slate-500 font-mono pt-1">
                                      <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-sm bg-cyan-500 inline-block"></span> Cache Read: {cRead}</span>
                                      <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-sm bg-indigo-500 inline-block"></span> Cache Write: {cCreate}</span>
                                      <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-sm bg-slate-700 inline-block"></span> Base Input: {baseIn}</span>
                                      <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-sm bg-emerald-500 inline-block"></span> Output: {outT}</span>
                                    </div>
                                  </>
                                );
                              })()}
                            </div>
                          )}
                        </div>
                      )}

                      {event.attributes && Object.keys(event.attributes).length > 0 && (
                        <div className="mt-3 space-y-3">
                          {!showRawJson[`${event.timestamp}-${event.event}-${index}`] && (
                            <>
                              {event.attributes.system && (
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">System Prompt</span>
                                  <pre className="max-h-40 overflow-auto rounded border border-slate-900 bg-slate-950 p-2.5 text-xs text-slate-300 font-mono whitespace-pre-wrap select-all">
                                    {String(event.attributes.system)}
                                  </pre>
                                </div>
                              )}

                              {event.attributes.messages && Array.isArray(event.attributes.messages) && (
                                <div className="space-y-2">
                                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Prompt Messages</span>
                                  <div className="space-y-2 max-h-80 overflow-auto rounded border border-slate-900 bg-slate-950 p-3 select-all">
                                    {(event.attributes.messages as Array<{ role: string; content: unknown }>).map((msg, idx) => (
                                      <div key={idx} className="border-b border-slate-900/60 pb-2 last:border-0 last:pb-0">
                                        <div className="flex items-center gap-2">
                                          <span className={`rounded px-1.5 py-0.5 text-[9px] uppercase font-bold ${
                                            msg.role === "user" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" : "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                                          }`}>
                                            {msg.role}
                                          </span>
                                        </div>
                                        <div className="mt-1 font-mono text-xs text-slate-355 whitespace-pre-wrap">
                                          {typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content, null, 2)}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {event.attributes.response_content && (
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Response Content</span>
                                  <pre className="max-h-80 overflow-auto rounded border border-slate-900 bg-slate-950 p-3 text-xs text-slate-300 font-mono whitespace-pre-wrap select-all">
                                    {String(event.attributes.response_content)}
                                  </pre>
                                </div>
                              )}

                              {event.attributes.tool_input && (
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Tool Input Arguments</span>
                                  <pre className="max-h-60 overflow-auto rounded border border-slate-900 bg-slate-950 p-3 text-xs text-slate-300 font-mono whitespace-pre-wrap select-all">
                                    {JSON.stringify(event.attributes.tool_input, null, 2)}
                                  </pre>
                                </div>
                              )}

                              {event.attributes.tool_output && (
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Tool Output</span>
                                  <pre className="max-h-80 overflow-auto rounded border border-slate-900 bg-[#03060d] p-3 text-xs text-slate-300 font-mono whitespace-pre-wrap select-all">
                                    {String(event.attributes.tool_output)}
                                  </pre>
                                </div>
                              )}
                            </>
                          )}

                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Properties</span>
                            <button
                              type="button"
                              onClick={() => {
                                const key = `${event.timestamp}-${event.event}-${index}`;
                                setShowRawJson(prev => ({ ...prev, [key]: !prev[key] }));
                              }}
                              className="text-[9px] font-bold uppercase text-amber-500 hover:text-amber-400 bg-slate-900 border border-slate-800 rounded px-2 py-1 transition-all"
                            >
                              {showRawJson[`${event.timestamp}-${event.event}-${index}`] ? "Hide Raw" : "View Raw JSON"}
                            </button>
                          </div>

                          {!showRawJson[`${event.timestamp}-${event.event}-${index}`] ? (
                            <div className="border border-slate-900/60 rounded-md overflow-hidden bg-slate-950/20 text-[11px]">
                              <table className="w-full text-left border-collapse">
                                <tbody>
                                  {Object.entries(event.attributes)
                                    .filter(([k]) => ![
                                      "cost_usd",
                                      "duration_ms",
                                      "input_tokens",
                                      "output_tokens",
                                      "cache_read_tokens",
                                      "cache_creation_tokens",
                                      "llm_model",
                                      "llm_purpose",
                                      "messages",
                                      "system",
                                      "response_content",
                                      "tool_input",
                                      "tool_output"
                                    ].includes(k))
                                    .map(([k, val]) => (
                                      <tr key={k} className="border-b border-slate-900/40 last:border-0 hover:bg-slate-900/10">
                                        <td className="px-3 py-2 font-semibold text-slate-400 capitalize w-1/3 truncate" title={k}>{k.replace(/_/g, " ")}</td>
                                        <td className="px-3 py-2 font-mono text-slate-300 break-all select-all whitespace-pre-wrap">
                                          {val !== null && typeof val === "object" ? JSON.stringify(val, null, 2) : String(val)}
                                        </td>
                                      </tr>
                                    ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <pre className="max-h-60 overflow-auto rounded border border-slate-900 bg-[#03060d] p-3 text-[11px] leading-relaxed text-slate-350 font-mono">
                              {JSON.stringify(event.attributes, null, 2)}
                            </pre>
                          )}
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}
