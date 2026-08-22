"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ReportViewProps {
  sessionState: any;
}

export function ReportView({ sessionState }: ReportViewProps) {
  const quickInsights = (sessionState.metadata.quick_insights as string) || "No quick insights generated.";
  const deepDive = (sessionState.metadata.deep_dive as string) || "No deep dive dossier compiled.";
  const evidenceLedger = sessionState.evidence_ledger || [];

  // Gate access to the Executive / Deep view based on backend synthesis completion.
  const canShowExecutive = Boolean(
    sessionState?.metadata?.as_is_workflow || sessionState?.metadata?.technology_neutral_recommendations
  );

  const [activeTab, setActiveTab] = React.useState<string>(canShowExecutive ? "deep" : "quick");

  React.useEffect(() => {
    // When backend state changes, enforce gating: if synthesis not ready, force Quick/Dialogue.
    const allow = Boolean(
      sessionState?.metadata?.as_is_workflow || sessionState?.metadata?.technology_neutral_recommendations
    );
    if (!allow && activeTab === "deep") {
      setActiveTab("quick");
    }
    // If the backend just completed synthesis, keep user's choice but allow switching to deep.
    // No automatic switch to deep to avoid surprising the user.
  }, [sessionState?.metadata, activeTab]);

  return (
    <Card className="w-full bg-[#0b0f19]/45 border border-slate-900/80 backdrop-blur-md text-slate-100 rounded-xl shadow-2xl overflow-hidden">
      <CardHeader className="border-b border-slate-900/60 bg-slate-950/20 py-5 px-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-teal-500">
              📊 Execution Dossier
            </CardTitle>
            <CardDescription className="text-slate-400 mt-1">
              Session ID: <span className="font-mono text-xs text-slate-500">{sessionState.session_id}</span>
              {sessionState.business_vertical && (
                <>
                  <span className="text-slate-600 mx-2">|</span>
                  Vertical Focus: <span className="text-amber-400 font-bold font-mono text-[11px]">{sessionState.business_vertical}</span>
                </>
              )}
            </CardDescription>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="bg-[#03060d]/80 border border-slate-900/60 rounded-lg px-3 py-1.5 text-center">
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Spend (USD)</p>
              <p className="font-mono text-sm font-semibold text-emerald-400">
                ${sessionState.budget_spent_usd.toFixed(3)}
                <span className="text-slate-600 text-xs"> / ${sessionState.max_budget_usd.toFixed(2)}</span>
              </p>
            </div>
            <div className="bg-[#03060d]/80 border border-slate-900/60 rounded-lg px-3 py-1.5 text-center">
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Steps</p>
              <p className="font-mono text-sm font-semibold text-teal-400">
                {sessionState.steps_taken}
                <span className="text-slate-600 text-xs"> / {sessionState.max_steps}</span>
              </p>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-6">
        <Tabs value={activeTab} onValueChange={(v) => {
          if (v === "deep" && !canShowExecutive) {
            // Prevent transition until backend signals completion
            setActiveTab("quick");
            return;
          }
          setActiveTab(v);
        }} className="w-full">
          <TabsList className="bg-[#03060d]/80 border border-slate-900/60 rounded-lg p-1 w-full grid grid-cols-2 max-w-[400px] mb-6">
            <TabsTrigger
              value="quick"
              className="rounded-md font-medium text-xs data-[active]:bg-slate-800/80 data-[active]:text-amber-400 data-[active]:border data-[active]:border-amber-500/20 text-slate-400 py-2 transition-all"
            >
              ⚡ Quick Insights
            </TabsTrigger>
            <TabsTrigger
              value="deep"
              className="rounded-md font-medium text-xs data-[active]:bg-slate-800/80 data-[active]:text-amber-400 data-[active]:border data-[active]:border-amber-500/20 text-slate-400 py-2 transition-all"
            >
              🔬 Deep Dive
            </TabsTrigger>
          </TabsList>

          <TabsContent value="quick" className="space-y-4 outline-none focus:ring-0">
            <div className="bg-[#03060d]/30 border border-slate-900/60 rounded-xl p-5 shadow-inner">
              <div className="prose prose-invert max-w-none text-slate-300 whitespace-pre-wrap leading-relaxed">
                <ReactMarkdown>{quickInsights}</ReactMarkdown>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="deep" className="space-y-4 outline-none focus:ring-0">
            <div className="bg-[#03060d]/30 border border-slate-900/60 rounded-xl p-5 shadow-inner">
              <div className="prose prose-invert max-w-none text-slate-300 whitespace-pre-wrap leading-relaxed">
                <ReactMarkdown>{deepDive}</ReactMarkdown>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Evidence Ladder Ledger Audit Panel */}
        {!canShowExecutive && (
          <div className="mt-4 text-xs text-slate-400">
            Executive report is not yet available — gathering more information. Continue the
            conversation in the Dialogue panel until analysis completes.
          </div>
        )}
        {evidenceLedger.length > 0 && (
          <div className="mt-8 border-t border-slate-900/60 pt-6">
            <h3 className="text-sm font-bold text-slate-200 mb-3 flex items-center gap-2">
              ⚖️ Evidence Ladder Audit Log
            </h3>
            <p className="text-[11px] text-slate-400 mb-4 leading-normal">
              Below are operational claims extracted from client intake interviews and categorized on the Evidence Ladder.
            </p>
            <div className="overflow-x-auto border border-slate-900/60 rounded-xl bg-slate-950/30">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-900 bg-slate-950/45 text-slate-400">
                    <th className="p-3 font-semibold">Stated Claim / Bottleneck</th>
                    <th className="p-3 font-semibold">Stated Source</th>
                    <th className="p-3 font-semibold text-right">Reliability Level</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900">
                  {evidenceLedger.map((item: any, idx: number) => {
                    const level = item.ladder_level || "Owner Estimate";
                    let badgeClass = "bg-rose-500/10 text-rose-400 border-rose-500/20";
                    if (level === "Employee Stated") badgeClass = "bg-orange-500/10 text-orange-400 border-orange-500/20";
                    else if (level === "System Export") badgeClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
                    
                    return (
                      <tr key={idx} className="hover:bg-slate-900/10 transition-colors">
                        <td className="p-3 text-slate-200 leading-relaxed font-medium">{item.claim}</td>
                        <td className="p-3 text-slate-400 font-mono text-[11px]">{item.source}</td>
                        <td className="p-3 text-right">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass}`}>
                            {level}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
