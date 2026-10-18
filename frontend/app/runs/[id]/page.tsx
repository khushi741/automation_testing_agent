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

  async function loadRun() {
    try {
      const data = await getTestRun(runId);
      setRun(data);
      if (data.status === "completed" || data.status === "failed") {
        // Stop polling
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadRun();
    const interval = setInterval(loadRun, 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  if (loading) {
    return (
      <div className="text-center py-20 text-gray-500">
        Loading run details...
      </div>
    );
  }

  if (!run) {
    return (
      <div className="text-center py-20 text-gray-500">Run not found.</div>
    );
  }

  const passRate =
    run.pass_count + run.fail_count > 0
      ? ((run.pass_count / (run.pass_count + run.fail_count)) * 100).toFixed(1)
      : "0.0";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-1">
            <span className="bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              Run {run.id.slice(0, 8)}
            </span>
          </h1>
          <p className="text-gray-400 text-sm">
            Target:{" "}
            {run.target && run.target.includes("/") ? (
              <a
                href={`https://github.com/${run.target}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-purple-400 hover:text-purple-300 hover:underline font-mono"
              >
                {run.target} ↗
              </a>
            ) : (
              <span className="text-slate-200 font-medium">{run.target || "demo"}</span>
            )}{" "}
            • Self-Healing: {run.self_healing_enabled ? "On" : "Off"}
          </p>
        </div>
        <span
          className={`badge badge-${run.status}`}
        >
          {run.status}
        </span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        {[
          {
            label: "Pass Rate",
            value: `${passRate}%`,
            color: "text-emerald-400",
            glow: "glow-green",
          },
          {
            label: "Passed",
            value: run.pass_count,
            color: "text-emerald-400",
            glow: "",
          },
          {
            label: "Failed",
            value: run.fail_count,
            color: "text-red-400",
            glow: run.fail_count > 0 ? "glow-red" : "",
          },
          {
            label: "Healed",
            value: run.heal_count,
            color: "text-yellow-400",
            glow: "",
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className={`glass-card p-5 text-center ${stat.glow}`}
          >
            <div className={`text-3xl font-bold ${stat.color}`}>
              {stat.value}
            </div>
            <div className="text-sm text-gray-500 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Evaluation Banner */}
      {run.target === "evaluation" && (
        <div className="glass-card p-8 border-purple-500/20 text-center space-y-4">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-purple-500/10 border border-purple-500/25 flex items-center justify-center text-3xl">
            📊
          </div>
          <div className="space-y-1">
            <h3 className="text-xl font-bold text-white">Self-Healing Evaluation Suite</h3>
            <p className="text-sm text-gray-400 max-w-lg mx-auto">
              This run executes the 20-scenario synthetic benchmark evaluating dynamic button mutations, class rewrites, and semantic selector recovery.
            </p>
          </div>
          <div className="pt-2">
            <Link
              href="/evaluation"
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium rounded-xl text-sm transition-all shadow-lg shadow-purple-500/20"
            >
              Open Evaluation Dashboard & Metrics →
            </Link>
          </div>
        </div>
      )}

      {/* Test Cases */}
      {run.test_cases && run.test_cases.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-300">
            Test Cases ({run.test_cases.length})
          </h2>

          {run.test_cases.map((tc, idx) => {
            const isExpanded = !!expandedCases[tc.id];
            const diag = diagnostics[tc.id];
            const isLoadingDiag = loadingDiag[tc.id];

            return (
              <div
                key={tc.id}
                className={`glass-card transition-all duration-200 border ${
                  tc.status === "failed"
                    ? "border-red-500/20 hover:border-red-500/40"
                    : tc.status === "healed"
                      ? "border-yellow-500/20 hover:border-yellow-500/40"
                      : "border-emerald-500/15 hover:border-emerald-500/30"
                }`}
              >
                {/* Clickable Header */}
                <div
                  onClick={() => toggleCase(tc.id)}
                  className="p-5 cursor-pointer select-none space-y-3"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <span className="text-gray-500 font-mono text-sm mt-0.5">
                        #{idx + 1}
                      </span>
                      <div className="space-y-1">
                        <p className="text-gray-100 font-medium text-sm leading-snug">
                          {tc.description}
                        </p>
                        <div className="flex items-center gap-2 flex-wrap">
                          {tc.source_route && (
                            <span className="text-[11px] text-gray-400 font-mono px-2 py-0.5 rounded bg-white/[0.04] border border-white/5">
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
                      <span className={`badge badge-${tc.status}`}>
                        {tc.status}
                      </span>
                      <button
                        type="button"
                        className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-all ${
                          isExpanded
                            ? "bg-purple-500/20 text-purple-300 border-purple-500/30"
                            : "bg-white/[0.04] text-gray-400 border-white/10 hover:text-white hover:bg-white/[0.08]"
                        }`}
                      >
                        {isExpanded ? "▲ Hide Guide" : "💡 Root Cause & Fix Guide ▼"}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Details Panel */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-0 space-y-5 border-t border-white/5 mt-1">
                    {/* ─── AI Root Cause & Fix Guide ─── */}
                    <div className="rounded-xl border border-purple-500/20 bg-purple-950/20 p-5 space-y-4 mt-4">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">🤖</span>
                          <div>
                            <h4 className="font-semibold text-sm text-purple-200">
                              AI Diagnostic & Root Cause Report
                            </h4>
                            <p className="text-[11px] text-purple-300/70">
                              Automated error analysis and actionable fix recommendations
                            </p>
                          </div>
                        </div>

                        {diag && (
                          <div className="flex items-center gap-2">
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30">
                              {diag.category}
                            </span>
                            {diag.severity && diag.severity !== "None" && (
                              <span
                                className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                  diag.severity.includes("High")
                                    ? "bg-red-500/20 text-red-300 border border-red-500/30"
                                    : "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30"
                                }`}
                              >
                                {diag.severity} Priority
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {isLoadingDiag ? (
                        <div className="flex items-center gap-3 py-6 text-purple-300/80 text-sm animate-pulse justify-center">
                          <span className="w-4 h-4 rounded-full border-2 border-purple-400 border-t-transparent animate-spin" />
                          Analyzing execution logs, network trace, and failure semantics...
                        </div>
                      ) : diag ? (
                        <div className="space-y-4 text-sm">
                          {/* Title */}
                          <div className="flex items-center justify-between flex-wrap gap-2">
                            <div className="text-sm font-semibold text-purple-100 flex items-center gap-2">
                              <span>📌</span> {diag.title}
                            </div>
                            {diag.target_file && (
                              <div className="flex items-center gap-1.5 text-xs font-mono text-purple-300 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-lg">
                                <span>📁</span>
                                <span>{diag.target_file}</span>
                              </div>
                            )}
                          </div>

                          {/* Root Cause (What went wrong) */}
                          <div className="space-y-1.5">
                            <div className="flex items-center gap-1.5 text-xs font-semibold text-red-400 uppercase tracking-wider">
                              <span>🔍</span> What Went Wrong (Root Cause)
                            </div>
                            <div className="text-gray-300 leading-relaxed bg-black/40 p-3.5 rounded-xl border border-white/5 font-sans">
                              {diag.root_cause}
                            </div>
                          </div>

                          {/* How Can It Be Fixed */}
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                                <span>🛠️</span> How Can It Be Fixed (Actionable Solution)
                              </div>
                              {diag.target_file && !diag.suggested_code && (
                                <span className="text-xs font-mono text-purple-300 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded flex items-center gap-1">
                                  📁 {diag.target_file}
                                </span>
                              )}
                            </div>
                            <div className="text-gray-300 whitespace-pre-line leading-relaxed bg-black/40 p-3.5 rounded-xl border border-white/5 font-sans">
                              {diag.fix_recommendation}
                            </div>
                          </div>

                          {/* Suggested Code */}
                          {diag.suggested_code && (
                            <div className="space-y-2">
                              <div className="flex items-center justify-between flex-wrap gap-2">
                                <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-400 uppercase tracking-wider">
                                  <span>💻</span> Recommended Code / Fix Snippet
                                </div>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    copySnippet(diag.suggested_code, tc.id);
                                  }}
                                  className="text-xs px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10 transition-all flex items-center gap-1"
                                >
                                  {copiedId === tc.id ? "✓ Copied!" : "📋 Copy Snippet"}
                                </button>
                              </div>

                              {/* Target File to Paste / Apply in */}
                              {diag.target_file && (
                                <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-purple-500/10 border border-purple-500/25 text-xs">
                                  <span className="text-purple-300 font-semibold flex items-center gap-1.5 whitespace-nowrap">
                                    <span>📁</span> Target File:
                                  </span>
                                  <span className="text-gray-400 text-xs hidden sm:inline whitespace-nowrap">
                                    Paste or modify code in:
                                  </span>
                                  <code className="font-mono text-purple-200 bg-purple-950/70 px-2.5 py-1 rounded-lg border border-purple-500/30 font-semibold select-all break-all">
                                    {diag.target_file}
                                  </code>
                                </div>
                              )}

                              <pre className="p-3.5 rounded-xl bg-black/60 border border-white/10 text-xs font-mono text-purple-200 overflow-x-auto leading-relaxed">
                                {diag.suggested_code}
                              </pre>
                            </div>
                          )}

                          {/* Prevention Tip */}
                          {diag.prevention_tip && (
                            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-200">
                              <span className="text-base mt-0.5">🛡️</span>
                              <div>
                                <strong className="font-semibold text-blue-300">Engineering Prevention Tip:</strong>{" "}
                                {diag.prevention_tip}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-gray-400 text-xs py-2">
                          Diagnostic analysis unavailable.
                        </div>
                      )}
                    </div>

                    {/* ─── Execution Steps ─── */}
                    {tc.steps_json && tc.steps_json.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Execution Steps ({tc.steps_json.length})
                        </h4>
                        <div className="space-y-1.5">
                          {tc.steps_json.map((step: ExecutionStep, si: number) => (
                            <div key={si} className="space-y-1">
                              <div className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] text-sm">
                                <span
                                  className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                                    step.status === "PASSED" || step.status === "HEALED"
                                      ? "bg-emerald-500/20 text-emerald-400"
                                      : step.status === "FAILED"
                                        ? "bg-red-500/20 text-red-400"
                                        : "bg-gray-500/20 text-gray-400"
                                  }`}
                                >
                                  {si + 1}
                                </span>
                                <span className="text-gray-300 flex-1 font-mono text-xs">
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
                                <div className="ml-8 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300 font-mono whitespace-pre-wrap">
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
                        <h4 className="text-xs font-medium text-yellow-400/90 uppercase tracking-wider">
                          🔧 Self-Healing Events
                        </h4>
                        <div className="space-y-2">
                          {tc.healing_events.map((he) => (
                            <div
                              key={he.id}
                              className="px-4 py-3 rounded-lg bg-yellow-500/5 border border-yellow-500/15 text-sm"
                            >
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-gray-400 text-xs">
                                  Step #{he.step_number}
                                </span>
                                <span className="text-yellow-400 font-semibold text-xs">
                                  {(he.confidence_score * 100).toFixed(1)}% confidence
                                </span>
                              </div>
                              <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                                <div>
                                  <span className="text-red-400">Before:</span>{" "}
                                  <span className="text-gray-400">{he.original_selector}</span>
                                </div>
                                <div>
                                  <span className="text-emerald-400">After:</span>{" "}
                                  <span className="text-gray-300">{he.healed_selector}</span>
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
                        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                          📸 Failure Screenshots
                        </h4>
                        <div className="flex gap-3 flex-wrap">
                          {tc.screenshots.map((ss) => (
                            <a
                              key={ss.id}
                              href={screenshotUrl(ss.file_path)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="block w-56 h-36 rounded-xl overflow-hidden border border-white/10 hover:border-purple-500/50 transition-all shadow-lg"
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
        <div className="glass-card p-12 text-center space-y-4">
          <div className="w-10 h-10 mx-auto rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-white">Executing Test Suite...</h3>
            <p className="text-sm text-gray-400 max-w-md mx-auto">
              Playwright browser is navigating target routes, validating assertions, and applying self-healing if selectors broke.
            </p>
          </div>
        </div>
      ) : run.target !== "evaluation" ? (
        <div className="glass-card p-12 text-center text-gray-500">
          No test cases found for this run.
        </div>
      ) : null}
    </div>
  );
}
