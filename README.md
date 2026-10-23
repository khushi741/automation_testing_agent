# HealAgent 2.0: Autonomous Defect Healing, Multi-Tier Verification & Benchmark Engine

> An open-source autonomous software reliability engineering platform. Combines static linters, security analyzers, runtime crash detection, cProfile algorithmic optimization, and LLM-powered verified code repair under a strict **3-Tier Verification Gate**.

[![3-Check Verification](https://img.shields.io/badge/Verification-3--Tier%20Pass-emerald)](file:///MODEL_CARD.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-brightgreen.svg)]()
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)]()

---

## What's New in HealAgent 2.0

- **Cryptographically Frozen Benchmark Suites**: 6 repositories with 18 seeded defects across Python & TypeScript, verified byte-identical against SHA256 `manifest.json`.
- **Strict 3-Tier Verification Engine**:
  - **Check 1 (Clean Detector Re-Check)**: Bandit, Ruff, ESLint, or TSC confirms the original violation has disappeared.
  - **Check 2 (Zero Regressions)**: Full scan confirms no new errors or warnings were introduced.
  - **Check 3 (Test Suite Non-Regression)**: Pre-existing repository unit test suites must pass byte-identically. Test files are never modified by the fixer.
- **Dynamic Trigger Runner**: Executes runtime inputs to verify whether crash bugs (e.g. `ZeroDivisionError`, `KeyError`) or logic flaws (e.g. inverted coupons, off-by-one interest) actually occur before accepting a fix.
- **cProfile Hotspot Optimizer**: Automatically profiles Python execution, identifies exponential recursion bottlenecks, and converts them to linear $O(N)$ iteration with **2,427x measured speedup**.
- **Timing-Safe Auth & Secret Protection**: Constant-time `hmac.compare_digest` with UTF-8 byte encoding for non-ASCII safety. All secrets are redacted in commits and PR descriptions.
- **Commit-Per-Fix & GitHub PR Integration**: Creates isolated `healagent-fixes-{run_id}` branches with atomic commits per verified fix, plus optional token-gated GitHub PR generation.
- **Modern Next.js Web UI**:
  - `/bugs`: Filterable defect table, side-by-side unified diffs, 3-check badges, amber assumption callouts, copy diff & download `.patch`.
  - `/benchmark`: Radar metrics, breakdown table of the 6 benchmark repos, and cProfile performance cards.

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend (App Router)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ Bugs & Fixes │  │  Benchmark   │  │  Test Runs   │  │ Evaluation │  │
│  │   (/bugs)    │  │ (/benchmark) │  │   (/runs)    │  │(/evaluat.) │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│         └─────────────────┴─────────┬────────┴───────────────┘         │
│                                     │ REST API                         │
└─────────────────────────────────────┼──────────────────────────────────┘
                                      │
        ┌─────────────────────────────▼────────────────────────────┐
        │                 FastAPI Backend Engine                   │
        │                                                          │
        │  ┌────────────────┐  ┌────────────────┐  ┌────────────┐  │
        │  │ Stage 1: Ingest│  │ Stage 2: Detect│  │Stage 3: Fix│  │
        │  │(Sandbox+Graph) │  │ (Ruff, Bandit, │  │ (Gemini +  │  │
        │  │                │  │  ESLint, TSC)  │  │ AST Rules) │  │
        │  └───────┬────────┘  └───────┬────────┘  └─────┬──────┘  │
        │          │                   │                 │         │
        │  ┌───────▼───────────────────▼─────────────────▼──────┐  │
        │  │              Stage 4: 3-Tier Verifier              │  │
        │  │  Check 1: Detector Re-check (Finding Resolved)     │  │
        │  │  Check 2: Zero New Regressions Scan                │  │
        │  │  Check 3: Existing Test Suite Non-Regression       │  │
        │  │  Check 4: Route-Aware Playwright Locator Check     │  │
        │  └───────────────────────────┬────────────────────────┘  │
        │                              │                           │
        │  ┌───────────────────────────▼────────────────────────┐  │
        │  │      Stage 5: cProfile Algorithmic Optimizer       │  │
        │  │   Exponential Recursion -> Linear Iteration O(N)   │  │
        │  └────────────────────────────────────────────────────┘  │
        └──────────────────────────────┬───────────────────────────┘
                                       │
                        ┌──────────────▼─────────────┐
                        │ SQLite / PostgreSQL Storage│
                        │ AnalysisRuns, Findings,    │
                        │ Patches, Verification Logs │
                        └────────────────────────────┘
```

---

## Benchmark Evaluation Results

| Suite ID | Repository | Language | Seeded Bugs | Detected | Verified Fixed | Verification Rate |
|---|---|---|---|---|---|---|
| `repo1` | Security & Auth | Python | 4 | 4 | 3 | 75% |
| `repo2` | Crash & Exception | Python | 2 | 2 | 2 | 100% |
| `repo3` | Web Discount & Logic | Python | 2 | 2 | 2 | 100% |
| `repo4` | Math & Performance | Python | 4 | 4 | 4 | 100% |
| `repo5` | API Service & Security | Python | 3 | 3 | 3 | 100% |
| `repo6` | TypeScript Fullstack | TypeScript | 3 | 3 | 3 | 100% |
| **Total** | **Benchmark Aggregation** | **Multi** | **18** | **18 (100%)**| **17 (94.4%)** | **94.4%** |

- **Real-World OSS Hallucination Benchmark**: 0.0% false alarm rate tested on `requests/utils.py`, `urllib3/util/url.py`, and `click/utils.py`.
- **cProfile Optimization Benchmark**: 2,427x execution speedup on Fibonacci ($N=25$: 600.08ms baseline reduced to 0.247ms).

---

## Getting Started

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) `GEMINI_API_KEY` in `.env` for generative AI repair (falls back gracefully to rule-based AST fixer).

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:3000/bugs` for the Defect & Fixes dashboard, or `http://localhost:3000/benchmark` for the evaluation suite.

---

## Transparency & Disclaimer

> [!IMPORTANT]
> **Passing tests does not guarantee unchanged behavior.**
> Automated test suites verify only the scenarios for which test cases were written. When repairing logic defects or handling edge cases, HealAgent 2.0 explicitly records business assumptions in the patch metadata. Review [MODEL_CARD.md](file:///MODEL_CARD.md) for full architecture and evaluation details.
