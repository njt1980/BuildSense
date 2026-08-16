"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { getApiBaseUrl } from "@/lib/api";

interface ComponentMap {
  trigger?: string | null;
  actor?: string | null;
  activity?: string | null;
  system?: string | null;
  friction?: string | null;
  location?: string | null;
}

interface Turn {
  turn_index: number;
  user_input: string;
  assistant_response: string;
  components: ComponentMap;
  confidence_score: number;
  next_question_strategy?: string;
}

interface JudgeScores {
  zero_jargon_score: number;
  hierarchy_integrity_score: number;
  consultant_intake_score: number;
  single_blind_spot_score: number;
  factual_grounding_score: number;
  privacy_safety_score: number;
  justification?: string;
}

interface ReportDetails {
  as_is_workflow?: string;
  friction_analysis?: string;
  technology_neutral_recommendations?: string;
  roi_economics?: string;
}

interface TestCaseResult {
  name: string;
  status: "PASSED" | "FAILED";
  latency: number;
  cost_usd: number;
  is_live: boolean;
  turns: Turn[];
  judge_scores: JudgeScores;
  report?: ReportDetails | null;
}

interface EvaluationData {
  timestamp: string;
  pass_rate: number;
  total_cases: number;
  passed_cases: number;
  avg_latency_seconds: number;
  total_latency_seconds: number;
  total_cost_usd: number;
  is_live_run: boolean;
  results: TestCaseResult[];
}

const apiBaseUrl = getApiBaseUrl();

