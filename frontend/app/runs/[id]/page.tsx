"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getTestRun,
  TestRun,
  ExecutionStep,
  screenshotUrl,
  CaseDiagnostic,
  getTestCaseDiagnosis,
} from "@/lib/api";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const [run, setRun] = useState<TestRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedCases, setExpandedCases] = useState<Record<string, boolean>>({});
  const [diagnostics, setDiagnostics] = useState<Record<string, CaseDiagnostic>>({});
  const [loadingDiag, setLoadingDiag] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  async function toggleCase(tcId: string) {
    const nextState = !expandedCases[tcId];
    setExpandedCases((prev) => ({ ...prev, [tcId]: nextState }));

    if (nextState && !diagnostics[tcId]) {
      setLoadingDiag((prev) => ({ ...prev, [tcId]: true }));
      try {
        const diag = await getTestCaseDiagnosis(tcId);
        setDiagnostics((prev) => ({ ...prev, [tcId]: diag }));
      } catch (err) {
        console.error("Failed to load diagnosis:", err);
      } finally {
        setLoadingDiag((prev) => ({ ...prev, [tcId]: false }));
      }
    }
  }

  function copySnippet(code: string, id: string) {
    navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  }

  const [loadError, setLoadError] = useState<string | null>(null);

  async function loadRun() {
    try {
      const data = await getTestRun(runId);
      setRun(data);
      setLoadError(null);
    } catch (err: unknown) {
      const error = err as Error;
      setLoadError(error.message || "Run not found");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadRun();
    const interval = setInterval(async () => {
      try {
        const data = await getTestRun(runId);
        setRun(data);
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  // Live timer for active runs so users see second-by-second updates
  useEffect(() => {
    if (run?.status !== "running") return;
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [run?.status]);

  if (loading) {
    return (
      <div className="glass-card p-16 text-center max-w-lg mx-auto my-12 space-y-4 bg-white/95 border-emerald-200 shadow-md">
        <div className="w-10 h-10 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <div className="space-y-1">
          <h3 className="font-bold text-gray-900 text-lg">Connecting to Test Runner...</h3>
          <p className="text-xs text-gray-600 leading-relaxed max-w-sm mx-auto">
            Fetching run status and execution logs. If the cloud container is waking up from idle, this may take a moment.
          </p>
        </div>
      </div>
    );
  }

  if (!run || loadError) {
    return (
      <div className="glass-card p-12 text-center max-w-xl mx-auto my-12 space-y-6 bg-white/95 border-emerald-200 shadow-md">
        <div className="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-3xl mx-auto shadow-2xs">
          🔍
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-extrabold text-[#0a291e]">
            Test Run Not Found or Expired
          </h2>
          <p className="text-sm text-gray-600 leading-relaxed max-w-md mx-auto">
            Run ID <code className="font-mono text-emerald-900 bg-emerald-100/80 px-2 py-0.5 rounded border border-emerald-200 text-xs font-bold">{runId}</code> does not exist in the active database.
          </p>
          <p className="text-xs text-gray-500 max-w-sm mx-auto">
            On cloud free tiers, previous test sessions are cleared whenever the container redeploys or restarts with a fresh database.
          </p>
        </div>

        <div className="flex items-center justify-center gap-3 flex-wrap pt-2">
          <Link
            href="/runs"
            className="px-5 py-2.5 btn-frosted-green font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-2xs"
          >
            ← View Active Test Runs
          </Link>
          <Link
            href="/#connect"
            className="px-5 py-2.5 btn-emerald-glow font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-xs"
          >
            ⚡ Start a New Test
          </Link>
          <Link
            href="/evaluation"
            className="px-5 py-2.5 bg-white border border-emerald-200 hover:bg-emerald-50 text-emerald-900 font-bold rounded-xl text-xs transition-colors"
          >
            📊 Run Evaluation Suite
          </Link>
        </div>
      </div>
    );
  }

  const passRate =
    run.pass_count + run.fail_count > 0
      ? ((run.pass_count / (run.pass_count + run.fail_count)) * 100).toFixed(1)
      : "0.0";

  const isRunning = run.status === "running";
  const isQueued = run.status === "queued";
  const totalCases = run.test_cases?.length || (run.pass_count + run.fail_count + run.heal_count) || 1;
  const completedCases = run.pass_count + run.fail_count + run.heal_count;
  const currentRunningIdx = isRunning && run.test_cases
    ? run.test_cases.findIndex((tc) => tc.status === "pending" || tc.status === "running")
    : -1;
  const currentRunningCase = currentRunningIdx !== -1 && run.test_cases
    ? run.test_cases[currentRunningIdx]
    : null;
  const progressPercent = totalCases > 0
    ? Math.min(100, Math.round((completedCases / totalCases) * 100))
    : (isRunning ? 10 : 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold font-serif mb-1 text-[#0f2e22]">
            <span className="bg-gradient-to-r from-emerald-700 via-teal-700 to-green-600 bg-clip-text text-transparent">
              Run {run.id.slice(0, 8)}
            </span>
          </h1>
          <p className="text-gray-600 text-sm">
            Target:{" "}
            {run.target && run.target.includes("/") ? (
              <a
                href={`https://github.com/${run.target}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-700 hover:text-emerald-900 hover:underline font-mono font-semibold"
              >
                {run.target} ↗
              </a>
            ) : (
              <span className="text-gray-800 font-semibold">{run.target || "demo"}</span>
            )}{" "}
            • Self-Healing: <span className="font-medium text-emerald-800">{run.self_healing_enabled ? "On" : "Off"}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`badge badge-${run.status} ${
              isRunning
                ? "ring-2 ring-emerald-400 bg-emerald-50 text-emerald-900 font-bold shadow-md shadow-emerald-500/20"
                : ""
            }`}
          >
            {isRunning && (
              <span className="relative flex h-2.5 w-2.5 mr-0.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-600"></span>
              </span>
            )}
            {isRunning ? "RUNNING (LIVE)" : run.status}
          </span>
        </div>
      </div>

      {/* ─── Active Execution Live Banner ─── */}
      {isRunning && (
        <div className="glass-card p-6 border-emerald-300 bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-emerald-500/5 relative overflow-hidden shadow-lg shadow-emerald-500/5 space-y-4">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-emerald-500 via-teal-400 to-green-500 animate-pulse" />

          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3.5">
              <div className="relative flex items-center justify-center w-12 h-12 rounded-2xl bg-white border border-emerald-200 shadow-sm shrink-0">
                <span className="text-2xl animate-bounce">⚡</span>
                <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500"></span>
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-extrabold text-[#0a291e] flex items-center gap-1.5">
                    Autonomous AI Test Agent is Running...
                  </h3>
                  <span className="text-[11px] px-2.5 py-0.5 rounded-full font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300 animate-pulse">
                    LIVE PLAYWRIGHT SESSION
                  </span>
                </div>
                <p className="text-xs text-gray-600 mt-1 flex items-center gap-2 flex-wrap">
                  <span>Executing headless browser actions</span>
                  <span>•</span>
                  <span className="font-mono font-semibold text-emerald-800">
                    {currentRunningIdx !== -1
                      ? `Testing Scenario #${currentRunningIdx + 1} of ${totalCases}`
                      : "Orchestrating test suite..."}
                  </span>
                  <span>•</span>
                  <span className="text-emerald-700 font-medium">Self-Healing Engine Armed</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 sm:text-right">
              <div className="bg-white/80 border border-emerald-200 px-3 py-1.5 rounded-xl shadow-2xs font-mono text-xs">
                <div className="font-bold text-emerald-900">
                  {completedCases} / {totalCases} Done ({progressPercent}%)
                </div>
                <div className="text-[10px] text-gray-500 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping inline-block" />
                  ⏱ {elapsedSeconds}s elapsed
                </div>
              </div>
            </div>
          </div>

          {/* Animated Progress Bar */}
          <div className="space-y-1.5">
            <div className="w-full h-3 bg-emerald-100/90 rounded-full overflow-hidden relative shadow-inner p-0.5 border border-emerald-200/60">
              <div
                className="h-full bg-gradient-to-r from-emerald-600 via-teal-500 to-green-500 rounded-full transition-all duration-700 ease-out relative"
                style={{ width: `${Math.max(progressPercent, 10)}%` }}
              >
                <div className="absolute inset-0 bg-white/40 animate-shimmer" />
              </div>
            </div>
          </div>

          {/* Current Target Live Ticker */}
          <div className="flex items-center justify-between text-xs text-gray-700 font-mono bg-white/80 p-2.5 rounded-xl border border-emerald-100 shadow-2xs flex-wrap gap-2">
            <div className="flex items-center gap-2 truncate max-w-xl">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping shrink-0" />
              <span className="font-bold text-emerald-900">Current Target:</span>
              <span className="truncate text-gray-700">
                {currentRunningCase ? currentRunningCase.description : "Initializing browser page context..."}
              </span>
            </div>
            <div className="text-[11px] text-emerald-800 font-semibold flex items-center gap-1.5 shrink-0">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Auto-refreshing every 3s
            </div>
          </div>
        </div>
      )}

      {/* ─── Queued Banner ─── */}
      {isQueued && (
        <div className="glass-card p-5 border-amber-300 bg-amber-50/60 flex items-center gap-3.5 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-amber-100 border border-amber-300 flex items-center justify-center text-xl shrink-0 animate-pulse">
            ⏳
          </div>
          <div className="space-y-0.5">
            <h4 className="text-sm font-bold text-amber-950">Test Run Queued</h4>
            <p className="text-xs text-amber-900 leading-relaxed">
              Waiting for the background browser worker thread to pick up this job. Execution will start automatically in a moment.
            </p>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: "Pass Rate",
            value: `${passRate}%`,
            color: "text-emerald-700",
            glow: "glow-green",
          },
          {
            label: "Passed",
            value: run.pass_count,
            color: "text-emerald-700",
            glow: "",
          },
          {
            label: "Failed",
            value: run.fail_count,
            color: "text-rose-600",
            glow: run.fail_count > 0 ? "glow-red" : "",
          },
          {
            label: "Healed",
            value: run.heal_count,
            color: "text-amber-600",
            glow: "",
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className={`glass-card p-5 text-center bg-white border-emerald-100 ${stat.glow} ${
              isRunning ? "border-emerald-200/80 shadow-xs" : ""
            }`}
          >
            <div className={`text-3xl font-bold ${stat.color}`}>
              {stat.value}
            </div>
            <div className="text-sm text-gray-500 mt-1 font-medium">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Evaluation Banner */}
      {run.target === "evaluation" && (
        <div className="glass-card p-8 border-emerald-200 bg-emerald-50/60 text-center space-y-4 shadow-sm">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-white border border-emerald-200 flex items-center justify-center text-3xl shadow-xs">
            📊
          </div>
          <div className="space-y-1">
            <h3 className="text-xl font-bold text-gray-900">Self-Healing Evaluation Suite</h3>
            <p className="text-sm text-gray-600 max-w-lg mx-auto leading-relaxed">
              This run executes the 20-scenario synthetic benchmark evaluating dynamic button mutations, class rewrites, and semantic selector recovery.
            </p>
          </div>
          <div className="pt-2">
            <Link
              href="/evaluation"
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium rounded-xl text-sm transition-all shadow-md shadow-emerald-600/20"
            >
              Open Evaluation Dashboard & Metrics →
            </Link>
          </div>
        </div>
      )}

      {/* Test Cases */}
      {run.test_cases && run.test_cases.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">
              Test Cases ({run.test_cases.length})
            </h2>
            {isRunning && (
              <span className="text-xs text-emerald-800 font-mono flex items-center gap-1.5 font-semibold bg-emerald-100/80 px-2.5 py-1 rounded-full border border-emerald-300">
                <span className="w-2 h-2 rounded-full bg-emerald-600 animate-ping" />
                Live Agent Interacting...
              </span>
            )}
          </div>

          {run.test_cases.map((tc, idx) => {
            const isExpanded = !!expandedCases[tc.id];
            const diag = diagnostics[tc.id];
            const isLoadingDiag = loadingDiag[tc.id];
            const isThisCaseRunning = isRunning && idx === currentRunningIdx;

            return (
              <div
                key={tc.id}
                className={`glass-card transition-all duration-200 border bg-white ${
                  isThisCaseRunning
                    ? "border-emerald-400 ring-2 ring-emerald-400/80 bg-gradient-to-r from-emerald-50/60 via-teal-50/20 to-white shadow-lg shadow-emerald-500/10"
                    : tc.status === "failed"
                      ? "border-rose-200 hover:border-rose-300"
                      : tc.status === "healed"
                        ? "border-amber-200 hover:border-amber-300"
                        : "border-emerald-100 hover:border-emerald-300"
                }`}
              >
                {/* Clickable Header */}
                <div
                  onClick={() => toggleCase(tc.id)}
                  className="p-5 cursor-pointer select-none space-y-3"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <span className="text-gray-400 font-mono text-sm mt-0.5 font-bold">
                        #{idx + 1}
                      </span>
                      <div className="space-y-1">
                        <p className="text-gray-900 font-medium text-sm leading-snug">
                          {tc.description}
                        </p>
                        {isThisCaseRunning && (
                          <div className="flex items-center gap-2 pt-1 text-xs text-emerald-800 font-semibold animate-pulse">
                            <span className="w-3.5 h-3.5 rounded-full border-2 border-emerald-600 border-t-transparent animate-spin inline-block" />
                            <span>Browser agent active • Interacting with page & validating elements...</span>
                          </div>
                        )}
                        <div className="flex items-center gap-2 flex-wrap pt-0.5">
                          {tc.source_route && (
                            <span className="text-[11px] text-emerald-800 font-mono px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200">
                              Route: {tc.source_route}
                            </span>
                          )}
                          {tc.duration > 0 && (
                            <span className="text-[11px] text-gray-500 font-mono">
                              ⏱ {tc.duration.toFixed(2)}s
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {isThisCaseRunning ? (
                        <span className="badge badge-running ring-1 ring-emerald-400/80 bg-emerald-100 text-emerald-950 font-extrabold flex items-center gap-1.5 shadow-2xs">
                          <span className="w-2 h-2 rounded-full bg-emerald-600 animate-ping shrink-0" />
                          EXECUTING NOW
                        </span>
                      ) : (
                        <span className={`badge badge-${tc.status}`}>
                          {tc.status}
                        </span>
                      )}
                      <button
                        type="button"
                        className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-all ${
                          isExpanded
                            ? "bg-emerald-100 text-emerald-800 border-emerald-300 font-semibold"
                            : "bg-gray-50 text-gray-600 border-gray-200 hover:text-emerald-800 hover:bg-emerald-50"
                        }`}
                      >
                        {isExpanded ? "▲ Hide Guide" : "💡 Root Cause & Fix Guide ▼"}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Details Panel */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-0 space-y-5 border-t border-gray-100 mt-1">
                    {/* ─── AI Root Cause & Fix Guide ─── */}
                    <div className="rounded-xl border border-emerald-200/90 bg-emerald-50/40 p-5 space-y-4 mt-4">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">🤖</span>
                          <div>
                            <h4 className="font-semibold text-sm text-emerald-950">
                              AI Diagnostic & Root Cause Report
                            </h4>
                            <p className="text-[11px] text-emerald-800/80">
                              Automated error analysis and actionable fix recommendations
                            </p>
                          </div>
                        </div>

                        {diag && (
                          <div className="flex items-center gap-2">
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">
                              {diag.category}
                            </span>
                            {diag.severity && diag.severity !== "None" && (
                              <span
                                className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                  diag.severity.includes("High")
                                    ? "bg-rose-100 text-rose-800 border border-rose-200"
                                    : "bg-amber-100 text-amber-800 border border-amber-200"
                                }`}
                              >
                                {diag.severity} Priority
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {isLoadingDiag ? (
                        <div className="flex items-center gap-3 py-6 text-emerald-800 text-sm animate-pulse justify-center">
                          <span className="w-4 h-4 rounded-full border-2 border-emerald-600 border-t-transparent animate-spin" />
                          Analyzing execution logs, network trace, and failure semantics...
                        </div>
                      ) : diag ? (
                        <div className="space-y-4 text-sm">
                          {/* Title */}
                          <div className="flex items-center justify-between flex-wrap gap-2">
                            <div className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                              <span>📌</span> {diag.title}
                            </div>
                            {diag.target_file && (
                              <div className="flex items-center gap-1.5 text-xs font-mono text-emerald-900 bg-emerald-100 border border-emerald-200 px-2.5 py-1 rounded-lg">
                                <span>📁</span>
                                <span>{diag.target_file}</span>
                              </div>
                            )}
                          </div>

                          {/* Root Cause (What went wrong) */}
                          <div className="space-y-1.5">
                            <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-700 uppercase tracking-wider">
                              <span>🔍</span> What Went Wrong (Root Cause)
                            </div>
                            <div className="text-gray-800 leading-relaxed bg-white p-3.5 rounded-xl border border-rose-100 font-sans shadow-2xs">
                              {diag.root_cause}
                            </div>
                          </div>

                          {/* How Can It Be Fixed */}
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-800 uppercase tracking-wider">
                                <span>🛠️</span> How Can It Be Fixed (Actionable Solution)
                              </div>
                              {diag.target_file && !diag.suggested_code && (
                                <span className="text-xs font-mono text-emerald-900 bg-emerald-100 border border-emerald-200 px-2 py-0.5 rounded flex items-center gap-1">
                                  📁 {diag.target_file}
                                </span>
                              )}
                            </div>
                            <div className="text-gray-800 whitespace-pre-line leading-relaxed bg-white p-3.5 rounded-xl border border-emerald-100 font-sans shadow-2xs">
                              {diag.fix_recommendation}
                            </div>
                          </div>

                          {/* Suggested Code */}
                          {diag.suggested_code && (
                            <div className="space-y-2">
                              <div className="flex items-center justify-between flex-wrap gap-2">
                                <div className="flex items-center gap-1.5 text-xs font-semibold text-teal-800 uppercase tracking-wider">
                                  <span>💻</span> Recommended Code / Fix Snippet
                                </div>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    copySnippet(diag.suggested_code, tc.id);
                                  }}
                                  className="text-xs px-2.5 py-1 rounded-lg bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-200 transition-all flex items-center gap-1 font-medium shadow-xs"
                                >
                                  {copiedId === tc.id ? "✓ Copied!" : "📋 Copy Snippet"}
                                </button>
                              </div>

                              {/* Target File to Paste / Apply in */}
                              {diag.target_file && (
                                <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-emerald-100/80 border border-emerald-300 text-xs shadow-2xs">
                                  <span className="text-emerald-950 font-bold flex items-center gap-1.5 whitespace-nowrap">
                                    <span>📁</span> Target File:
                                  </span>
                                  <span className="text-emerald-800 text-xs hidden sm:inline whitespace-nowrap">
                                    Paste or modify code in:
                                  </span>
                                  <code className="font-mono text-emerald-900 bg-white px-2.5 py-1 rounded-lg border border-emerald-300 font-bold select-all break-all">
                                    {diag.target_file}
                                  </code>
                                </div>
                              )}

                              <pre className="p-4 rounded-xl bg-[#0c1813] border border-emerald-500/20 text-xs font-mono text-emerald-300 overflow-x-auto leading-relaxed shadow-inner">
                                {diag.suggested_code}
                              </pre>
                            </div>
                          )}

                          {/* Prevention Tip */}
                          {diag.prevention_tip && (
                            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-teal-50 border border-teal-200 text-xs text-teal-900">
                              <span className="text-base mt-0.5">🛡️</span>
                              <div>
                                <strong className="font-semibold text-teal-950">Engineering Prevention Tip:</strong>{" "}
                                {diag.prevention_tip}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-gray-500 text-xs py-2">
                          Diagnostic analysis unavailable.
                        </div>
                      )}
                    </div>

                    {/* ─── Execution Steps ─── */}
                    {tc.steps_json && tc.steps_json.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-medium text-gray-600 uppercase tracking-wider">
                          Execution Steps ({tc.steps_json.length})
                        </h4>
                        <div className="space-y-1.5">
                          {tc.steps_json.map((step: ExecutionStep, si: number) => (
                            <div key={si} className="space-y-1">
                              <div className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg bg-white border border-emerald-100 text-sm shadow-2xs">
                                <span
                                  className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                                    step.status === "PASSED" || step.status === "HEALED"
                                      ? "bg-emerald-100 text-emerald-800"
                                      : step.status === "FAILED"
                                        ? "bg-rose-100 text-rose-800"
                                        : "bg-gray-100 text-gray-600"
                                  }`}
                                >
                                  {si + 1}
                                </span>
                                <span className="text-gray-800 flex-1 font-mono text-xs">
                                  {step.description || `${step.action} → ${step.target}`}
                                </span>
                                <span className="text-xs text-gray-500 font-mono">
                                  {step.duration ? `${step.duration.toFixed(2)}s` : ""}
                                </span>
                                {step.status === "HEALED" && (
                                  <span className="badge badge-healed text-[10px]">
                                    HEALED
                                  </span>
                                )}
                              </div>
                              {step.error && (
                                <div className="ml-8 px-3 py-2 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 font-mono whitespace-pre-wrap">
                                  {step.error}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* ─── Healing Events ─── */}
                    {tc.healing_events && tc.healing_events.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-medium text-amber-800 uppercase tracking-wider">
                          🔧 Self-Healing Events
                        </h4>
                        <div className="space-y-2">
                          {tc.healing_events.map((he) => (
                            <div
                              key={he.id}
                              className="px-4 py-3 rounded-lg bg-amber-50/70 border border-amber-200 text-sm"
                            >
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-gray-600 text-xs font-medium">
                                  Step #{he.step_number}
                                </span>
                                <span className="text-amber-800 font-semibold text-xs">
                                  {(he.confidence_score * 100).toFixed(1)}% confidence
                                </span>
                              </div>
                              <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                                <div>
                                  <span className="text-rose-700 font-bold">Before:</span>{" "}
                                  <span className="text-gray-600">{he.original_selector}</span>
                                </div>
                                <div>
                                  <span className="text-emerald-700 font-bold">After:</span>{" "}
                                  <span className="text-gray-800">{he.healed_selector}</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* ─── Failure Screenshots ─── */}
                    {tc.screenshots && tc.screenshots.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-medium text-gray-600 uppercase tracking-wider">
                          📸 Failure Screenshots
                        </h4>
                        <div className="flex gap-3 flex-wrap">
                          {tc.screenshots.map((ss) => (
                            <a
                              key={ss.id}
                              href={screenshotUrl(ss.file_path)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="block w-56 h-36 rounded-xl overflow-hidden border border-emerald-200 hover:border-emerald-400 transition-all shadow-sm"
                            >
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              <img
                                src={screenshotUrl(ss.file_path)}
                                alt={`Step ${ss.step_number} failure`}
                                className="w-full h-full object-cover"
                              />
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : run.status === "running" || run.status === "queued" ? (
        <div className="glass-card p-12 text-center space-y-4 bg-white border-emerald-100">
          <div className="w-10 h-10 mx-auto rounded-full border-2 border-emerald-500 border-t-transparent animate-spin" />
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-gray-900">Executing Test Suite...</h3>
            <p className="text-sm text-gray-600 max-w-md mx-auto">
              Playwright browser is navigating target routes, validating assertions, and applying self-healing if selectors broke.
            </p>
          </div>
        </div>
      ) : run.target !== "evaluation" ? (
        <div className="glass-card p-12 text-center text-gray-500 bg-white border-emerald-100">
          No test cases found for this run.
        </div>
      ) : null}
    </div>
  );
}
