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
