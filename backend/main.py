"""
FastAPI Application Server — replaces the original Flask app.py.
Serves the demo target site, REST API endpoints for repo analysis,
test execution, and evaluation, all backed by PostgreSQL.
"""
import os
import json
import uuid
import queue
import logging
import threading
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader

from database import engine, Base, get_db, SessionLocal
from models import Repo, TestRun, TestCase, HealingEvent, Screenshot, GeneratedTestCase
from schemas import (
    RepoCreate, RepoOut, TestRunCreate, TestRunOut, TestRunSummary,
    EvalResultsOut, GeneratedTestCaseOut
)
from src.config import (
    PLAYWRIGHT_HEADLESS, PLAYWRIGHT_SLOW_MO, SCRATCH_DIR,
    SCREENSHOTS_DIR, REPORTS_DIR, HEALING_THRESHOLD, PLAYWRIGHT_TIMEOUT
)
from src.agent import run_test_case
from src.repo_analyzer import clone_repo, analyze_repo
from src.test_generator import generate_tests_for_routes
from src.cleanup import cleanup_repo, startup_cleanup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Jinja2 templates for demo site
templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

# Browser worker queue
job_queue = queue.Queue()


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    # Startup cleanup of orphaned scratch directories
    db = SessionLocal()
    try:
        startup_cleanup(db)
    finally:
        db.close()

    yield

    # Shutdown: send sentinel to browser worker
    job_queue.put(None)
    logger.info("Shutdown signal sent to browser worker.")


app = FastAPI(
    title="AI Self-Healing Test Agent",
    description="AI-powered browser test automation with self-healing locators",
    version="2.0.0",
    lifespan=lifespan
)

# CORS — allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for screenshots and reports
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ─── Browser Worker Thread ───────────────────────────────────────────────────

def browser_worker():
    """
    Single persistent background worker that owns the Playwright browser instance.
    Processes jobs from the queue sequentially on one thread.
    """
    from playwright.sync_api import sync_playwright

    logger.info("Initializing background browser worker thread...")

    with sync_playwright() as p:
        logger.info("Launching Playwright Chromium browser...")
        try:
            browser = p.chromium.launch(
                headless=PLAYWRIGHT_HEADLESS,
                slow_mo=PLAYWRIGHT_SLOW_MO
            )
        except Exception as launch_err:
            logger.warning(f"Default Chromium launch failed ({launch_err}). Launching system Chrome...")
            browser = p.chromium.launch(
                channel="chrome",
                headless=PLAYWRIGHT_HEADLESS,
                slow_mo=PLAYWRIGHT_SLOW_MO
            )
        logger.info("Browser ready.")

        while True:
            try:
                job = job_queue.get()
                if job is None:
                    logger.info("Shutdown sentinel received. Closing browser...")
                    break

                job_type = job["type"]
                logger.info(f"Processing {job_type} job...")

                if job_type == "test_run":
                    _process_test_run_job(job, browser)
                elif job_type == "evaluation":
                    _process_evaluation_job(job, browser)

                job_queue.task_done()
            except Exception as e:
                logger.error(f"Browser worker error: {e}")

        browser.close()
        logger.info("Browser closed.")


