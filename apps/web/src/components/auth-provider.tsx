"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { supabase, isMockAuth, mockAuthService } from "@/lib/supabase";

interface AuthContextType {
  user: any | null;
  token: string | null;
  signOut: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  signOut: async () => {},
  loading: true,
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkUser = async () => {
      setLoading(true);
      if (isMockAuth()) {
        const { data } = await mockAuthService.getSession();
        if (data?.session) {
          setUser(data.session.user);
          setToken(data.session.token);
        } else {
          setUser(null);
          setToken(null);
          if (pathname !== "/login") {
            router.push("/login");
          }
        }
      } else {
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          setUser(session.user);
          setToken(session.access_token);
        } else {
          setUser(null);
          setToken(null);
          if (pathname !== "/login") {
            router.push("/login");
          }
        }
      }
      setLoading(false);
    };

    checkUser();

    // Subscribe to auth state updates (only if not in mock mode)
    if (!isMockAuth()) {
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        async (event, session) => {
          if (session) {
            setUser(session.user);
            setToken(session.access_token);
          } else {
            setUser(null);
            setToken(null);
            if (pathname !== "/login") {
              router.push("/login");
            }
          }
          setLoading(false);
        }
      );
      return () => {
        subscription.unsubscribe();
      };
    }
  }, [router, pathname]);

  const signOut = async () => {
    setLoading(true);
    if (isMockAuth()) {
      await mockAuthService.signOut();
    } else {
      await supabase.auth.signOut();
    }
    setUser(null);
    setToken(null);
    router.push("/login");
    setLoading(false);
  };

  // If loading and not on login page, show loader
  if (loading && pathname !== "/login") {
    return (
      <div className="min-h-screen bg-[#03060d] text-slate-100 flex flex-col items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-t-amber-500 border-slate-900 animate-spin" />
          <p className="text-xs text-slate-400 font-medium tracking-wide">Syncing Security Access Credentials...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, token, signOut, loading }}>
      {children}
    </AuthContext.Provider>
  );
}
