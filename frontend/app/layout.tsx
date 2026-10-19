import type { Metadata } from "next";
import "./globals.css";
import { NavLinks } from "./nav-links";

export const metadata: Metadata = {
  title: "AI Self-Healing Test Agent | HealAgent",
  description:
    "AI-powered browser test automation with self-healing locators, powered by local LLM inference",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased text-[#0a291e] selection:bg-emerald-200 selection:text-emerald-950 min-h-screen relative overflow-x-hidden">
        {/* Navigation */}
        <nav className="sticky top-0 z-50 border-b border-emerald-200/70 bg-white/90 backdrop-blur-2xl shadow-[0_4px_20px_rgba(16,185,129,0.06)]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <NavLinks />
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-3.5 sm:px-6 py-6 sm:py-8 relative z-10">{children}</main>
      </body>
    </html>
  );
}
