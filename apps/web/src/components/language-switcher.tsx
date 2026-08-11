"use client";

import React from "react";
import { usePathname, useRouter } from "next/navigation";

export function LanguageSwitcher({ currentLang }: { currentLang: string }) {
  const pathname = usePathname();
  const router = useRouter();

  const locales = [
    { code: "en", name: "English" },
    { code: "hi", name: "हिन्दी (Hindi)" },
    { code: "kn", name: "ಕನ್ನಡ (Kannada)" },
    { code: "ta", name: "தமிழ் (Tamil)" },
    { code: "ml", name: "മലയാളം (Malayalam)" },
  ];

  const handleLanguageChange = (newLang: string) => {
    if (!pathname) return;
    const segments = pathname.split("/");
    // pathname starts with a slash, so segments[0] is "", segments[1] is the locale
    if (segments.length > 1) {
      segments[1] = newLang;
      router.push(segments.join("/"));
    } else {
      router.push(`/${newLang}`);
    }
  };

  return (
    <div className="flex items-center gap-1 bg-[#0b0f19]/45 border border-slate-900/60 rounded-lg px-2.5 py-1">
      <span className="text-[11px] text-slate-400 font-bold">🌐</span>
      <select
        value={currentLang}
        onChange={(e) => handleLanguageChange(e.target.value)}
        className="bg-transparent text-slate-300 text-xs font-semibold focus:outline-none focus:ring-0 cursor-pointer py-0.5 border-none outline-none appearance-none"
      >
        {locales.map((loc) => (
          <option key={loc.code} value={loc.code} className="bg-[#0b0f19] text-slate-300">
            {loc.name}
          </option>
        ))}
      </select>
    </div>
  );
}
