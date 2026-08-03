from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


# ---------- Request Schemas ----------

class RepoCreate(BaseModel):
    github_url: str


class TestRunCreate(BaseModel):
    repo_id: Optional[str] = None
    target: Optional[str] = None
    test_case_text: Optional[str] = None
    broken: bool = False
    self_healing_enabled: bool = True


# ---------- Response Schemas ----------

class HealingEventOut(BaseModel):
    id: str
    step_number: Optional[int] = None
    original_selector: str
    healed_selector: str
    confidence_score: float
    representation: Optional[str] = None

    class Config:
        from_attributes = True


class ScreenshotOut(BaseModel):
    id: str
    file_path: str
    step_number: Optional[int] = None

    class Config:
        from_attributes = True


class TestCaseOut(BaseModel):
    id: str
    description: str
    source_route: Optional[str] = None
    status: str
    steps_json: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    healing_events: List[HealingEventOut] = []
    screenshots: List[ScreenshotOut] = []

    class Config:
        from_attributes = True


class TestRunOut(BaseModel):
    id: str
    repo_id: Optional[str] = None
    target: Optional[str] = None
    self_healing_enabled: bool
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pass_count: int = 0
    fail_count: int = 0
    heal_count: int = 0
    created_at: Optional[datetime] = None
    logs: Optional[List[str]] = []
    test_cases: List[TestCaseOut] = []

    class Config:
        from_attributes = True


class TestRunSummary(BaseModel):
    id: str
    repo_id: Optional[str] = None
    target: Optional[str] = None
    self_healing_enabled: bool
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pass_count: int = 0
    fail_count: int = 0
    heal_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GeneratedTestCaseOut(BaseModel):
    id: str
    description: str
    source_route: Optional[str] = None

    class Config:
        from_attributes = True


class RepoOut(BaseModel):
    id: str
    github_url: str
    status: str
    framework_detected: Optional[str] = None
    routes_json: Optional[Any] = None
    analyzed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    generated_cases: List[GeneratedTestCaseOut] = []

    class Config:
        from_attributes = True


class EvalResultsOut(BaseModel):
    total_cases: int = 0
    without_healing: Optional[Any] = None
    with_healing: Optional[Any] = None
