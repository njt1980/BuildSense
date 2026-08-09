"use client";

import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SessionState } from "@/lib/useOrchestratorStream";

/**
 * Prop type definitions for the ReportView component.
 */
interface ReportViewProps {
  /** The final or active SessionState containing report text and metadata */
  sessionState: SessionState;
}

/**
 * Premium dashboard widget showing session execution costs and compiling the
 * Dual-View report (Quick Insights vs Deep Dive).
 *
 * @param props - Component parameters including SessionState.
 */
export function ReportView({ sessionState }: ReportViewProps) {
  const quickInsights = (sessionState.metadata.quick_insights as string) || "No quick insights generated.";
  const deepDive = (sessionState.metadata.deep_dive as string) || "No deep dive dossier compiled.";

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
            </CardDescription>
          </div>
          
          {/* Real-time budget spent and step count indicator tags */}
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
        <Tabs defaultValue="quick" className="w-full">
          <TabsList className="bg-[#03060d]/80 border border-slate-900/60 rounded-lg p-1 w-full grid grid-cols-2 max-w-[400px] mb-6">
            <TabsTrigger
              value="quick"
              className="rounded-md font-medium text-xs data-[state=active]:bg-slate-800/80 data-[state=active]:text-amber-400 data-[state=active]:border data-[state=active]:border-amber-500/20 text-slate-400 py-2 transition-all"
            >
              ⚡ Quick Insights
            </TabsTrigger>
            <TabsTrigger
              value="deep"
              className="rounded-md font-medium text-xs data-[state=active]:bg-slate-800/80 data-[state=active]:text-amber-400 data-[state=active]:border data-[state=active]:border-amber-500/20 text-slate-400 py-2 transition-all"
            >
              🔬 Deep Dive
            </TabsTrigger>
          </TabsList>

          <TabsContent value="quick" className="space-y-4 outline-none focus:ring-0">
            <div className="bg-[#03060d]/30 border border-slate-900/60 rounded-xl p-5 shadow-inner">
              <div className="prose prose-invert max-w-none text-slate-300 whitespace-pre-wrap leading-relaxed">
                {quickInsights}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="deep" className="space-y-4 outline-none focus:ring-0">
            <div className="bg-[#03060d]/30 border border-slate-900/60 rounded-xl p-5 shadow-inner">
              <div className="prose prose-invert max-w-none text-slate-300 whitespace-pre-wrap leading-relaxed">
                {deepDive}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
