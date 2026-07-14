# Data Model

## ChangeRequest

Represents a planned Microsoft security change.

Fields include:

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

## HistoricalChange

Represents a past change used for similarity and analytics.

Fields include:

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
- `created_at`

## RiskAssessment

Stores the result of deterministic analysis for one change.

Fields include:

- `id`
- `change_request_id`
- `score`
- `level`
- `recommendation`
- `confidence`
- `created_at`

Repeated analysis replaces the previous assessment for that change.

## RiskFactor

Stores each triggered risk rule.

Fields include:

- `code`
- `title`
- `description`
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

## Demo Assets

`demo-data/demo_assets.json` is intentionally not a database table in the MVP. It provides deterministic asset context for the primary demonstration scenario:

- contractor accounts
- legacy applications
- service accounts
- break-glass accounts
- legacy VPN integration

This keeps the MVP small while demonstrating how future CMDB, Entra ID, Intune, or Microsoft Graph integrations could enrich risk analysis.
