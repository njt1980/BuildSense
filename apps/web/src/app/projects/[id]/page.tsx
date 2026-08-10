"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { ReportView } from "@/components/report-view";
import { StrategicProgress } from "@/components/strategic-progress";
import { useOrchestratorStream } from "@/lib/useOrchestratorStream";
import { ClarificationModal } from "@/components/clarification-modal";

// React Flow Imports
import { ReactFlow, Background, Controls, MiniMap } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// Custom Nodes styling mapping
const customNodeTypes = {
  MarketNode: ({ data }: any) => (
    <div className="bg-[#0b0f19] border-2 border-sky-500/40 text-slate-100 p-4 rounded-xl shadow-[0_0_15px_rgba(14,165,233,0.15)] max-w-xs font-sans">
      <div className="flex items-center justify-between border-b border-slate-900 pb-1.5 mb-2">
        <span className="text-[10px] uppercase font-extrabold text-sky-400 tracking-wider">📊 Market Signal</span>
        <span className="text-[9px] bg-sky-500/10 text-sky-400 px-1.5 py-0.5 rounded font-bold">Cited</span>
      </div>
      <p className="text-xs font-bold text-slate-200">{data.label}</p>
      <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">{data.details}</p>
    </div>
  ),
  EconomicsNode: ({ data }: any) => (
    <div className="bg-[#0b0f19] border-2 border-emerald-500/40 text-slate-100 p-4 rounded-xl shadow-[0_0_15px_rgba(16,185,129,0.15)] max-w-xs font-sans">
      <div className="flex items-center justify-between border-b border-slate-900 pb-1.5 mb-2">
        <span className="text-[10px] uppercase font-extrabold text-emerald-400 tracking-wider">💰 Financial Audit</span>
        <span className="text-[9px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded font-bold">Healthy</span>
      </div>
      <p className="text-xs font-bold text-slate-200">{data.label}</p>
      <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">{data.details}</p>
    </div>
  ),
  WorkflowNode: ({ data }: any) => (
    <div className="bg-[#0b0f19] border-2 border-orange-500/40 text-slate-100 p-4 rounded-xl shadow-[0_0_15px_rgba(249,115,22,0.15)] max-w-xs font-sans">
      <div className="flex items-center justify-between border-b border-slate-900 pb-1.5 mb-2">
        <span className="text-[10px] uppercase font-extrabold text-orange-400 tracking-wider">🕸️ Process Workflow</span>
        <span className="text-[9px] bg-orange-500/10 text-orange-400 px-1.5 py-0.5 rounded font-bold">Optimized</span>
      </div>
      <p className="text-xs font-bold text-slate-200">{data.label}</p>
      <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">{data.details}</p>
    </div>
  ),
  RecommendationNode: ({ data }: any) => (
    <div className="bg-[#0b0f19] border-2 border-amber-500/60 text-slate-100 p-4 rounded-xl shadow-[0_0_15px_rgba(245,158,11,0.25)] max-w-xs font-sans">
      <div className="flex items-center justify-between border-b border-slate-900 pb-1.5 mb-2">
        <span className="text-[10px] uppercase font-extrabold text-amber-400 tracking-wider">👑 Executive Plan</span>
        <span className="text-[9px] bg-amber-500/10 text-amber-400 px-1.5 py-0.5 rounded font-bold">Ready</span>
      </div>
      <p className="text-xs font-bold text-amber-200">{data.label}</p>
      <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">{data.details}</p>
    </div>
  ),
};

