const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ─── Repos ───────────────────────────────────────────────────────────────────

export interface Repo {
  id: string;
  github_url: string;
  status: string;
  framework_detected: string | null;
  routes_json: Route[] | null;
  analyzed_at: string | null;
  created_at: string | null;
  generated_cases: GeneratedTestCase[];
}

export interface Route {
  path: string;
  method: string;
  file: string;
}

export interface GeneratedTestCase {
  id: string;
  description: string;
  source_route: string | null;
}

export async function createRepo(github_url: string): Promise<Repo> {
  return fetchApi<Repo>("/api/repos", {
    method: "POST",
    body: JSON.stringify({ github_url }),
  });
}

export async function getRepos(): Promise<Repo[]> {
  return fetchApi<Repo[]>("/api/repos");
}

export async function getRepo(id: string): Promise<Repo> {
  return fetchApi<Repo>(`/api/repos/${id}`);
}

export async function analyzeRepo(id: string): Promise<void> {
  await fetchApi(`/api/repos/${id}/analyze`, { method: "POST" });
}

export async function generateTests(id: string): Promise<void> {
  await fetchApi(`/api/repos/${id}/generate-tests`, { method: "POST" });
}

// ─── Test Runs ───────────────────────────────────────────────────────────────

export interface HealingEvent {
  id: string;
  step_number: number | null;
  original_selector: string;
  healed_selector: string;
  confidence_score: number;
  representation: string | null;
}

export interface Screenshot {
  id: string;
  file_path: string;
  step_number: number | null;
}

export interface TestCaseResult {
  id: string;
  description: string;
  source_route: string | null;
  status: string;
  steps_json: Record<string, unknown>[] | null;
  error: string | null;
  duration: number;
  healing_events: HealingEvent[];
  screenshots: Screenshot[];
}

export interface TestRun {
  id: string;
  repo_id: string | null;
  target: string | null;
  self_healing_enabled: boolean;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  pass_count: number;
  fail_count: number;
  heal_count: number;
  created_at: string | null;
  logs?: string[];
  test_cases?: TestCaseResult[];
}

export async function createTestRun(params: {
  repo_id?: string;
  target?: string;
  test_case_text?: string;
  broken?: boolean;
  self_healing_enabled?: boolean;
}): Promise<TestRun> {
  return fetchApi<TestRun>("/api/test-runs", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function getTestRuns(params?: {
  repo_id?: string;
  status?: string;
}): Promise<TestRun[]> {
  const query = new URLSearchParams();
  if (params?.repo_id) query.set("repo_id", params.repo_id);
  if (params?.status) query.set("status", params.status);
  const qs = query.toString();
  return fetchApi<TestRun[]>(`/api/test-runs${qs ? `?${qs}` : ""}`);
}

export async function getTestRun(id: string): Promise<TestRun> {
  return fetchApi<TestRun>(`/api/test-runs/${id}`);
}

// ─── Evaluation ──────────────────────────────────────────────────────────────

export interface EvalCaseDetail {
  case: string;
  status: string;
  error?: string;
}

export interface EvalResults {
  total_cases: number;
  without_healing: {
    pass_rate: number;
    total_passed: number;
    total_failed: number;
    details: EvalCaseDetail[];
  };
  with_healing: {
    pass_rate: number;
    total_passed: number;
    total_failed: number;
    avg_healing_confidence: number;
    details: EvalCaseDetail[];
  };
  empty?: boolean;
}

export async function runEvaluation(): Promise<{ eval_run_id: string }> {
  return fetchApi("/api/run-evaluation", { method: "POST" });
}

export async function getEvalResults(): Promise<EvalResults> {
  return fetchApi<EvalResults>("/api/eval-results");
}

export async function getEvalCases(): Promise<Record<string, unknown>[]> {
  return fetchApi<Record<string, unknown>[]>("/api/eval-cases");
}

// ─── Screenshots ─────────────────────────────────────────────────────────────

export function screenshotUrl(filename: string): string {
  return `${API_BASE}/api/screenshots/${filename}`;
}

// ─── Health ──────────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<{ status: string }> {
  return fetchApi("/api/health");
}
