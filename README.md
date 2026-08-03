# AI Self-Healing Test Agent

> An AI-powered browser test automation system that converts natural language test cases into real Playwright browser automation — with **self-healing locators** that automatically recover when UI selectors break.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                         │
│                     (localhost:3000)                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Connect  │  │  Test    │  │   Run    │  │  Evaluation   │  │
│  │   Repo   │  │  Runs   │  │  Detail  │  │    Suite      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬────────┘  │
│       │              │             │               │            │
│       └──────────────┴─────────────┴───────────────┘            │
│                              │  REST API (fetch)                │
└──────────────────────────────┼──────────────────────────────────┘
                               │
         ┌─────────────────────▼──────────────────────────┐
         │              FastAPI Backend                     │
         │             (localhost:8000)                     │
         │                                                 │
         │  ┌───────────┐  ┌────────────┐  ┌───────────┐  │
         │  │  Parser   │  │  Executor  │  │   Agent   │  │
         │  │ (LLM/     │  │ (Playwright│  │(Orchestr.)│  │
         │  │ Heuristic)│  │  Actions)  │  │           │  │
         │  └─────┬─────┘  └─────┬──────┘  └─────┬─────┘  │
         │        │              │              │          │
         │  ┌─────▼──────────────▼──────────────▼─────┐   │
         │  │           Self-Healing Engine            │   │
         │  │  (SentenceTransformer Embeddings +       │   │
         │  │   Cosine Similarity DOM Matching)        │   │
         │  └─────────────────────────────────────────┘   │
         │        │                              │         │
         │  ┌─────▼─────┐              ┌────────▼──────┐  │
         │  │  Ollama    │              │  Repo Analyzer│  │
         │  │ qwen2.5:   │              │  + Test Gen   │  │
         │  │  1.5b      │              │               │  │
         │  └────────────┘              └───────────────┘  │
         └─────────────────────┬───────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    PostgreSQL 16    │
                    │   (Docker Container)│
                    │                     │
                    │  repos              │
                    │  test_runs          │
                    │  test_cases         │
                    │  healing_events     │
                    │  screenshots        │
                    │  generated_cases    │
                    └─────────────────────┘
```

## Key Features

- **Natural Language → Browser Automation**: Write tests in plain English, the system parses them into structured Playwright actions
- **Self-Healing Locators**: When UI selectors change, the AI engine uses semantic embeddings (all-MiniLM-L6-v2) to find the closest matching DOM element
- **Local LLM Integration**: Uses Ollama with `qwen2.5:1.5b` for test case parsing — zero API costs
- **Repository Analysis**: Clone any GitHub repo, auto-detect the framework (Next.js, React, Flask, Django, etc.), extract routes, and generate tests
- **Evaluation Suite**: 20 pre-built test scenarios comparing pass rates with and without self-healing
- **Full-Stack Dashboard**: Real-time test execution monitoring, healing event visualization, and comparison charts

## Tech Stack

| Layer       | Technology                                    |
|-------------|-----------------------------------------------|
| Frontend    | Next.js 16, TypeScript, Tailwind CSS          |
| Backend     | FastAPI, Python 3.11                          |
| Database    | PostgreSQL 16 (Docker)                        |
| Browser     | Playwright (Chromium, headless)               |
| LLM         | Ollama → qwen2.5:1.5b (local, free)          |
| Embeddings  | SentenceTransformers (all-MiniLM-L6-v2)      |
| Infra       | Docker Compose                                |

## Setup Instructions

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Node.js 18+](https://nodejs.org/)
- [Ollama](https://ollama.ai/) (optional, for LLM parsing)

### 1. Start Backend + Database

```bash
# Clone the repository
git clone <repo-url>
cd Automation_testing

# Start PostgreSQL and FastAPI backend
docker-compose up --build -d

# Verify services are running
docker-compose ps
curl http://localhost:8000/api/health
```

### 2. Start Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
# → Open http://localhost:3000
```

### 3. (Optional) Pull the Local LLM

```bash
# Install Ollama from https://ollama.ai
ollama pull qwen2.5:1.5b

# The backend auto-detects Ollama and uses it for test parsing.
# Without Ollama, the built-in heuristic parser handles all cases.
```

## Frontend Pages

### Connect Repo (`/`)
Submit a GitHub URL → live progress tracking (clone → analyze → ready) → view detected framework and routes → generate AI test cases → execute with one click.

### Test Runs (`/runs`)
Filterable history table of all test executions showing status badges, pass/fail/heal counts, duration, and timestamps.

### Run Detail (`/runs/[id]`)
Step-by-step execution timeline, failure error messages, self-healing events showing original vs healed selectors with confidence scores, and failure screenshots.