def _process_test_run_job(job: dict, browser):
    """Execute a test run with all its cases."""
    run_id = job["run_id"]
    db = SessionLocal()

    try:
        run = db.query(TestRun).filter(TestRun.id == run_id).first()
        if not run:
            logger.error(f"TestRun {run_id} not found in database")
            return

        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()

        cases = db.query(TestCase).filter(TestCase.test_run_id == run_id).all()
        pass_count = 0
        fail_count = 0
        heal_count = 0

        for tc in cases:
            scenario = tc.description
            scenario = scenario.replace("localhost:5000", "localhost:8000")
            if job.get("broken") and "?broken=true" not in scenario:
                scenario = scenario.replace("/demo/login", "/demo/login?broken=true")

            # If scenario lacks navigation and run has a target URL, navigate first
            if "http://" not in scenario and "https://" not in scenario and run.target and (run.target.startswith("http://") or run.target.startswith("https://")):
                scenario = f"Navigate to {run.target}, {scenario}"

            try:
                result = run_test_case(
                    scenario,
                    browser,
                    self_healing_enabled=run.self_healing_enabled,
                    log_callback=None
                )

                tc.status = result.get("status", "FAILED").lower()
                tc.steps_json = result.get("steps", [])
                tc.duration = result.get("duration", 0.0)
                tc.error = result.get("error")

                if tc.status == "passed":
                    pass_count += 1
                else:
                    fail_count += 1

                # Save healing events
                for h in result.get("healing_logs", []):
                    event = HealingEvent(
                        test_case_id=tc.id,
                        step_number=h.get("step_index"),
                        original_selector=h.get("original_target", ""),
                        healed_selector=h.get("healed_selector", ""),
                        confidence_score=h.get("confidence", 0.0),
                        representation=h.get("healed_representation", "")
                    )
                    db.add(event)
                    heal_count += 1

                # Save screenshots
                for step in result.get("steps", []):
                    if step.get("screenshot"):
                        ss = Screenshot(
                            test_case_id=tc.id,
                            file_path=step["screenshot"],
                            step_number=step.get("step_num")
                        )
                        db.add(ss)

            except Exception as e:
                tc.status = "failed"
                tc.error = str(e)
                fail_count += 1
                logger.error(f"Test case execution error: {e}")

            db.commit()

        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.pass_count = pass_count
        run.fail_count = fail_count
        run.heal_count = heal_count
        db.commit()

        # Cleanup cloned repo if this run was against an analyzed repo
        if run.repo_id:
            repo = db.query(Repo).filter(Repo.id == run.repo_id).first()
            if repo and repo.local_path:
                cleanup_repo(repo.id, repo.local_path)
                repo.local_path = None
                db.commit()

    except Exception as e:
        logger.error(f"Test run job error: {e}")
        try:
            run = db.query(TestRun).filter(TestRun.id == run_id).first()
            if run:
                run.status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _process_evaluation_job(job: dict, browser):
    """Run the 20-case evaluation suite."""
    run_id = job["run_id"]
    db = SessionLocal()

    try:
        run = db.query(TestRun).filter(TestRun.id == run_id).first()
        if not run:
            return

        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()

        cases_path = Path(__file__).parent / "tests" / "test_cases.json"
        if not cases_path.exists():
            run.status = "failed"
            db.commit()
            return

        with open(cases_path, "r", encoding="utf-8") as f:
            cases = json.load(f)

        results_without = []
        results_with = []
        healing_confidences = []
        passed_without = 0
        passed_with = 0

        # Phase 1: WITHOUT self-healing
        for tc_data in cases:
            scenario = tc_data["text"].replace("/demo/login", "/demo/login?broken=true")
            scenario = scenario.replace("localhost:5000", "localhost:8000")
            try:
                res = run_test_case(scenario, browser, self_healing_enabled=False)
                status = res.get("status", "FAILED")
                if status == "PASSED":
                    passed_without += 1
                results_without.append({"case": tc_data["text"], "status": status})
            except Exception as e:
                results_without.append({"case": tc_data["text"], "status": "FAILED", "error": str(e)})

        # Phase 2: WITH self-healing
        for tc_data in cases:
            scenario = tc_data["text"].replace("/demo/login", "/demo/login?broken=true")
            scenario = scenario.replace("localhost:5000", "localhost:8000")
            try:
                res = run_test_case(scenario, browser, self_healing_enabled=True)
                status = res.get("status", "FAILED")
                if status == "PASSED":
                    passed_with += 1
                for h in res.get("healing_logs", []):
                    healing_confidences.append(h["confidence"])
                results_with.append({"case": tc_data["text"], "status": status})
            except Exception as e:
                results_with.append({"case": tc_data["text"], "status": "FAILED", "error": str(e)})

        avg_conf = sum(healing_confidences) / len(healing_confidences) if healing_confidences else 0.0

        eval_summary = {
            "total_cases": len(cases),
            "without_healing": {
                "pass_rate": passed_without / len(cases) if cases else 0,
                "total_passed": passed_without,
                "total_failed": len(cases) - passed_without,
                "details": results_without
            },
            "with_healing": {
                "pass_rate": passed_with / len(cases) if cases else 0,
                "total_passed": passed_with,
                "total_failed": len(cases) - passed_with,
                "avg_healing_confidence": avg_conf,
                "details": results_with
            }
        }

        # Save to results.json
        results_path = Path(__file__).parent / "results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(eval_summary, f, indent=2)

        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.pass_count = passed_with
        run.fail_count = len(cases) - passed_with
        run.logs = [
            f"Without healing: {passed_without}/{len(cases)} passed",
            f"With healing: {passed_with}/{len(cases)} passed",
            f"Avg confidence: {avg_conf:.1%}"
        ]
        db.commit()

    except Exception as e:
        logger.error(f"Evaluation job error: {e}")
        try:
            run = db.query(TestRun).filter(TestRun.id == run_id).first()
            if run:
                run.status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# Lazy browser worker start
