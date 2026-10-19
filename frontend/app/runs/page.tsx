"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getTestRuns, TestRun } from "@/lib/api";

export default function RunsPage() {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");

  async function loadRuns() {
    try {
      const data = await getTestRuns(filter ? { status: filter } : undefined);
      setRuns(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadRuns();
    const interval = setInterval(loadRuns, 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  function formatDate(d: string | null) {
    if (!d) return "—";
    return new Date(d).toLocaleString();
  }

  function duration(run: TestRun) {
    if (!run.started_at || !run.completed_at) return "—";
    const ms =
      new Date(run.completed_at).getTime() -
      new Date(run.started_at).getTime();
    return `${(ms / 1000).toFixed(1)}s`;
  }

  const totalRuns = runs.length;
  const completedRuns = runs.filter((r) => r.status === "completed").length;
  const totalPassed = runs.reduce((acc, r) => acc + (r.pass_count || 0), 0);
  const totalFailed = runs.reduce((acc, r) => acc + (r.fail_count || 0), 0);
  const totalHealed = runs.reduce((acc, r) => acc + (r.heal_count || 0), 0);
  const overallPassRate =
    totalPassed + totalFailed > 0
      ? ((totalPassed / (totalPassed + totalFailed)) * 100).toFixed(0)
      : "100";

  return (
    <div className="space-y-6">
      
      {/* Top Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-xs font-bold text-emerald-900 border border-emerald-300 mb-2">
            <span>📊 Test Execution History</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-[#0a291e]">
            <span className="bg-gradient-to-r from-emerald-800 via-teal-700 to-green-700 bg-clip-text text-transparent">
              Test Runs & Diagnostics
            </span>
          </h1>
          <p className="text-gray-600 text-sm">
            Real-time Playwright execution history with self-healing audit logs
          </p>
        </div>

        {/* Action Button */}
        <Link
          href="/#connect"
          className="px-5 py-2.5 btn-emerald-glow font-bold rounded-xl text-sm flex items-center gap-2 shadow-xs cursor-pointer"
        >
          <span>+ Launch New Test</span>
        </Link>
      </div>

      {/* Metrics Summary Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="glass-card p-4 bg-white/95 border-emerald-200 shadow-xs">
          <div className="text-xs text-gray-500 font-medium">Total Runs</div>
          <div className="text-2xl font-extrabold text-emerald-950 font-mono mt-0.5">{totalRuns}</div>
        </div>
        <div className="glass-card p-4 bg-white/95 border-emerald-200 shadow-xs">
          <div className="text-xs text-gray-500 font-medium">Overall Pass Rate</div>
          <div className="text-2xl font-extrabold text-emerald-700 font-mono mt-0.5">{overallPassRate}%</div>
        </div>
        <div className="glass-card p-4 bg-white/95 border-emerald-200 shadow-xs">
          <div className="text-xs text-gray-500 font-medium">Self-Healed Selectors</div>
          <div className="text-2xl font-extrabold text-amber-600 font-mono mt-0.5">{totalHealed} saves</div>
        </div>
        <div className="glass-card p-4 bg-white/95 border-emerald-200 shadow-xs">
          <div className="text-xs text-gray-500 font-medium">Completed Suites</div>
          <div className="text-2xl font-extrabold text-teal-800 font-mono mt-0.5">{completedRuns}</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between flex-wrap gap-2 pt-2">
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar py-1 max-w-full">
          {["", "completed", "running", "failed", "queued"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3.5 py-1.5 text-xs rounded-xl transition-all capitalize cursor-pointer font-bold ${
                filter === f
                  ? "bg-emerald-600 text-white shadow-xs"
                  : "bg-white text-gray-700 border border-emerald-200/90 hover:bg-emerald-50 hover:text-emerald-900"
              }`}
            >
              {f || "All Runs"}
            </button>
          ))}
        </div>
        <span className="text-xs text-emerald-800 font-mono font-medium">
          Showing {runs.length} records
        </span>
      </div>

      {/* Table Card */}
      <div className="glass-card overflow-hidden border-emerald-300/80 shadow-md bg-white/95 rounded-2xl">
        {loading ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center gap-3">
            <span className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <span>Loading test run records...</span>
          </div>
        ) : runs.length === 0 ? (
          <div className="p-16 text-center text-gray-500 space-y-3">
            <div className="text-4xl">🧪</div>
            <div className="font-semibold text-gray-800">No test runs found</div>
            <p className="text-xs text-gray-500 max-w-sm mx-auto">
              Start your first automated test run from the home page.
            </p>
            <Link
              href="/"
              className="inline-flex px-4 py-2 btn-emerald-glow rounded-lg text-xs font-bold"
            >
              Go to Home Page →
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-emerald-50/90 border-b border-emerald-200">
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-bold">
                    Run ID
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-bold">
                    Target Suite
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-bold">
                    Self-Healing
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-bold">
                    Status
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-bold">
                    Results
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-bold">
                    Duration
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-bold">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    className="border-t border-emerald-100 hover:bg-emerald-50/60 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <Link
                        href={`/runs/${run.id}`}
                        className="font-mono text-emerald-700 hover:text-emerald-950 font-extrabold hover:underline"
                      >
                        {run.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 text-gray-800">
                      {run.target === "evaluation" ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          Evaluation Suite
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs text-gray-900 font-semibold font-mono">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          {run.target || "Repository Suite"}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      {run.self_healing_enabled ? (
                        <span className="text-emerald-700 font-bold flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
                          <span>Enabled</span>
                        </span>
                      ) : (
                        <span className="text-gray-400 font-medium">Disabled</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`badge badge-${run.status}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-xs">
                      <span className="text-emerald-700 font-extrabold">
                        {run.pass_count} Passed
                      </span>
                      {run.fail_count > 0 && (
                        <>
                          <span className="text-gray-400 mx-1">•</span>
                          <span className="text-rose-600 font-extrabold">{run.fail_count} Failed</span>
                        </>
                      )}
                      {run.heal_count > 0 && (
                        <>
                          <span className="text-gray-400 mx-1">•</span>
                          <span className="text-amber-600 font-extrabold">
                            {run.heal_count} Healed
                          </span>
                        </>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-gray-600 font-mono text-xs">
                      {duration(run)}
                    </td>
                    <td className="px-5 py-3.5 text-gray-500 text-xs">
                      {formatDate(run.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
