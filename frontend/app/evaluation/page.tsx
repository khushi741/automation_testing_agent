"use client";

import { useState, useEffect } from "react";
import { runEvaluation, getEvalResults, EvalResults, EvalCaseDetail } from "@/lib/api";

function BarChart({
  label,
  value,
  max,
  color,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
}) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">{label}</span>
        <span className={color}>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-3 rounded-full bg-white/5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-out ${
            color.includes("emerald")
              ? "bg-gradient-to-r from-emerald-600 to-emerald-400"
              : color.includes("red")
                ? "bg-gradient-to-r from-red-600 to-red-400"
                : "bg-gradient-to-r from-blue-600 to-blue-400"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function EvaluationPage() {
  const [results, setResults] = useState<EvalResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function loadResults() {
    try {
      const data = await getEvalResults();
      if (!("empty" in data)) {
        setResults(data);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadResults();
  }, []);

  async function handleRun() {
    setRunning(true);
    setError("");
    try {
      await runEvaluation();
      // Poll for results
      const interval = setInterval(async () => {
        try {
          const data = await getEvalResults();
          if (!("empty" in data)) {
            setResults(data);
            setRunning(false);
            clearInterval(interval);
          }
        } catch {
          // ignore
        }
      }, 5000);
    } catch (err: unknown) {
      const error = err as Error;
      setError(error.message);
      setRunning(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-1">
            <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Evaluation Suite
            </span>
          </h1>
          <p className="text-gray-400 text-sm">
            20-case validation: Normal vs Broken UI, With vs Without
            Self-Healing
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold rounded-xl transition-all disabled:opacity-50 shadow-lg shadow-purple-500/20"
        >
          {running ? "Running Evaluation..." : "▶ Run Evaluation"}
        </button>
      </div>

      {error && (
        <div className="glass-card p-4 border-red-500/30 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-20 text-gray-500">
          Loading results...
        </div>
      ) : !results ? (
        <div className="glass-card p-12 text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-xl font-semibold text-gray-300 mb-2">
            No Evaluation Data Yet
          </h2>
          <p className="text-gray-500">
            Click &quot;Run Evaluation&quot; to execute the 20-case suite and
            generate comparison metrics.
          </p>
        </div>
      ) : (
        <>
          {/* Comparison Cards */}
          <div className="grid grid-cols-2 gap-6">
            {/* Without Self-Healing */}
            <div className="glass-card p-6 glow-red space-y-4">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                  <span className="text-red-400 text-xl">✗</span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-200">
                    Without Self-Healing
                  </h3>
                  <p className="text-xs text-gray-500">
                    Standard Playwright locators on broken UI
                  </p>
                </div>
              </div>

              <div className="text-center py-4">
                <div className="text-5xl font-bold text-red-400">
                  {((results.without_healing?.pass_rate || 0) * 100).toFixed(
                    0
                  )}
                  %
                </div>
                <div className="text-sm text-gray-500 mt-1">Pass Rate</div>
              </div>

              <BarChart
                label="Passed"
                value={results.without_healing?.total_passed || 0}
                max={results.total_cases}
                color="text-emerald-400"
              />
              <BarChart
                label="Failed"
                value={results.without_healing?.total_failed || 0}
                max={results.total_cases}
                color="text-red-400"
              />
            </div>

            {/* With Self-Healing */}
            <div className="glass-card p-6 glow-green space-y-4">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                  <span className="text-emerald-400 text-xl">✓</span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-200">
                    With Self-Healing
                  </h3>
                  <p className="text-xs text-gray-500">
                    AI-powered locator recovery on broken UI
                  </p>
                </div>
              </div>

              <div className="text-center py-4">
                <div className="text-5xl font-bold text-emerald-400">
                  {((results.with_healing?.pass_rate || 0) * 100).toFixed(0)}%
                </div>
                <div className="text-sm text-gray-500 mt-1">Pass Rate</div>
              </div>

              <BarChart
                label="Passed"
                value={results.with_healing?.total_passed || 0}
                max={results.total_cases}
                color="text-emerald-400"
              />
              <BarChart
                label="Failed"
                value={results.with_healing?.total_failed || 0}
                max={results.total_cases}
                color="text-red-400"
              />

              {results.with_healing?.avg_healing_confidence != null && (
                <div className="pt-3 border-t border-white/5">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">
                      Avg Healing Confidence
                    </span>
                    <span className="text-yellow-400 font-semibold">
                      {(
                        (results.with_healing.avg_healing_confidence || 0) * 100
                      ).toFixed(1)}
                      %
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Improvement Summary */}
          <div className="glass-card p-6 text-center">
            <div className="text-sm text-gray-500 mb-2">
              Self-Healing Improvement
            </div>
            <div className="text-4xl font-bold bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
              +
              {(
                ((results.with_healing?.pass_rate || 0) -
                  (results.without_healing?.pass_rate || 0)) *
                100
              ).toFixed(0)}
              % pass rate
            </div>
            <p className="text-gray-500 mt-2 text-sm">
              on {results.total_cases} test cases against broken UI selectors
            </p>
          </div>

          {/* Detail Tables */}
          <div className="grid grid-cols-2 gap-6">
            {[
              {
                title: "Without Self-Healing",
                data: results.without_healing?.details,
              },
              {
                title: "With Self-Healing",
                data: results.with_healing?.details,
              },
            ].map((section) => (
              <div key={section.title} className="glass-card overflow-hidden">
                <div className="px-5 py-3 bg-white/[0.03] border-b border-white/5">
                  <h3 className="text-sm font-medium text-gray-400">
                    {section.title}
                  </h3>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {section.data?.map((item: EvalCaseDetail, i: number) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 px-5 py-2.5 border-b border-white/[0.03] text-sm"
                    >
                      <span
                        className={`w-2 h-2 rounded-full ${
                          item.status === "PASSED"
                            ? "bg-emerald-400"
                            : "bg-red-400"
                        }`}
                      />
                      <span className="text-gray-400 truncate flex-1">
                        {item.case?.slice(0, 60)}...
                      </span>
                      <span
                        className={`text-xs font-medium ${
                          item.status === "PASSED"
                            ? "text-emerald-400"
                            : "text-red-400"
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
