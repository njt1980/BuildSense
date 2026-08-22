"use client";

import React, { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./auth-provider";
import { useCompany } from "./company-provider";
import { LanguageSwitcher } from "./language-switcher";
import { getDictionary } from "@/lib/dictionaries";

export function GlobalHeader({ lang }: { lang: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useAuth();
  const { companies, activeCompany, setActiveCompany, createCompany } = useCompany();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [devDropdownOpen, setDevDropdownOpen] = useState(false);
  
  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState("");
  const [newCompanyIndustry, setNewCompanyIndustry] = useState("");
  const [newCompanyTools, setNewCompanyTools] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  const dict = getDictionary(lang);

  const handleCreateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError("");
    setIsCreating(true);
    try {
      await createCompany(newCompanyName, newCompanyIndustry, newCompanyTools);
      setIsCreateModalOpen(false);
      setNewCompanyName("");
      setNewCompanyIndustry("");
      setNewCompanyTools("");
      setDropdownOpen(false);
    } catch (err: any) {
      setCreateError(err.message || "Failed to create company");
    } finally {
      setIsCreating(false);
    }
  };

  // Do not render the header on login page
  if (pathname?.includes("/login")) {
    return null;
  }

  const handleCompanySelect = (company: any) => {
    setActiveCompany(company);
    setDropdownOpen(false);
    
    // If the user is currently looking at a project, redirect to home.
    // This is because the current project is linked to a different company.
    if (pathname?.includes("/projects/")) {
      router.push(`/${lang}`);
    }
  };

  return (
    <header className="w-full max-w-6xl flex flex-col md:flex-row items-center justify-between gap-4 border-b border-slate-900/60 pb-5 mt-2 relative z-20">
      <div className="flex flex-col md:flex-row items-center gap-4">
        <div>
          <h1 
            onClick={() => router.push(`/${lang}`)}
            className="text-2xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500 cursor-pointer hover:opacity-90 transition-opacity"
          >
            {dict.brand || "BuildSense"}
          </h1>
          <p className="text-slate-400 text-xs mt-0.5">
            {dict.tagline || "Workflow Intelligence Engine"}
          </p>
        </div>

        {/* Global Company Context Switcher Dropdown */}
        {activeCompany && companies.length > 0 && (
          <div className="relative ml-2">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 bg-[#0b0f19]/60 hover:bg-[#121827] border border-slate-800 hover:border-slate-700 text-slate-200 text-xs font-semibold rounded-lg px-3.5 py-2 transition-all shadow-md focus:outline-none"
            >
              <span>🏢</span>
              <span className="max-w-[150px] truncate">{activeCompany.name}</span>
              <span className="text-[10px] text-slate-500">▼</span>
            </button>

            {dropdownOpen && (
              <div className="absolute left-0 mt-1.5 w-60 bg-[#0b0f19] border border-slate-800 rounded-xl shadow-2xl z-50 overflow-hidden py-1.5 animate-fade-in backdrop-blur-xl">
                <div className="px-3 py-1.5 border-b border-slate-850 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                  Switch Active Company
                </div>
                
                <div className="max-h-48 overflow-y-auto">
                  {companies.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => handleCompanySelect(c)}
                      className={`w-full text-left px-3.5 py-2.5 text-xs flex flex-col gap-0.5 transition-all ${
                        c.id === activeCompany.id
                          ? "bg-amber-500/10 text-amber-300 font-bold border-l-2 border-amber-500"
                          : "text-slate-400 hover:bg-slate-900/50 hover:text-slate-200"
                      }`}
                    >
                      <span className="truncate">{c.name}</span>
                      <span className="text-[9px] text-slate-500 font-medium tracking-wide uppercase">{c.industry_vertical || c.industry}</span>
                    </button>
                  ))}
                </div>
                <div className="border-t border-slate-800 p-1.5">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      setIsCreateModalOpen(true);
                    }}
                    className="w-full text-left px-3.5 py-2 text-xs text-emerald-400 hover:bg-slate-900/50 hover:text-emerald-300 font-medium transition-all rounded-md flex items-center gap-1.5"
                  >
                    <span>➕</span> Create New Company
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-center md:justify-end gap-3">
        {/* Unified Language Switcher */}
        <LanguageSwitcher currentLang={lang} />

        {/* Developer Space Dropdown */}
        <div className="relative">
          <button
            onClick={() => setDevDropdownOpen(!devDropdownOpen)}
            className="flex items-center gap-1.5 bg-[#0b0f19]/60 hover:bg-[#121827] border border-slate-800 hover:border-slate-700 text-slate-200 text-xs font-semibold rounded-lg px-3 py-2 transition-all shadow-md focus:outline-none"
          >
            <span>🛠️</span>
            <span>Dev Tools</span>
            <span className="text-[8px] text-slate-500">▼</span>
          </button>

          {devDropdownOpen && (
            <div className="absolute right-0 mt-1.5 w-44 bg-[#0b0f19] border border-slate-800 rounded-xl shadow-2xl z-50 overflow-hidden py-1.5 animate-fade-in backdrop-blur-xl">
              <div className="px-3 py-1.5 border-b border-slate-850 text-[9px] uppercase font-bold text-slate-500 tracking-wider">
                Developer Space
              </div>
              <button
                onClick={() => {
                  router.push(`/${lang}`);
                  setDevDropdownOpen(false);
                }}
                className="w-full text-left px-3.5 py-2.5 text-xs text-slate-400 hover:bg-slate-900/50 hover:text-slate-200 transition-all"
              >
                🏠 Workspace Home
              </button>
              <a
                href={`/${lang}/dev/telemetry`}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => {
                  setDevDropdownOpen(false);
                }}
                className="block w-full text-left px-3.5 py-2.5 text-xs text-slate-400 hover:bg-slate-900/50 hover:text-slate-200 transition-all"
              >
                📊 Telemetry Flow
              </a>
              <button
                onClick={() => {
                  router.push(`/${lang}/dev/evaluations`);
                  setDevDropdownOpen(false);
                }}
                className="w-full text-left px-3.5 py-2.5 text-xs text-slate-400 hover:bg-slate-900/50 hover:text-slate-200 transition-all"
              >
                🔬 Evaluation Metrics
              </button>
            </div>
          )}
        </div>

        {user && (
          <div className="flex items-center gap-2 bg-[#0b0f19]/45 border border-slate-900/60 rounded-lg px-3 py-1.5 text-slate-300 font-mono text-xs">
            <span className="max-w-[140px] truncate" title={user.email}>👤 {user.email}</span>
            <button 
              type="button" 
              onClick={signOut}
              className="text-[9px] bg-rose-950/20 text-rose-400 border border-rose-950/40 rounded px-1.5 py-0.5 hover:bg-rose-900/30 hover:text-rose-300 font-bold ml-1 transition-all"
            >
              {dict.signOut || "Sign Out"}
            </button>
          </div>
        )}

        <div className="flex items-center gap-2 bg-slate-900/30 border border-slate-800/30 rounded-full px-3 py-2">
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-[11px] text-slate-300 font-medium tracking-wide">{dict.enterpriseOnline || "Online"}</span>
        </div>
      </div>
      
      {/* Create Company Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-[#0b0f19] border border-slate-800 w-full max-w-md rounded-2xl shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-800">
              <h2 className="text-lg font-semibold text-slate-200">Create New Company</h2>
              <p className="text-xs text-slate-400 mt-1">Establish a new business entity for project workspaces.</p>
            </div>
            <form onSubmit={handleCreateCompany} className="p-5 flex flex-col gap-4 text-left">
              {createError && (
                <div className="bg-rose-950/40 border border-rose-900/50 text-rose-400 text-xs p-3 rounded-lg">
                  {createError}
                </div>
              )}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-slate-300">Business Name *</label>
                <input
                  type="text"
                  required
                  value={newCompanyName}
                  onChange={(e) => setNewCompanyName(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all placeholder:text-slate-600"
                  placeholder="e.g. Acme Corp"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-slate-300">Industry Vertical *</label>
                <input
                  type="text"
                  required
                  value={newCompanyIndustry}
                  onChange={(e) => setNewCompanyIndustry(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all placeholder:text-slate-600"
                  placeholder="e.g. E-commerce, Real Estate"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-slate-300">Core Tools</label>
                <input
                  type="text"
                  value={newCompanyTools}
                  onChange={(e) => setNewCompanyTools(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all placeholder:text-slate-600"
                  placeholder="e.g. Shopify, Salesforce"
                />
              </div>
              <div className="flex justify-end gap-3 mt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  disabled={isCreating}
                  className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating || !newCompanyName.trim() || !newCompanyIndustry.trim()}
                  className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 text-sm font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isCreating ? "Creating..." : "Create Company"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
}
