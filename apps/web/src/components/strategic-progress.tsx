import React from "react";

interface StrategicProgressProps {
  status: "ROUTING" | "PLANNING" | "EXECUTING" | "AWAITING_CLARIFICATION" | "SYNTHESIZING" | "COMPLETED" | "FAILED" | string;
  stepsTaken: number;
  maxSteps: number;
  budgetSpent: number;
  failureReason?: string;
}

export const StrategicProgress: React.FC<StrategicProgressProps> = ({
  status,
  stepsTaken,
  maxSteps,
  budgetSpent,
  failureReason,
}) => {
  const phases = [
    {
      key: "ROUTING",
      label: "1. Intent Routing",
      desc: "Analyzing user inputs and validating completeness",
    },
    {
      key: "PLANNING",
      label: "2. Strategic Planning",
      desc: "Constructing task dependency DAG graphs",
    },
    {
      key: "EXECUTING",
      label: "3. Agent Research Loop",
      desc: "Querying MCP calculators, market signals & web research",
    },
    {
      key: "SYNTHESIZING",
      label: "4. Dossier Compilation",
      desc: "Formatting zero-jargon metrics & visual diagrams",
    },
  ];

  const getStatusIndex = (currentStatus: string) => {
    if (currentStatus === "ROUTING") return 0;
    if (currentStatus === "PLANNING") return 1;
    if (currentStatus === "EXECUTING" || currentStatus === "AWAITING_CLARIFICATION") return 2;
    if (currentStatus === "SYNTHESIZING") return 3;
    if (currentStatus === "COMPLETED") return 4;
    return -1;
  };

  const activeIndex = getStatusIndex(status);

  return (
    <div className="bg-[#0b0f19]/45 border border-slate-900 rounded-xl p-6 backdrop-blur-md flex flex-col gap-6 shadow-2xl relative overflow-hidden">
      {/* Decorative gradient glow */}
      <div className="absolute top-0 right-0 w-[150px] h-[150px] rounded-full bg-amber-500/5 blur-[50px] pointer-events-none" />

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-950 pb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              {status !== "COMPLETED" && status !== "FAILED" && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              )}
              <span className={`relative inline-flex rounded-full h-2 w-2 ${
                status === "FAILED" ? "bg-rose-500" : status === "COMPLETED" ? "bg-emerald-500" : "bg-amber-500"
              }`}></span>
            </span>
            Agent Intelligence Pipeline
          </h3>
          <p className="text-[11px] text-slate-400 mt-1">
            Real-time execution status of the business research orchestrator
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="bg-slate-950/45 px-2.5 py-1 rounded border border-slate-900 text-slate-300">
            Spend: <span className="text-amber-400 font-bold">${budgetSpent.toFixed(3)}</span>
          </div>
          <div className="bg-slate-950/45 px-2.5 py-1 rounded border border-slate-900 text-slate-300">
            Steps: <span className="text-amber-400 font-bold">{stepsTaken}/{maxSteps}</span>
          </div>
        </div>
      </div>

      {/* Progress Timeline */}
      <div className="space-y-4">
        {phases.map((phase, idx) => {
          let stepState: "pending" | "active" | "completed" | "failed" = "pending";
          
          if (idx < activeIndex) {
            stepState = "completed";
          } else if (idx === activeIndex) {
            stepState = status === "FAILED" ? "failed" : "active";
          }

          return (
            <div key={phase.key} className="flex gap-4 relative">
              {/* Connector line */}
              {idx < phases.length - 1 && (
                <div className={`absolute left-[11px] top-6 w-[2px] h-[calc(100%-12px)] ${
                  idx < activeIndex ? "bg-gradient-to-b from-emerald-500 to-emerald-600" : "bg-slate-950"
                }`} />
              )}

              {/* Status Indicator circle */}
              <div className={`w-6 h-6 rounded-full flex items-center justify-center border-2 text-[10px] font-bold shrink-0 z-10 transition-all duration-300 ${
                stepState === "completed" 
                  ? "bg-emerald-500/10 border-emerald-500 text-emerald-400" 
                  : stepState === "active"
                    ? "bg-amber-500/10 border-amber-500 text-amber-400 animate-pulse scale-105 shadow-[0_0_10px_rgba(245,158,11,0.2)]"
                    : stepState === "failed"
                      ? "bg-rose-500/10 border-rose-500 text-rose-400"
                      : "bg-[#03060d] border-slate-950 text-slate-500"
              }`}>
                {stepState === "completed" ? "✓" : idx + 1}
              </div>

              {/* Content description */}
              <div className="space-y-1">
                <h4 className={`text-xs font-bold transition-colors ${
                  stepState === "active" ? "text-amber-400" : stepState === "completed" ? "text-slate-200" : "text-slate-400"
                }`}>
                  {phase.label}
                </h4>
                <p className="text-[10px] text-slate-400 leading-normal">
                  {phase.desc}
                </p>
                {stepState === "active" && status === "AWAITING_CLARIFICATION" && (
                  <div className="mt-2 bg-amber-500/5 border border-amber-500/20 text-amber-300 text-[10px] p-2.5 rounded-md leading-relaxed animate-pulse">
                    ⏸️ Graph execution paused: Human clarification input required below.
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {status === "COMPLETED" && (
          <div className="bg-emerald-500/5 border border-emerald-500/20 text-emerald-400 text-[11px] p-3 rounded-lg flex items-center gap-2">
            🚀 <strong>Success:</strong> Strategic analysis dossier and business models compiled successfully!
          </div>
        )}

        {status === "FAILED" && (
          <div className="bg-rose-500/5 border border-rose-500/20 text-rose-400 text-[11px] p-3 rounded-lg flex flex-col gap-1">
            <strong>❌ Pipeline Execution Failed:</strong>
            <span className="text-[10px] text-slate-300 font-mono mt-0.5">{failureReason || "Maximum spending limits exceeded."}</span>
          </div>
        )}
      </div>
    </div>
  );
};
