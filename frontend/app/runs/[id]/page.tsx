"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { getTestRun, TestRun, screenshotUrl } from "@/lib/api";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const [run, setRun] = useState<TestRun | null>(null);
  const [loading, setLoading] = useState(true);

  interface ExecutionStep {
    status: string;
    description?: string;
    action?: string;
    target?: string;
    duration?: number;
    screenshot?: string;
    step_num?: number;
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
            Target: {run.target || "demo"} • Self-Healing:{" "}
            {run.self_healing_enabled ? "On" : "Off"}
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

      {/* Test Cases */}
      {run.test_cases && run.test_cases.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-300">
            Test Cases ({run.test_cases.length})
          </h2>

          {run.test_cases.map((tc, idx) => (
            <div key={tc.id} className="glass-card p-5 space-y-4">
              {/* Case Header */}
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <span className="text-gray-500 font-mono text-sm mt-0.5">
                    #{idx + 1}
                  </span>
                  <div>
                    <p className="text-gray-200 text-sm">{tc.description}</p>
                    {tc.source_route && (
                      <p className="text-xs text-gray-500 mt-1 font-mono">
                        Route: {tc.source_route}
                      </p>
                    )}
                  </div>
                </div>
                <span
                  className={`badge badge-${tc.status}`}
                >
                  {tc.status}
                </span>
              </div>

              {/* Error */}
              {tc.error && (
                <div className="px-4 py-3 rounded-lg bg-red-500/5 border border-red-500/20 text-sm text-red-300 font-mono">
                  {tc.error}
                </div>
              )}

              {/* Steps Timeline */}
              {tc.steps_json && tc.steps_json.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wider">
                    Execution Steps
                  </h4>
                  <div className="space-y-1">
                    {tc.steps_json.map((step: ExecutionStep, si: number) => (
                      <div
                        key={si}
                        className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02] text-sm"
                      >
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
                        <span className="text-gray-400 flex-1">
                          {step.description ||
                            `${step.action} → ${step.target}`}
                        </span>
                        <span className="text-xs text-gray-600">
                          {step.duration
                            ? `${step.duration.toFixed(2)}s`
                            : ""}
                        </span>
                        {step.status === "HEALED" && (
                          <span className="badge badge-healed text-[10px]">
                            HEALED
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Healing Events */}
              {tc.healing_events && tc.healing_events.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-yellow-400/80 mb-2 uppercase tracking-wider">
                    🔧 Self-Healing Events
                  </h4>
                  <div className="space-y-2">
                    {tc.healing_events.map((he) => (
                      <div
                        key={he.id}
                        className="px-4 py-3 rounded-lg bg-yellow-500/5 border border-yellow-500/15 text-sm"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-gray-400">
                            Step #{he.step_number}
                          </span>
                          <span className="text-yellow-400 font-semibold">
                            {(he.confidence_score * 100).toFixed(1)}% confidence
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                          <div>
                            <span className="text-red-400">Before:</span>{" "}
                            <span className="text-gray-400">
                              {he.original_selector}
                            </span>
                          </div>
                          <div>
                            <span className="text-emerald-400">After:</span>{" "}
                            <span className="text-gray-300">
                              {he.healed_selector}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Screenshots */}
              {tc.screenshots && tc.screenshots.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wider">
                    📸 Failure Screenshots
                  </h4>
                  <div className="flex gap-3 flex-wrap">
                    {tc.screenshots.map((ss) => (
                      <a
                        key={ss.id}
                        href={screenshotUrl(ss.file_path)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block w-48 h-32 rounded-lg overflow-hidden border border-white/10 hover:border-blue-500/30 transition-all"
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
          ))}
        </div>
      )}
    </div>
  );
}
