import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://mock.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "mock-key";

// Create client
export const supabase = createClient(supabaseUrl, supabaseAnonKey);

/**
 * Custom helper to determine if we are running in simulated local dev auth mode
 */
export const isMockAuth = () => {
  return (
    !process.env.NEXT_PUBLIC_SUPABASE_URL ||
    process.env.NEXT_PUBLIC_SUPABASE_URL.includes("mock.supabase.co")
  );
};

// Mock Auth service for local standalone developer environments
export const mockAuthService = {
  signUp: async (email: string) => {
    console.log("Mock Sign Up for email:", email);
    const mockUser = {
      id: "d3b07384-d113-4e4e-9c29-ba4f2a74c2e6",
      email,
    };
    try {
      if (typeof window !== "undefined") {
        localStorage.setItem("buildsense_mock_session", JSON.stringify({ user: mockUser, token: "mock-jwt-token" }));
      }
    } catch (e) {
      console.warn("Mock auth signUp localStorage error:", e);
    }
    return { data: { user: mockUser }, error: null };
  },
  signIn: async (email: string) => {
    console.log("Mock Sign In for email:", email);
    const mockUser = {
      id: "d3b07384-d113-4e4e-9c29-ba4f2a74c2e6",
      email,
    };
    try {
      if (typeof window !== "undefined") {
        localStorage.setItem("buildsense_mock_session", JSON.stringify({ user: mockUser, token: "mock-jwt-token" }));
      }
    } catch (e) {
      console.warn("Mock auth signIn localStorage error:", e);
    }
    return { data: { user: mockUser }, error: null };
  },
  signOut: async () => {
    console.log("Mock Sign Out");
    try {
      if (typeof window !== "undefined") {
        localStorage.removeItem("buildsense_mock_session");
      }
    } catch (e) {
      console.warn("Mock auth signOut localStorage error:", e);
    }
    return { error: null };
  },
  getSession: async () => {
    try {
      if (typeof window !== "undefined") {
        const stored = localStorage.getItem("buildsense_mock_session");
        if (stored) {
          return { data: { session: JSON.parse(stored) }, error: null };
        }
      }
    } catch (e) {
      console.warn("Mock auth getSession localStorage error:", e);
    }
    return { data: { session: null }, error: null };
  }
};
