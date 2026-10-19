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
        <span className="text-gray-600 font-medium">{label}</span>
        <span className={`${color} font-bold`}>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-3 rounded-full bg-emerald-50 border border-emerald-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-out ${
            color.includes("emerald")
              ? "bg-gradient-to-r from-emerald-600 to-teal-400"
              : color.includes("red") || color.includes("rose")
                ? "bg-gradient-to-r from-rose-600 to-rose-400"
                : "bg-gradient-to-r from-teal-600 to-emerald-400"
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
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold font-serif mb-1 text-[#0f2e22]">
            <span className="bg-gradient-to-r from-emerald-700 via-teal-700 to-green-600 bg-clip-text text-transparent">
              Evaluation Suite
            </span>
          </h1>
          <p className="text-gray-600 text-sm">
            20-case validation: Normal vs Broken UI, With vs Without Self-Healing
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="w-full sm:w-auto px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-xl transition-all disabled:opacity-50 shadow-md shadow-emerald-600/20 text-center"
        >
          {running ? "Running Evaluation..." : "▶ Run Evaluation"}
        </button>
      </div>

      {error && (
        <div className="glass-card p-4 border-rose-200 text-rose-700 text-sm bg-rose-50">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-20 text-gray-500">
          Loading evaluation results...
        </div>
      ) : !results ? (
        <div className="glass-card p-12 text-center bg-white border-emerald-100 shadow-sm">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            No Evaluation Data Yet
          </h2>
          <p className="text-gray-600 max-w-md mx-auto text-sm">
            Click &quot;Run Evaluation&quot; to execute the 20-case benchmark and generate accuracy comparison metrics.
          </p>
        </div>
      ) : (
        <>
          {/* Comparison Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Without Self-Healing */}
            <div className="glass-card p-4 sm:p-6 space-y-4 bg-white border-rose-200/80 shadow-xs">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center">
                  <span className="text-rose-600 text-xl font-bold">✗</span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">
                    Without Self-Healing
                  </h3>
                  <p className="text-xs text-gray-500">
                    Standard Playwright locators on broken UI
                  </p>
                </div>
              </div>

              <div className="text-center py-4">
                <div className="text-5xl font-bold text-rose-600">
                  {((results.without_healing?.pass_rate || 0) * 100).toFixed(0)}%
                </div>
                <div className="text-sm text-gray-500 mt-1 font-medium">Pass Rate</div>
              </div>

              <BarChart
                label="Passed"
                value={results.without_healing?.total_passed || 0}
                max={results.total_cases}
                color="text-emerald-700"
              />
              <BarChart
                label="Failed"
                value={results.without_healing?.total_failed || 0}
                max={results.total_cases}
                color="text-rose-600"
              />
            </div>

            {/* With Self-Healing */}
            <div className="glass-card p-4 sm:p-6 space-y-4 bg-emerald-50/40 border-emerald-300 shadow-xs">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 border border-emerald-300 flex items-center justify-center">
                  <span className="text-emerald-700 text-xl font-bold">✓</span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">
                    With Self-Healing
                  </h3>
                  <p className="text-xs text-emerald-800">
                    AI-powered locator recovery on broken UI
                  </p>
                </div>
              </div>

              <div className="text-center py-4">
                <div className="text-5xl font-bold text-emerald-700">
                  {((results.with_healing?.pass_rate || 0) * 100).toFixed(0)}%
                </div>
                <div className="text-sm text-emerald-800 mt-1 font-medium">Pass Rate</div>
              </div>

              <BarChart
                label="Passed"
                value={results.with_healing?.total_passed || 0}
                max={results.total_cases}
                color="text-emerald-700"
              />
              <BarChart
                label="Failed"
                value={results.with_healing?.total_failed || 0}
                max={results.total_cases}
                color="text-rose-600"
              />

              {results.with_healing?.avg_healing_confidence != null && (
                <div className="pt-3 border-t border-emerald-200/80">
                  <div className="flex justify-between text-sm">
                    <span className="text-emerald-900 font-medium">
                      Avg Healing Confidence
                    </span>
                    <span className="text-amber-700 font-bold">
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
          <div className="glass-card p-6 text-center bg-white border-emerald-200 shadow-xs">
            <div className="text-sm text-gray-500 mb-2 font-medium">
              Self-Healing Improvement
            </div>
            <div className="text-4xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
              +
              {(
                ((results.with_healing?.pass_rate || 0) -
                  (results.without_healing?.pass_rate || 0)) *
                100
              ).toFixed(0)}
              % pass rate
            </div>
            <p className="text-gray-600 mt-2 text-sm">
              on {results.total_cases} test cases against broken UI selectors
            </p>
          </div>

          {/* Detail Tables */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
              <div key={section.title} className="glass-card overflow-hidden bg-white border-emerald-200/80 shadow-xs">
                <div className="px-5 py-3 bg-emerald-50/80 border-b border-emerald-100">
                  <h3 className="text-sm font-semibold text-emerald-950">
                    {section.title}
                  </h3>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {section.data?.map((item: EvalCaseDetail, i: number) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 px-5 py-2.5 border-b border-emerald-50 text-sm hover:bg-emerald-50/30 transition-colors"
                    >
                      <span
                        className={`w-2 h-2 rounded-full ${
                          item.status === "PASSED"
                            ? "bg-emerald-500"
                            : "bg-rose-500"
                        }`}
                      />
                      <span className="text-gray-700 truncate flex-1 font-mono text-xs">
                        {item.case?.slice(0, 60)}...
                      </span>
                      <span
                        className={`text-xs font-bold ${
                          item.status === "PASSED"
                            ? "text-emerald-700"
                            : "text-rose-600"
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