export default function ProjectWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuth();
  const projectId = params.id as string;

  const [project, setProject] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"report" | "graph" | "stepper" | "chat">("report");
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [isClarificationOpen, setIsClarificationOpen] = useState(false);

  // Onboarding Wizard states
  const [isOnboardingActive, setIsOnboardingActive] = useState(true);
  const [onboardingStep, setOnboardingStep] = useState<1 | 2>(1);
  const [wizardTitle, setWizardTitle] = useState("");
  const [wizardDescription, setWizardDescription] = useState("");
  const [wizardPersona, setWizardPersona] = useState("Solo Founder");

  // Audio Recorder states
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState("Auto-Detect");
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<any>(null);

  // Chat follow-up state
  const [chatMessageInput, setChatMessageInput] = useState("");

  const {
    activeSessionState,
    isOrchestratorLoopActive,
    executeOrchestratorRequest,
  } = useOrchestratorStream();

  // Load project details on mount
  useEffect(() => {
    if (!token || !projectId) return;
    
    const loadProjectDetails = async () => {
      try {
        const res = await fetch(`http://localhost:9000/api/v1/projects/${projectId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setProject(data);
          setWizardTitle(data.title || "");
          setWizardDescription(data.description || "");
          setWizardPersona(data.user_persona || "Solo Founder");
        }
      } catch (err) {
        console.error("Error loading project details:", err);
      }
    };

    const loadGraphDetails = async () => {
      try {
        const res = await fetch(`http://localhost:9000/api/v1/projects/${projectId}/graph`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setNodes(data.nodes || []);
          setEdges(data.edges || []);
        }
      } catch (err) {
        console.error("Error loading graph:", err);
      }
    };

    const checkExistingRun = async () => {
      try {
        const res = await fetch(`http://localhost:9000/api/v1/session/${projectId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const stateData = await res.json();
          if (stateData && stateData.messages && stateData.messages.length > 0) {
            setIsOnboardingActive(false);
            executeOrchestratorRequest({ session_id: projectId });
          }
        }
      } catch {}
    };

    loadProjectDetails();
    loadGraphDetails();
    checkExistingRun();
  }, [token, projectId, executeOrchestratorRequest]);

  // Sync state transitions & clarification modals
  useEffect(() => {
    if (activeSessionState?.status === "AWAITING_CLARIFICATION") {
      setIsClarificationOpen(true);
    } else {
      setIsClarificationOpen(false);
    }

    if (activeSessionState && activeSessionState.messages && activeSessionState.messages.length > 0) {
      setIsOnboardingActive(false);
    }

    if (activeSessionState?.status === "COMPLETED") {
      const refreshGraph = async () => {
        try {
          const res = await fetch(`http://localhost:9000/api/v1/projects/${projectId}/graph`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            setNodes(data.nodes || []);
            setEdges(data.edges || []);
          }
        } catch {}
      };
      refreshGraph();
    }
  }, [activeSessionState, projectId, token]);

  // Audio timer management
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setRecordingSeconds(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: "audio/webm" });
        await handleAudioTranscription(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access denied:", err);
      alert("Microphone access denied. Please grant permissions in your browser.");
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleAudioTranscription = async (blob: Blob) => {
    if (!token) return;
    setTranscribing(true);
    
    const maxRetries = 3;
    let attempt = 0;
    let success = false;
    let responseText = "";

    const formData = new FormData();
    formData.append("file", blob, "recording.webm");
    formData.append("language", selectedLanguage);

    while (attempt < maxRetries && !success) {
      try {
        const res = await fetch("http://localhost:9000/api/v1/transcribe", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData
        });

        if (res.ok) {
          const data = await res.json();
          responseText = data.transcript;
          success = true;
        } else {
          throw new Error(`HTTP error ${res.status}`);
        }
      } catch (err) {
        attempt++;
        console.warn(`Transcription upload attempt ${attempt} failed:`, err);
        if (attempt >= maxRetries) {
          alert("Network connection error: failed to upload audio. Please try again.");
        } else {
          // Exponential backoff: 2s, 4s
          await new Promise((resolve) => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
        }
      }
    }

    if (success) {
      if (isOnboardingActive) {
        setWizardDescription(responseText);
      } else {
        setChatMessageInput(responseText);
      }
    }
    setTranscribing(false);
  };

  const handleStartOrchestration = async () => {
    if (!token || isOrchestratorLoopActive) return;

    // Start discovery execution
    executeOrchestratorRequest({
      prompt: wizardDescription,
      mode: project.mode,
      motivation: project.motivation,
      user_persona: wizardPersona,
      session_id: projectId
    });
    
    setIsOnboardingActive(false);
    setActiveTab("stepper");
  };

  const handleClarificationSubmit = (answers: Record<string, string>) => {
    setIsClarificationOpen(false);
    executeOrchestratorRequest({
      session_id: projectId,
      clarification_responses: answers,
    });
  };

  const handleSendChatMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessageInput.trim() || isOrchestratorLoopActive) return;

    executeOrchestratorRequest({
      prompt: chatMessageInput,
      session_id: projectId
    });
    setChatMessageInput("");
  };

  const handleExportSummary = () => {
    if (!project) return;
    
    const quickInsights = activeSessionState?.metadata?.quick_insights as string || "No insights synthesized yet.";
    const deepDive = activeSessionState?.metadata?.deep_dive as string || "No deep dive dossier compiled yet.";
    
    const fileContent = `# Executive Summary: ${project.title}\n\n` +
      `**Mode:** ${project.mode} | **Motivation:** ${project.motivation} | **Persona:** ${project.user_persona}\n\n` +
      `---\n\n` +
      `${quickInsights}\n\n` +
      `---\n\n` +
      `${deepDive}\n\n` +
      `*Generated dynamically by BuildSense Multi-Tenant RAG engine on ${new Date().toLocaleDateString()}*`;
      
    const blob = new Blob([fileContent], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${project.title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}_executive_report.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!project) {
    return (
      <div className="min-h-screen bg-[#03060d] text-slate-100 flex flex-col items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-t-amber-500 border-slate-900 animate-spin" />
          <p className="text-xs text-slate-400 font-medium">Loading project workspace context...</p>
        </div>
      </div>
    );
  }

  // --- Render Wizard Onboarding ---
  if (isOnboardingActive) {
    return (
      <main className="min-h-screen bg-[#03060d] text-slate-100 p-4 md:p-8 flex flex-col items-center justify-center font-sans select-none relative overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-amber-500/5 blur-[130px] pointer-events-none" />
        
        <div className="w-full max-w-xl bg-[#0b0f19]/45 border border-slate-900 rounded-2xl p-8 backdrop-blur-md shadow-2xl relative">
          
          {/* Header */}
          <div className="border-b border-slate-950 pb-5 mb-6 text-center">
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-amber-400 to-orange-500">
              Welcome to {wizardTitle || "Project Workspace"}
            </h1>
            <p className="text-xs text-slate-400 mt-1.5">
              Let&rsquo;s configure your operational discovery settings before kicking off research.
            </p>
          </div>

          {/* Steps Breadcrumbs */}
          <div className="flex items-center justify-center gap-3 mb-8 text-xs font-semibold">
            <span className={`px-2.5 py-1 rounded-md border ${
              onboardingStep === 1 ? "bg-amber-500/10 border-amber-500/20 text-amber-400" : "bg-slate-950/20 border-slate-900 text-slate-500"
            }`}>
              1. Profile Verification
            </span>
            <span className="text-slate-700">➔</span>
            <span className={`px-2.5 py-1 rounded-md border ${
              onboardingStep === 2 ? "bg-amber-500/10 border-amber-500/20 text-amber-400" : "bg-slate-950/20 border-slate-900 text-slate-500"
            }`}>
              2. Day in the Life Capture
            </span>
          </div>

          {/* Step 1 Content: Profile Verification */}
          {onboardingStep === 1 && (
            <div className="space-y-5">
              <div className="space-y-2">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Workspace Title</label>
                <input
                  type="text"
                  value={wizardTitle}
                  onChange={(e) => setWizardTitle(e.target.value)}
                  className="w-full bg-[#03060d]/60 border border-slate-800 text-slate-200 text-xs rounded-lg p-2.5 focus:outline-none"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">User Persona Focus</label>
                <select
                  value={wizardPersona}
                  onChange={(e) => setWizardPersona(e.target.value)}
                  className="w-full bg-[#03060d]/60 border border-slate-800 text-slate-200 text-xs rounded-lg p-2.5 focus:outline-none"
                >
                  <option value="Solo Founder">🚀 Solo Founder (Speed & Tech Moats)</option>
                  <option value="Small Business Operator">🌾 Small Business Operator (Direct ROI, Jargon-free)</option>
                  <option value="Enterprise PM">🏢 Enterprise PM (Compliance & Scale)</option>
                  <option value="Student">🎓 Student (Technical Learning Path)</option>
                </select>
              </div>

              <Button
                onClick={() => setOnboardingStep(2)}
                className="w-full bg-slate-950/80 hover:bg-slate-900 text-slate-300 font-extrabold py-3 rounded-lg border border-slate-900 text-xs mt-4"
              >
                Next: Intake Setup →
              </Button>
            </div>
          )}

          {/* Step 2 Content: Operational Intake Capture */}
          {onboardingStep === 2 && (
            <div className="space-y-5">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Spoken Language</label>
                  <select
                    value={selectedLanguage}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                    className="bg-[#03060d]/60 border border-slate-800 text-slate-400 text-[10px] rounded px-2 py-1 focus:outline-none"
                  >
                    <option value="Auto-Detect">Auto-Detect</option>
                    <option value="English">English</option>
                    <option value="Hindi">Hindi</option>
                    <option value="Kannada">Kannada</option>
                    <option value="Tamil">Tamil</option>
                    <option value="Malayalam">Malayalam</option>
                  </select>
                </div>

                {/* Recorder Control Area */}
                <div className="bg-[#03060d]/65 border border-slate-900 rounded-xl p-4 flex flex-col items-center justify-center gap-3">
                  <p className="text-[10px] text-slate-400 text-center">
                    Describe a typical <strong>&ldquo;Day in the life&rdquo;</strong> of your operations. Focus on manual steps and software tools.
                  </p>
                  
                  <div className="flex items-center gap-3">
                    {!isRecording ? (
                      <button
                        type="button"
                        onClick={handleStartRecording}
                        className="bg-amber-500 hover:bg-amber-600 text-slate-950 text-xs font-bold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all"
                      >
                        🎙️ Start Voice Recording
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={handleStopRecording}
                        className="bg-rose-600 hover:bg-rose-700 text-slate-100 text-xs font-bold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all animate-pulse"
                      >
                        ⏹️ Stop Recording ({recordingSeconds}s)
                      </button>
                    )}
                  </div>

                  {transcribing && (
                    <div className="flex items-center gap-2 text-[10px] text-amber-400">
                      <div className="w-3 h-3 rounded-full border border-t-amber-500 border-slate-900 animate-spin" />
                      Converting regional audio to English...
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Review Transcript / Operations Description</label>
                <textarea
                  rows={4}
                  value={wizardDescription}
                  onChange={(e) => setWizardDescription(e.target.value)}
                  placeholder="Review audio transcript or type operational details manually..."
                  className="w-full bg-[#03060d]/30 border border-slate-800 text-slate-200 text-xs rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-amber-500/40 resize-none"
                />
              </div>

              <div className="flex items-center gap-3 pt-3">
                <Button
                  variant="outline"
                  onClick={() => setOnboardingStep(1)}
                  className="border-slate-800 bg-[#0b0f19]/35 hover:bg-slate-900/40 text-slate-400 rounded-lg text-xs px-4 py-3"
                >
                  ← Back
                </Button>
                <Button
                  onClick={handleStartOrchestration}
                  disabled={!wizardDescription.trim() || transcribing}
                  className="flex-grow bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-slate-950 font-extrabold py-3 rounded-lg shadow-lg text-xs"
                >
                  🚀 Run Discovery Analysis
                </Button>
              </div>
            </div>
          )}
        </div>
      </main>
    );
  }

  // --- Render Live Dashboard Workspace ---
  return (
    <main className="min-h-screen bg-[#03060d] text-slate-100 p-4 md:p-8 flex flex-col items-center justify-start gap-6 font-sans select-none relative overflow-hidden">
      {/* Ambient background glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-to-br from-amber-500/5 to-orange-500/0 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-to-tr from-emerald-500/5 to-teal-500/0 blur-[130px] pointer-events-none" />

      {/* Workspace Header */}
      <header className="w-full max-w-6xl flex flex-col md:flex-row items-center justify-between gap-4 border-b border-slate-900/60 pb-5 mt-2 relative z-10">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <button onClick={() => router.push("/")} className="hover:text-amber-400 font-semibold transition-all">← Dashboard</button>
            <span>/</span>
            <span>Projects</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500 mt-1">
            {project.title}
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Role Persona: <span className="text-amber-300 font-bold">{wizardPersona}</span> | Mode: <span className="text-amber-300 font-bold">{project.mode}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={handleExportSummary}
            disabled={!activeSessionState || activeSessionState.status !== "COMPLETED"}
            className="border-slate-800 bg-[#0b0f19]/35 hover:bg-slate-900/40 text-slate-300 rounded-lg text-xs font-extrabold px-4 py-2 transition-all flex items-center gap-1.5"
          >
            📥 Export to Executive Summary
          </Button>

          <Button
            onClick={handleRunAnalysis}
            disabled={isOrchestratorLoopActive}
            className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-slate-950 font-extrabold py-2 px-4 rounded-lg shadow-lg hover:shadow-xl transition-all text-xs"
          >
            {isOrchestratorLoopActive ? "Evaluating..." : "Run Analysis"}
          </Button>
        </div>
      </header>

      {/* Tab Selectors */}
      <div className="w-full max-w-6xl flex items-center justify-start border-b border-slate-900 relative z-10">
        <button
          onClick={() => setActiveTab("report")}
          className={`text-xs font-bold py-3.5 px-6 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "report" ? "border-amber-500 text-amber-400" : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          📄 Executive Report
        </button>
        <button
          onClick={() => setActiveTab("graph")}
          className={`text-xs font-bold py-3.5 px-6 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "graph" ? "border-amber-500 text-amber-400" : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          🕸️ Interactive Graph / Flowchart View
        </button>
        <button
          onClick={() => setActiveTab("stepper")}
          className={`text-xs font-bold py-3.5 px-6 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "stepper" ? "border-amber-500 text-amber-400" : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          ⚙️ Pipeline Stepper
        </button>
        <button
          onClick={() => setActiveTab("chat")}
          className={`text-xs font-bold py-3.5 px-6 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "chat" ? "border-amber-500 text-amber-400" : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          💬 Dialogue Panel
        </button>
      </div>

      {/* Tab Panels */}
      <section className="w-full max-w-6xl flex-grow grid grid-cols-1 gap-6 relative z-10 min-h-[500px]">
        {activeTab === "report" && (
          <div className="bg-[#0b0f19]/20 border border-slate-900/60 rounded-xl p-6 shadow-xl flex flex-col gap-6">
            {activeSessionState && activeSessionState.status === "COMPLETED" ? (
              <ReportView sessionState={activeSessionState} />
            ) : (
              <div className="flex flex-col items-center justify-center p-20 text-center gap-4 border border-dashed border-slate-800 rounded-xl">
                <p className="text-sm text-slate-400">No synthesized report dossier exists yet.</p>
                <p className="text-xs text-slate-600 leading-normal max-w-md">Click &ldquo;Run Analysis&rdquo; in the header to start execution.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === "graph" && (
          <div className="bg-[#03060d]/80 border border-slate-900/60 rounded-xl overflow-hidden shadow-2xl relative h-[550px] w-full">
            {nodes.length > 0 ? (
              <ReactFlow nodes={nodes} edges={edges} nodeTypes={customNodeTypes} fitView className="font-sans">
                <Background color="#334155" gap={16} size={1} />
                <Controls className="bg-slate-900 border border-slate-800 text-slate-100 rounded shadow-md fill-slate-100" />
                <MiniMap className="bg-slate-950 border border-slate-900 text-slate-100 rounded" />
              </ReactFlow>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center gap-4 p-8">
                <p className="text-sm text-slate-400">No workflow visual diagram generated yet.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === "stepper" && (
          <div className="max-w-xl mx-auto w-full">
            <StrategicProgress
              status={activeSessionState?.status || "ROUTING"}
              stepsTaken={activeSessionState?.steps_taken || 0}
              maxSteps={activeSessionState?.max_steps || 6}
              budgetSpent={activeSessionState?.budget_spent_usd || 0.0}
              failureReason={activeSessionState?.metadata?.failure_reason as string}
            />
          </div>
        )}

        {activeTab === "chat" && (
          <div className="bg-[#0b0f19]/35 border border-slate-900 rounded-xl p-6 shadow-xl flex flex-col gap-4 h-[550px]">
            <div className="flex-grow overflow-y-auto pr-1 space-y-3.5">
              {activeSessionState?.messages?.filter((msg: any) => msg.role !== "system" && msg.role !== "tool").map((msg: any, idx: number) => {
                const isUser = msg.role === "user";
                return (
                  <div key={idx} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[75%] rounded-xl px-4 py-2.5 text-xs leading-relaxed border ${
                      isUser
                        ? "bg-slate-950/60 border-slate-800 text-slate-200"
                        : "bg-amber-500/10 border-amber-500/20 text-amber-300"
                    }`}>
                      <p className="font-bold text-[9px] uppercase tracking-wider text-slate-500 mb-1">
                        {isUser ? "User Input" : msg.name || "BuildSense Intelligence"}
                      </p>
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                );
              })}
            </div>

            <form onSubmit={handleSendChatMessage} className="flex flex-col gap-2.5 border-t border-slate-950 pt-4">
              <div className="flex items-center justify-between gap-3 bg-[#03060d]/65 border border-slate-900 rounded-lg px-3 py-1.5">
                <div className="flex items-center gap-2">
                  <select
                    value={selectedLanguage}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                    className="bg-transparent text-slate-400 text-[10px] focus:outline-none focus:ring-0 font-medium"
                  >
                    <option value="Auto-Detect">Auto-Detect</option>
                    <option value="English">English</option>
                    <option value="Hindi">Hindi</option>
                    <option value="Kannada">Kannada</option>
                    <option value="Tamil">Tamil</option>
                    <option value="Malayalam">Malayalam</option>
                  </select>

                  <span className="text-slate-800">|</span>

                  {!isRecording ? (
                    <button
                      type="button"
                      onClick={handleStartRecording}
                      className="text-slate-400 hover:text-amber-400 transition-colors text-xs flex items-center gap-1.5"
                    >
                      🎤 Record Audio
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleStopRecording}
                      className="text-rose-400 font-bold transition-colors text-xs flex items-center gap-1.5 animate-pulse"
                    >
                      ⏹️ Stop ({recordingSeconds}s)
                    </button>
                  )}
                </div>

                {transcribing && (
                  <span className="text-[10px] text-amber-400 animate-pulse">Transcribing...</span>
                )}
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatMessageInput}
                  onChange={(e) => setChatMessageInput(e.target.value)}
                  placeholder="Continue dialogue, clarify operations, or submit evidence..."
                  className="flex-grow bg-[#03060d]/60 border border-slate-800 text-slate-200 text-xs rounded-lg px-4 py-3 focus:outline-none"
                />
                <Button
                  type="submit"
                  disabled={!chatMessageInput.trim() || isOrchestratorLoopActive}
                  className="bg-gradient-to-r from-amber-500 to-orange-600 text-slate-950 font-bold text-xs px-5 rounded-lg"
                >
                  Send
                </Button>
              </div>
            </form>
          </div>
        )}
      </section>

      {/* HITL Clarification Modal */}
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
