import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Repo(Base):
    __tablename__ = "repos"

    id = Column(String, primary_key=True, default=generate_uuid)
    github_url = Column(String, nullable=False)
    local_path = Column(String, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
    framework_detected = Column(String, nullable=True)
    routes_json = Column(JSON, nullable=True)
    status = Column(String, default="pending")  # pending, cloning, analyzing, ready, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    test_runs = relationship("TestRun", back_populates="repo", cascade="all, delete-orphan")
    generated_cases = relationship("GeneratedTestCase", back_populates="repo", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="repo", cascade="all, delete-orphan")


class GeneratedTestCase(Base):
    """Test cases generated from repo analysis, before they are executed."""
    __tablename__ = "generated_test_cases"

    id = Column(String, primary_key=True, default=generate_uuid)
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    description = Column(Text, nullable=False)
    source_route = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    repo = relationship("Repo", back_populates="generated_cases")


class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    repo_id = Column(String, ForeignKey("repos.id"), nullable=True)
    target = Column(String, nullable=True)
    self_healing_enabled = Column(Boolean, default=True)
    status = Column(String, default="queued")  # queued, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    heal_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    logs = Column(JSON, default=list)

    repo = relationship("Repo", back_populates="test_runs")
    test_cases = relationship("TestCase", back_populates="test_run", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(String, primary_key=True, default=generate_uuid)
    test_run_id = Column(String, ForeignKey("test_runs.id"), nullable=False)
    description = Column(Text, nullable=False)
    source_route = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, passed, failed, healed
    steps_json = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    duration = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    test_run = relationship("TestRun", back_populates="test_cases")
    healing_events = relationship("HealingEvent", back_populates="test_case", cascade="all, delete-orphan")
    screenshots = relationship("Screenshot", back_populates="test_case", cascade="all, delete-orphan")


class HealingEvent(Base):
    __tablename__ = "healing_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    test_case_id = Column(String, ForeignKey("test_cases.id"), nullable=False)
    step_number = Column(Integer, nullable=True)
    original_selector = Column(String, nullable=False)
    healed_selector = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    representation = Column(Text, nullable=True)

    test_case = relationship("TestCase", back_populates="healing_events")


class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(String, primary_key=True, default=generate_uuid)
    test_case_id = Column(String, ForeignKey("test_cases.id"), nullable=False)
    file_path = Column(String, nullable=False)
    step_number = Column(Integer, nullable=True)

    test_case = relationship("TestCase", back_populates="screenshots")


# ─── HealAgent 2.0 Models: Bugs, Findings, and Patches ───────────────────────

class AnalysisRun(Base):
    """Execution run of the bug detection and verified fixing pipeline."""
    __tablename__ = "analysis_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    repo_id = Column(String, ForeignKey("repos.id"), nullable=True)
    repo_name = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, detecting, triaging, fixing, verifying, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_findings = Column(Integer, default=0)
    verified_fixes = Column(Integer, default=0)
    needs_review = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    repo = relationship("Repo", back_populates="analysis_runs")
    findings = relationship("Finding", back_populates="run", cascade="all, delete-orphan")
    patches = relationship("Patch", back_populates="run", cascade="all, delete-orphan")


class Finding(Base):
    """Canonical representation of an individual bug or defect found by tools."""
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("analysis_runs.id"), nullable=False)
    file = Column(String, nullable=False)
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=False)
    category = Column(String, nullable=False)  # security, crash, correctness, performance, style
    severity = Column(String, nullable=False)  # critical, high, medium, low, info
    source_tool = Column(String, nullable=False)  # bandit, ruff, etc.
    message = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    status = Column(String, default="open")  # open, triaged, patch_proposed, verified, needs_review, ignored
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("AnalysisRun", back_populates="findings")
    patches = relationship("Patch", back_populates="finding", cascade="all, delete-orphan")


class Patch(Base):
    """Proposed or verified code fix patch for a finding."""
    __tablename__ = "patches"

    id = Column(String, primary_key=True, default=generate_uuid)
    finding_id = Column(String, ForeignKey("findings.id"), nullable=False)
    run_id = Column(String, ForeignKey("analysis_runs.id"), nullable=False)
    diff_content = Column(Text, nullable=False)
    old_snippet = Column(Text, nullable=True)
    new_snippet = Column(Text, nullable=True)
    status = Column(String, default="proposed")  # proposed, verified, rejected, needs_review
    attempts = Column(Integer, default=0)
    verification_log = Column(JSON, default=list)
    failure_reason = Column(Text, nullable=True)
    lines_added = Column(Integer, default=0)
    lines_removed = Column(Integer, default=0)
    explanation = Column(Text, nullable=True)
    model_name = Column(String, default="gemini-3.5-flash-lite")
    thinking_level = Column(String, default="standard")
    assumption = Column(Text, nullable=True)
    check1_status = Column(Boolean, default=False)
    check2_status = Column(Boolean, default=False)
    check3_status = Column(Boolean, default=False)
    combined_status = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    finding = relationship("Finding", back_populates="patches")
    run = relationship("AnalysisRun", back_populates="patches")