_worker_started = False
_worker_lock = threading.Lock()


def ensure_worker():
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            t = threading.Thread(target=browser_worker, daemon=True)
            t.start()
            _worker_started = True
            logger.info("Browser worker thread started.")


# ─── Demo Target Site Routes ─────────────────────────────────────────────────

@app.get("/demo/login", response_class=HTMLResponse)
async def demo_login(request: Request, broken: str = "false"):
    template = jinja_env.get_template("demo_login.html")
    return HTMLResponse(template.render(broken=(broken == "true"), error=None))


@app.post("/demo/login", response_class=HTMLResponse)
async def demo_login_post(request: Request, broken: str = "false"):
    form = await request.form()
    is_broken = broken == "true"

    username = form.get("username") if not is_broken else form.get("usr_login")
    password = form.get("password") if not is_broken else form.get("pass_key")

    if username == "admin" and password == "admin123":
        redirect_url = "/demo/dashboard"
        if is_broken:
            redirect_url += "?broken=true"
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=redirect_url, status_code=303)

    template = jinja_env.get_template("demo_login.html")
    return HTMLResponse(template.render(broken=is_broken, error="Invalid credentials."))


@app.get("/demo/dashboard", response_class=HTMLResponse)
async def demo_dashboard(broken: str = "false"):
    template = jinja_env.get_template("demo_dashboard.html")
    return HTMLResponse(template.render(broken=(broken == "true")))


@app.get("/demo/logout")
async def demo_logout(broken: str = "false"):
    from fastapi.responses import RedirectResponse
    url = "/demo/login"
    if broken == "true":
        url += "?broken=true"
    return RedirectResponse(url=url, status_code=303)


# ─── Repository API ──────────────────────────────────────────────────────────

