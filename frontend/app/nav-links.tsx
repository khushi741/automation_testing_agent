"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function NavLinks() {
  const pathname = usePathname();

  const handleConnectClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
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

  return (
    <div className="flex items-center gap-1.5">
      <Link
        href="/#connect"
        onClick={handleConnectClick}
        className="px-4 py-2 text-sm text-gray-600 hover:text-emerald-800 font-medium transition-colors rounded-lg hover:bg-emerald-50/80"
      >
        Connect Repo
      </Link>
      <Link
        href="/runs"
        className={`px-4 py-2 text-sm font-medium transition-colors rounded-lg ${
          isRunsActive
            ? "text-emerald-800 bg-emerald-100/70 font-semibold border border-emerald-200/60 shadow-xs"
            : "text-gray-600 hover:text-emerald-800 hover:bg-emerald-50/80"
        }`}
      >
        Test Runs
      </Link>
      <Link
        href="/evaluation"
        className={`px-4 py-2 text-sm font-medium transition-colors rounded-lg ${
          isEvalActive
            ? "text-emerald-800 bg-emerald-100/70 font-semibold border border-emerald-200/60 shadow-xs"
            : "text-gray-600 hover:text-emerald-800 hover:bg-emerald-50/80"
        }`}
      >
        Evaluation
      </Link>
    </div>
  );
}