### Evaluation Suite (`/evaluation`)
Side-by-side comparison: broken UI without self-healing (0% pass rate) vs broken UI with self-healing (high pass rate). Bar charts, improvement metrics, and per-case detail tables.

## Database Schema

| Table                  | Purpose                                           |
|------------------------|---------------------------------------------------|
| `repos`                | Tracked GitHub repositories and analysis results  |
| `generated_test_cases` | AI-generated test cases linked to repos           |
| `test_runs`            | Execution instances with pass/fail/heal counts    |
| `test_cases`           | Individual test case results within a run         |
| `healing_events`       | Self-healing locator matches with confidence       |
| `screenshots`          | Failure screenshot references                      |

## Engineering Tradeoffs

### BackgroundTasks + Polling vs Celery/Redis

This project uses FastAPI's built-in `BackgroundTasks` with client-side polling instead of a dedicated task queue like Celery with Redis. This is a deliberate architectural decision, not an oversight:

| Factor               | BackgroundTasks + Polling | Celery + Redis              |
|----------------------|---------------------------|-----------------------------|
| **Infrastructure**   | Zero additional services  | +2 services (Redis + Worker)|
| **Memory overhead**  | ~0 MB                     | ~200+ MB                    |
| **Setup complexity** | None                      | Config, serializers, broker |
| **Local dev UX**     | `docker-compose up` only  | Additional containers       |
| **Horizontal scale** | No (single process)       | Yes                         |

**Rationale**: On resource-constrained local development hardware (dual-core i3, no GPU), every additional service competes for CPU and RAM. The single-process model keeps the demo responsive and the setup dead simple while still providing non-blocking execution with real-time progress feedback via polling.

For a production deployment handling concurrent users, migrating to Celery + Redis is the natural next step — the `BackgroundTasks` functions are already structured as standalone jobs that can be trivially wrapped as Celery tasks.

### Automatic Cleanup

After each test run completes (pass, fail, or error), the cloned repository directory and its `node_modules` are automatically deleted from the scratch directory. Only test results, screenshots, and the `routes_json` summary persist in the database.

A startup cleanup step also runs when the FastAPI server boots, removing any orphaned scratch directories from previously crashed runs by cross-referencing active database records.

## Security Considerations

> ⚠️ **Repository analysis currently runs `npm install` and `npm run dev` directly on the host machine without sandboxing.**

This is a known, documented tradeoff for the portfolio/demo scope of this project:

- **Risk**: A malicious repository's `postinstall` scripts or build commands could execute arbitrary code on the host.
- **Mitigation for production**: Each analyzed repository should be isolated in its own **ephemeral container** (e.g., Docker-in-Docker, Firecracker microVM, or a dedicated Kubernetes Job) with:
  - Network isolation
  - Read-only filesystem (except for the clone target)
  - Resource limits (CPU, memory, time)
  - Non-root execution
- **Current scope**: The demo targets trusted repositories (typically the user's own GitHub projects) on a local development machine, making the unsandboxed execution acceptable for portfolio demonstration purposes.

This is an engineering decision documented here — not an oversight.

## Project Structure

```
Automation_testing/
├── docker-compose.yml          # PostgreSQL + FastAPI orchestration
├── .env.example                # Environment configuration template
├── README.md
│
├── backend/
│   ├── Dockerfile              # mcr.microsoft.com/playwright/python base
│   ├── main.py                 # FastAPI application server
│   ├── database.py             # SQLAlchemy engine + sessions
│   ├── models.py               # ORM table definitions
│   ├── schemas.py              # Pydantic request/response models
│   ├── requirements.txt
│   ├── src/
│   │   ├── config.py           # Environment-based settings
│   │   ├── parser.py           # NL → structured steps (LLM + fallback)
│   │   ├── executor.py         # Playwright action execution
│   │   ├── self_healing.py     # Embedding-based DOM matching
│   │   ├── agent.py            # Test run orchestrator
│   │   ├── reporter.py         # HTML report generator
│   │   ├── repo_analyzer.py    # Git clone + framework detection
│   │   ├── test_generator.py   # AI test case generation
│   │   └── cleanup.py          # Post-run + startup cleanup
│   ├── templates/              # Demo target site HTML
│   └── tests/                  # 20-case evaluation suite
│
└── frontend/
    ├── app/
    │   ├── layout.tsx          # Root layout with navigation
    │   ├── page.tsx            # Connect Repo page
    │   ├── evaluation/
    │   │   └── page.tsx        # Evaluation suite page
    │   └── runs/
    │       ├── page.tsx        # Test runs history
    │       └── [id]/
    │           └── page.tsx    # Run detail view
    ├── lib/
    │   └── api.ts              # TypeScript API client
    └── .env.local              # API URL configuration
```

## License

MIT
