"""create mvp tables

Revision ID: 202607130001
Revises:
Create Date: 2026-07-13 00:00:01 UTC
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202607130001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ENVIRONMENT_VALUES = (
    "entra_id",
    "microsoft_365",
    "defender",
    "azure",
    "other",
)

CHANGE_TYPE_VALUES = (
    "mfa_rollout",
    "conditional_access",
    "legacy_authentication_block",
    "admin_role_change",
    "guest_access_change",
    "defender_policy_change",
    "device_compliance",
    "password_policy",
    "other",
)

CHANGE_STATUS_VALUES = (
    "draft",
    "analyzing",
    "review_required",
    "approved",
    "rejected",
    "completed",
    "failed",
)


def _enum(name: str, values: tuple[str, ...]) -> sa.Enum:
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _create_postgresql_enums() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    postgresql.ENUM(*ENVIRONMENT_VALUES, name="environment_enum").create(bind, checkfirst=True)
    postgresql.ENUM(*CHANGE_TYPE_VALUES, name="change_type_enum").create(bind, checkfirst=True)
    postgresql.ENUM(*CHANGE_STATUS_VALUES, name="change_status_enum").create(bind, checkfirst=True)


def upgrade() -> None:
    _create_postgresql_enums()
    environment_enum = _enum("environment_enum", ENVIRONMENT_VALUES)
    change_type_enum = _enum("change_type_enum", CHANGE_TYPE_VALUES)
    change_status_enum = _enum("change_status_enum", CHANGE_STATUS_VALUES)

    op.create_table(
        "change_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("environment", environment_enum, nullable=False),
        sa.Column("change_type", change_type_enum, nullable=False),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("affected_scope", sa.Text(), nullable=False),
        sa.Column("rollback_plan", sa.Text(), nullable=False),
        sa.Column("maintenance_window", sa.Boolean(), nullable=False),
        sa.Column("pilot_enabled", sa.Boolean(), nullable=False),
        sa.Column("report_only_mode", sa.Boolean(), nullable=False),
        sa.Column("status", change_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "historical_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("environment", environment_enum, nullable=False),
        sa.Column("change_type", change_type_enum, nullable=False),
        sa.Column("outcome", sa.String(length=100), nullable=False),
        sa.Column("incident_occurred", sa.Boolean(), nullable=False),
        sa.Column("downtime_minutes", sa.Integer(), nullable=False),
        sa.Column("rollback_required", sa.Boolean(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("lessons_learned", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_request_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["change_request_id"], ["change_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_risk_assessments_change_request_id"),
        "risk_assessments",
        ["change_request_id"],
        unique=False,
    )
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("risk_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["risk_assessment_id"], ["risk_assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_checklist_items_risk_assessment_id"),
        "checklist_items",
        ["risk_assessment_id"],
        unique=False,
    )
    op.create_table(
        "risk_factors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("risk_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["risk_assessment_id"], ["risk_assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_risk_factors_risk_assessment_id"),
        "risk_factors",
        ["risk_assessment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_factors_risk_assessment_id"), table_name="risk_factors")
    op.drop_table("risk_factors")
    op.drop_index(op.f("ix_checklist_items_risk_assessment_id"), table_name="checklist_items")
    op.drop_table("checklist_items")
    op.drop_index(op.f("ix_risk_assessments_change_request_id"), table_name="risk_assessments")
    op.drop_table("risk_assessments")
    op.drop_table("historical_changes")
    op.drop_table("change_requests")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(*CHANGE_STATUS_VALUES, name="change_status_enum").drop(bind, checkfirst=True)
        postgresql.ENUM(*CHANGE_TYPE_VALUES, name="change_type_enum").drop(bind, checkfirst=True)
        postgresql.ENUM(*ENVIRONMENT_VALUES, name="environment_enum").drop(bind, checkfirst=True)
