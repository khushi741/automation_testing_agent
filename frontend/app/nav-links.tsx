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

  return (
    <div className="flex items-center gap-1">
      <Link
        href="/#connect"
        onClick={handleConnectClick}
        className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
      >
        Connect Repo
      </Link>
      <Link
        href="/runs"
        className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
      >
        Test Runs
      </Link>
      <Link
        href="/evaluation"
        className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
      >
        Evaluation
      </Link>
    </div>
  );
}
