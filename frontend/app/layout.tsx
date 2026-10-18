import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import { NavLinks } from "./nav-links";

export const metadata: Metadata = {
  title: "HealAgent — AI Self-Healing Browser Test Automation",
  description:
    "AI-powered browser test automation with self-healing locators, powered by local LLM and embedding vector models",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Geist+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased text-[#0a291e] selection:bg-emerald-200 selection:text-emerald-950 min-h-screen relative overflow-x-hidden">
        
        {/* Top Micro-Banner */}
        <div className="relative z-50 bg-gradient-to-r from-emerald-600 via-teal-600 to-green-600 text-white text-xs font-medium py-1.5 px-4 text-center shadow-xs overflow-hidden">
          <div className="absolute inset-0 bg-white/10 animate-shimmer" />
          <div className="max-w-7xl mx-auto flex items-center justify-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-300 animate-blink" />
            <span>Next-Gen Test Automation: AI route discovery & self-healing selector recovery</span>
            <span className="hidden sm:inline opacity-80">• Free & open on Render</span>
          </div>
        </div>

        {/* Navigation Bar */}
        <nav className="sticky top-0 z-40 border-b border-emerald-200/70 bg-white/80 backdrop-blur-2xl shadow-[0_4px_20px_rgba(16,185,129,0.06)]">
          <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="relative w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 via-teal-500 to-green-600 flex items-center justify-center shadow-md shadow-emerald-500/30 group-hover:scale-105 transition-all">
                <div className="absolute -inset-0.5 rounded-xl bg-emerald-400/40 blur-xs opacity-70 group-hover:opacity-100 transition-opacity" />
                <svg
                  className="relative w-5 h-5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                  />
                </svg>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-900 via-teal-800 to-green-800 bg-clip-text text-transparent">
                  HealAgent
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100/90 text-emerald-800 border border-emerald-300 shadow-2xs">
                  v2.0
                </span>
              </div>
            </Link>

            <div className="flex items-center gap-4">
              <NavLinks />
              
              <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50/90 border border-emerald-200/80 text-xs font-semibold text-emerald-800 shadow-2xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse-ring" />
                <span>Engine Online</span>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-6 py-8 relative z-10">{children}</main>
      </body>
    </html>
  );
}
