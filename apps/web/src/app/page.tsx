"use client";
 
import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
 
export default function Home() {
  const router = useRouter();
  const { user, token, signOut } = useAuth();
 
  const [prompt, setPrompt] = useState<string>("");
  const [uploadedFile, setUploadedFile] = useState<{ name: string; content: string } | null>(null);
 
  // Voice Recording States
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [transcribing, setTranscribing] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("Auto-Detect");
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
 
  // Companies Layer States
  const [companies, setCompanies] = useState<any[]>([]);
  const [activeCompany, setActiveCompany] = useState<any | null>(null);
  const [loadingCompanies, setLoadingCompanies] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);
 
  // Onboarding Modal Form States
  const [newCompanyName, setNewCompanyName] = useState("");
  const [newCompanyIndustry, setNewCompanyIndustry] = useState("General Business");
  const [newCompanyTools, setNewCompanyTools] = useState("");
  const [creatingCompany, setCreatingCompany] = useState(false);
 
  // Projects list state
  const [projects, setProjects] = useState<any[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);
  const [errorText, setErrorText] = useState("");
 
  // BYOK States
  const [userApiKey, setUserApiKey] = useState<string>("");
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [hasStoredKey, setHasStoredKey] = useState<boolean>(false);
 
  // Fetch companies on mount/token ready
  useEffect(() => {
    if (!token) return;
    const fetchCompanies = async () => {
      setLoadingCompanies(true);
      try {
        const res = await fetch("http://localhost:9000/api/v1/companies", {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setCompanies(data || []);
          if (data && data.length > 0) {
            setActiveCompany(data[0]);
            setShowOnboarding(false);
          } else {
            setShowOnboarding(true);
          }
        }
      } catch (err) {
        console.error("Error fetching companies:", err);
      } finally {
        setLoadingCompanies(false);
      }
    };
    fetchCompanies();
  }, [token]);
 
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
 
  // Handle recording timer
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
          await new Promise((resolve) => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
        }
      }
    }
 
    if (success) {
      setPrompt(responseText);
    }
    setTranscribing(false);
  };
 
  // Load BYOK key from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("buildsense_user_api_key") || "";
      setUserApiKey(stored);
      setHasStoredKey(!!stored);
    }
  }, []);
 
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
          raw_input_text_or_audio: prompt,
          industry_vertical: activeCompany?.industry || "General Business",
          user_persona: "Solo Founder",
          file_name: uploadedFile?.name,
          file_content: uploadedFile?.content,
          company_id: activeCompany?.id
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
 
  const handleCreateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCompanyName.trim() || creatingCompany || !token) return;
 
    setCreatingCompany(true);
    try {
      const res = await fetch("http://localhost:9000/api/v1/companies", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          name: newCompanyName,
          industry: newCompanyIndustry,
          core_tools: newCompanyTools
        })
      });
      if (res.ok) {
        const data = await res.json();
        const createdCompany = {
          id: data.company_id,
          name: newCompanyName,
          industry: newCompanyIndustry,
          core_tools: newCompanyTools
        };
        setCompanies([createdCompany, ...companies]);
        setActiveCompany(createdCompany);
        setShowOnboarding(false);
      } else {
        alert("Failed to establish business baseline. Please try again.");
      }
    } catch (err) {
      console.error("Error creating company:", err);
      alert("Network error. Please try again.");
    } finally {
      setCreatingCompany(false);
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
 
  const getStarterChips = (industry: string) => {
    switch (industry) {
      case "Logistics & Fleet":
        return ["Manual dispatch routing", "Fuel invoice auditing", "Driver log compliance checks"];
      case "Manufacturing":
        return ["Machine downtime reports", "Raw material QC checklists", "Production schedule adjustments"];
      case "Wholesale & Distribution":
        return ["Purchase order processing", "Inventory count reconciliation", "Supplier invoicing cycles"];
      default:
        return ["Manual data entry", "Approval delays", "Client onboarding paperwork"];
    }
  };
 
  const handleChipClick = (chipText: string) => {
    setPrompt(chipText);
  };
 
  return (
    <main className="min-h-screen bg-[#03060d] text-slate-100 p-4 md:p-8 flex flex-col items-center justify-start gap-8 font-sans selection:bg-amber-500/30 selection:text-amber-200 relative overflow-hidden">
      
      {/* Ambient background glows */}
      <div className="absolute top-[-10%] left-[-15%] w-[60%] h-[60%] rounded-full bg-gradient-to-br from-amber-500/5 to-orange-500/0 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-15%] w-[60%] h-[60%] rounded-full bg-gradient-to-tr from-emerald-500/5 to-teal-500/0 blur-[130px] pointer-events-none" />
 
      {/* Dashboard Header */}
      <header className="w-full max-w-5xl text-center md:text-left flex flex-col md:flex-row items-center justify-between gap-6 border-b border-slate-900/60 pb-6 mt-4 relative z-10">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500">
            BuildSense
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Agentic Process Discovery & SMB Automation Engine
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
            <span className="text-[11px] text-slate-300 font-medium tracking-wide">Enterprise Core Online</span>
          </div>
        </div>
      </header>
 
      {/* Centered Horizontal Hero & Workspaces Layout */}
      <section className="w-full max-w-4xl flex flex-col gap-8 relative z-10">
        
        {/* Top: Wide, Centered Process Intake Form */}
        <div className="bg-[#0b0f19]/25 shadow-2xl rounded-2xl border border-slate-900/50 backdrop-blur-md p-6 md:p-8 flex flex-col gap-6 w-full">
          
          {/* Active Company Status Panel */}
          {activeCompany && (
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-900/60 pb-5">
              <div className="flex items-center gap-2">
                <span className="text-lg">🏢</span>
                <div>
                  <h3 className="text-sm font-bold text-slate-200">{activeCompany.name}</h3>
                  <p className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">{activeCompany.industry} Sector</p>
                </div>
              </div>
              
              <div className="text-[10px] text-slate-400 bg-slate-950/40 border border-slate-800/60 rounded-lg px-3 py-1.5">
                <span className="font-semibold text-slate-300">Stack Baseline:</span> {activeCompany.core_tools}
              </div>
            </div>
          )}
 
          <form onSubmit={handleStartPipeline} className="space-y-6">
            
            {/* Voice Capture Section */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Voice Intake Dictation</label>
                <div className="flex items-center gap-1.5 text-[9px] text-slate-500">
                  <span>🌐 Regional audio translation active</span>
                </div>
              </div>
 
              <div className="bg-[#03060d]/50 border border-slate-900 rounded-xl p-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <select
                    value={selectedLanguage}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                    className="bg-[#0b0f19] border border-slate-850 text-slate-400 text-[10px] rounded-lg px-2.5 py-1.5 focus:outline-none"
                  >
                    <option value="Auto-Detect">Auto-Detect Language</option>
                    <option value="English">English</option>
                    <option value="Hindi">Hindi</option>
                    <option value="Kannada">Kannada</option>
                    <option value="Tamil">Tamil</option>
                    <option value="Malayalam">Malayalam</option>
                  </select>
                </div>
 
                {!isRecording ? (
                  <button
                    type="button"
                    onClick={handleStartRecording}
                    className="bg-amber-500 hover:bg-amber-600 text-slate-950 text-xs font-extrabold px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shadow-md"
                  >
                    🎙️ Mic On
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleStopRecording}
                    className="bg-rose-600 hover:bg-rose-700 text-slate-100 text-xs font-extrabold px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 transition-all animate-pulse"
                  >
                    ⏹️ Stop ({recordingSeconds}s)
                  </button>
                )}
              </div>
              {transcribing && (
                <p className="text-[10px] text-amber-400 animate-pulse flex items-center gap-1.5 mt-1 justify-center">
                  <span className="w-2.5 h-2.5 rounded-full border border-t-amber-500 animate-spin inline-block"></span>
                  Transcribing regional audio to English...
                </p>
              )}
            </div>
 
            {/* Process Description Text Area */}
            <div className="space-y-2 border-t border-slate-900/60 pt-4">
              <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest block">
                What process is slowing {activeCompany?.name || "your business"} down today?
              </label>
              
              <textarea
                rows={4}
                placeholder={`Describe the bottleneck slowing down ${activeCompany?.name || "your organization"}...`}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full bg-[#03060d]/40 border border-slate-800 text-slate-200 text-xs rounded-xl p-4 focus:outline-none focus:ring-1 focus:ring-amber-500/40 resize-none shadow-inner leading-relaxed"
                required
              />
 
              {/* Starter Chips */}
              {activeCompany && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {getStarterChips(activeCompany.industry).map((chip, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleChipClick(chip)}
                      className="text-[10px] bg-slate-950/60 hover:bg-amber-500/10 border border-slate-900 hover:border-amber-500/30 text-slate-400 hover:text-amber-400 font-medium px-3 py-1.5 rounded-full transition-all duration-200"
                    >
                      💡 {chip}
                    </button>
                  ))}
                </div>
              )}
            </div>
 
            {/* Attachment option */}
            <div className="space-y-2 border-t border-slate-900/60 pt-4">
              <div className="flex items-center justify-between text-[10px] text-slate-500">
                <span>Context Document (Optional)</span>
                <input
                  type="file"
                  accept=".txt,.pdf,.csv,.md"
                  onChange={handleFileUpload}
                  id="doc-upload"
                  className="hidden"
                />
                <label htmlFor="doc-upload" className="cursor-pointer hover:text-amber-400 transition-colors underline font-medium">
                  {uploadedFile ? "Change file" : "Attach SOP/file"}
                </label>
              </div>
              {uploadedFile && (
                <div className="flex items-center justify-between bg-[#03060d]/80 border border-slate-850 px-3 py-2 rounded-lg text-[11px]">
                  <span className="truncate max-w-[200px] text-slate-300">📎 {uploadedFile.name}</span>
                  <button type="button" onClick={() => setUploadedFile(null)} className="text-rose-400 hover:text-rose-300 text-xs">✕</button>
                </div>
              )}
            </div>
 
            <Button
              type="submit"
              disabled={!prompt.trim() || creatingProject}
              className="w-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 hover:from-amber-600 hover:via-orange-600 hover:to-rose-600 text-slate-950 font-extrabold py-3.5 rounded-xl shadow-xl transition-all tracking-wide text-xs"
            >
              {creatingProject ? "Scaffolding Workspace..." : "🚀 Start Business Discovery"}
            </Button>
 
            {errorText && (
              <p className="text-rose-400 text-[10px] bg-rose-950/15 border border-rose-900/35 p-2.5 rounded-lg text-center font-medium">{errorText}</p>
            )}
          </form>
        </div>
 
        {/* Bottom Section: Horizontal Grid of Active Workspaces */}
        <div className="bg-[#0b0f19]/25 shadow-2xl rounded-2xl border border-slate-900/50 p-6 md:p-8 backdrop-blur-md flex flex-col gap-5 w-full">
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
            <div className="text-center p-16 border border-dashed border-slate-800/60 rounded-2xl">
              <p className="text-xs text-slate-500 italic">No project workspaces created yet.</p>
              <p className="text-[10px] text-slate-600 mt-1 leading-normal max-w-sm mx-auto">Fill out the intake form above to start your first process optimization discovery run.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.map((proj) => (
                <div
                  key={proj.id}
                  onClick={() => router.push(`/projects/${proj.id}`)}
                  className="group bg-[#03060d]/50 hover:bg-slate-900/30 border border-slate-900 hover:border-slate-800 rounded-xl p-4 transition-all duration-300 cursor-pointer flex flex-col justify-between gap-4 relative overflow-hidden"
                >
                  <div>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[8px] bg-amber-500/10 text-amber-400 font-extrabold px-1.5 py-0.5 rounded tracking-wide uppercase">
                        {proj.mode}
                      </span>
                    </div>
                    <h3 className="text-xs font-bold text-slate-200 mt-2.5 truncate group-hover:text-amber-400 transition-colors">
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
      </section>
 
      {/* Conversational Onboarding Baseline Modal */}
      {showOnboarding && !loadingCompanies && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="w-full max-w-md bg-[#0b101c]/95 border border-slate-800 text-slate-100 p-6 md:p-8 rounded-2xl shadow-2xl flex flex-col gap-5 relative overflow-hidden">
            <div className="absolute top-[-20%] left-[-20%] w-[55%] h-[55%] rounded-full bg-gradient-to-br from-amber-500/10 to-orange-500/0 blur-[80px] pointer-events-none" />
            
            <div className="text-center space-y-1">
              <h3 className="text-xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500">
                Let&apos;s establish your business baseline.
              </h3>
              <p className="text-slate-400 text-xs leading-relaxed">
                Connect your workspace context with enterprise reasoning to skip setup questions.
              </p>
            </div>
 
            <form onSubmit={handleCreateCompany} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest block">
                  Business Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Acme Fleet Services"
                  value={newCompanyName}
                  onChange={(e) => setNewCompanyName(e.target.value)}
                  className="w-full bg-[#03060d]/80 border border-slate-800 text-slate-200 text-xs placeholder:text-slate-700 rounded-xl p-3 focus:outline-none focus:ring-1 focus:ring-amber-500/40 transition-all font-sans"
                  required
                />
              </div>
 
              <div className="space-y-1.5">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest block">
                  Industry Vertical
                </label>
                <select
                  value={newCompanyIndustry}
                  onChange={(e) => setNewCompanyIndustry(e.target.value)}
                  className="w-full bg-[#03060d]/80 border border-slate-800 text-slate-200 text-xs rounded-xl p-3 focus:outline-none focus:ring-1 focus:ring-amber-500/40"
                >
                  <option value="Logistics & Fleet">🚚 Logistics & Fleet</option>
                  <option value="Manufacturing">🏭 Manufacturing</option>
                  <option value="Wholesale & Distribution">📦 Wholesale & Distribution</option>
                  <option value="General Business">💼 General Business / Other</option>
                </select>
              </div>
 
              <div className="space-y-1.5">
                <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest block">
                  Core Tools Used
                </label>
                <input
                  type="text"
                  placeholder="e.g. Excel, QuickBooks, SAP (comma-separated)"
                  value={newCompanyTools}
                  onChange={(e) => setNewCompanyTools(e.target.value)}
                  className="w-full bg-[#03060d]/80 border border-slate-800 text-slate-200 text-xs placeholder:text-slate-700 rounded-xl p-3 focus:outline-none focus:ring-1 focus:ring-amber-500/40 transition-all font-sans"
                  required
                />
              </div>
 
              <Button
                type="submit"
                disabled={creatingCompany || !newCompanyName.trim()}
                className="w-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 hover:from-amber-600 hover:via-orange-600 hover:to-rose-600 text-slate-950 font-extrabold py-3.5 rounded-xl shadow-xl transition-all tracking-wide text-xs"
              >
                {creatingCompany ? "Establishing Baseline..." : "Setup Business Baseline"}
              </Button>
            </form>
          </div>
        </div>
      )}
 
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
                <p className="text-[10px] text-slate-500">Stored locally in your browser&apos;s localStorage. Never sent to database tables or logged.</p>
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
