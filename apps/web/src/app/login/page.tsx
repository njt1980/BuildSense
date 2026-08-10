"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase, isMockAuth, mockAuthService } from "@/lib/supabase";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [mockActive, setMockActive] = useState(false);

  useEffect(() => {
    setMockActive(isMockAuth());
    
    // Check if user is already logged in
    const checkUser = async () => {
      if (isMockAuth()) {
        const { data } = await mockAuthService.getSession();
        if (data?.session) {
          router.push("/");
        }
      } else {
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          router.push("/");
        }
      }
    };
    checkUser();
  }, [router]);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      if (mockActive) {
        if (isSignUp) {
          await mockAuthService.signUp(email);
          setMessage("Mock registration successful! Logging in...");
        } else {
          await mockAuthService.signIn(email);
          setMessage("Mock login successful!");
        }
        setTimeout(() => {
          router.push("/");
        }, 1000);
      } else {
        if (isSignUp) {
          const { error } = await supabase.auth.signUp({
            email,
            password,
          });
          if (error) throw error;
          setMessage("Registration successful! Check your email to confirm.");
        } else {
          const { error } = await supabase.auth.signInWithPassword({
            email,
            password,
          });
          if (error) throw error;
          setMessage("Login successful! Redirecting...");
          setTimeout(() => {
            router.push("/");
          }, 1000);
        }
      }
    } catch (err: any) {
      setMessage(`Error: ${err.message || "Something went wrong"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickMockLogin = async (role: string) => {
    setLoading(true);
    setMessage("");
    const mockEmail = `${role.toLowerCase().replace(" ", "_")}@buildsense.app`;
    try {
      await mockAuthService.signIn(mockEmail);
      setMessage(`Logged in as simulated ${role}! Redirecting...`);
      setTimeout(() => {
        router.push("/");
      }, 800);
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#03060d] text-slate-100 flex flex-col items-center justify-center p-4 relative overflow-hidden font-sans select-none">
      {/* Background ambient glows */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-gradient-to-br from-amber-500/5 to-orange-500/0 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-gradient-to-tr from-emerald-500/5 to-teal-500/0 blur-[130px] pointer-events-none" />

      <div className="w-full max-w-md bg-[#0b0f19]/45 border border-slate-900 rounded-2xl p-8 backdrop-blur-xl shadow-2xl relative z-10 flex flex-col gap-6">
        <div className="text-center">
          <h1 className="text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500">
            BuildSense
          </h1>
          <p className="text-slate-400 text-xs mt-2">
            Enterprise Product Ideation, Evaluation, and Workflow Optimization
          </p>
        </div>

        {mockActive && (
          <div className="bg-amber-500/5 border border-amber-500/20 text-amber-300 text-[11px] leading-relaxed p-3 rounded-lg flex items-center justify-between">
            <span>⚙️ Local Standalone Mode: Simulated Auth active.</span>
            <span className="bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded text-[9px] font-bold">DEV</span>
          </div>
        )}

        <form onSubmit={handleAuth} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">
              Email Address
            </label>
            <input
              type="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#03060d]/60 border border-slate-800 text-slate-200 text-sm placeholder:text-slate-700 rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-amber-500/40 transition-all"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">
              Password
            </label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#03060d]/60 border border-slate-800 text-slate-200 text-sm placeholder:text-slate-700 rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-amber-500/40 transition-all"
              required={!mockActive}
            />
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 hover:from-amber-600 hover:via-orange-600 hover:to-rose-600 text-slate-950 font-extrabold py-3.5 rounded-lg shadow-lg hover:shadow-xl transition-all tracking-wide text-xs"
          >
            {loading ? "Processing..." : isSignUp ? "Create Account" : "Sign In"}
          </Button>
        </form>

        {mockActive && (
          <div className="space-y-2">
            <div className="relative flex py-1 items-center">
              <div className="flex-grow border-t border-slate-800/40"></div>
              <span className="flex-shrink mx-4 text-slate-600 text-[10px] uppercase font-bold tracking-widest">Simulated Profiles</span>
              <div className="flex-grow border-t border-slate-800/40"></div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleQuickMockLogin("Enterprise PM")}
                className="text-[10px] font-bold text-slate-300 hover:text-white bg-slate-950/45 hover:bg-slate-900 border border-slate-900 rounded-lg py-2 transition-all"
              >
                🏢 Enterprise PM
              </button>
              <button
                type="button"
                onClick={() => handleQuickMockLogin("Small Business Operator")}
                className="text-[10px] font-bold text-slate-300 hover:text-white bg-slate-950/45 hover:bg-slate-900 border border-slate-900 rounded-lg py-2 transition-all"
              >
                🌾 SMB Operator
              </button>
              <button
                type="button"
                onClick={() => handleQuickMockLogin("Solo Founder")}
                className="text-[10px] font-bold text-slate-300 hover:text-white bg-slate-950/45 hover:bg-slate-900 border border-slate-900 rounded-lg py-2 transition-all"
              >
                🚀 Solo Founder
              </button>
              <button
                type="button"
                onClick={() => handleQuickMockLogin("Student")}
                className="text-[10px] font-bold text-slate-300 hover:text-white bg-slate-950/45 hover:bg-slate-900 border border-slate-900 rounded-lg py-2 transition-all"
              >
                🎓 Student
              </button>
            </div>
          </div>
        )}

        {message && (
          <p className="text-center text-xs font-semibold text-amber-400 mt-2 leading-relaxed bg-[#03060d]/50 border border-slate-900 p-2.5 rounded-lg">
            {message}
          </p>
        )}

        <div className="text-center text-xs">
          <button
            type="button"
            onClick={() => setIsSignUp(!isSignUp)}
            className="text-slate-400 hover:text-amber-300 font-semibold transition-all"
          >
            {isSignUp
              ? "Already have an account? Sign In"
              : "Don't have an account? Create Account"}
          </button>
        </div>
      </div>
    </main>
  );
}
