# Architecture

## Components

Operational Change Intelligence is a small MVP composed of:

- Next.js frontend
- FastAPI backend
- PostgreSQL database in Docker Compose
- Alembic migrations
- SQLAlchemy 2 models
- Pydantic 2 schemas
- YAML-based deterministic risk rules
- Deterministic similarity service
- Human Error Intelligence analytics service
- Synthetic demo data and demo asset context

## Runtime Flow

1. User creates a `ChangeRequest` in the frontend.
2. Frontend calls `POST /api/v1/changes`.
3. User opens the change detail page.
4. Frontend loads:
   - `GET /api/v1/changes/{id}`
   - `GET /api/v1/changes/{id}/similar`
   - `GET /api/v1/changes/{id}/assessment`
5. User runs analysis.
6. Frontend calls `POST /api/v1/changes/{id}/analyze`.
7. Backend loads:
   - change request
   - historical changes
   - matching demo asset context
   - YAML risk rules
8. Risk engine creates:
   - `RiskAssessment`
   - `RiskFactor` records
   - `ChecklistItem` records
9. Frontend renders score, level, recommendation, evidence, checklist, similar failures, and lessons learned.

## Backend Modules

- `app/api`: HTTP routes.
- `app/models`: SQLAlchemy models and enums.
- `app/schemas`: Pydantic request/response contracts.
- `app/services/risk_engine.py`: deterministic rule engine.
- `app/services/similarity.py`: deterministic historical similarity.
- `app/services/analytics.py`: Human Error Intelligence analytics.
- `app/services/demo_assets.py`: demo asset context matching.
- `app/rules/change_risk_rules.yaml`: explainable risk rules.

## Deployment

`docker compose up --build` starts:

- `db`: PostgreSQL 16
- `backend`: FastAPI, Alembic migration, demo seed, API
- `frontend`: Next.js UI

The backend entrypoint runs migrations and idempotent demo seed before starting the API.
