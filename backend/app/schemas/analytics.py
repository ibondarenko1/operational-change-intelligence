from pydantic import BaseModel, Field

from app.models.enums import ChangeType


class AnalyticsSummaryResponse(BaseModel):
    total_changes: int
    successful_changes: int
    failed_changes: int
    failure_rate: float
    changes_with_incidents: int
    average_downtime_minutes: float
    most_common_root_cause: str | None
    highest_risk_change_type: ChangeType | None
    common_process_failures: list[str] = Field(default_factory=list)
    common_preventive_controls: list[str] = Field(default_factory=list)
    common_business_impacts: list[str] = Field(default_factory=list)


class RootCauseAnalyticsResponse(BaseModel):
    root_cause: str
    count: int
    percentage: float
    average_downtime: float
    rollback_rate: float
    affected_change_types: list[ChangeType] = Field(default_factory=list)


class ChangeTypeAnalyticsResponse(BaseModel):
    change_type: ChangeType
    total: int
    successful: int
    failed: int
    failure_rate: float
    average_downtime: float
    common_root_causes: list[str] = Field(default_factory=list)


class FailurePatternResponse(BaseModel):
    pattern_type: str
    title: str
    description: str
    count: int
    rate: float | None = None
    average_downtime: float | None = None
    severity_score: float
    affected_change_types: list[ChangeType] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    process_failure: str | None = None
    technical_cause: str | None = None
    business_impact: str | None = None
    preventive_control: str | None = None
