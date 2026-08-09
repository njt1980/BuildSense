"use client";

import React, { useState } from "react";
import { useOrchestratorStream } from "@/lib/useOrchestratorStream";
import { ClarificationModal } from "@/components/clarification-modal";
import { ReportView } from "@/components/report-view";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

/**
 * Main interactive Dashboard page for BuildSense.
 * Orchestrates form settings inputs, consumes SSE streams, triggers HILT questions modals,
 * and compiles final dual-view insight reports.
 *
 * @returns React node representing the application dashboard.
 */
export default function Home() {
  const {
    activeSessionState,
    isOrchestratorLoopActive,
    orchestratorLogs,
    errorDetails,
    executeOrchestratorRequest,
    resetOrchestratorSession,
  } = useOrchestratorStream();

  const [prompt, setPrompt] = useState<string>("");
  const [mode, setMode] = useState<"SUGGESTER" | "EVALUATOR" | "OPTIMIZER">("SUGGESTER");
  const [motivation, setMotivation] = useState<"REVENUE" | "EDUCATION">("EDUCATION");
  const [isClarificationOpen, setIsClarificationOpen] = useState<boolean>(false);

  // Auto-open HITL clarification modal if backend status signals AWAITING_CLARIFICATION
  React.useEffect(() => {
    if (activeSessionState?.status === "AWAITING_CLARIFICATION") {
      setIsClarificationOpen(true);
    } else {
      setIsClarificationOpen(false);
    }
  }, [activeSessionState]);

  /**
   * Dispatches initial pipeline start command to FastAPI.
   */
  const handleStartPipeline = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isOrchestratorLoopActive) return;

    executeOrchestratorRequest({
      prompt,
      mode,
      motivation,
    });
  };

  /**
   * Posts answers back to resume the pipeline loop.
   */
  const handleClarificationSubmit = (answers: Record<string, string>) => {
    if (!activeSessionState) return;
    setIsClarificationOpen(false);

    executeOrchestratorRequest({
      session_id: activeSessionState.session_id,
      clarification_responses: answers,
    });
  };

  return (
    <main className="min-h-screen bg-[#03060d] text-slate-100 p-4 md:p-8 flex flex-col items-center justify-start gap-8 font-sans selection:bg-amber-500/30 selection:text-amber-200 relative overflow-hidden">
      
      {/* Premium ambient radial glows */}
      <div className="absolute top-[-10%] left-[-15%] w-[60%] h-[60%] rounded-full bg-gradient-to-br from-amber-500/5 to-orange-500/0 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-15%] w-[60%] h-[60%] rounded-full bg-gradient-to-tr from-emerald-500/5 to-teal-500/0 blur-[130px] pointer-events-none" />

      {/* Premium Dashboard Header Banner */}
      <header className="w-full max-w-6xl text-center md:text-left flex flex-col md:flex-row items-center justify-between gap-6 border-b border-slate-900/60 pb-6 mt-4 relative z-10">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500">
            BuildSense
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Agentic Business Ideation, Evaluation, and Workflow Optimization
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            onClick={resetOrchestratorSession}
            className="border-slate-800/80 bg-slate-950/20 hover:bg-slate-900/40 hover:text-slate-100 text-slate-400 rounded-lg text-xs px-4 py-2 transition-all"
          >
            Clear Screen
          </Button>
          <div className="flex items-center gap-2 bg-slate-900/30 border border-slate-800/30 rounded-full px-3 py-1.5">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[11px] text-slate-300 font-medium tracking-wide">Core Engine Online</span>
          </div>
        </div>
      </header>

      {/* Primary Dashboard Content Panel Grid */}
      <section className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 relative z-10">
        
        {/* Left Side: Setup Panel */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <Card className="bg-[#0b0f19]/25 border border-slate-900/40 shadow-2xl rounded-xl backdrop-blur-md">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg font-bold text-slate-100">
                🚀 Pipeline Configuration
              </CardTitle>
              <CardDescription className="text-slate-400">
                Establish target mode, motivation boundaries, and prompt metadata.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleStartPipeline} className="space-y-6">
                
                {/* Mode Toggles */}
                <div className="space-y-2">
                  <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Mode</label>
                  <div className="grid grid-cols-3 gap-1.5 bg-[#03060d]/30 p-1.5 rounded-lg border border-slate-950">
                    {(["SUGGESTER", "EVALUATOR", "OPTIMIZER"] as const).map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setMode(m)}
                        className={`text-xs font-semibold py-2 px-1 rounded-md transition-all border ${
                          mode === m
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-md font-bold"
                            : "text-slate-400 border-transparent hover:text-slate-200 hover:bg-slate-900/20"
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Motivation Toggles */}
                <div className="space-y-2">
                  <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Motivation</label>
                  <div className="grid grid-cols-2 gap-1.5 bg-[#03060d]/30 p-1.5 rounded-lg border border-slate-950">
                    {(["REVENUE", "EDUCATION"] as const).map((mot) => (
                      <button
                        key={mot}
                        type="button"
                        onClick={() => setMotivation(mot)}
                        className={`text-xs font-semibold py-2 px-1 rounded-md transition-all border ${
                          motivation === mot
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-md font-bold"
                            : "text-slate-400 border-transparent hover:text-slate-200 hover:bg-slate-900/20"
                        }`}
                      >
                        {mot}
                      </button>
                    ))}
                  </div>
                </div>

                {/* User Prompt Text Area */}
                <div className="space-y-2">
                  <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Prompt</label>
                  <textarea
                    rows={4}
                    placeholder="Enter your SaaS product idea, business challenge, or workflow details..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    className="w-full bg-[#03060d]/30 border border-slate-900/30 text-slate-200 text-sm placeholder:text-slate-800 rounded-lg p-3.5 focus:outline-none focus:ring-1 focus:ring-amber-500/30 focus:border-transparent transition-all leading-relaxed resize-none shadow-inner"
                    required
                  />
                </div>

                {/* Submit Action Trigger Button */}
                <Button
                  type="submit"
                  disabled={!prompt.trim() || isOrchestratorLoopActive}
                  className="w-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 hover:from-amber-600 hover:via-orange-600 hover:to-rose-600 text-slate-950 font-extrabold py-3.5 rounded-lg shadow-lg hover:shadow-xl transition-all tracking-wide text-xs"
                >
                  {isOrchestratorLoopActive ? "Running Pipeline..." : "Start Orchestration"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Right Side: Log Console / Output Dossier View */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* Real-time Thought Logs Terminal Console */}
          <Card className="bg-[#0b0f19]/25 border border-slate-900/40 shadow-2xl rounded-xl overflow-hidden flex flex-col h-[280px] backdrop-blur-md">
            <CardHeader className="bg-transparent border-b border-slate-900/40 py-3.5 flex flex-row items-center justify-between px-5">
              <div>
                <CardTitle className="text-[10px] uppercase font-extrabold tracking-widest text-slate-400 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                  Agent Thought Console
                </CardTitle>
              </div>
              {isOrchestratorLoopActive && (
                <span className="text-[9px] uppercase tracking-wider text-amber-500 font-extrabold animate-pulse">Stream Active</span>
              )}
            </CardHeader>
            <CardContent className="p-0 flex-1 font-mono text-xs text-slate-300">
              <ScrollArea className="h-full p-5">
                <div className="space-y-2.5">
                  {orchestratorLogs.length === 0 ? (
                    <p className="text-slate-700 italic">No console logs streamed yet. Start a session...</p>
                  ) : (
                    orchestratorLogs.map((logLine, index) => {
                      let colorClass = "text-slate-300";
                      if (logLine.includes("[ERROR]")) colorClass = "text-rose-500 font-bold";
                      else if (logLine.includes("[COMPLETED]")) colorClass = "text-emerald-400 font-bold";
                      else if (logLine.includes("[HITL]")) colorClass = "text-amber-400";
                      else if (logLine.includes("[CLIENT]")) colorClass = "text-sky-400";
                      
                      return (
                        <div key={index} className={`whitespace-pre-wrap leading-relaxed ${colorClass}`}>
                          {logLine}
                        </div>
                      );
                    })
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Final Generated Output View */}
          {activeSessionState && activeSessionState.status === "COMPLETED" && (
            <ReportView sessionState={activeSessionState} />
          )}

          {/* Errors Indicator Banner */}
          {errorDetails && (
            <div className="bg-rose-950/20 border border-rose-900/60 text-rose-400 text-xs p-4 rounded-lg flex items-start gap-2 shadow-lg">
              <span className="font-bold text-rose-500">Error:</span> {errorDetails}
            </div>
          )}
        </div>
      </section>

      {/* Human-in-the-Loop Clarification Modal */}
      {activeSessionState && (
        <ClarificationModal
          isOpen={isClarificationOpen}
          questions={activeSessionState.clarification_questions}
          onSubmit={handleClarificationSubmit}
          onClose={() => setIsClarificationOpen(false)}
        />
      )}
    </main>
  );
}
