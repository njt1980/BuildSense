"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

export default function Home() {
  const router = useRouter();
  const { user, token, signOut } = useAuth();

  const [prompt, setPrompt] = useState<string>("");
  const [mode, setMode] = useState<"SUGGESTER" | "EVALUATOR" | "OPTIMIZER">("SUGGESTER");
  const [motivation, setMotivation] = useState<"REVENUE" | "EDUCATION">("EDUCATION");
  const [userPersona, setUserPersona] = useState<string>("Solo Founder");
  const [uploadedFile, setUploadedFile] = useState<{ name: string; content: string } | null>(null);

  // Projects list state
  const [projects, setProjects] = useState<any[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);
  const [errorText, setErrorText] = useState("");

  // BYOK States
  const [userApiKey, setUserApiKey] = useState<string>("");
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [hasStoredKey, setHasStoredKey] = useState<boolean>(false);

  // Load BYOK key from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("buildsense_user_api_key") || "";
      setUserApiKey(stored);
      setHasStoredKey(!!stored);
    }
  }, []);

  // Fetch projects list on mount and when token is ready
  useEffect(() => {
    if (!token) return;
    const fetchProjects = async () => {
      setLoadingProjects(true);
      try {
        const res = await fetch("http://localhost:9000/api/v1/projects", {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setProjects(data || []);
        }
      } catch (err) {
        console.error("Error fetching projects:", err);
      } finally {
        setLoadingProjects(false);
      }
    };
    fetchProjects();
  }, [token]);

  const handleStartPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || creatingProject || !token) return;

    setCreatingProject(true);
    setErrorText("");

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      };
      if (userApiKey) {
        headers["X-User-Anthropic-Key"] = userApiKey;
      }

      // Start orchestration (which returns project_id as session_id)
      const res = await fetch("http://localhost:9000/api/v1/orchestrate", {
        method: "POST",
        headers,
        body: JSON.stringify({
          prompt,
          mode,
          motivation,
          user_persona: userPersona,
          file_name: uploadedFile?.name,
          file_content: uploadedFile?.content
        })
      });

      if (!res.ok) {
        throw new Error(`Execution error: ${res.statusText}`);
      }

      const state = await res.json();
      const newProjectId = state.session_id;

      // Redirect immediately to the project's workspace
      router.push(`/projects/${newProjectId}`);
    } catch (err: any) {
      setErrorText(err.message || "Failed to start orchestration.");
      setCreatingProject(false);
    }
  };

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

  const handleDeleteProject = async (projectId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this project workspace?") || !token) return;

    try {
      const res = await fetch(`http://localhost:9000/api/v1/projects/${projectId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        setProjects(projects.filter(p => p.id !== projectId));
      }
    } catch (err) {
      console.error("Error deleting project:", err);
    }
  };

  const handleSaveApiKey = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("buildsense_user_api_key", userApiKey);
      setHasStoredKey(!!userApiKey);
    }
    setIsSettingsOpen(false);
  };

  const handleClearApiKey = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("buildsense_user_api_key");
      setUserApiKey("");
      setHasStoredKey(false);
    }
    setIsSettingsOpen(false);
  };

  const scenarioGuidance = {
    "SUGGESTER_REVENUE": "Focusing on market gaps, B2B SaaS opportunities, high margins, and defensibility.",
    "SUGGESTER_EDUCATION": "Focusing on hands-on skill building, portfolio value, and zero-cost free-tier tech stacks.",
    "EVALUATOR_REVENUE": "Auditing commercial viability, demand signals, competitive moats, and LTV:CAC payback.",
    "EVALUATOR_EDUCATION": "Auditing technical design, architectural elegance, learning milestones, and open-source stacks.",
    "OPTIMIZER_REVENUE": "Focusing on operational cost reduction, error reduction, manual labor elimination, and ROI.",
    "OPTIMIZER_EDUCATION": "Focusing on personal productivity, custom automation scripts, API integrations, and self-hosted tools.",
  };

  const examplePrompts = {
    "SUGGESTER_REVENUE": [
      "Suggest 3 B2B micro-SaaS opportunities in supply chain logistics with high profit margins.",
      "Suggest 3 underserved software niches for tracking real-time regional commodity prices."
    ],
    "SUGGESTER_EDUCATION": [
      "Suggest 3 weekend projects to master multi-agent orchestration loops in Python.",
      "Suggest 3 zero-cost free-tier project ideas to learn vector databases and RAG."
    ],
    "EVALUATOR_REVENUE": [
      "Audit my idea: A web application that explains complex stock filings in plain English.",
      "Audit my idea: An AI platform tracking real-time industrial steel prices."
    ],
    "EVALUATOR_EDUCATION": [
      "Audit my project: A personal workout and macro tracker running on local open-source models.",
      "Audit my project: A browser extension that summarizes GitHub pull requests using Claude."
    ],
    "OPTIMIZER_REVENUE": [
      "Our team manually transcribes 50+ PDF vendor invoices into Excel weekly. Show us how to automate this.",
      "We manually triage incoming customer support emails into Jira tickets. Draft an AI routing roadmap."
    ],
    "OPTIMIZER_EDUCATION": [
      "I manually copy workout logs from my notes app into a spreadsheet. How can I automate this?",
      "How can I set up an automated local script to summarize daily RSS news feeds?"
    ]
  };

  const guidanceKey = `${mode}_${motivation}` as keyof typeof scenarioGuidance;
  const currentGuidance = scenarioGuidance[guidanceKey];
  const currentPills = examplePrompts[guidanceKey];

  return (
    <main className="min-h-screen bg-[#03060d] text-slate-100 p-4 md:p-8 flex flex-col items-center justify-start gap-8 font-sans selection:bg-amber-500/30 selection:text-amber-200 relative overflow-hidden">
      
      {/* Ambient background glows */}
      <div className="absolute top-[-10%] left-[-15%] w-[60%] h-[60%] rounded-full bg-gradient-to-br from-amber-500/5 to-orange-500/0 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-15%] w-[60%] h-[60%] rounded-full bg-gradient-to-tr from-emerald-500/5 to-teal-500/0 blur-[130px] pointer-events-none" />

      {/* Dashboard Header */}
      <header className="w-full max-w-6xl text-center md:text-left flex flex-col md:flex-row items-center justify-between gap-6 border-b border-slate-900/60 pb-6 mt-4 relative z-10">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500">
            BuildSense
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Agentic Business Ideation, Evaluation, and Workflow Optimization
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {user && (
            <div className="flex items-center gap-2 bg-[#0b0f19]/45 border border-slate-900/60 rounded-lg px-3 py-1.5 text-slate-300 font-mono text-xs">
              <span className="max-w-[140px] truncate" title={user.email}>👤 {user.email}</span>
              <button 
                type="button" 
                onClick={signOut}
                className="text-[9px] bg-rose-950/20 text-rose-400 border border-rose-950/40 rounded px-1.5 py-0.5 hover:bg-rose-900/30 hover:text-rose-300 font-bold ml-1 transition-all"
              >
                Sign Out
              </button>
            </div>
          )}

          {/* BYOK Settings Trigger */}
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
            <span className="text-[11px] text-slate-300 font-medium tracking-wide">Multi-Tenant Core Online</span>
          </div>
        </div>
      </header>

      {/* Dashboard Main Grid */}
      <section className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 relative z-10">
        
        {/* Left: Configure new project Form */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bg-[#0b0f19]/25 shadow-2xl rounded-xl backdrop-blur-md p-6 flex flex-col gap-5">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                🚀 Create Business Analysis
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Configure your project boundaries and request LangGraph valuation.
              </p>
            </div>

            <form onSubmit={handleStartPipeline} className="space-y-5">
              {/* Persona Select */}
              <div className="space-y-2">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">User Persona Focus</label>
                <select
                  value={userPersona}
                  onChange={(e) => setUserPersona(e.target.value)}
                  className="w-full bg-[#03060d]/60 border border-slate-800 text-slate-200 text-xs rounded-lg p-2.5 focus:outline-none focus:ring-1 focus:ring-amber-500/40"
                >
                  <option value="Solo Founder">🚀 Solo Founder (Speed & Tech Moats)</option>
                  <option value="Small Business Operator">🌾 Small Business Operator (Direct ROI, Jargon-free)</option>
                  <option value="Enterprise PM">🏢 Enterprise PM (Compliance & Scale)</option>
                  <option value="Student">🎓 Student (Technical Learning Path)</option>
                </select>
              </div>

              {/* Mode Select */}
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

              {/* Motivation Select */}
              <div className="space-y-2">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Motivation Focus</label>
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

              <div className="bg-[#03060d]/40 border border-slate-900/40 rounded-lg p-3 text-[11px] leading-relaxed text-slate-300">
                <span className="font-semibold text-amber-400">Target Focus:</span> {currentGuidance}
              </div>

              {/* SOP Upload Area */}
              <div className="space-y-2">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Workflow Attachment</label>
                <div className={`border-2 border-dashed rounded-lg p-3 text-center relative ${
                  mode === "OPTIMIZER" ? "border-amber-500/40 bg-amber-500/5 animate-pulse" : "border-slate-800 bg-slate-950/20"
                }`}>
                  <input type="file" accept=".txt,.pdf,.csv,.md" onChange={handleFileUpload} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                  {!uploadedFile ? (
                    <div>
                      <p className="text-xs font-semibold text-slate-300">{mode === "OPTIMIZER" ? "★ Drop SOP Process File Here" : "Attach Context File"}</p>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between bg-slate-900 px-3 py-1.5 rounded text-xs">
                      <span className="truncate max-w-[150px]">📎 {uploadedFile.name}</span>
                      <button type="button" onClick={() => setUploadedFile(null)} className="text-rose-400">✕</button>
                    </div>
                  )}
                </div>
              </div>

              {/* Prompt Text Area */}
              <div className="space-y-2">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Concept Description</label>
                <div className="flex flex-wrap gap-1 max-h-[80px] overflow-y-auto pr-1">
                  {currentPills.slice(0, 2).map((pillText, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setPrompt(pillText)}
                      className="text-left text-[10px] text-slate-400 bg-slate-950/50 hover:bg-slate-900 border border-slate-900/40 p-1.5 rounded transition-all truncate max-w-full"
                      title={pillText}
                    >
                      💡 {pillText}
                    </button>
                  ))}
                </div>

                <textarea
                  rows={3}
                  placeholder="Describe your SaaS product idea or manual workflow..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="w-full bg-[#03060d]/30 border border-slate-800 text-slate-200 text-xs rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-amber-500/40 resize-none shadow-inner"
                  required
                />
              </div>

              <Button
                type="submit"
                disabled={!prompt.trim() || creatingProject}
                className="w-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 hover:from-amber-600 hover:via-orange-600 hover:to-rose-600 text-slate-950 font-extrabold py-3 rounded-lg shadow-lg transition-all tracking-wide text-xs"
              >
                {creatingProject ? "Scaffolding Workspace..." : "Create & Start Analysis"}
              </Button>

              {errorText && (
                <p className="text-rose-500 text-[10px] bg-rose-950/10 border border-rose-900/35 p-2 rounded text-center">{errorText}</p>
              )}
            </form>
          </div>
        </div>

        {/* Right: Active Projects Listing */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <div className="bg-[#0b0f19]/25 shadow-2xl rounded-xl p-6 backdrop-blur-md flex flex-col gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                📁 Your Active Workspaces
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Select any existing project to view reports, graphs, and chat history.
              </p>
            </div>

            {loadingProjects ? (
              <div className="flex flex-col items-center justify-center p-12 gap-2 text-slate-400">
                <div className="w-5 h-5 rounded-full border border-t-amber-500 animate-spin" />
                <span className="text-[10px]">Loading projects...</span>
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center p-16 border border-dashed border-slate-800/60 rounded-xl">
                <p className="text-xs text-slate-500 italic">No project workspaces created yet.</p>
                <p className="text-[10px] text-slate-600 mt-1 leading-normal max-w-sm mx-auto">Fill out the configuration form on the left to start your first multi-tenant business analysis run.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-h-[480px] overflow-y-auto pr-1">
                {projects.map((proj) => (
                  <div
                    key={proj.id}
                    onClick={() => router.push(`/projects/${proj.id}`)}
                    className="group bg-[#03060d]/50 hover:bg-slate-900/30 border border-slate-900 hover:border-slate-800 rounded-xl p-4 transition-all duration-300 cursor-pointer flex flex-col justify-between gap-3 relative overflow-hidden"
                  >
                    <div>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-[8px] bg-amber-500/10 text-amber-400 font-extrabold px-1.5 py-0.5 rounded tracking-wide uppercase">
                          {proj.mode}
                        </span>
                        <span className="text-[8px] bg-slate-800/80 text-slate-300 font-extrabold px-1.5 py-0.5 rounded tracking-wide uppercase">
                          {proj.user_persona}
                        </span>
                      </div>
                      <h3 className="text-xs font-bold text-slate-200 mt-2 truncate group-hover:text-amber-400 transition-colors">
                        {proj.title}
                      </h3>
                      <p className="text-[10px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                        {proj.description || "No project description."}
                      </p>
                    </div>

                    <div className="flex items-center justify-between border-t border-slate-950 pt-2.5 mt-1 text-[9px] text-slate-400">
                      <span className="hover:text-amber-400 transition-all font-semibold">Open Workspace →</span>
                      <button
                        onClick={(e) => handleDeleteProject(proj.id, e)}
                        className="text-slate-600 hover:text-rose-400 transition-all p-1"
                        title="Delete project"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* BYOK Settings Dialog Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 text-slate-100 p-6 rounded-xl shadow-2xl flex flex-col gap-4">
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">🔑 API Credentials Settings</h3>
              <p className="text-slate-400 text-xs mt-1">Provide a custom Anthropic key to pay for API usage directly and bypass global daily server thresholds.</p>
            </div>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Anthropic API Key</label>
                <input
                  type="password"
                  placeholder="sk-ant-..."
                  value={userApiKey}
                  onChange={(e) => setUserApiKey(e.target.value)}
                  className="w-full bg-[#03060d]/60 border border-slate-800 text-slate-200 text-sm placeholder:text-slate-700 rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-amber-500/40 transition-all font-mono"
                />
                <p className="text-[10px] text-slate-500">Stored locally in your browser's localStorage. Never sent to database tables or logged.</p>
              </div>
              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-slate-400 font-medium">Status:</span>
                {hasStoredKey ? (
                  <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full px-2.5 py-0.5 font-bold tracking-wide">Custom Key Configured</span>
                ) : (
                  <span className="bg-slate-800/80 text-slate-400 border border-slate-700/30 rounded-full px-2.5 py-0.5 font-bold tracking-wide">Server Default Fallback</span>
                )}
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={handleClearApiKey}
                className="border border-slate-800 bg-slate-950/20 text-slate-400 hover:bg-rose-950/20 hover:text-rose-400 rounded-lg text-xs px-3 py-2 transition-all"
              >
                Remove Key
              </button>
              <button
                onClick={handleSaveApiKey}
                className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold rounded-lg text-xs px-4 py-2 transition-all"
              >
                Save Settings
              </button>
              <button
                onClick={() => setIsSettingsOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-xs px-2 py-2"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
