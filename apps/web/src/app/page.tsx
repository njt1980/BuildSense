"use client";

import React, { useState } from "react";
import { useOrchestratorStream } from "@/lib/useOrchestratorStream";
import { ClarificationModal } from "@/components/clarification-modal";
import { ReportView } from "@/components/report-view";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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
  const [uploadedFile, setUploadedFile] = useState<{ name: string; content: string } | null>(null);

  // BYOK (Bring Your Own Key) States
  const [userApiKey, setUserApiKey] = useState<string>("");
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [hasStoredKey, setHasStoredKey] = useState<boolean>(false);

  // Mount logic: load credentials from localStorage
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("buildsense_user_api_key") || "";
      setUserApiKey(stored);
      setHasStoredKey(!!stored);
    }
  }, []);

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
      file_name: uploadedFile?.name,
      file_content: uploadedFile?.content,
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

  /**
   * Reads target document content via browser FileReader API.
   */
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setUploadedFile({
        name: file.name,
        content: content || "",
      });
    };
    reader.readAsText(file);
  };

  const clearUploadedFile = () => {
    setUploadedFile(null);
  };

  /**
   * Saves credentials config changes back to localStorage cache bounds.
   */
  const handleSaveApiKey = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("buildsense_user_api_key", userApiKey);
      setHasStoredKey(!!userApiKey);
    }
    setIsSettingsOpen(false);
  };

  /**
   * Clears credentials config from cache bounds.
   */
  const handleClearApiKey = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("buildsense_user_api_key");
      setUserApiKey("");
      setHasStoredKey(false);
    }
    setIsSettingsOpen(false);
  };

  // Dynamic scenario guidance text mapping
  const scenarioGuidance = {
    "SUGGESTER_REVENUE": "Focusing on market gaps, B2B SaaS opportunities, high margins, and defensibility.",
    "SUGGESTER_EDUCATION": "Focusing on hands-on skill building, portfolio value, and zero-cost free-tier tech stacks.",
    "EVALUATOR_REVENUE": "Auditing commercial viability, demand signals, competitive moats, and LTV:CAC payback.",
    "EVALUATOR_EDUCATION": "Auditing technical design, architectural elegance, learning milestones, and open-source stacks.",
    "OPTIMIZER_REVENUE": "Focusing on operational cost reduction, error reduction, manual labor elimination, and ROI.",
    "OPTIMIZER_EDUCATION": "Focusing on personal productivity, custom automation scripts, API integrations, and self-hosted tools.",
  };

  // Clickable example prompt pills list mapping
  const examplePrompts = {
    "SUGGESTER_REVENUE": [
      "Suggest 3 B2B micro-SaaS opportunities in supply chain logistics with high profit margins.",
      "Suggest 3 underserved software niches for tracking real-time regional commodity prices.",
      "Suggest 3 AI-driven financial tools aimed at making stock analysis accessible to retail investors."
    ],
    "SUGGESTER_EDUCATION": [
      "Suggest 3 weekend projects to master multi-agent orchestration loops in Python.",
      "Suggest 3 zero-cost free-tier project ideas to learn vector databases and RAG architectures.",
      "Suggest 3 fun IoT or local automation ideas that utilize lightweight open-source LLMs."
    ],
    "EVALUATOR_REVENUE": [
      "Audit my idea: A web application that explains complex stock filings in plain English for everyday investors.",
      "Audit my idea: An AI platform tracking real-time industrial steel prices across major regional hubs.",
      "Audit my idea: An automated micro-SaaS that generates hyper-local SEO campaigns for dental practices."
    ],
    "EVALUATOR_EDUCATION": [
      "Audit my project: A personal workout and macro tracker running entirely on local open-source models.",
      "Audit my project: A browser extension that summarizes GitHub pull requests using Gemini 3.5 Flash.",
      "Audit my project: A retro 8-bit game engine built with TypeScript to master the HTML5 Canvas API."
    ],
    "OPTIMIZER_REVENUE": [
      "Our team manually transcribes 50+ PDF vendor invoices into Excel weekly. Show us how to automate this.",
      "We manually triage incoming customer support emails into Jira tickets. Draft an AI routing roadmap.",
      "We copy-paste daily market prices from multiple websites into a master spreadsheet. Design an automated pipeline."
    ],
    "OPTIMIZER_EDUCATION": [
      "I manually copy workout logs from my notes app into a spreadsheet. How can I build a quick script to automate this?",
      "How can I set up an automated local script to summarize daily RSS news feeds directly into my terminal?",
      "Draft a simple workflow to automatically categorize and rename PDF downloads in my local folder."
    ]
  };

  const guidanceKey = `${mode}_${motivation}` as keyof typeof scenarioGuidance;
  const currentGuidance = scenarioGuidance[guidanceKey];
  const currentPills = examplePrompts[guidanceKey];

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
        
        {/* Navigation configuration settings actions */}
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={resetOrchestratorSession}
            className="border-slate-800/80 bg-slate-950/20 hover:bg-slate-900/40 hover:text-slate-100 text-slate-400 rounded-lg text-xs px-4 py-2.5 transition-all"
          >
            Clear Screen
          </Button>

          {/* BYOK Settings Modal Trigger Button */}
          <Button
            variant="outline"
            onClick={() => setIsSettingsOpen(true)}
            className={`border-slate-800/80 bg-slate-950/20 hover:bg-slate-900/40 rounded-lg px-3 py-2.5 transition-all text-sm flex items-center gap-1.5 ${
              hasStoredKey ? "text-emerald-400 border-emerald-500/20 bg-emerald-500/5" : "text-slate-400"
            }`}
            title="Configure Custom API Credentials"
          >
            🔑 <span className="text-xs font-semibold hidden sm:inline">{hasStoredKey ? "BYOK Active" : "Set API Key"}</span>
          </Button>

          <div className="flex items-center gap-2 bg-slate-900/30 border border-slate-800/30 rounded-full px-3 py-2">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[11px] text-slate-300 font-medium tracking-wide">Core Engine Online</span>
          </div>
        </div>
      </header>

      {/* Primary Dashboard Content Grid */}
      <section className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 relative z-10">
        
        {/* Left Side: Setup Panel */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bg-[#0b0f19]/25 shadow-2xl rounded-xl backdrop-blur-md p-6 flex flex-col gap-5">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                🚀 Pipeline Configuration
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Establish target mode, motivation boundaries, and prompt metadata.
              </p>
            </div>

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

              {/* Dynamic Scenario Guidance Banner */}
              <div className="bg-[#03060d]/40 border border-slate-900/40 rounded-lg p-3 text-[11px] leading-relaxed text-slate-300">
                <span className="font-semibold text-amber-400">Target Focus:</span> {currentGuidance}
              </div>

              {/* Document Upload Area (with Optimizer emphasis) */}
              <div className="space-y-2">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Document Attachment</label>
                <div 
                  className={`border-2 border-dashed rounded-lg p-4 transition-all duration-300 text-center relative ${
                    mode === "OPTIMIZER"
                      ? "border-amber-500/45 bg-amber-500/5 shadow-[0_0_15px_rgba(245,158,11,0.05)] animate-pulse"
                      : "border-slate-800/40 bg-slate-950/20 hover:border-slate-800"
                  }`}
                >
                  <input
                    type="file"
                    accept=".pdf,.txt,.csv,.md"
                    onChange={handleFileUpload}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  {!uploadedFile ? (
                    <div>
                      <p className="text-xs font-semibold text-slate-300">
                        {mode === "OPTIMIZER" ? "★ RECOMMENDED: Drop SOP / Workflow File" : "Upload File (PDF, TXT, CSV, MD)"}
                      </p>
                      <p className="text-[10px] text-slate-500 mt-1">Click or drag file to attach context</p>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between bg-[#03060d]/60 px-3 py-1.5 rounded border border-slate-900 text-xs">
                      <span className="text-slate-300 truncate max-w-[200px] font-mono">📎 {uploadedFile.name}</span>
                      <button
                        type="button"
                        onClick={clearUploadedFile}
                        className="text-rose-400 hover:text-rose-300 font-bold ml-2 relative z-10"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* User Prompt Text Area & Clickable Example Pills */}
              <div className="space-y-2.5">
                <div className="flex justify-between items-center">
                  <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Prompt</label>
                  <span className="text-[10px] text-slate-500 font-mono">Mode helper</span>
                </div>
                
                {/* Example pills */}
                <div className="flex flex-col gap-1.5 max-h-[120px] overflow-y-auto pr-1">
                  {currentPills.map((pillText, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setPrompt(pillText)}
                      className="text-left text-[10px] text-slate-400 bg-[#03060d]/50 hover:bg-slate-900 hover:text-slate-200 border border-slate-950 p-2 rounded-md transition-all truncate"
                      title={pillText}
                    >
                      💡 &ldquo;{pillText}&rdquo;
                    </button>
                  ))}
                </div>

                <textarea
                  rows={4}
                  placeholder="Enter your SaaS product idea, business challenge, or workflow details..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="w-full bg-[#03060d]/30 border border-slate-900/30 text-slate-200 text-sm placeholder:text-slate-800 rounded-lg p-3.5 focus:outline-none focus:ring-1 focus:ring-amber-500/30 focus:border-transparent transition-all leading-relaxed resize-none shadow-inner"
                  required
                />
                <p className="text-[10px] text-slate-600 mt-1 leading-normal">
                  Note: Prompts containing less than 15 characters will trigger a clarification request.
                </p>
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
          </div>
        </div>

        {/* Right Side: Log Console / Output Dossier View */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* Real-time Thought Logs Terminal Console */}
          <div className="bg-[#0b0f19]/25 shadow-2xl rounded-xl overflow-hidden flex flex-col h-[280px] backdrop-blur-md">
            <div className="border-b border-slate-900/40 py-3.5 flex flex-row items-center justify-between px-5">
              <div>
                <h2 className="text-[10px] uppercase font-extrabold tracking-widest text-slate-400 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                  Agent Thought Console
                </h2>
              </div>
              {isOrchestratorLoopActive && (
                <span className="text-[9px] uppercase tracking-wider text-amber-500 font-extrabold animate-pulse">Stream Active</span>
              )}
            </div>
            <div className="p-0 flex-1 font-mono text-xs text-slate-300">
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
            </div>
          </div>

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

      {/* BYOK Settings Modal Panel Dialog */}
      <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
        <DialogContent className="sm:max-w-[450px] bg-slate-900 border border-slate-800 text-slate-100 shadow-2xl backdrop-blur-md rounded-xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-slate-100 flex items-center gap-2">
              🔑 API Credentials Settings
            </DialogTitle>
            <DialogDescription className="text-slate-400 text-xs">
              Provide a custom Anthropic key to pay for API usage directly and bypass global daily server thresholds.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">
                Anthropic API Key
              </label>
              <input
                type="password"
                placeholder="sk-ant-..."
                value={userApiKey}
                onChange={(e) => setUserApiKey(e.target.value)}
                className="w-full bg-[#03060d]/60 border border-slate-800 text-slate-200 text-sm placeholder:text-slate-700 rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-amber-500/40 transition-all font-mono"
              />
              <p className="text-[10px] text-slate-500">
                Stored locally in your browser&apos;s localStorage. Never sent to database tables or logged.
              </p>
            </div>
            <div className="flex items-center justify-between text-xs pt-2">
              <span className="text-slate-400 font-medium">Status:</span>
              {hasStoredKey ? (
                <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full px-2.5 py-0.5 font-bold tracking-wide">
                  Custom Key Configured
                </span>
              ) : (
                <span className="bg-slate-800/80 text-slate-400 border border-slate-700/30 rounded-full px-2.5 py-0.5 font-bold tracking-wide">
                  Server Default Fallback
                </span>
              )}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="outline"
              onClick={handleClearApiKey}
              className="border-slate-800 bg-slate-950/20 text-slate-400 hover:bg-rose-950/20 hover:text-rose-400 rounded-lg text-xs"
            >
              Remove Key
            </Button>
            <Button
              onClick={handleSaveApiKey}
              className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold rounded-lg text-xs px-4"
            >
              Save Settings
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
}
