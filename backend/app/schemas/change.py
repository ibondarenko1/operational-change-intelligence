import uuid
from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ChangeStatus, ChangeType, Environment


class ChangeRequestBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    environment: Environment
    change_type: ChangeType
    planned_start: datetime
    planned_end: datetime
    affected_scope: str = Field(min_length=1)
    rollback_plan: str = Field(min_length=1)
    maintenance_window: bool = False
    pilot_enabled: bool = False
    report_only_mode: bool = False

    @model_validator(mode="after")
    def validate_planned_dates(self) -> Self:
        if self.planned_end < self.planned_start:
            raise ValueError("planned_end cannot be earlier than planned_start")
        return self


class ChangeRequestCreate(ChangeRequestBase):
    status: ChangeStatus = ChangeStatus.draft


class ChangeRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    environment: Environment | None = None
    change_type: ChangeType | None = None
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    affected_scope: str | None = Field(default=None, min_length=1)
    rollback_plan: str | None = Field(default=None, min_length=1)
    maintenance_window: bool | None = None
    pilot_enabled: bool | None = None
    report_only_mode: bool | None = None
    status: ChangeStatus | None = None

    @model_validator(mode="after")
    def validate_planned_dates(self) -> Self:
        if self.planned_start is not None and self.planned_end is not None:
            if self.planned_end < self.planned_start:
                raise ValueError("planned_end cannot be earlier than planned_start")
        return self


class RiskFactorCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category: str = Field(default="uncategorized", min_length=1, max_length=80)
    category_cap: int = 100
    points: int
    evidence: str | None = None


class RiskFactorUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=80)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    category_cap: int | None = None
    points: int | None = None
    evidence: str | None = None


class RiskFactorResponse(RiskFactorCreate):
    id: uuid.UUID
    risk_assessment_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class ChecklistItemCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    priority: str = Field(min_length=1, max_length=50)
    status: str = Field(min_length=1, max_length=50)


class ChecklistItemUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=80)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    priority: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = Field(default=None, min_length=1, max_length=50)


class ChecklistItemResponse(ChecklistItemCreate):
    id: uuid.UUID
    risk_assessment_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentCreate(BaseModel):
    change_request_id: uuid.UUID
    score: int
    raw_score: int = 0
    capped_score: int = 0
    level: str = Field(min_length=1, max_length=50)
    recommendation: str = Field(min_length=1)
    confidence: float
    category_scores: dict[str, dict[str, int]] = Field(default_factory=dict)
    formula_explanation: str = ""
    similar_changes: list[dict[str, Any]] = Field(default_factory=list)
    directly_affected_assets: list[dict[str, Any]] = Field(default_factory=list)
    dependent_assets: list[dict[str, Any]] = Field(default_factory=list)
    affected_business_services: list[dict[str, Any]] = Field(default_factory=list)
    impact_paths: list[dict[str, Any]] = Field(default_factory=list)
    predicted_failure_modes: list[dict[str, Any]] = Field(default_factory=list)
    blast_radius: dict[str, int] = Field(default_factory=dict)
    missing_context: list[str] = Field(default_factory=list)


class RiskAssessmentUpdate(BaseModel):
    score: int | None = None
    raw_score: int | None = None
    capped_score: int | None = None
    level: str | None = Field(default=None, min_length=1, max_length=50)
    recommendation: str | None = Field(default=None, min_length=1)
    confidence: float | None = None
    category_scores: dict[str, dict[str, int]] | None = None
    formula_explanation: str | None = None
    similar_changes: list[dict[str, Any]] | None = None
    directly_affected_assets: list[dict[str, Any]] | None = None
    dependent_assets: list[dict[str, Any]] | None = None
    affected_business_services: list[dict[str, Any]] | None = None
    impact_paths: list[dict[str, Any]] | None = None
    predicted_failure_modes: list[dict[str, Any]] | None = None
    blast_radius: dict[str, int] | None = None
    missing_context: list[str] | None = None


class RiskAssessmentResponse(RiskAssessmentCreate):
    id: uuid.UUID
    created_at: datetime
    formula: str
    risk_factors: list[RiskFactorResponse] = Field(default_factory=list)
    checklist_items: list[ChecklistItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class HistoricalChangeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    environment: Environment
    change_type: ChangeType
    outcome: str = Field(min_length=1, max_length=100)
    incident_occurred: bool = False
    downtime_minutes: int = 0
    rollback_required: bool = False
    root_cause: str | None = None
    lessons_learned: str | None = None
    trigger: str | None = None
    technical_cause: str | None = None
    process_failure: str | None = None
    business_impact: str | None = None
    preventive_control: str | None = None


class HistoricalChangeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    environment: Environment | None = None
    change_type: ChangeType | None = None
    outcome: str | None = Field(default=None, min_length=1, max_length=100)
    incident_occurred: bool | None = None
    downtime_minutes: int | None = None
    rollback_required: bool | None = None
    root_cause: str | None = None
    lessons_learned: str | None = None
    trigger: str | None = None
    technical_cause: str | None = None
    process_failure: str | None = None
    business_impact: str | None = None
    preventive_control: str | None = None


class HistoricalChangeResponse(HistoricalChangeCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimilarHistoricalChangeResponse(BaseModel):
    historical_change_id: uuid.UUID
    title: str
    similarity_score: float = Field(ge=0, le=1)
    matching_factors: list[str] = Field(default_factory=list)
    outcome: str
    incident_occurred: bool
    root_cause: str | None = None
    downtime_minutes: int
    rollback_required: bool = False
    lessons_learned: str | None = None
    historical_failure_signal: bool = False
    historical_severity: str = "low"

    model_config = ConfigDict(from_attributes=True)


class ChangeRequestResponse(ChangeRequestBase):
    id: uuid.UUID
    status: ChangeStatus
    created_at: datetime
    updated_at: datetime
    risk_assessments: list[RiskAssessmentResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
