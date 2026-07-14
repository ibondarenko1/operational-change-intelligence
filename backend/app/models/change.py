import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base
from app.models.enums import AssetType, ChangeStatus, ChangeType, Criticality, DependencyType, Environment


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
    change_assets: Mapped[list["ChangeAsset"]] = relationship(
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
    trigger: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    process_failure: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    preventive_control: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    raw_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    capped_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    category_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    formula_explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    similar_changes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    directly_affected_assets: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    dependent_assets: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    affected_business_services: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    impact_paths: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    predicted_failure_modes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    blast_radius: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    missing_context: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
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
        return (
            "score = min(100, sum(min(category_cap, max(0, sum(points by category)))))"
        )


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
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="uncategorized")
    category_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
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


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType, name="asset_type_enum"), nullable=False)
    environment: Mapped[Environment] = mapped_column(Enum(Environment, name="environment_enum"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    business_service: Mapped[str | None] = mapped_column(String(200), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    criticality: Mapped[Criticality] = mapped_column(Enum(Criticality, name="criticality_enum"), nullable=False)
    authentication_method: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_legacy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_privileged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    asset_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    outgoing_dependencies: Mapped[list["AssetDependency"]] = relationship(
        foreign_keys="AssetDependency.source_asset_id",
        back_populates="source_asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    incoming_dependencies: Mapped[list["AssetDependency"]] = relationship(
        foreign_keys="AssetDependency.target_asset_id",
        back_populates="target_asset",
    )
    change_assets: Mapped[list["ChangeAsset"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AssetDependency(Base):
    __tablename__ = "asset_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_type: Mapped[DependencyType] = mapped_column(
        Enum(DependencyType, name="dependency_type_enum"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

    source_asset: Mapped[Asset] = relationship(
        foreign_keys=[source_asset_id],
        back_populates="outgoing_dependencies",
    )
    target_asset: Mapped[Asset] = relationship(
        foreign_keys=[target_asset_id],
        back_populates="incoming_dependencies",
    )


class ChangeAsset(Base):
    __tablename__ = "change_assets"

    change_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("change_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(80), primary_key=True)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)

    change_request: Mapped[ChangeRequest] = relationship(back_populates="change_assets")
    asset: Mapped[Asset] = relationship(back_populates="change_assets")
