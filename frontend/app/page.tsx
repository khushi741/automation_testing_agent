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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [runStarted, setRunStarted] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const connectSectionRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Mock console log simulation
  const [consoleLogs, setConsoleLogs] = useState<string[]>([]);
  useEffect(() => {
    const lines = [
      "$ autotest analyze https://github.com/khushi/todo-app",
      "Cloning repository into scratch directory... Success (1.8s)",
      "Detecting project framework... Next.js (App Router) detected",
      "Extracting application routes... Found 4 active routes",
      "  - GET  / (Dashboard)",
      "  - GET  /login (Sign In)",
      "  - GET  /settings (User Settings)",
      "  - GET  /tasks (Task List)",
      "Running AI Test Case Synthesizer...",
      "Successfully generated 12 natural language test scenarios",
      "Executing Playwright runner with self-healing engine...",
      "  [1/4] GET /login -> Passed",
      "  [2/4] GET /tasks -> Passed",
      "  [3/4] GET /settings -> Healed (button selector changed: matched login_submit with 92% confidence)",
      "  [4/4] GET / -> Passed",
      "All tests completed. Generating execution report... Done!"
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
    }, 1500);

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
      await generateTests(repo.id);
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
    <div className="space-y-20 pb-20">
      
      {/* ─── Hero Section ─── */}
      <section className="relative flex flex-col items-center justify-center text-center pt-10 pb-8 px-4 overflow-hidden">
        {/* Soft emerald dot-grid ambient background */}
        <div className="absolute inset-0 opacity-30 pointer-events-none bg-[radial-gradient(#10b981_1.2px,transparent_1.2px)] [background-size:26px_26px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,black_0%,transparent_100%)] z-0"></div>

        <div className="relative z-10 max-w-4xl mx-auto space-y-6">
          {/* Badge */}
          <div className="flex justify-center">
            <span className="relative overflow-hidden inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800 shadow-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-blink" />
              Powered by local LLM + Playwright — now in beta
            </span>
          </div>

          {/* Heading */}
          <h1 className="font-serif text-6xl md:text-8xl tracking-tight leading-[0.95] text-[#0f2e22] max-w-3xl mx-auto">
            Connect repo.<br />
            <span className="bg-gradient-to-r from-emerald-600 via-teal-600 to-green-600 bg-clip-text text-transparent italic">
              AI tests it.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-gray-600 text-lg md:text-xl max-w-xl mx-auto leading-relaxed">
            Connect your GitHub repository, let our AI generate a complete test suite, and watch Playwright execute them locally — with self-healing.
          </p>

          {/* Action Buttons */}
          <div className="flex gap-4 justify-center flex-wrap pt-4">
            <button
              onClick={scrollToConnect}
              className="px-8 py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-xl transition-all shadow-lg shadow-emerald-600/20 transform hover:-translate-y-0.5"
            >
              ⬡ Connect GitHub repo →
            </button>
            <a
              href="/evaluation"
              className="px-8 py-3.5 bg-white hover:bg-emerald-50/70 text-emerald-900 border border-emerald-200 font-semibold rounded-xl transition-all flex items-center justify-center gap-2 shadow-xs hover:border-emerald-300"
            >
              ▶ View Evaluation Suite
            </a>
          </div>
        </div>

        {/* Mock Terminal Console */}
        <div className="relative w-full max-w-3xl mt-16 mx-auto z-10">
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-emerald-500/15 to-teal-500/10 filter blur-xl -z-10"></div>
          <div className="glass-card border-emerald-200/80 overflow-hidden text-left shadow-xl bg-white/95">
            {/* Header bar */}
            <div className="flex items-center gap-2 px-5 py-3.5 bg-emerald-50/80 border-b border-emerald-100">
              <span className="w-3 h-3 rounded-full bg-rose-400 inline-block" />
              <span className="w-3 h-3 rounded-full bg-amber-400 inline-block" />
              <span className="w-3 h-3 rounded-full bg-emerald-400 inline-block" />
              <span className="font-mono text-xs text-emerald-800/80 font-medium ml-3">autotest — zsh</span>
            </div>
            {/* Logs Area */}
            <div className="p-6 bg-white min-height-[240px] font-mono text-sm leading-relaxed text-gray-700 overflow-y-auto max-h-[300px]">
              {consoleLogs.map((log, index) => {
                if (!log || typeof log !== "string") return null;
                const isCmd = log.startsWith("$");
                const isSuccess = log.includes("Passed") || log.includes("Success");
                const isHealed = log.includes("Healed");
                return (
                  <div key={index} className="flex gap-2">
                    <span className="text-emerald-500 select-none font-bold">›</span>
                    <span
                      className={
                        isCmd
                          ? "text-teal-900 font-bold"
                          : isSuccess
                            ? "text-emerald-700 font-medium"
                            : isHealed
                              ? "text-amber-700 font-medium"
                              : "text-gray-600"
                      }
                    >
                      {log}
                    </span>
                  </div>
                );
              })}
              <span className="inline-block w-2 h-4 bg-emerald-500 animate-blink ml-1 align-middle" />
            </div>
          </div>
        </div>
      </section>

      {/* ─── Process Flow (How it flows) ─── */}
      <section className="max-w-6xl mx-auto px-4 text-center space-y-12">
        <p className="font-mono text-xs uppercase tracking-widest text-emerald-700 font-bold">
          How it flows
        </p>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 md:gap-0 items-center justify-between text-left">
          {[
            {
              step: "01",
              title: "GitHub Repo",
              desc: "Connect and clone projects",
              icon: "⬡",
              color: "text-emerald-700"
            },
            {
              step: "02",
              title: "AI Analysis",
              desc: "Map routes and structures",
              icon: "✦",
              color: "text-teal-700"
            },
            {
              step: "03",
              title: "Test Cases",
              desc: "Auto-generate steps",
              icon: "⚙",
              color: "text-green-700"
            },
            {
              step: "04",
              title: "Playwright",
              desc: "Fast browser execution",
              icon: "☁",
              color: "text-emerald-800"
            },
            {
              step: "05",
              title: "Self-Healing",
              desc: "Fix selectors automatically",
              icon: "✓",
              color: "text-emerald-600"
            }
          ].map((flow, i) => (
            <div key={flow.step} className="flex items-center w-full relative">
              <div className="flex flex-col items-center text-center space-y-3 w-full px-4">
                <div className={`w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-2xl ${flow.color} shadow-sm`}>
                  {flow.icon}
                </div>
                <div>
                  <h4 className="font-semibold text-sm text-gray-900">{flow.title}</h4>
                  <p className="text-xs text-gray-500 mt-1 max-w-[150px] mx-auto leading-relaxed">{flow.desc}</p>
                </div>
              </div>

              {/* Connecting line */}
              {i < 4 && (
                <div className="hidden md:block absolute right-[-20px] top-[28px] w-10 h-[1px] bg-gradient-to-r from-emerald-300 to-teal-300 z-0">
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-emerald-400" />
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ─── Connection Panel (Active Tool Dashboard) ─── */}
      <section id="connect" ref={connectSectionRef} className="max-w-4xl mx-auto px-4 scroll-mt-24 space-y-6">
        <div>
          <h2 className="text-3xl font-bold font-serif text-[#0f2e22] flex items-center gap-2">
            <span className="bg-gradient-to-r from-emerald-700 to-teal-700 bg-clip-text text-transparent">
              Connect Repository
            </span>
          </h2>
          <p className="text-gray-600 text-sm mt-1">
            Submit a GitHub repository URL to analyze its framework, extract page routes, and generate tests.
          </p>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="glass-card p-6 border-emerald-200/80">
          <label className="block text-sm font-semibold text-emerald-900 mb-2">
            GitHub Repository URL
          </label>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              id="repo-url-input"
              ref={inputRef}
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/username/repo"
              className="flex-1 px-4 py-3 bg-white border border-emerald-200/90 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-400/20 transition-all shadow-xs"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-emerald-600/20 whitespace-nowrap"
            >
              {loading ? "Connecting..." : "Analyze Repo"}
            </button>
          </div>
          {error && (
            <p className="mt-3 text-sm text-rose-600 font-medium">{error}</p>
          )}
        </form>

        {/* Status Stepper & Routes Result */}
        {repo && (
          <div className="glass-card p-6 border-emerald-200/80 space-y-6">
            <div className="flex items-center justify-between border-b border-emerald-100 pb-4">
              <div className="flex items-center gap-3">
                <StatusDot status={repo.status} />
                <h3 className="text-lg font-semibold text-gray-900">
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
                  label: "Clone Repository",
                  done: ["analyzing", "ready"].includes(repo.status),
                  active: repo.status === "cloning",
                },
                {
                  label: "Detect Framework",
                  done: repo.status === "ready",
                  active: repo.status === "analyzing",
                },
                {
                  label: "Scan Page Routes",
                  done: repo.status === "ready",
                  active: false,
                },
              ].map((step) => (
                <div
                  key={step.label}
                  className={`p-4 rounded-xl border text-center transition-all ${
                    step.done
                      ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                      : step.active
                        ? "border-teal-400 bg-teal-50 text-teal-800"
                        : "border-gray-200 bg-gray-50/50 text-gray-400"
                  }`}
                >
                  <div className="text-xl mb-1 font-bold">
                    {step.done ? "✓" : step.active ? "◉" : "○"}
                  </div>
                  <div className="text-xs font-semibold">{step.label}</div>
                </div>
              ))}
            </div>

            {/* Framework & Route Scan Info */}
            {repo.status === "ready" && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200/80">
                    <div className="text-xs text-gray-500 mb-1">Framework Detected</div>
                    <div className="text-base font-semibold text-emerald-900 capitalize">
                      {repo.framework_detected || "Unknown"}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200/80">
                    <div className="text-xs text-gray-500 mb-1">Routes Found</div>
                    <div className="text-base font-semibold text-emerald-700">
                      {repo.routes_json?.length || 0}
                    </div>
                  </div>
                </div>

                {/* Scanned Routes List */}
                {repo.routes_json && repo.routes_json.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                      Routes List
                    </h4>
                    <div className="rounded-xl border border-emerald-200/80 overflow-hidden bg-white shadow-xs">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="bg-emerald-50/90 border-b border-emerald-100">
                            <th className="px-4 py-2.5 text-emerald-900 font-semibold">Path</th>
                            <th className="px-4 py-2.5 text-emerald-900 font-semibold">Method</th>
                            <th className="px-4 py-2.5 text-emerald-900 font-semibold">Source Code File</th>
                          </tr>
                        </thead>
                        <tbody>
                          {repo.routes_json.map((route: Route, i: number) => (
                            <tr
                              key={i}
                              className="border-b border-emerald-50 hover:bg-emerald-50/50 transition-colors"
                            >
                              <td className="px-4 py-2.5 font-mono text-emerald-800 font-semibold">{route.path}</td>
                              <td className="px-4 py-2.5">
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 border border-emerald-200 text-emerald-800">
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

                {/* Action button to generate tests */}
                {(!repo.generated_cases || repo.generated_cases.length === 0) && (
                  <button
                    onClick={handleGenerateTests}
                    disabled={generating}
                    className="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-xl transition-all disabled:opacity-50 shadow-md shadow-emerald-600/20"
                  >
                    {generating ? "Generating Test Cases..." : "🤖 Generate Test Cases with AI"}
                  </button>
                )}

                {/* Generated cases view & execute button */}
                {repo.generated_cases && repo.generated_cases.length > 0 && (
                  <div className="space-y-4 pt-2">
                    <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                      Generated Scenarios ({repo.generated_cases.length})
                    </h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {repo.generated_cases.map((tc) => (
                        <div
                          key={tc.id}
                          className="p-3.5 rounded-xl bg-emerald-50/50 border border-emerald-100 flex items-start gap-3"
                        >
                          <span className="text-emerald-600 font-bold">▸</span>
                          <div className="space-y-0.5">
                            <p className="text-sm text-gray-800 leading-snug">{tc.description}</p>
                            {tc.source_route && (
                              <p className="text-[10px] text-emerald-700 font-mono">
                                Target Route: {tc.source_route}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    <button
                      onClick={handleRunTests}
                      disabled={runStarted}
                      className="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-xl transition-all disabled:opacity-50 shadow-md shadow-emerald-600/20"
                    >
                      {runStarted ? "🚀 Launching & Redirecting to Test Run..." : "🚀 Execute AI Test Suite"}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </section>

      {/* ─── Capabilities Section ─── */}
      <section className="max-w-6xl mx-auto px-4 space-y-12">
        <div className="text-center space-y-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-semibold shadow-xs">
            Capabilities
          </span>
          <h3 className="font-serif text-4xl text-[#0f2e22]">Everything in one pipeline</h3>
          <p className="text-sm text-gray-600 max-w-md mx-auto leading-relaxed">
            From framework route scanning to dynamic self-healing runs — no configurations needed.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              icon: "⬡",
              title: "Framework Scanner",
              desc: "Analyzes projects and maps routes in Next.js, React, Flask, Express, Django and more."
            },
            {
              icon: "✦",
              title: "AI Test Synth",
              desc: "Synthesizes complete user login, navigation, and form interaction scenarios in plain English."
            },
            {
              icon: "☁",
              title: "Playwright Integration",
              desc: "Runs tests on a persistent local Chromium browser instance, reducing initialization delays."
            },
            {
              icon: "🎬",
              title: "Visual Logs",
              desc: "Captures step-by-step logs and screenshots for every test execution to ease error root-causing."
            },
            {
              icon: "🔁",
              title: "Semantic Self-Healing",
              desc: "Matches selectors semantically using SentenceTransformer embeddings, tolerating broken code."
            },
            {
              icon: "📊",
              title: "Evaluation Suite",
              desc: "Features a 20-scenario comparison run comparing normal runs against heals and failures."
            }
          ].map((cap) => (
            <div key={cap.title} className="glass-card p-6 border-emerald-100/90 hover:border-emerald-300 space-y-3 shadow-xs">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-lg text-emerald-700">
                {cap.icon}
              </div>
              <h4 className="font-semibold text-sm text-gray-900">{cap.title}</h4>
              <p className="text-xs text-gray-600 leading-relaxed">{cap.desc}</p>
            </div>
          ))}
        </div>
      </section>

    </div>
  );
}
