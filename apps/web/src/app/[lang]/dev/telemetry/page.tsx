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
                        <span className="rounded border border-slate-800 px-1.5 py-0.5 text-[10px] uppercase text-slate-400">
                          {run.status}
                        </span>
                      </div>
                      <p className="mt-2 truncate font-mono text-[11px] text-slate-500">{run.session_id || "no session"}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                        <span>{run.event_count} events</span>
                        <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase ${
                          run.is_eval ? "border-sky-800 text-sky-300" : "border-slate-800 text-slate-400"
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
            <div className="flex flex-col gap-2 border-b border-slate-900 px-4 py-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-100">Event Timeline</h2>
                <p className="mt-1 font-mono text-xs text-slate-500">{selectedRunId || "Select a run"}</p>
              </div>
              {isLoading && <span className="text-xs text-amber-400">Loading...</span>}
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

                      {event.attributes && Object.keys(event.attributes).length > 0 && (
                        <pre className="mt-3 max-h-48 overflow-auto rounded border border-slate-900 bg-[#03060d] p-3 text-[11px] leading-relaxed text-slate-300">
                          {JSON.stringify(event.attributes, null, 2)}
                        </pre>
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
