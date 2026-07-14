# Operational Change Intelligence

Operational Change Intelligence is an MVP for analyzing planned changes in a Microsoft security environment before implementation. It estimates operational risk, explains why risk was assigned, finds similar historical failures, and produces a pre-implementation checklist.

The MVP is deterministic: no LLMs, no embeddings, and no opaque scoring.

## Problem

Security operations teams often approve Microsoft 365, Entra ID, Defender, Intune, and Azure changes with incomplete context:

- hidden legacy dependencies;
- service accounts affected by interactive controls;
- break-glass accounts accidentally scoped into enforcement;
- missing pilot or report-only phases;
- rollback plans that do not describe validation;
- repeated operational mistakes that are documented only in old tickets.

This creates avoidable lockouts, downtime, incident escalations, and emergency rollbacks.

## Product Value

The MVP helps reviewers answer:

- What is the risk level of this planned change?
- Which factors made it risky?
- What evidence triggered each factor?
- What similar changes failed before?
- What lessons learned should be reviewed?
- What checklist items should be completed before implementation?

## Architecture

Runtime services:

- `frontend`: Next.js, TypeScript, React, plain CSS.
- `backend`: FastAPI, SQLAlchemy 2, Pydantic 2, Alembic.
- `db`: PostgreSQL 16.

Backend intelligence modules:

- YAML rule engine: `backend/app/rules/change_risk_rules.yaml`
- Risk service: `backend/app/services/risk_engine.py`
- Similarity service: `backend/app/services/similarity.py`
- Human Error Intelligence analytics: `backend/app/services/analytics.py`
- Demo asset context: `backend/app/services/demo_assets.py`

More detail:

- [Architecture](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [Risk Engine](docs/RISK_ENGINE.md)
- [Demo Scenario](docs/DEMO_SCENARIO.md)
- [Limitations](docs/LIMITATIONS.md)

## Included UI

- Dashboard
- New Change
- Change Details
- Historical Changes
- Human Error Analytics

## Quick Start With Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Health: `http://localhost:8000/health`

On startup, the backend container runs:

1. `alembic upgrade head`
2. idempotent demo seed when `DEMO_MODE=true`
3. FastAPI server

## Local Backend

PowerShell SQLite demo setup:

```powershell
cd backend
$env:DATABASE_URL = "sqlite+pysqlite:///./local_dev.db"
$env:APP_CHECK_DB_ON_STARTUP = "false"
$env:DEMO_MODE = "true"
$env:CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
python -m pip install -r requirements.txt
python -m alembic upgrade head
cd ..
python scripts\seed_demo_data.py
cd backend
python -m uvicorn app.main:app --reload
```

## Local Frontend

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000"
npm run dev
```

## Demo Flow

Primary scenario:

```text
Enable MFA for all contractors
```

1. Open `http://localhost:3000`.
2. Go to `New Change`.
3. Select `Load demo scenario`.
4. Create the change.
5. Open the created change detail page.
6. Select `Run analysis`.
7. Review:
   - risk score;
   - risk level;
   - recommendation;
   - risk factors and points;
   - evidence for each factor;
   - checklist items;
   - similar historical changes;
   - past incidents;
   - lessons learned.

Expected demo result:

- risk level: `high` or `critical`;
- recommendation: `pilot_first` or `delay_and_investigate`;
- at least five risk factors;
- at least six checklist items;
- at least three similar historical changes;
- at least two similar failed changes.

## API Examples

Create a change:

```bash
curl -X POST http://localhost:8000/api/v1/changes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Enable MFA for all contractors",
    "description": "Require MFA for all external contractor accounts and block legacy authentication.",
    "environment": "entra_id",
    "change_type": "mfa_rollout",
    "planned_start": "2026-08-05T10:00:00Z",
    "planned_end": "2026-08-05T11:00:00Z",
    "affected_scope": "All contractor accounts, VPN access, Microsoft 365, legacy business applications.",
    "rollback_plan": "Disable the new Conditional Access policy.",
    "maintenance_window": false,
    "pilot_enabled": false,
    "report_only_mode": false
  }'
```

Analyze:

```bash
curl -X POST http://localhost:8000/api/v1/changes/{id}/analyze
curl http://localhost:8000/api/v1/changes/{id}/assessment
curl "http://localhost:8000/api/v1/changes/{id}/similar?limit=5"
```

Analytics:

```bash
curl http://localhost:8000/api/v1/analytics/summary
curl http://localhost:8000/api/v1/analytics/root-causes
curl http://localhost:8000/api/v1/analytics/change-types
curl http://localhost:8000/api/v1/analytics/failure-patterns
```

## Screenshots Placeholders

Add final screenshots after running the MVP locally:

- `docs/screenshots/dashboard.png`
- `docs/screenshots/new-change.png`
- `docs/screenshots/change-details-risk.png`
- `docs/screenshots/historical-changes.png`
- `docs/screenshots/human-error-analytics.png`

## Validation

Backend:

```bash
cd backend
python -m pytest
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
npm audit --audit-level=moderate
```

Compose syntax:

```bash
docker compose config
```

## Current Limitations

- No authentication.
- No real Microsoft Graph integration.
- No live Entra ID, Intune, Defender, or Azure ingestion.
- No embeddings or semantic search.
- Demo assets are JSON context, not first-class database entities.
- Risk scoring is deterministic and should be calibrated before production use.

See [Limitations](docs/LIMITATIONS.md).

## Future Integrations

- Microsoft Graph
- Entra Conditional Access policy export
- Intune device compliance policies
- Defender policy baselines
- CMDB or asset inventory
- ServiceNow or Jira change tickets
- Evidence attachments
- Approval workflow
- Role-based access control
