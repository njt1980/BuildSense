"use client";

import * as React from "react";

/**
 * Types representing the selectable options in the dual-view toggle.
 */
export type ViewType = "quick" | "deep";

/**
 * Interface defining the configuration properties for the DualViewLayout component.
 */
export interface DualViewLayoutProps {
  /** Optional children elements to render within the active view panel */
  children?: React.ReactNode;
}

/**
 * A premium, responsive layout container featuring a toggle between
 * 'Quick Insights' (2-minute high-level summary) and 'Deep Dive' (complete analysis).
 * Design uses dark-mode aesthetics, subtle borders, and smooth hover micro-animations.
 *
 * @param props - Component configuration props.
 * @returns React layout interface with toggle headers and responsive content viewport.
 */
export function DualViewLayout({ children }: DualViewLayoutProps): React.JSX.Element {
  const [selectedActiveView, setSelectedActiveView] = React.useState<ViewType>("quick");

  /**
   * Handles transitioning the layout's active viewport display mode.
   *
   * @param targetView - The chosen view type.
   */
  const handleViewTransition = (targetView: ViewType): void => {
    setSelectedActiveView(targetView);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased selection:bg-indigo-500 selection:text-white">
      {/* Premium Glassmorphic Header */}
      <header className="sticky top-0 z-50 w-full border-b border-slate-800 bg-slate-900/70 backdrop-blur-md">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <span className="text-white font-bold text-lg select-none">B</span>
            </div>
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-50 to-slate-200 tracking-tight">
              BuildSense
            </span>
          </div>

          {/* Interactive Dual-View Toggle Controller */}
          <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-xl shadow-inner">
            <button
              onClick={(): void => handleViewTransition("quick")}
              className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-300 flex items-center gap-2 ${
                selectedActiveView === "quick"
                  ? "bg-gradient-to-r from-indigo-600 to-indigo-500 text-white shadow-md"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <span>⚡</span>
              <span>Quick Insights</span>
            </button>
            <button
              onClick={(): void => handleViewTransition("deep")}
              className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-300 flex items-center gap-2 ${
                selectedActiveView === "deep"
                  ? "bg-gradient-to-r from-purple-600 to-purple-500 text-white shadow-md"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <span>🔬</span>
              <span>Deep Dive</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main content area */}
      <main className="flex-1 container mx-auto px-4 py-8 max-w-6xl">
        {children ? (
          children
        ) : (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Upper Info Banner with motivating stats */}
            <div className="rounded-2xl bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-900/40 border border-indigo-500/20 p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div>
                <h1 className="text-2xl font-bold text-slate-50">Active Session</h1>
                <p className="text-sm text-slate-400 mt-1">
                  Ready to SUGGEST, EVALUATE, or OPTIMIZE. Scaffolded environment active.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className="px-3 py-1 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-full text-xs font-semibold">
                  Status: Scaffolding Ready
                </div>
                <div className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-semibold">
                  No Cost Active
                </div>
              </div>
            </div>

            {/* Displaying view states based on Toggle selection */}
            {selectedActiveView === "quick" ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in duration-300">
                {/* Quick Insights View Card 1 */}
                <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl hover:border-slate-700 transition-all group">
                  <div className="text-emerald-400 text-2xl group-hover:scale-110 transition-transform duration-300 w-fit">
                    🎯
                  </div>
                  <h3 className="text-lg font-bold text-slate-100 mt-4">Pillar 1: Market Demand</h3>
                  <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                    Quick insight signals mapping consumer search volumes, interest profiles, and primary competitor coverage metrics.
                  </p>
                  <div className="mt-4 flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <span className="text-xs text-slate-400 font-medium">Valid signals found</span>
                  </div>
                </div>

                {/* Quick Insights View Card 2 */}
                <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl hover:border-slate-700 transition-all group">
                  <div className="text-indigo-400 text-2xl group-hover:scale-110 transition-transform duration-300 w-fit">
                    🛡️
                  </div>
                  <h3 className="text-lg font-bold text-slate-100 mt-4">Pillar 2: Defensibility</h3>
                  <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                    Basic barriers to entry assessment, branding advantages, and key technical integrations that define the unique moat.
                  </p>
                  <div className="mt-4 flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-indigo-500"></span>
                    <span className="text-xs text-slate-400 font-medium">Unique moats mapped</span>
                  </div>
                </div>

                {/* Quick Insights View Card 3 */}
                <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl hover:border-slate-700 transition-all group">
                  <div className="text-purple-400 text-2xl group-hover:scale-110 transition-transform duration-300 w-fit">
                    ⚙️
                  </div>
                  <h3 className="text-lg font-bold text-slate-100 mt-4">Pillar 3: MVP Architecture</h3>
                  <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                    Lean system setups targeting 90/10 MVP execution, zero-cost third party APIs, and quick mock integrations.
                  </p>
                  <div className="mt-4 flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-purple-500"></span>
                    <span className="text-xs text-slate-400 font-medium">Architecture optimized</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-6 animate-in fade-in duration-300">
                {/* Deep Dive View Panel */}
                <div className="p-8 bg-slate-900/30 border border-slate-800 rounded-2xl relative overflow-hidden">
                  <div className="absolute top-0 right-0 h-40 w-40 bg-purple-500/5 blur-3xl rounded-full"></div>
                  <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                    <span>🔬</span>
                    <span>Deep Dive Analysis & CDD Dossier</span>
                  </h2>
                  <p className="text-sm text-slate-400 mt-2">
                    Fully-featured 4-Pillar dossier covering target unit economics (LTV/CAC ratios), detailed defensibility matrix, architecture DAG plans, and full market evidence reports.
                  </p>
                  <div className="mt-6 border-t border-slate-800 pt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-lg">
                        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Unit Economics</span>
                        <div className="text-lg font-semibold text-slate-200 mt-1">LTV : CAC Calculations</div>
                        <p className="text-xs text-slate-400 mt-1">Calculates detailed lifetime value projections vs customer acquisition metrics.</p>
                      </div>
                      <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-lg">
                        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Defensibility moats</span>
                        <div className="text-lg font-semibold text-slate-200 mt-1">Competitive Matrix & Defensibility</div>
                        <p className="text-xs text-slate-400 mt-1">Detailed matrix mapping direct features, pricing, and scaling vectors.</p>
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-lg">
                        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">System Design</span>
                        <div className="text-lg font-semibold text-slate-200 mt-1">90/10 Lean Architecture Specs</div>
                        <p className="text-xs text-slate-400 mt-1">Diagrams representing target databases, models, hosting plans, and auth layers.</p>
                      </div>
                      <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-lg">
                        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">SOP Automation</span>
                        <div className="text-lg font-semibold text-slate-200 mt-1">Modernization AI Roadmaps</div>
                        <p className="text-xs text-slate-400 mt-1">Breakdown of manual steps and code hooks needed to orchestrate standard operations.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
