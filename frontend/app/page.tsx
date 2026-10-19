"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  createRepo,
  getRepo,
  analyzeRepo,
  generateTests,
  createTestRun,
  Repo,
  Route,
} from "@/lib/api";

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-emerald-400",
    cloning: "bg-teal-400 animate-pulse-dot",
    analyzing: "bg-emerald-500 animate-pulse-dot",
    ready: "bg-emerald-600",
    failed: "bg-rose-500",
  };
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${colors[status] || "bg-gray-400"}`}
    />
  );
}

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [repo, setRepo] = useState<Repo | null>(null);
  const [targetBaseUrl, setTargetBaseUrl] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [runStarted, setRunStarted] = useState(false);
  const [activeTab, setActiveTab] = useState<"terminal" | "synthesizer" | "healing">("terminal");
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const connectSectionRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Mock console log simulation
  const [consoleLogs, setConsoleLogs] = useState<string[]>([]);
  useEffect(() => {
    const lines = [
      "$ autotest analyze https://github.com/khushi741/automation_testing_agent",
      "Cloning repository into scratch directory... Success (1.4s)",
      "Detecting project framework... FastAPI + Next.js (Full Stack)",
      "Extracting application routes... Found 6 active endpoints",
      "  - GET  /api/health (Service Health)",
      "  - GET  /api/repos (Repository Registry)",
      "  - POST /api/test-runs (Test Runner Trigger)",
      "  - GET  /api/eval-results (Self-Healing Benchmark)",
      "Running AI Test Case Synthesizer...",
      "Synthesized 12 natural language interaction scenarios",
      "Executing Playwright runner with self-healing engine...",
      "  [1/4] GET /api/health -> Passed (42ms)",
      "  [2/4] GET /api/repos -> Passed (118ms)",
      "  [3/4] POST /api/test-runs -> Healed (button selector mutated: matched #run-btn with 94.6% confidence)",
      "  [4/4] GET / -> Passed (204ms)",
      "Self-healing accuracy: 100% • Zero manual test maintenance required!"
    ];

    let currentLine = 0;
    const interval = setInterval(() => {
      if (currentLine < lines.length && lines[currentLine] !== undefined) {
        const nextLine = lines[currentLine];
        setConsoleLogs((prev) => [...prev, nextLine]);
        currentLine++;
      } else {
        clearInterval(interval);
      }
    }, 1400);

    return () => clearInterval(interval);
  }, []);

  // Poll repo status while cloning/analyzing
  useEffect(() => {
    if (
      repo &&
      (repo.status === "cloning" ||
        repo.status === "analyzing" ||
        repo.status === "pending")
    ) {
      pollRef.current = setInterval(async () => {
        try {
          const updated = await getRepo(repo.id);
          setRepo(updated);
          if (
            updated.status === "ready" ||
            updated.status === "failed"
          ) {
            if (pollRef.current) clearInterval(pollRef.current);
          }
        } catch {
          // ignore polling errors
        }
      }, 2000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repo?.id, repo?.status]);

  useEffect(() => {
    if (repo && repo.status === "ready" && !targetBaseUrl) {
      const isRender = typeof window !== "undefined" && window.location.hostname.includes("onrender.com");
      const ghLower = (repo.github_url || "").toLowerCase();
      if (ghLower.includes("packet_analyzer") || ghLower.includes("packet-analyzer")) {
        setTargetBaseUrl("https://packet-analyzer-9lp9.onrender.com");
      } else if (isRender) {
        setTargetBaseUrl("https://automation-testing-agent-backend.onrender.com");
      } else if (repo.framework_detected === "fastapi" || repo.framework_detected === "django") {
        setTargetBaseUrl("http://localhost:8000");
      } else if (repo.framework_detected === "flask") {
        setTargetBaseUrl("http://localhost:5000");
      } else {
        setTargetBaseUrl("http://localhost:3000");
      }
    }
  }, [repo, targetBaseUrl]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setError("");
    setLoading(true);
    setRepo(null);

    try {
      const created = await createRepo(url.trim());
      setRepo(created);
      await analyzeRepo(created.id);
      const updated = await getRepo(created.id);
      setRepo(updated);
    } catch (err: unknown) {
      const error = err as Error;
      setError(error.message || "Failed to connect repository");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateTests() {
    if (!repo) return;
    setGenerating(true);
    try {
      await generateTests(repo.id, targetBaseUrl || undefined);
      await new Promise((r) => setTimeout(r, 3000));
      const updated = await getRepo(repo.id);
      setRepo(updated);
    } catch (err: unknown) {
      const error = err as Error;
      setError(error.message);
    } finally {
      setGenerating(false);
    }
  }

  async function handleRunTests() {
    if (!repo) return;
    setRunStarted(true);
    try {
      const run = await createTestRun({
        repo_id: repo.id,
        target: targetBaseUrl || undefined,
        self_healing_enabled: true,
      });
      if (run && run.id) {
        router.push(`/runs/${run.id}`);
      }
    } catch (err: unknown) {
      const error = err as Error;
      setError(error.message);
      setRunStarted(false);
    }
  }

  const scrollToConnect = () => {
    connectSectionRef.current?.scrollIntoView({ behavior: "smooth" });
    setTimeout(() => {
      inputRef.current?.focus();
    }, 300);
  };

  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text.trim());
        inputRef.current?.focus();
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    const checkHashAndScroll = () => {
      if (typeof window !== "undefined" && window.location.hash === "#connect") {
        connectSectionRef.current?.scrollIntoView({ behavior: "smooth" });
        setTimeout(() => {
          inputRef.current?.focus();
        }, 300);
      }
    };

    checkHashAndScroll();
    window.addEventListener("hashchange", checkHashAndScroll);
    return () => window.removeEventListener("hashchange", checkHashAndScroll);
  }, []);

  return (
    <div className="space-y-24 pb-20 relative">
      
      {/* ─── Hero Section ─── */}
      <section className="relative flex flex-col items-center justify-center text-center pt-8 pb-4 px-4 overflow-hidden">
        
        {/* Decorative Grid Mesh */}
        <div className="absolute inset-0 bg-grid-mesh opacity-60 pointer-events-none [mask-image:radial-gradient(ellipse_70%_60%_at_50%_10%,black_30%,transparent_100%)] z-0" />

        {/* Ambient Top Glow Orbs */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-80 bg-gradient-to-b from-emerald-300/30 via-teal-200/20 to-transparent blur-3xl pointer-events-none -z-10" />

        <div className="relative z-10 max-w-4xl mx-auto space-y-6">
          
          {/* Top Pill Badge */}
          <div className="flex justify-center">
            <span className="relative overflow-hidden inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/95 border border-emerald-300/80 shadow-[0_4px_20px_rgba(16,185,129,0.15)] text-xs font-semibold text-emerald-900 backdrop-blur-md">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-blink" />
              Powered by local LLM + Playwright — now in beta
            </span>
          </div>

          {/* Heading */}
          <h1 className="text-5xl sm:text-7xl md:text-8xl font-extrabold tracking-tight leading-[1.08] text-[#0a291e] max-w-4xl mx-auto">
            Autonomous tests.<br />
            <span className="inline-block bg-gradient-to-r from-emerald-600 via-teal-600 to-green-500 bg-clip-text text-transparent italic pr-4 pb-1">
              Zero broken
            </span>{" "}
            <span className="inline-block bg-gradient-to-r from-teal-600 to-green-500 bg-clip-text text-transparent italic pr-4 pb-1">
              locators.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-emerald-950/80 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed font-normal">
            Connect any GitHub repository. Our agent scans framework routes, generates complete browser test suites, and heals mutated selectors using local embedding models.
          </p>

          {/* Action Buttons */}
          <div className="flex gap-4 justify-center flex-wrap pt-2">
            <button
              onClick={scrollToConnect}
              className="px-8 py-3.5 btn-emerald-glow font-bold rounded-xl text-base flex items-center gap-2 cursor-pointer shadow-md"
            >
              ⬡ Connect GitHub repo →
            </button>
            <a
              href="/evaluation"
              className="px-8 py-3.5 btn-frosted-green font-bold rounded-xl text-base flex items-center justify-center gap-2"
            >
              ▶ View Evaluation Suite
            </a>
          </div>

          {/* Quick Demo Repo Pills (1-Click Try It!) */}
          <div className="flex items-center justify-center gap-2 flex-wrap pt-3 text-xs">
            <span className="text-emerald-800 font-semibold flex items-center gap-1">
              <span>⚡</span> Quick Test:
            </span>
            {[
              {
                label: "Current Repo (Full-Stack)",
                url: "https://github.com/khushi741/automation_testing_agent",
              },
              {
                label: "FastAPI Sample",
                url: "https://github.com/tiangolo/fastapi",
              },
              {
                label: "Next.js Demo",
                url: "https://github.com/vercel/next-learn-starter",
              },
            ].map((sample) => (
              <button
                key={sample.label}
                type="button"
                onClick={() => {
                  setUrl(sample.url);
                  scrollToConnect();
                }}
                className="px-3 py-1 rounded-full bg-white/90 hover:bg-emerald-50 text-emerald-900 border border-emerald-300/80 font-mono text-[11px] font-medium shadow-2xs hover:border-emerald-500 transition-all cursor-pointer flex items-center gap-1"
              >
                <span className="text-emerald-600 font-bold">+</span>
                <span>{sample.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* ─── Ultra-Cool Studio IDE Terminal ─── */}
        <div className="relative w-full max-w-4xl mt-14 mx-auto z-10">
          
          {/* Card Ambient Glow Aura */}
          <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-emerald-400/30 via-teal-300/30 to-green-400/30 blur-xl opacity-70 -z-10" />

          <div className="glass-card border-emerald-300/80 overflow-hidden text-left shadow-2xl bg-white/95 rounded-2xl">
            
            {/* Window Header Bar with Tabs */}
            <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-emerald-50/90 via-teal-50/80 to-emerald-50/90 border-b border-emerald-200/80">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-400/90 inline-block shadow-2xs" />
                <span className="w-3 h-3 rounded-full bg-amber-400/90 inline-block shadow-2xs" />
                <span className="w-3 h-3 rounded-full bg-emerald-500/90 inline-block shadow-2xs" />
                
                {/* Frosted Tabs */}
                <div className="ml-4 flex items-center gap-1">
                  <button
                    onClick={() => setActiveTab("terminal")}
                    className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition-all ${
                      activeTab === "terminal"
                        ? "bg-white text-emerald-950 font-bold shadow-xs border border-emerald-200"
                        : "text-emerald-800/70 hover:text-emerald-950 hover:bg-white/50"
                    }`}
                  >
                    ▸ live-runner.zsh
                  </button>
                  <button
                    onClick={() => setActiveTab("synthesizer")}
                    className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition-all ${
                      activeTab === "synthesizer"
                        ? "bg-white text-emerald-950 font-bold shadow-xs border border-emerald-200"
                        : "text-emerald-800/70 hover:text-emerald-950 hover:bg-white/50"
                    }`}
                  >
                    ⚙ ai-synthesizer.json
                  </button>
                  <button
                    onClick={() => setActiveTab("healing")}
                    className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition-all ${
                      activeTab === "healing"
                        ? "bg-white text-emerald-950 font-bold shadow-xs border border-emerald-200"
                        : "text-emerald-800/70 hover:text-emerald-950 hover:bg-white/50"
                    }`}
                  >
                    🛡️ self-healing-matrix
                  </button>
                </div>
              </div>

              {/* Status Indicator */}
              <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-100 text-[11px] font-semibold text-emerald-900 border border-emerald-300">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                <span>Playwright Live</span>
              </div>
            </div>

            {/* Tab Contents */}
            <div className="p-6 bg-white min-h-[260px] font-mono text-sm leading-relaxed overflow-y-auto max-h-[340px]">
              {activeTab === "terminal" && (
                <div className="space-y-1">
                  {consoleLogs.map((log, index) => {
                    if (!log || typeof log !== "string") return null;
                    const isCmd = log.startsWith("$");
                    const isSuccess = log.includes("Passed") || log.includes("Success");
                    const isHealed = log.includes("Healed");
                    return (
                      <div key={index} className="flex gap-2.5 items-start">
                        <span className="text-emerald-600 select-none font-bold">›</span>
                        <span
                          className={
                            isCmd
                              ? "text-teal-950 font-bold"
                              : isSuccess
                                ? "text-emerald-700 font-semibold"
                                : isHealed
                                  ? "text-amber-700 font-semibold bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200"
                                  : "text-gray-700"
                          }
                        >
                          {log}
                        </span>
                      </div>
                    );
                  })}
                  <span className="inline-block w-2.5 h-4 bg-emerald-500 animate-blink ml-1 align-middle" />
                </div>
              )}

              {activeTab === "synthesizer" && (
                <div className="space-y-2 text-xs text-gray-800">
                  <div className="text-emerald-700 font-semibold">// AI Synthesis Pipeline generated scenarios from detected framework routes:</div>
                  <pre className="p-4 bg-emerald-50/50 rounded-xl border border-emerald-200 text-emerald-900 font-mono leading-relaxed">
{`{
  "project": "automation_testing_agent",
  "framework": "fastapi_nextjs",
  "scenarios": [
    { "id": 1, "description": "Verify /api/health returns HTTP 200 with online status" },
    { "id": 2, "description": "Navigate to repository analyzer and submit GitHub URL" },
    { "id": 3, "description": "Trigger evaluation benchmark and compare self-healing pass rates" }
  ]
}`}
                  </pre>
                </div>
              )}

              {activeTab === "healing" && (
                <div className="space-y-3 text-xs">
                  <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900">
                    <span className="font-bold">SentenceTransformer Vector Healing:</span> Calculates cosine element similarity matrix in real-time when DOM locators change.
                  </div>
                  <div className="grid grid-cols-2 gap-3 font-mono">
                    <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800">
                      <div className="font-bold mb-1 text-[11px] uppercase tracking-wider">Broken Selector (Original)</div>
                      <code>button#submit-v1</code>
                    </div>
                    <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-900">
                      <div className="font-bold mb-1 text-[11px] uppercase tracking-wider">Healed Selector (94.6% Match)</div>
                      <code>button[data-testid=&apos;submit-btn&apos;]</code>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Studio Footer Telemetry Bar */}
            <div className="px-5 py-2.5 bg-gradient-to-r from-emerald-50/80 via-teal-50/60 to-emerald-50/80 border-t border-emerald-100 flex items-center justify-between text-xs text-emerald-900 font-mono flex-wrap gap-2">
              <div className="flex items-center gap-4">
                <span>⚡ Latency: <strong>18ms</strong></span>
                <span>🎯 Healing Confidence: <strong className="text-emerald-700">94.6%</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <span>🛡️ Engine: <strong>SentenceTransformer + Playwright</strong></span>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ─── Process Flow (Interactive Timeline) ─── */}
      <section className="max-w-6xl mx-auto px-4 text-center space-y-10">
        <div className="space-y-2">
          <span className="font-mono text-xs uppercase tracking-widest text-emerald-800 font-bold bg-emerald-100/80 px-3 py-1 rounded-full border border-emerald-300">
            How It Works
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0a291e] tracking-tight">
            From Git commit to fully healed browser tests
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-stretch text-left">
          {[
            {
              step: "01",
              title: "Connect Repo",
              desc: "Paste your GitHub URL for automatic cloning into the sandbox.",
              icon: "⬡",
              color: "text-emerald-700",
              badge: "Clone & Parse"
            },
            {
              step: "02",
              title: "Route Discovery",
              desc: "Scans Next.js, FastAPI, Flask, React, and Django routes automatically.",
              icon: "✦",
              color: "text-teal-700",
              badge: "AST Scanner"
            },
            {
              step: "03",
              title: "AI Synthesis",
              desc: "Generates natural language test cases and browser execution steps.",
              icon: "⚙",
              color: "text-green-700",
              badge: "LLM Synthesizer"
            },
            {
              step: "04",
              title: "Playwright Run",
              desc: "Executes in a real Chromium browser instance with assertion checks.",
              icon: "☁",
              color: "text-emerald-800",
              badge: "Headless/Headed"
            },
            {
              step: "05",
              title: "Self-Healing",
              desc: "Mutated selectors are auto-healed via semantic embeddings.",
              icon: "✓",
              color: "text-emerald-600",
              badge: "Vector Recovery"
            }
          ].map((flow) => (
            <div
              key={flow.step}
              className="glass-card p-5 border-emerald-200/80 hover:border-emerald-400 flex flex-col justify-between space-y-4 group"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded border border-emerald-200">
                    Step {flow.step}
                  </span>
                  <div className={`w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-lg ${flow.color} group-hover:scale-110 transition-transform shadow-2xs`}>
                    {flow.icon}
                  </div>
                </div>
                <div>
                  <h3 className="font-bold text-base text-gray-900 group-hover:text-emerald-800 transition-colors">
                    {flow.title}
                  </h3>
                  <p className="text-xs text-gray-600 mt-1.5 leading-relaxed">
                    {flow.desc}
                  </p>
                </div>
              </div>

              <div className="pt-2 border-t border-emerald-100/80 flex items-center justify-between text-[11px] font-mono text-emerald-800">
                <span>{flow.badge}</span>
                <span>→</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Connection Panel (Active Tool Dashboard) ─── */}
      <section id="connect" ref={connectSectionRef} className="max-w-4xl mx-auto px-4 scroll-mt-24 space-y-6">
        
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-800 bg-emerald-100/90 px-3 py-1 rounded-full border border-emerald-300">
            <span>🚀 Live Workbench</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0a291e] tracking-tight">
            Connect & Analyze Repository
          </h2>
          <p className="text-gray-600 text-sm">
            Enter a public GitHub repository. Our agent will inspect files, map frontend/backend routes, and generate an actionable test suite.
          </p>
        </div>

        {/* Input Form Card */}
        <form onSubmit={handleSubmit} className="glass-card p-6 border-emerald-300/80 shadow-lg space-y-4 bg-white/95">
          <div className="flex items-center justify-between">
            <label className="text-sm font-bold text-emerald-950 flex items-center gap-2">
              <span>GitHub Repository URL</span>
            </label>
            <button
              type="button"
              onClick={handlePasteClipboard}
              className="text-xs text-emerald-700 hover:text-emerald-900 font-medium hover:underline flex items-center gap-1 cursor-pointer"
            >
              <span>📋 Paste from clipboard</span>
            </button>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-mono text-sm">
                gh:
              </span>
              <input
                id="repo-url-input"
                ref={inputRef}
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/username/repo"
                className="w-full pl-12 pr-4 py-3.5 bg-white border border-emerald-300 rounded-xl text-gray-900 placeholder-gray-400 font-mono text-sm focus:outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-400/25 transition-all shadow-xs"
                required
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="px-7 py-3.5 btn-emerald-glow font-bold rounded-xl text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap cursor-pointer flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                  <span>Connecting & Cloning...</span>
                </>
              ) : (
                <span>⚡ Analyze Repo</span>
              )}
            </button>
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-center gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}
        </form>

        {/* Status Stepper & Routes Result */}
        {repo && (
          <div className="glass-card p-6 border-emerald-300/80 space-y-6 shadow-xl bg-white/95">
            <div className="flex items-center justify-between border-b border-emerald-100 pb-4 flex-wrap gap-2">
              <div className="flex items-center gap-3">
                <StatusDot status={repo.status} />
                <h3 className="text-lg font-bold text-gray-900 font-mono">
                  {repo.github_url.split("/").slice(-1)[0]}
                </h3>
              </div>
              <span className={`badge badge-${repo.status === "ready" ? "completed" : repo.status === "failed" ? "failed" : "running"}`}>
                {repo.status}
              </span>
            </div>

            {/* Stepper */}
            <div className="grid grid-cols-3 gap-4">
              {[
                {
                  label: "1. Clone Repo",
                  done: ["analyzing", "ready"].includes(repo.status),
                  active: repo.status === "cloning",
                },
                {
                  label: "2. Detect Framework",
                  done: repo.status === "ready",
                  active: repo.status === "analyzing",
                },
                {
                  label: "3. Scan Routes",
                  done: repo.status === "ready",
                  active: false,
                },
              ].map((step) => (
                <div
                  key={step.label}
                  className={`p-4 rounded-xl border text-center transition-all ${
                    step.done
                      ? "border-emerald-400 bg-emerald-50 text-emerald-900 shadow-2xs font-semibold"
                      : step.active
                        ? "border-teal-400 bg-teal-50 text-teal-900 font-semibold animate-pulse"
                        : "border-gray-200 bg-gray-50/50 text-gray-400"
                  }`}
                >
                  <div className="text-xl mb-1 font-bold">
                    {step.done ? "✓" : step.active ? "◉" : "○"}
                  </div>
                  <div className="text-xs">{step.label}</div>
                </div>
              ))}
            </div>

            {/* Framework & Route Scan Info */}
            {repo.status === "ready" && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-200 shadow-2xs">
                    <div className="text-xs text-emerald-800 mb-1 font-semibold">Framework Detected</div>
                    <div className="text-base font-bold text-emerald-950 capitalize font-mono">
                      {repo.framework_detected || "Unknown"}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-200 shadow-2xs">
                    <div className="text-xs text-emerald-800 mb-1 font-semibold">Routes Found</div>
                    <div className="text-base font-bold text-emerald-700 font-mono">
                      {repo.routes_json?.length || 0} Endpoints
                    </div>
                  </div>
                </div>

                {/* Scanned Routes List */}
                {repo.routes_json && repo.routes_json.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-gray-800 uppercase tracking-wider flex items-center justify-between">
                      <span>Scanned Route Manifest</span>
                      <span className="text-emerald-700 font-mono font-medium">{repo.routes_json.length} paths</span>
                    </h4>
                    <div className="rounded-xl border border-emerald-200/90 overflow-hidden bg-white shadow-xs">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="bg-emerald-50/90 border-b border-emerald-200">
                            <th className="px-4 py-2.5 text-emerald-950 font-bold">Path</th>
                            <th className="px-4 py-2.5 text-emerald-950 font-bold">Method</th>
                            <th className="px-4 py-2.5 text-emerald-950 font-bold">Source File</th>
                          </tr>
                        </thead>
                        <tbody>
                          {repo.routes_json.map((route: Route, i: number) => (
                            <tr
                              key={i}
                              className="border-b border-emerald-50 hover:bg-emerald-50/60 transition-colors"
                            >
                              <td className="px-4 py-2.5 font-mono text-emerald-900 font-bold">{route.path}</td>
                              <td className="px-4 py-2.5">
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 border border-emerald-300 text-emerald-900">
                                  {route.method}
                                </span>
                              </td>
                              <td className="px-4 py-2.5 text-gray-600 font-mono">{route.file}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Target Application Base URL Config */}
                <div className="p-4 rounded-xl bg-white border border-emerald-200/90 shadow-2xs space-y-2.5">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <label className="text-xs font-bold text-emerald-950 uppercase tracking-wider flex items-center gap-1.5">
                      <span>🌐 Target Base URL</span>
                    </label>
                    <span className="text-[11px] text-gray-500">Destination host where tests execute</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="url"
                      value={targetBaseUrl}
                      onChange={(e) => setTargetBaseUrl(e.target.value)}
                      placeholder="e.g. https://packet-analyzer-9lp9.onrender.com or http://localhost:8001"
                      className="flex-1 px-3.5 py-2.5 bg-emerald-50/40 border border-emerald-300 rounded-xl text-gray-900 font-mono text-xs focus:outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-400/25 transition-all shadow-2xs"
                    />
                    {repo.generated_cases && repo.generated_cases.length > 0 && (
                      <button
                        type="button"
                        onClick={handleGenerateTests}
                        disabled={generating}
                        className="px-3.5 py-2.5 bg-emerald-100 hover:bg-emerald-200 text-emerald-900 font-bold rounded-xl text-xs border border-emerald-300 transition-all flex items-center gap-1 shrink-0 cursor-pointer shadow-2xs"
                        title="Re-synthesize tests with this updated base URL"
                      >
                        <span>🔄 Update URL</span>
                      </button>
                    )}
                  </div>
                  {/* Preset quick selection pills */}
                  <div className="flex items-center gap-1.5 flex-wrap text-[11px]">
                    <span className="text-gray-500 font-medium">Quick presets:</span>
                    <button
                      type="button"
                      onClick={() => setTargetBaseUrl("https://automation-testing-agent-backend.onrender.com")}
                      className="px-2 py-0.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800 font-mono font-semibold transition-colors cursor-pointer"
                    >
                      Live Backend API
                    </button>
                    <button
                      type="button"
                      onClick={() => setTargetBaseUrl("https://packet-analyzer-9lp9.onrender.com")}
                      className="px-2 py-0.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 border border-indigo-300 text-indigo-800 font-mono font-semibold transition-colors cursor-pointer"
                    >
                      Packet Analyzer (Live)
                    </button>
                    <button
                      type="button"
                      onClick={() => setTargetBaseUrl("http://localhost:8001")}
                      className="px-2 py-0.5 rounded-lg bg-gray-50 hover:bg-emerald-50 border border-gray-200 text-gray-700 hover:text-emerald-800 font-mono transition-colors cursor-pointer"
                    >
                      Port 8001
                    </button>
                    <button
                      type="button"
                      onClick={() => setTargetBaseUrl("http://localhost:8000")}
                      className="px-2 py-0.5 rounded-lg bg-gray-50 hover:bg-emerald-50 border border-gray-200 text-gray-700 hover:text-emerald-800 font-mono transition-colors cursor-pointer"
                    >
                      Port 8000
                    </button>
                    <button
                      type="button"
                      onClick={() => setTargetBaseUrl("http://localhost:3000")}
                      className="px-2 py-0.5 rounded-lg bg-gray-50 hover:bg-emerald-50 border border-gray-200 text-gray-700 hover:text-emerald-800 font-mono transition-colors cursor-pointer"
                    >
                      Port 3000
                    </button>
                  </div>
                </div>

                {/* Action button to generate tests */}
                {(!repo.generated_cases || repo.generated_cases.length === 0) && (
                  <button
                    onClick={handleGenerateTests}
                    disabled={generating}
                    className="w-full py-4 btn-emerald-glow font-bold rounded-xl text-sm transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
                  >
                    {generating ? (
                      <>
                        <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                        <span>Synthesizing Test Scenarios with AI...</span>
                      </>
                    ) : (
                      <span>🤖 Synthesize Test Scenarios with AI</span>
                    )}
                  </button>
                )}

                {/* Generated cases view & execute button */}
                {repo.generated_cases && repo.generated_cases.length > 0 && (
                  <div className="space-y-4 pt-2">
                    <h4 className="text-xs font-bold text-gray-800 uppercase tracking-wider flex items-center justify-between">
                      <span>Synthesized Scenarios ({repo.generated_cases.length})</span>
                      <span className="text-emerald-700 font-mono text-xs">Ready for execution</span>
                    </h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                      {repo.generated_cases.map((tc) => (
                        <div
                          key={tc.id}
                          className="p-3.5 rounded-xl bg-emerald-50/50 border border-emerald-200 flex items-start gap-3 hover:bg-emerald-50 transition-colors"
                        >
                          <span className="text-emerald-600 font-bold">▸</span>
                          <div className="space-y-0.5">
                            <p className="text-sm text-gray-900 font-medium leading-snug">{tc.description}</p>
                            {tc.source_route && (
                              <p className="text-[11px] text-emerald-800 font-mono font-medium">
                                Target: {tc.source_route}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    <button
                      onClick={handleRunTests}
                      disabled={runStarted}
                      className="w-full py-4 btn-emerald-glow font-bold rounded-xl text-sm transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
                    >
                      {runStarted ? (
                        <>
                          <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                          <span>Launching & Redirecting to Test Run...</span>
                        </>
                      ) : (
                        <span>🚀 Execute Test Suite with Self-Healing</span>
                      )}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </section>

      {/* ─── Capabilities Feature Matrix ─── */}
      <section className="max-w-6xl mx-auto px-4 space-y-10">
        <div className="text-center space-y-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-xs text-emerald-900 font-bold border border-emerald-300">
            Capabilities
          </span>
          <h3 className="font-serif text-4xl text-[#0a291e]">Everything in one pipeline</h3>
          <p className="text-sm text-gray-600 max-w-md mx-auto leading-relaxed">
            From framework route scanning to dynamic self-healing runs — no configurations needed.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            {
              icon: "🔍",
              title: "Framework Route Scanner",
              desc: "Deep AST parsing maps endpoints across Next.js App Router, FastAPI, Flask, React, and Django with file references."
            },
            {
              icon: "🤖",
              title: "AI Scenario Synthesizer",
              desc: "Translates code routes into realistic user flows: auth forms, navigation, state mutations, and API requests."
            },
            {
              icon: "⚡",
              title: "Playwright Integration",
              desc: "Fast headless Chromium test execution with console crash monitoring, network tracing, and visual diffs."
            },
            {
              icon: "🛡️",
              title: "Vector Self-Healing",
              desc: "SentenceTransformer cosine embeddings repair broken UI locators on-the-fly without stopping execution."
            },
            {
              icon: "📁",
              title: "Exact File Target Pinpointing",
              desc: "When a test fails, the diagnostic engine isolates the exact file and line to paste the suggested fix snippet."
            },
            {
              icon: "📊",
              title: "20-Case Benchmark Suite",
              desc: "Validates healing accuracy on mutated IDs, rewritten classes, and renamed buttons to prove recovery rates."
            }
          ].map((cap) => (
            <div
              key={cap.title}
              className="glass-card p-6 border-emerald-200/90 hover:border-emerald-400 space-y-3.5 group shadow-xs"
            >
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-100 to-teal-100 border border-emerald-300 flex items-center justify-center text-xl shadow-xs group-hover:scale-110 transition-transform">
                {cap.icon}
              </div>
              <h4 className="font-bold text-base text-gray-900 group-hover:text-emerald-900 transition-colors">
                {cap.title}
              </h4>
              <p className="text-xs text-gray-600 leading-relaxed font-normal">
                {cap.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

    </div>
  );
}