export default function DevEvaluationsPage(): React.JSX.Element {
  const params = useParams();
  const router = useRouter();
  const lang = (params.lang as string) || "en";

  const [data, setData] = useState<EvaluationData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorText, setErrorText] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "PASSED" | "FAILED">("ALL");
  const [expandedCase, setExpandedCase] = useState<string | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    setErrorText("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/dev/evaluations/results`, {
        cache: "no-store",
      });
      if (response.status === 404) {
        throw new Error("No evaluation results file found. Please run the pytest evaluations suite first: `pytest tests/evals --run-evals`.");
      }
      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }
      const jsonData = (await response.json()) as EvaluationData;
      setData(jsonData);
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : "An unknown error occurred.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  const filteredResults = useMemo(() => {
    if (!data) return [];
    return data.results.filter((res) => {
      const matchesSearch = res.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === "ALL" || res.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [data, searchQuery, statusFilter]);

  const toggleExpand = (caseName: string) => {
    setExpandedCase(expandedCase === caseName ? null : caseName);
  };

  return (
    <main className="min-h-screen bg-[#03060d] text-slate-100 p-4 md:p-8 flex flex-col items-center justify-start gap-6 font-sans relative overflow-hidden">
      {/* Ambient background glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-to-br from-amber-500/5 to-orange-500/0 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-to-tr from-emerald-500/5 to-teal-500/0 blur-[130px] pointer-events-none" />

      {/* Header */}
      <header className="w-full max-w-6xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-900/60 pb-5 mt-2 relative z-10">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <button onClick={() => router.push(`/${lang}`)} className="hover:text-amber-400 font-semibold transition-all">← Dashboard</button>
            <span>/</span>
            <span>Developer Space</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500 mt-1">
            BuildSense Evaluation Metrics
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Step-by-step E2E run traces, component mapping accuracy, and LLM-as-a-judge quality scorecards.
          </p>
        </div>

        <button
          onClick={fetchResults}
          disabled={loading}
          className="bg-[#0b0f19] border border-slate-800 hover:bg-slate-900 text-amber-400 hover:text-amber-300 font-extrabold py-2 px-4 rounded-lg shadow-md transition-all text-xs flex items-center gap-1.5"
        >
          🔄 Refresh Results
        </button>
      </header>

      {/* Loading & Error States */}
      {loading && (
        <div className="w-full max-w-6xl py-20 flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-t-amber-500 border-slate-900 animate-spin" />
          <p className="text-xs text-slate-400 font-medium">Fetching evaluation run metrics...</p>
        </div>
      )}

      {!loading && errorText && (
        <div className="w-full max-w-6xl bg-rose-500/10 border border-rose-500/20 rounded-xl p-8 text-center flex flex-col items-center justify-center gap-4 relative z-10">
          <span className="text-3xl">⚠️</span>
          <h3 className="text-sm font-bold text-rose-400">Evaluation History Missing</h3>
          <p className="text-xs text-slate-400 max-w-md leading-relaxed">{errorText}</p>
        </div>
      )}

      {/* Main Content */}
      {!loading && !errorText && data && (
        <div className="w-full max-w-6xl flex flex-col gap-6 relative z-10">
          {/* KPI Grid */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-[#0b0f19]/35 border border-slate-900 p-4 rounded-xl flex flex-col gap-1 shadow-md">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Pass Rate</span>
              <span className={`text-xl font-extrabold ${data.pass_rate >= 90 ? "text-emerald-400" : "text-rose-400"}`}>
                {data.pass_rate}%
              </span>
              <span className="text-[9px] text-slate-500 mt-1">
                Passed: {data.passed_cases} / {data.total_cases}
              </span>
            </div>

            <div className="bg-[#0b0f19]/35 border border-slate-900 p-4 rounded-xl flex flex-col gap-1 shadow-md">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Avg Latency</span>
              <span className="text-xl font-extrabold text-sky-400">{data.avg_latency_seconds}s</span>
              <span className="text-[9px] text-slate-500 mt-1">Total: {data.total_latency_seconds}s</span>
            </div>

            <div className="bg-[#0b0f19]/35 border border-slate-900 p-4 rounded-xl flex flex-col gap-1 shadow-md">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Run Cost</span>
              <span className="text-xl font-extrabold text-emerald-400">${data.total_cost_usd}</span>
              <span className="text-[9px] text-slate-500 mt-1">Calculated API spend</span>
            </div>

            <div className="bg-[#0b0f19]/35 border border-slate-900 p-4 rounded-xl flex flex-col gap-1 shadow-md">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Execution Mode</span>
              <span className={`text-xl font-extrabold uppercase ${data.is_live_run ? "text-amber-400" : "text-slate-400"}`}>
                {data.is_live_run ? "⚡ Live Run" : "🛠️ Mocked"}
              </span>
              <span className="text-[9px] text-slate-500 mt-1">
                {new Date(data.timestamp).toLocaleString()}
              </span>
            </div>
          </section>

          {/* Filter Bar */}
          <section className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-[#0b0f19]/15 border border-slate-900 p-3 rounded-xl">
            <div className="relative w-full sm:max-w-xs">
              <input
                type="text"
                placeholder="Search scenario cases..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#03060d] border border-slate-800 text-xs text-slate-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
              />
            </div>

            <div className="flex gap-2 w-full sm:w-auto">
              {(["ALL", "PASSED", "FAILED"] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setStatusFilter(filter)}
                  className={`flex-grow sm:flex-grow-0 text-[10px] font-bold uppercase py-2 px-4 rounded-md border transition-all ${
                    statusFilter === filter
                      ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                      : "bg-[#03060d] border-slate-900 text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>
          </section>

          {/* Test Case Accordions */}
          <section className="flex flex-col gap-4">
            {filteredResults.length === 0 ? (
              <div className="text-center py-10 border border-dashed border-slate-900 rounded-xl text-xs text-slate-500">
                No matching scenarios found.
              </div>
            ) : (
              filteredResults.map((tc, idx) => {
                const isOpen = expandedCase === tc.name;
                return (
                  <div
                    key={idx}
                    className={`bg-[#0b0f19]/25 border rounded-xl overflow-hidden shadow-sm transition-all duration-200 ${
                      isOpen ? "border-slate-800" : "border-slate-900 hover:border-slate-800/60"
                    }`}
                  >
                    {/* Accordion Trigger */}
                    <div
                      onClick={() => toggleExpand(tc.name)}
                      className="p-4 flex items-center justify-between cursor-pointer select-none"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={`text-[10px] font-black uppercase px-2.5 py-1 rounded-md tracking-wider ${
                            tc.status === "PASSED"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                          }`}
                        >
                          {tc.status}
                        </span>
                        <h4 className="text-xs font-bold text-slate-200">{tc.name}</h4>
                      </div>

                      <div className="flex items-center gap-4 text-[10px] text-slate-500">
                        <span>🕒 {tc.latency}s</span>
                        {tc.cost_usd > 0 && <span>💰 ${tc.cost_usd}</span>}
                        <span>{isOpen ? "🔼" : "🔽"}</span>
                      </div>
                    </div>

                    {/* Accordion Content */}
                    {isOpen && (
                      <div className="border-t border-slate-950 p-5 bg-[#03060d]/40 flex flex-col gap-6 text-xs text-slate-300">
                        {/* Summary Details */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          {/* Extracted Process Components Grid */}
                          <div className="bg-[#0b0f19]/35 border border-slate-900 p-4 rounded-xl flex flex-col gap-3">
                            <h5 className="font-extrabold text-[10px] uppercase text-slate-400 tracking-wider">
                              Extracted Process Components
                            </h5>
                            <div className="grid grid-cols-2 gap-3 text-[10px]">
                              {Object.entries(tc.turns[tc.turns.length - 1]?.components || {}).map(([key, val]) => (
                                <div key={key} className="flex flex-col gap-0.5 bg-[#03060d]/50 p-2 rounded-md">
                                  <span className="font-bold text-slate-500 capitalize">{key}</span>
                                  <span className="text-slate-300 break-words mt-0.5">
                                    {val ? String(val) : <span className="text-slate-600 font-medium">None</span>}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* LLM Judge Scorecard */}
                          <div className="bg-[#0b0f19]/35 border border-slate-900 p-4 rounded-xl flex flex-col gap-3">
                            <h5 className="font-extrabold text-[10px] uppercase text-slate-400 tracking-wider">
                              LLM Judge Scorecard
                            </h5>
                            <div className="grid grid-cols-3 gap-2">
                              {Object.entries(tc.judge_scores)
                                .filter(([key]) => key !== "justification")
                                .map(([key, val]) => {
                                  const label = key.replace("_score", "").replace(/_/g, " ");
                                  const score = val as number;
                                  return (
                                    <div
                                      key={key}
                                      className="flex flex-col items-center justify-center p-2 bg-[#03060d]/50 rounded-md border border-slate-900"
                                    >
                                      <span className="text-[8px] font-bold text-slate-500 uppercase text-center leading-tight">
                                        {label}
                                      </span>
                                      <span
                                        className={`text-xs font-black mt-1 ${
                                          score >= 0.90 ? "text-emerald-400" : "text-amber-400"
                                        }`}
                                      >
                                        {score.toFixed(2)}
                                      </span>
                                    </div>
                                  );
                                })}
                            </div>
                            {tc.judge_scores.justification && (
                              <p className="text-[10px] text-slate-500 italic mt-1 leading-relaxed bg-[#03060d]/20 p-2 rounded-md border border-slate-900/60">
                                "{tc.judge_scores.justification}"
                              </p>
                            )}
                          </div>
                        </div>

                        {/* Step-by-Step Turn Timeline */}
                        <div className="flex flex-col gap-3">
                          <h5 className="font-extrabold text-[10px] uppercase text-slate-400 tracking-wider">
                            Turn-by-Turn Dialog Trace
                          </h5>
                          <div className="space-y-4">
                            {tc.turns.map((turn, tIdx) => (
                              <div key={tIdx} className="border border-slate-900 rounded-xl p-4 bg-[#0b0f19]/10 space-y-3">
                                <div className="flex items-center justify-between text-[9px] font-bold border-b border-slate-900 pb-2">
                                  <span className="text-amber-400">TURN {turn.turn_index}</span>
                                  <div className="flex items-center gap-3 text-slate-500">
                                    <span>🎯 Score: {turn.confidence_score.toFixed(2)}</span>
                                    <span>Strategy: <span className="text-slate-400 capitalize">{turn.next_question_strategy || "default"}</span></span>
                                  </div>
                                </div>
                                
                                <div className="space-y-2">
                                  <div className="flex flex-col gap-1">
                                    <span className="text-[8px] font-extrabold uppercase text-slate-500">User Input</span>
                                    <p className="text-[11px] text-slate-200 bg-[#03060d]/60 p-2 rounded-md">{turn.user_input}</p>
                                  </div>
                                  
                                  <div className="flex flex-col gap-1">
                                    <span className="text-[8px] font-extrabold uppercase text-slate-500">Assistant Response</span>
                                    <p className="text-[11px] text-amber-300 bg-amber-500/5 p-2 rounded-md border border-amber-500/10 leading-relaxed whitespace-pre-wrap">{turn.assistant_response}</p>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Generated Report Dossier */}
                        {tc.report && (
                          <div className="bg-[#0b0f19]/35 border border-slate-900 p-4 rounded-xl flex flex-col gap-4">
                            <h5 className="font-extrabold text-[10px] uppercase text-slate-400 tracking-wider">
                              Synthesized Report Preview
                            </h5>
                            <div className="space-y-4 text-[11px] leading-relaxed">
                              {tc.report.as_is_workflow && (
                                <div className="bg-[#03060d]/50 p-3 rounded-lg border border-slate-900">
                                  <h6 className="font-bold text-amber-400 mb-1">As-Is Process Map</h6>
                                  <p className="whitespace-pre-wrap">{tc.report.as_is_workflow}</p>
                                </div>
                              )}
                              {tc.report.friction_analysis && (
                                <div className="bg-[#03060d]/50 p-3 rounded-lg border border-slate-900">
                                  <h6 className="font-bold text-amber-400 mb-1">Friction & Bleed Diagnostic</h6>
                                  <p className="whitespace-pre-wrap">{tc.report.friction_analysis}</p>
                                </div>
                              )}
                              {tc.report.technology_neutral_recommendations && (
                                <div className="bg-[#03060d]/50 p-3 rounded-lg border border-slate-900">
                                  <h6 className="font-bold text-amber-400 mb-1">Technology Neutral Recommendations</h6>
                                  <p className="whitespace-pre-wrap">{tc.report.technology_neutral_recommendations}</p>
                                </div>
                              )}
                              {tc.report.roi_economics && (
                                <div className="bg-[#03060d]/50 p-3 rounded-lg border border-slate-900">
                                  <h6 className="font-bold text-amber-400 mb-1">ROI & Value Ratios</h6>
                                  <p className="whitespace-pre-wrap">{tc.report.roi_economics}</p>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </section>
        </div>
      )}
    </main>
  );
}
