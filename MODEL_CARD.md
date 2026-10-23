# Model Card: HealAgent 2.0 Autonomous Defect Healing & Verification Engine

## 1. Overview & System Description

**HealAgent 2.0** is an open-source autonomous defect detection, verified remediation, and performance optimization platform. It bridges static linting, security analysis, runtime crash detection, algorithmic optimization, and LLM-powered code repair under an autonomous 3-tier verification architecture.

- **Primary LLM**: `gemini-3.5-flash-lite` (Free-tier Google Generative AI API)
- **Thinking Levels**: Supported semantic levels (`minimal`, `medium`, `high`)
- **Resilience Engine**: Exponential backoff retry loop (2s, 4s, 8s) on HTTP 503 / 429 with automatic model fallback to `gemini-3.6-flash` and `gemini-3.5-flash`, and deterministic rule-based AST fallback.
- **Static & Dynamic Detectors**:
  - Python: `ruff` (syntax, style, logic codes), `bandit` (security, SQL injection, hardcoded secrets)
  - TypeScript / JavaScript: `eslint` (style, unused variables), `tsc` (TypeScript compiler type safety)
  - Python Performance: `cProfile` (algorithmic hotspot detection)
  - Dynamic Trigger Runner: Verifies crash exceptions and logic assertions before and after patch application.
- **Test Runners**: `pytest`, Node.js test runner, route-aware Playwright locator engine.

---

## 2. The 3-Check Verification Engine

Every proposed patch is evaluated in an isolated sandbox branch against a strict 3-tier verification gate:

1. **Check 1: Clean Detector Re-Check**
   The detector that surfaced the finding (e.g. Bandit, Ruff, ESLint, TSC) is re-executed on the patched file. The specific finding must be 100% resolved.
2. **Check 2: Zero New Regressions**
   A full-repository detector scan verifies that no secondary defects, style violations, or type errors were introduced by the patch.
3. **Check 3: Test Suite Non-Regression**
   The repository's pre-existing test suites are executed. Any patch that fails existing tests or attempts to modify existing test files is rejected immediately.
4. **Combined Multi-Patch Verification**
   After each patch passes individual verification, all candidate patches are applied together to confirm mutual compatibility.

---

## 3. Mandatory Safety & Transparency Disclaimers

> [!WARNING]
> **Passing tests does not guarantee unchanged behavior.**
> Automated test suites verify only the scenarios for which test cases were written. When repairing logic defects or handling edge cases (such as zero-element collections, tax discount ordering, or empty authentication tokens), HealAgent 2.0 records explicit business assumptions. Human review is recommended before deploying to production.

- **Assumption Policy**: All patches with implicit business assumptions (e.g. `calculate_average([]) == 0.0`, discounts applied pre-tax) feature an amber callout in the UI and git commit messages.
- **Byte-Identical Test Preservation**: HealAgent strictly forbids modifying existing test files. Auto-generated reproduction tests are saved in distinct `test_repro_*.py` files.
- **Secret Redaction**: All API keys, passwords, and tokens are redacted (`[REDACTED_SECRET]`) from commit messages and generated Pull Requests.
- **Timing Attack Safety**: Authentication token comparisons enforce non-empty string validation and byte-encoded constant-time comparison via `hmac.compare_digest(token.encode('utf-8'), ADMIN_TOKEN.encode('utf-8'))`.

---

## 4. Benchmark Evaluation & Performance

HealAgent 2.0 was evaluated against a hash-checked benchmark suite (`manifest.json`, 39 files, SHA256 verified) comprising 6 seeded repositories and 3 real-world open-source packages. Hashes provide tamper-evident auditing against accidental drift or unauthorized edits (they are tamper-evident, not tamper-proof against deliberate hash overwrite):

| Suite ID | Repository Name | Language | Seeded Defects | Detected | Verified Fixed | Verification Rate |
|---|---|---|---|---|---|---|
| `repo1` | Security & Auth Suite | Python | 4 | 4 | 3 | 75% |
| `repo2` | Crash & Exception Suite | Python | 2 | 2 | 2 | 100% |
| `repo3` | Web Discount & Logic Suite | Python | 2 | 2 | 2 | 100% |
| `repo4` | Math & Performance Suite | Python | 4 | 4 | 4 | 100% |
| `repo5` | API Service & Security Suite | Python | 3 | 3 | 3 | 100% |
| `repo6` | TypeScript Fullstack Suite | TypeScript | 3 | 3 | 3 | 100% |
| **Total** | **Benchmark Aggregation** | **Multi** | **18** | **18 (100%)** | **17 (94.4%)** | **94.4%** |

### Real-World OSS Hallucination Benchmark
Tested on real-world production files from:
- `requests/utils.py`
- `urllib3/util/url.py`
- `click/utils.py`

**Hallucination Rate**: **0.0%** (Dynamic trigger runner confirmed safe code handled inputs without throwing unhandled exceptions).

### cProfile Algorithmic Speedup Benchmark (repo4)
- **Defect**: Exponential $O(2^N)$ recursion in `compute_fibonacci_slow`
- **Baseline Duration**: 600.08 ms (75,025 calls for $N=25$)
- **Optimized Duration**: 0.247 ms (linear iteration $O(N)$, 0 recursive calls)
- **Speedup Factor**: **2,427x** (verified equivalent for $N=0..25$ and baseline tests passing).

---

## 5. Licensing & Transparency

HealAgent 2.0 is 100% Free and Open Source under the Apache 2.0 / MIT licenses. It uses only open-source linters and Google Generative AI free-tier models.
