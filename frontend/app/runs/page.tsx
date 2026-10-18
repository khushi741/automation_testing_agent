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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-1">
            <span className="bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              Test Runs
            </span>
          </h1>
          <p className="text-gray-400 text-sm">
            History of all test executions
          </p>
        </div>

        {/* Filter */}
        <div className="flex gap-2">
          {["", "completed", "running", "failed", "queued"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                filter === f
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                  : "bg-white/5 text-gray-400 border border-white/5 hover:bg-white/10"
              }`}
            >
              {f || "All"}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500">Loading...</div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            No test runs found. Start one from the{" "}
            <Link href="/" className="text-blue-400 hover:underline">
              home page
            </Link>
            .
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-white/[0.03] border-b border-white/5">
                <th className="text-left px-5 py-3.5 text-gray-400 font-medium">
                  ID
                </th>
                <th className="text-left px-5 py-3.5 text-gray-400 font-medium">
                  Target
                </th>
                <th className="text-left px-5 py-3.5 text-gray-400 font-medium">
                  Self-Healing
                </th>
                <th className="text-left px-5 py-3.5 text-gray-400 font-medium">
                  Status
                </th>
                <th className="text-left px-5 py-3.5 text-gray-400 font-medium">
                  Results
                </th>
                <th className="text-left px-5 py-3.5 text-gray-400 font-medium">
                  Duration
                </th>
                <th className="text-left px-5 py-3.5 text-gray-400 font-medium">
                  Created
                </th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className="border-t border-white/5 hover:bg-white/[0.02] transition-colors"
                >
                  <td className="px-5 py-3.5">
                    <Link
                      href={`/runs/${run.id}`}
                      className="font-mono text-blue-400 hover:text-blue-300 hover:underline"
                    >
                      {run.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-5 py-3.5 text-gray-300">
                    {run.target === "evaluation" ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                        Evaluation Suite
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-xs text-gray-300">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        {run.target || "Repository Suite"}
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    {run.self_healing_enabled ? (
                      <span className="text-emerald-400">● On</span>
                    ) : (
                      <span className="text-gray-500">○ Off</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <span className={`badge badge-${run.status}`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-emerald-400">
                      {run.pass_count}P
                    </span>
                    <span className="text-gray-600 mx-1">/</span>
                    <span className="text-red-400">{run.fail_count}F</span>
                    {run.heal_count > 0 && (
                      <>
                        <span className="text-gray-600 mx-1">/</span>
                        <span className="text-yellow-400">
                          {run.heal_count}H
                        </span>
                      </>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-gray-500">
                    {duration(run)}
                  </td>
                  <td className="px-5 py-3.5 text-gray-500">
                    {formatDate(run.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