@app.post("/api/repos", response_model=RepoOut)
async def create_repo(body: RepoCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    repo = Repo(github_url=body.github_url, status="pending")
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


@app.get("/api/repos", response_model=List[RepoOut])
async def list_repos(db: Session = Depends(get_db)):
    return db.query(Repo).order_by(Repo.created_at.desc()).all()


@app.get("/api/repos/{repo_id}", response_model=RepoOut)
async def get_repo(repo_id: str, db: Session = Depends(get_db)):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo


@app.post("/api/repos/{repo_id}/analyze")
async def analyze_repo_endpoint(repo_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")

    background_tasks.add_task(_bg_analyze_repo, repo_id)
    repo.status = "cloning"
    db.commit()
    return {"message": "Analysis started", "repo_id": repo_id}


def _bg_analyze_repo(repo_id: str):
    """Background task: clone repo, detect framework, extract routes."""
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            return

        # Clone
        repo.status = "cloning"
        db.commit()
        local_path = clone_repo(repo.github_url, repo_id)
        repo.local_path = local_path

        # Analyze
        repo.status = "analyzing"
        db.commit()
        result = analyze_repo(local_path)

        repo.framework_detected = result["framework"]
        repo.routes_json = result["routes"]
        repo.analyzed_at = datetime.utcnow()
        repo.status = "ready"
        db.commit()

    except Exception as e:
        logger.error(f"Repo analysis failed: {e}")
        try:
            repo = db.query(Repo).filter(Repo.id == repo_id).first()
            if repo:
                repo.status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@app.post("/api/repos/{repo_id}/generate-tests")
async def generate_tests_endpoint(repo_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    if not repo.routes_json:
        raise HTTPException(status_code=400, detail="Repo has not been analyzed yet")

    background_tasks.add_task(_bg_generate_tests, repo_id)
    return {"message": "Test generation started", "repo_id": repo_id}


def _bg_generate_tests(repo_id: str):
    """Background task: generate test cases from analyzed routes."""
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo or not repo.routes_json:
            return

        cases = generate_tests_for_routes(
            routes=repo.routes_json,
            framework=repo.framework_detected or "unknown"
        )

        for c in cases:
            gen_case = GeneratedTestCase(
                repo_id=repo_id,
                description=c["description"],
                source_route=c.get("source_route")
            )
            db.add(gen_case)

        db.commit()
        logger.info(f"Generated {len(cases)} test cases for repo {repo_id}")

    except Exception as e:
        logger.error(f"Test generation failed: {e}")
    finally:
        db.close()


# ─── Test Runs API ────────────────────────────────────────────────────────────

@app.post("/api/test-runs", response_model=TestRunSummary)
async def create_test_run(body: TestRunCreate, db: Session = Depends(get_db)):
    ensure_worker()

    run = TestRun(
        repo_id=body.repo_id,
        target=body.target or "demo",
        self_healing_enabled=body.self_healing_enabled,
        status="queued"
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # If a single test case text is provided, create one TestCase
    if body.test_case_text:
        tc = TestCase(
            test_run_id=run.id,
            description=body.test_case_text,
        )
        db.add(tc)
        db.commit()
    elif body.repo_id:
        # Load generated test cases for this repo
        gen_cases = db.query(GeneratedTestCase).filter(
            GeneratedTestCase.repo_id == body.repo_id
        ).all()
        for gc in gen_cases:
            tc = TestCase(
                test_run_id=run.id,
                description=gc.description,
                source_route=gc.source_route,
            )
            db.add(tc)
        db.commit()

    # Enqueue for browser worker
    job_queue.put({
        "type": "test_run",
        "run_id": run.id,
        "broken": body.broken,
    })

    return run


@app.get("/api/test-runs", response_model=List[TestRunSummary])
async def list_test_runs(
    repo_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(TestRun)
    if repo_id:
        q = q.filter(TestRun.repo_id == repo_id)
    if status:
        q = q.filter(TestRun.status == status)
    return q.order_by(TestRun.created_at.desc()).all()


@app.get("/api/test-runs/{run_id}", response_model=TestRunOut)
async def get_test_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")
    return run


# ─── Evaluation API ──────────────────────────────────────────────────────────

@app.post("/api/run-evaluation")
async def run_evaluation(db: Session = Depends(get_db)):
    ensure_worker()

    run = TestRun(
        target="evaluation",
        self_healing_enabled=True,
        status="queued"
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    job_queue.put({
        "type": "evaluation",
        "run_id": run.id,
    })

    return {"eval_run_id": run.id, "status": "queued"}


@app.get("/api/eval-results")
async def get_eval_results():
    results_path = Path(__file__).parent / "results.json"
    if results_path.exists():
        with open(results_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"empty": True}


@app.get("/api/eval-cases")
async def get_eval_cases():
    cases_path = Path(__file__).parent / "tests" / "test_cases.json"
    if cases_path.exists():
        with open(cases_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ─── Screenshots API ─────────────────────────────────────────────────────────

@app.get("/api/screenshots/{filename}")
async def get_screenshot(filename: str):
    path = SCREENSHOTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(str(path))


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
