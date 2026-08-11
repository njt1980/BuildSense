import type { Metadata } from "next";
import { Noto_Sans, Noto_Sans_Devanagari, Noto_Sans_Kannada, Noto_Sans_Tamil, Noto_Sans_Malayalam } from "next/font/google";
import "../globals.css";
import { cn } from "@/lib/utils";
import { AuthProvider } from "@/components/auth-provider";
import { CompanyProvider } from "@/components/company-provider";

const notoSans = Noto_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "700", "900"],
  variable: "--font-noto-sans",
});

const notoDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["300", "400", "500", "700", "900"],
  variable: "--font-noto-devanagari",
});

const notoKannada = Noto_Sans_Kannada({
  subsets: ["kannada"],
  weight: ["300", "400", "500", "700", "900"],
  variable: "--font-noto-kannada",
});

const notoTamil = Noto_Sans_Tamil({
  subsets: ["tamil"],
  weight: ["300", "400", "500", "700", "900"],
  variable: "--font-noto-tamil",
});

const notoMalayalam = Noto_Sans_Malayalam({
  subsets: ["malayalam"],
  weight: ["300", "400", "500", "700", "900"],
  variable: "--font-noto-malayalam",
});

export const metadata: Metadata = {
  title: "BuildSense Platform",
  description: "Agentic Intelligence Engine for Idea Evaluation & Workflow Optimization",
};

export default function LangLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: { lang: string };
}>): React.JSX.Element {
  return (
    <html lang={params.lang || "en"} className={cn("dark font-sans", notoSans.variable)}>
      <body
        className={`${notoSans.variable} ${notoDevanagari.variable} ${notoKannada.variable} ${notoTamil.variable} ${notoMalayalam.variable} antialiased`}
      >
        <AuthProvider>
          <CompanyProvider lang={params.lang || "en"}>
            {children}
          </CompanyProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
