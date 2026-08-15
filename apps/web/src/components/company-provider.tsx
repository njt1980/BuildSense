"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getApiBaseUrl } from "@/lib/api";
import { useAuth } from "./auth-provider";

interface Company {
  id: string;
  user_id: string;
  name: string;
  industry: string;
  industry_vertical: string;
  core_tools: string;
}

interface CompanyContextType {
  companies: Company[];
  activeCompany: Company | null;
  loading: boolean;
  setActiveCompany: (company: Company) => void;
  refreshCompanies: () => Promise<void>;
  createCompany: (name: string, industry: string, tools: string) => Promise<Company>;
}

interface ApiErrorPayload {
  detail?: string;
  message?: string;
}

const CompanyContext = createContext<CompanyContextType>({
  companies: [],
  activeCompany: null,
  loading: true,
  setActiveCompany: () => {},
  refreshCompanies: async () => {},
  createCompany: async () => ({} as Company),
});

export const useCompany = () => useContext(CompanyContext);

export function CompanyProvider({ children, lang }: { children: React.ReactNode; lang: string }) {
  const { token } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [activeCompany, setActiveCompanyState] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);

  const apiBaseUrl = getApiBaseUrl();

  const fetchCompanies = useCallback(async (authToken: string) => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/companies`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        const loadedCompanies = data || [];
        setCompanies(loadedCompanies);

        if (loadedCompanies.length > 0) {
          const storedId = localStorage.getItem("buildsense_active_company_id");
          const found = loadedCompanies.find((c: Company) => c.id === storedId);
          if (found) {
            setActiveCompanyState(found);
          } else {
            setActiveCompanyState(loadedCompanies[0]);
            localStorage.setItem("buildsense_active_company_id", loadedCompanies[0].id);
          }
        } else {
          setActiveCompanyState(null);
        }
      }
    } catch (err) {
      console.error("Error loading companies context:", err);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    if (!token) {
      setCompanies([]);
      setActiveCompanyState(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    fetchCompanies(token);
  }, [token, fetchCompanies]);

  const setActiveCompany = useCallback((company: Company) => {
    setActiveCompanyState(company);
    localStorage.setItem("buildsense_active_company_id", company.id);
  }, []);

  const refreshCompanies = useCallback(async () => {
    if (!token) return;
    await fetchCompanies(token);
  }, [token, fetchCompanies]);

  const createCompany = useCallback(async (name: string, industry: string, tools: string): Promise<Company> => {
    if (!token) throw new Error("No auth credentials found.");

    const apiBaseUrl = getApiBaseUrl();
    const res = await fetch(`${apiBaseUrl}/api/v1/companies`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name,
        industry,
        core_tools: tools,
        industry_vertical: industry,
      }),
    });

    if (!res.ok) {
      const responseText = await res.text();
      let errorDetail = responseText;
      try {
        const payload = JSON.parse(responseText) as ApiErrorPayload;
        errorDetail = payload.detail || payload.message || "";
      } catch {
        errorDetail = responseText;
      }
      const readableDetail = errorDetail ? ` ${errorDetail}` : "";
      throw new Error(`Failed to establish business baseline (${res.status}).${readableDetail}`);
    }

    const data = await res.json();
    const newCompany: Company = {
      id: data.company_id,
      user_id: "", // will be fetched correctly on refresh
      name,
      industry,
      industry_vertical: industry,
      core_tools: tools,
    };

    await fetchCompanies(token);
    setActiveCompany(newCompany);
    return newCompany;
  }, [token, fetchCompanies, setActiveCompany]);

  return (
    <CompanyContext.Provider
      value={{
        companies,
        activeCompany,
        loading,
        setActiveCompany,
        refreshCompanies,
        createCompany,
      }}
    >
      {children}
    </CompanyContext.Provider>
  );
}
