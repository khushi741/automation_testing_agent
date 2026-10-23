"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function NavLinks() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleConnectClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    setMobileMenuOpen(false);
    if (pathname === "/") {
      e.preventDefault();
      if (window.location.hash !== "#connect") {
        window.history.pushState(null, "", "#connect");
      }
      const el = document.getElementById("connect");
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
      }
      setTimeout(() => {
        const input = document.getElementById("repo-url-input") as HTMLInputElement | null;
        if (input) {
          input.focus();
          input.select();
        }
      }, 300);
    }
  };

  const isRunsActive = pathname.startsWith("/runs");
  const isEvalActive = pathname.startsWith("/evaluation");
  const isBugsActive = pathname.startsWith("/bugs");
  const isBenchActive = pathname.startsWith("/benchmark");

  return (
    <div>
      <div className="flex items-center justify-between h-16">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-2.5 sm:gap-3 group shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 via-teal-500 to-green-600 flex items-center justify-center shadow-md shadow-emerald-500/25 group-hover:scale-105 transition-all">
            <svg
              className="w-4 h-4 text-white"
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
          <span className="text-xl font-bold bg-gradient-to-r from-emerald-800 via-teal-700 to-green-700 bg-clip-text text-transparent">
            HealAgent 2.0
          </span>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden sm:flex items-center gap-1.5">
          <Link
            href="/bugs"
            className={`px-3.5 py-1.5 text-sm font-medium transition-colors rounded-lg ${
              isBugsActive
                ? "text-emerald-800 bg-emerald-100/70 font-semibold border border-emerald-200/60 shadow-xs"
                : "text-gray-600 hover:text-emerald-800 hover:bg-emerald-50/80"
            }`}
          >
            Bugs & Fixes
          </Link>
          <Link
            href="/benchmark"
            className={`px-3.5 py-1.5 text-sm font-medium transition-colors rounded-lg ${
              isBenchActive
                ? "text-emerald-800 bg-emerald-100/70 font-semibold border border-emerald-200/60 shadow-xs"
                : "text-gray-600 hover:text-emerald-800 hover:bg-emerald-50/80"
            }`}
          >
            Benchmark
          </Link>
          <Link
            href="/runs"
            className={`px-3.5 py-1.5 text-sm font-medium transition-colors rounded-lg ${
              isRunsActive
                ? "text-emerald-800 bg-emerald-100/70 font-semibold border border-emerald-200/60 shadow-xs"
                : "text-gray-600 hover:text-emerald-800 hover:bg-emerald-50/80"
            }`}
          >
            Test Runs
          </Link>
          <Link
            href="/evaluation"
            className={`px-3.5 py-1.5 text-sm font-medium transition-colors rounded-lg ${
              isEvalActive
                ? "text-emerald-800 bg-emerald-100/70 font-semibold border border-emerald-200/60 shadow-xs"
                : "text-gray-600 hover:text-emerald-800 hover:bg-emerald-50/80"
            }`}
          >
            Evaluation
          </Link>
        </div>

        {/* Mobile Hamburger Button */}
        <div className="sm:hidden flex items-center">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-emerald-900 hover:bg-emerald-50 focus:outline-none transition-colors border border-emerald-200/60"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-t border-emerald-100 py-3 px-1 space-y-1 bg-white/95 backdrop-blur-md rounded-b-2xl shadow-lg">
          <Link
            href="/#connect"
            onClick={handleConnectClick}
            className="block px-4 py-2.5 text-sm font-medium text-emerald-950 rounded-lg hover:bg-emerald-50 transition-colors"
          >
            Connect Repo
          </Link>
          <Link
            href="/runs"
            onClick={() => setMobileMenuOpen(false)}
            className={`block px-4 py-2.5 text-sm font-medium rounded-lg transition-colors ${
              isRunsActive ? "bg-emerald-100/80 text-emerald-900 font-bold" : "text-emerald-950 hover:bg-emerald-50"
            }`}
          >
            Test Runs
          </Link>
          <Link
            href="/evaluation"
            onClick={() => setMobileMenuOpen(false)}
            className={`block px-4 py-2.5 text-sm font-medium rounded-lg transition-colors ${
              isEvalActive ? "bg-emerald-100/80 text-emerald-900 font-bold" : "text-emerald-950 hover:bg-emerald-50"
            }`}
          >
            Evaluation
          </Link>
        </div>
      )}
    </div>
  );
}
