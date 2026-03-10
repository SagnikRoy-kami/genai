from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from enum import Enum


# ── Enums ───────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DELAYED = "delayed"


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Input Schemas ───────────────────────────────────────────────────

class TaskInput(BaseModel):
    task_name: str = Field(..., description="Name of the task")
    start_date: date = Field(..., description="Planned start date")
    end_date: date = Field(..., description="Planned end date")
    current_status: TaskStatus = Field(..., description="Current task status")
    description: Optional[str] = Field(None, description="Brief task description")


class ResourceInput(BaseModel):
    resource_type: str = Field(..., description="E.g. Engineer, Designer, Budget")
    needed: float = Field(..., description="Amount needed")
    currently_used: float = Field(..., description="Amount currently allocated")
    unit: str = Field("count", description="Unit of measurement: count, USD, hours")


class DependencyInput(BaseModel):
    dependency_name: str = Field(..., description="What this project depends on")
    dependency_type: str = Field("internal", description="internal or external")
    status: str = Field("pending", description="resolved, pending, blocked")
    blocking_tasks: Optional[List[str]] = Field(
        default_factory=list,
        description="Which tasks are blocked by this dependency"
    )


class ProjectPlanInput(BaseModel):
    project_name: str
    project_description: Optional[str] = None
    tasks: List[TaskInput]
    resources: List[ResourceInput]
    dependencies: List[DependencyInput]


# ── Agent Output Schemas ────────────────────────────────────────────

class MarketRisk(BaseModel):
    factor: str
    impact: str
    likelihood: str
    evidence: str


class InternalRisk(BaseModel):
    category: str
    description: str
    severity: RiskSeverity
    affected_tasks: List[str]
    evidence: str


class RiskStatement(BaseModel):
    risk_id: str
    title: str
    description: str
    severity: RiskSeverity
    score: int = Field(..., ge=1, le=25)
    probability: str
    impact_area: str


class MitigationAction(BaseModel):
    risk_id: str
    strategy: str
    action_steps: List[str]
    owner: str
    priority: str
    timeline: str


class FinalRiskReport(BaseModel):
    project_name: str
    generated_at: str
    overall_risk_score: int = Field(..., ge=1, le=25)
    overall_severity: RiskSeverity
    executive_summary: str
    market_risks: List[MarketRisk]
    internal_risks: List[InternalRisk]
    risk_statements: List[RiskStatement]
    mitigation_plan: List[MitigationAction]
    recommendations: List[str]
