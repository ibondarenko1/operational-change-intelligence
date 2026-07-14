# Data Model

## ChangeRequest

Represents a planned Microsoft security change.

Core fields:

- `id`
- `title`
- `description`
- `environment`
- `change_type`
- `planned_start`
- `planned_end`
- `affected_scope`
- `rollback_plan`
- `maintenance_window`
- `pilot_enabled`
- `report_only_mode`
- `status`
- `created_at`
- `updated_at`

## Asset

Represents a concrete object that can be affected by a change.

Core fields:

- `id`
- `name`
- `asset_type`
- `environment`
- `description`
- `business_service`
- `owner`
- `criticality`
- `authentication_method`
- `is_legacy`
- `is_privileged`
- `asset_metadata`
- `created_at`

Supported asset types include user groups, service accounts, break-glass accounts, applications, VPNs, policies, business services, integrations, device groups, and `other`.

## AssetDependency

Represents a directed dependency between two assets.

Core fields:

- `id`
- `source_asset_id`
- `target_asset_id`
- `dependency_type`
- `description`

Dependency types include `authenticates_through`, `depends_on`, `used_by`, `supports`, `connects_to`, `protected_by`, and `owned_by`.

## ChangeAsset

Links a `ChangeRequest` to a concrete `Asset`.

Core fields:

- `change_request_id`
- `asset_id`
- `relationship_type`
- `evidence`

The demo scenario links contractor accounts, service accounts, and break-glass accounts as directly affected assets.

## HistoricalChange

Represents a past change used for similarity and analytics.

Core fields:

- `id`
- `title`
- `description`
- `environment`
- `change_type`
- `outcome`
- `incident_occurred`
- `downtime_minutes`
- `rollback_required`
- `root_cause`
- `lessons_learned`
- `trigger`
- `technical_cause`
- `process_failure`
- `business_impact`
- `preventive_control`
- `created_at`

The causal-chain fields support Human Error Intelligence views.

## RiskAssessment

Stores the latest deterministic analysis for one change.

Core fields:

- `id`
- `change_request_id`
- `score`
- `raw_score`
- `capped_score`
- `level`
- `recommendation`
- `confidence`
- `category_scores`
- `formula_explanation`
- `similar_changes`
- `directly_affected_assets`
- `dependent_assets`
- `affected_business_services`
- `impact_paths`
- `predicted_failure_modes`
- `blast_radius`
- `missing_context`
- `created_at`

Repeated analysis replaces the previous assessment for that change.

## RiskFactor

Stores each triggered risk rule.

Fields include:

- `code`
- `title`
- `description`
- `category`
- `category_cap`
- `points`
- `evidence`

## ChecklistItem

Stores implementation checks generated from triggered rules.

Fields include:

- `code`
- `title`
- `description`
- `priority`
- `status`
