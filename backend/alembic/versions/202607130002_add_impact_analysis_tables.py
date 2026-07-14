"""add impact analysis tables

Revision ID: 202607130002
Revises: 202607130001
Create Date: 2026-07-13 00:00:02 UTC
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202607130002"
down_revision: str | Sequence[str] | None = "202607130001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ASSET_TYPE_VALUES = (
    "user_group",
    "service_account",
    "break_glass_account",
    "application",
    "vpn",
    "policy",
    "business_service",
    "integration",
    "device_group",
    "other",
)

DEPENDENCY_TYPE_VALUES = (
    "authenticates_through",
    "depends_on",
    "used_by",
    "supports",
    "connects_to",
    "protected_by",
    "owned_by",
)

CRITICALITY_VALUES = ("low", "medium", "high", "critical")
ENVIRONMENT_VALUES = ("entra_id", "microsoft_365", "defender", "azure", "other")


def _enum(name: str, values: tuple[str, ...]) -> sa.Enum:
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _create_postgresql_enums() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    postgresql.ENUM(*ASSET_TYPE_VALUES, name="asset_type_enum").create(bind, checkfirst=True)
    postgresql.ENUM(*DEPENDENCY_TYPE_VALUES, name="dependency_type_enum").create(bind, checkfirst=True)
    postgresql.ENUM(*CRITICALITY_VALUES, name="criticality_enum").create(bind, checkfirst=True)


def upgrade() -> None:
    _create_postgresql_enums()
    asset_type_enum = _enum("asset_type_enum", ASSET_TYPE_VALUES)
    dependency_type_enum = _enum("dependency_type_enum", DEPENDENCY_TYPE_VALUES)
    criticality_enum = _enum("criticality_enum", CRITICALITY_VALUES)
    environment_enum = _enum("environment_enum", ENVIRONMENT_VALUES)

    op.add_column("historical_changes", sa.Column("trigger", sa.Text(), nullable=True))
    op.add_column("historical_changes", sa.Column("technical_cause", sa.Text(), nullable=True))
    op.add_column("historical_changes", sa.Column("process_failure", sa.Text(), nullable=True))
    op.add_column("historical_changes", sa.Column("business_impact", sa.Text(), nullable=True))
    op.add_column("historical_changes", sa.Column("preventive_control", sa.Text(), nullable=True))

    op.add_column("risk_assessments", sa.Column("raw_score", sa.Integer(), nullable=True))
    op.add_column("risk_assessments", sa.Column("capped_score", sa.Integer(), nullable=True))
    op.add_column("risk_assessments", sa.Column("category_scores", sa.JSON(), nullable=True))
    op.add_column("risk_assessments", sa.Column("formula_explanation", sa.Text(), nullable=True))
    op.add_column("risk_assessments", sa.Column("similar_changes", sa.JSON(), nullable=True))
    op.add_column("risk_assessments", sa.Column("directly_affected_assets", sa.JSON(), nullable=True))
    op.add_column("risk_assessments", sa.Column("dependent_assets", sa.JSON(), nullable=True))
    op.add_column("risk_assessments", sa.Column("affected_business_services", sa.JSON(), nullable=True))
    op.add_column("risk_assessments", sa.Column("impact_paths", sa.JSON(), nullable=True))
    op.add_column("risk_assessments", sa.Column("predicted_failure_modes", sa.JSON(), nullable=True))
    op.add_column("risk_assessments", sa.Column("blast_radius", sa.JSON(), nullable=True))
    op.add_column("risk_assessments", sa.Column("missing_context", sa.JSON(), nullable=True))

    op.add_column(
        "risk_factors",
        sa.Column("category", sa.String(length=80), nullable=False, server_default="uncategorized"),
    )
    op.add_column(
        "risk_factors",
        sa.Column("category_cap", sa.Integer(), nullable=False, server_default="100"),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("asset_type", asset_type_enum, nullable=False),
        sa.Column("environment", environment_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("business_service", sa.String(length=200), nullable=True),
        sa.Column("owner", sa.String(length=200), nullable=True),
        sa.Column("criticality", criticality_enum, nullable=False),
        sa.Column("authentication_method", sa.String(length=200), nullable=True),
        sa.Column("is_legacy", sa.Boolean(), nullable=False),
        sa.Column("is_privileged", sa.Boolean(), nullable=False),
        sa.Column("asset_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_assets_name"), "assets", ["name"], unique=False)

    op.create_table(
        "asset_dependencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_asset_id", sa.Uuid(), nullable=False),
        sa.Column("target_asset_id", sa.Uuid(), nullable=False),
        sa.Column("dependency_type", dependency_type_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["source_asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_dependencies_source_asset_id"),
        "asset_dependencies",
        ["source_asset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_dependencies_target_asset_id"),
        "asset_dependencies",
        ["target_asset_id"],
        unique=False,
    )

    op.create_table(
        "change_assets",
        sa.Column("change_request_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=80), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["change_request_id"], ["change_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("change_request_id", "asset_id", "relationship_type"),
    )


def downgrade() -> None:
    op.drop_table("change_assets")
    op.drop_index(op.f("ix_asset_dependencies_target_asset_id"), table_name="asset_dependencies")
    op.drop_index(op.f("ix_asset_dependencies_source_asset_id"), table_name="asset_dependencies")
    op.drop_table("asset_dependencies")
    op.drop_index(op.f("ix_assets_name"), table_name="assets")
    op.drop_table("assets")

    op.drop_column("risk_factors", "category_cap")
    op.drop_column("risk_factors", "category")

    op.drop_column("risk_assessments", "missing_context")
    op.drop_column("risk_assessments", "blast_radius")
    op.drop_column("risk_assessments", "predicted_failure_modes")
    op.drop_column("risk_assessments", "impact_paths")
    op.drop_column("risk_assessments", "affected_business_services")
    op.drop_column("risk_assessments", "dependent_assets")
    op.drop_column("risk_assessments", "directly_affected_assets")
    op.drop_column("risk_assessments", "similar_changes")
    op.drop_column("risk_assessments", "formula_explanation")
    op.drop_column("risk_assessments", "category_scores")
    op.drop_column("risk_assessments", "capped_score")
    op.drop_column("risk_assessments", "raw_score")

    op.drop_column("historical_changes", "preventive_control")
    op.drop_column("historical_changes", "business_impact")
    op.drop_column("historical_changes", "process_failure")
    op.drop_column("historical_changes", "technical_cause")
    op.drop_column("historical_changes", "trigger")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(*CRITICALITY_VALUES, name="criticality_enum").drop(bind, checkfirst=True)
        postgresql.ENUM(*DEPENDENCY_TYPE_VALUES, name="dependency_type_enum").drop(bind, checkfirst=True)
        postgresql.ENUM(*ASSET_TYPE_VALUES, name="asset_type_enum").drop(bind, checkfirst=True)
