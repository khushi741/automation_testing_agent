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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold font-serif mb-1 text-[#0f2e22]">
            <span className="bg-gradient-to-r from-emerald-700 via-teal-700 to-green-600 bg-clip-text text-transparent">
              Test Runs
            </span>
          </h1>
          <p className="text-gray-600 text-sm">
            History of all AI browser test executions
          </p>
        </div>

        {/* Filter */}
        <div className="flex gap-2 flex-wrap">
          {["", "completed", "running", "failed", "queued"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all capitalize ${
                filter === f
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300 font-semibold shadow-xs"
                  : "bg-white text-gray-600 border border-emerald-100/90 hover:bg-emerald-50/80 hover:text-emerald-800 shadow-xs"
              }`}
            >
              {f || "All Runs"}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden border-emerald-200/80 shadow-sm bg-white">
        {loading ? (
          <div className="p-12 text-center text-gray-500">Loading test runs...</div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            No test runs found. Start one from the{" "}
            <Link href="/" className="text-emerald-700 font-semibold hover:underline">
              home page
            </Link>
            .
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-emerald-50/80 border-b border-emerald-100">
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-semibold">
                    Run ID
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-semibold">
                    Target
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-semibold">
                    Self-Healing
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-semibold">
                    Status
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-semibold">
                    Results
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-semibold">
                    Duration
                  </th>
                  <th className="text-left px-5 py-3.5 text-emerald-950 font-semibold">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    className="border-t border-emerald-50 hover:bg-emerald-50/50 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <Link
                        href={`/runs/${run.id}`}
                        className="font-mono text-emerald-700 hover:text-emerald-900 font-semibold hover:underline"
                      >
                        {run.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 text-gray-700">
                      {run.target === "evaluation" ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          Evaluation Suite
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs text-gray-800 font-medium">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          {run.target || "Repository Suite"}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      {run.self_healing_enabled ? (
                        <span className="text-emerald-700 font-semibold">● On</span>
                      ) : (
                        <span className="text-gray-400">○ Off</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`badge badge-${run.status}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-medium">
                      <span className="text-emerald-700 font-bold">
                        {run.pass_count}P
                      </span>
                      <span className="text-gray-400 mx-1">/</span>
                      <span className="text-rose-600 font-bold">{run.fail_count}F</span>
                      {run.heal_count > 0 && (
                        <>
                          <span className="text-gray-400 mx-1">/</span>
                          <span className="text-amber-600 font-bold">
                            {run.heal_count}H
                          </span>
                        </>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-gray-500">
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
