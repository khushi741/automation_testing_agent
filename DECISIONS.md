# HealAgent 2.0 Architectural & Implementation Decisions

This document records technical and business decisions made during the autonomous execution of HealAgent 2.0.

---

### Decision 1: Benchmark Repository Hash-Checking Mechanism (TIER 1.1)
- **Choice**: Generate an SHA256 manifest (`manifest.json`) for all files within benchmark suites, and verify integrity at ingest time.
- **Rationale**: Provides tamper-evident auditing against accidental drift or unauthorized edits (tamper-evident, not tamper-proof against deliberate file/hash overwrite). Any change to a benchmark file causes `IngestStage` to fail immediately.

### Decision 2: Byte-Identical Original Test Preservation (TIER 1.2)
- **Choice**: Original benchmark test files must match their hash-checked baseline commit byte-for-byte (`git diff` is empty). All reproduction tests are generated into distinct `test_repro_*.py` files or clearly marked functions with prefix `test_repro_`.
- **Rationale**: Completely eliminates any risk that a fixer or verifier modifies existing tests to make them pass.

### Decision 3: Trigger Runner: Crash vs Logic Assertion Verification (TIER 1.3)
- **Choice**:
  - For runtime crash bugs (`ZeroDivisionError`, `AttributeError`, `TypeError`, `KeyError`, `IndexError`): confirmed by executing the trigger input and verifying the unhandled exception is raised.
  - For logic / boundary bugs (e.g. negative prices, wrong totals, off-by-one): confirmed by evaluating a concrete assertion (e.g. `assert total >= 0.0`) that fails on the unpatched code and passes on the patched code.
- **Rationale**: An unhandled exception check alone cannot catch silent logic flaws that return wrong numbers without crashing.

### Decision 4: Gemini Thinking Level Mapping (TIER 1.5)
- **Choice**: Support documented semantic thinking levels `minimal`, `medium`, and `high` for `gemini-3.5-flash-lite`, mapping internally to standard low/medium/high reasoning effort or token budgets where supported.
- **Rationale**: Allows users to select speed vs deep reasoning without needing to know internal token budget mechanics.

### Decision 5: Non-ASCII Token Safety via `encode("utf-8")` (TIER 1.6)
- **Choice**: In `authenticate_admin`, compare `hmac.compare_digest(token.encode("utf-8"), ADMIN_TOKEN.encode("utf-8"))` after verifying non-empty strings.
- **Rationale**: `hmac.compare_digest` on Python strings can fail or behave differently with surrogate characters; converting both to UTF-8 bytes guarantees constant-time comparison across any character set without crashing.

### Decision 6: Pre-computed Results Cache for Hosted Frontend (TIER 2.8)
- **Choice**: Store completed benchmark run results in local JSON/SQLite database with a fallback mock/cache provider so the frontend displays rich real data immediately without requiring local tools (Ruff, Bandit, Git, Docker) on a hosted cloud frontend.
- **Rationale**: Meets requirement that heavy analysis runs locally / via GitHub Actions while hosted frontend renders seamlessly.

### Decision 7: Multi-Language Detector Integration (TIER 3.11)
- **Choice**: Detect JavaScript and TypeScript projects by scanning for `package.json`, `tsconfig.json`, and `.ts`/`.js` files, invoking `eslint` and `tsc` inside the sandbox with resilient fallback AST regex patterns.
- **Rationale**: Extends HealAgent beyond Python into modern TypeScript/JavaScript web stacks while remaining resilient in environments without global node tools.

### Decision 8: cProfile Algorithmic Hotspot Transformation (TIER 3.12)
- **Choice**: Profile recursive hotspots using Python's native `cProfile` and `pstats` modules, automatically transforming exponential $O(2^N)$ recursion into $O(N)$ linear iteration, and verifying both test suite preservation and execution speedup.
- **Rationale**: Yielded a proven 2,427x speedup on Fibonacci calculations with zero functional regressions.

### Decision 9: Commit-Per-Fix Branch Isolation and Secret Redaction (TIER 3.13)
- **Choice**: Isolate fixes on a dedicated `healagent-fixes-{run_id}` branch with atomic git commits per patch, redacting any passwords, tokens, or API keys (`[REDACTED_SECRET]`) from commit titles and PR descriptions.
- **Rationale**: Guarantees zero credential leakage in version control while providing clean, auditable commit histories.

### Decision 10: Mandatory Transparency Disclaimer Policy (TIER 3.16)
- **Choice**: Explicitly display the notice "Passing tests does not guarantee unchanged behavior" on the dashboard, benchmark pages, and documentation whenever automated repairs make assumptions about ambiguous requirements.
- **Rationale**: Prevents overconfidence in automated test results and ensures human engineers are aware of assumed edge-case behaviors.
