import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base
from app.models.enums import ChangeStatus, ChangeType, Environment


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[Environment] = mapped_column(Enum(Environment, name="environment_enum"), nullable=False)
    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType, name="change_type_enum"), nullable=False)
    planned_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    planned_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    affected_scope: Mapped[str] = mapped_column(Text, nullable=False)
    rollback_plan: Mapped[str] = mapped_column(Text, nullable=False)
    maintenance_window: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pilot_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    report_only_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[ChangeStatus] = mapped_column(
        Enum(ChangeStatus, name="change_status_enum"),
        nullable=False,
        default=ChangeStatus.draft,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(
        back_populates="change_request",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class HistoricalChange(Base):
    __tablename__ = "historical_changes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[Environment] = mapped_column(Enum(Environment, name="environment_enum"), nullable=False)
    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType, name="change_type_enum"), nullable=False)
    outcome: Mapped[str] = mapped_column(String(100), nullable=False)
    incident_occurred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    downtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rollback_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("change_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    change_request: Mapped[ChangeRequest] = relationship(back_populates="risk_assessments")
    risk_factors: Mapped[list["RiskFactor"]] = relationship(
        back_populates="risk_assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    checklist_items: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="risk_assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def formula(self) -> str:
        return "score = min(100, max(0, sum(risk_factors.points)))"


class RiskFactor(Base):
    __tablename__ = "risk_factors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_assessment: Mapped[RiskAssessment] = relationship(back_populates="risk_factors")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    risk_assessment: Mapped[RiskAssessment] = relationship(back_populates="checklist_items")
