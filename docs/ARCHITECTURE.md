# Architecture

## Components

Operational Change Intelligence is a deterministic MVP composed of:

- Next.js frontend
- FastAPI backend
- PostgreSQL database in Docker Compose
- Alembic migrations
- SQLAlchemy 2 models
- Pydantic 2 schemas
- YAML-based risk rules
- YAML-based failure mode rules
- deterministic similarity service
- deterministic impact analysis service
- Human Error Intelligence analytics
- synthetic historical changes and synthetic asset graph

## Runtime Flow

1. User creates a `ChangeRequest`.
2. Frontend calls `POST /api/v1/changes`.
3. User opens Change Details and runs analysis.
4. Backend loads the change, historical changes, demo asset graph, asset dependencies, risk rules, and failure mode rules.
5. `ImpactAnalysisService` identifies directly affected assets, dependent assets, business services, dependency paths, failure modes, blast radius, and missing context.
6. `SimilarityService` ranks historical changes by similarity only. Historical outcome, incident, root cause, downtime, and rollback are returned as context, not used as similarity score.
7. `RiskEngine` evaluates all matching risk rules, applies category caps, and creates risk factors and checklist items.
8. Backend stores the latest `RiskAssessment`; repeated analysis replaces the previous assessment for the same change.
9. Frontend renders impact summary, affected assets, dependency paths, failure modes, historical evidence, risk breakdown, checklist, and missing context.

## Backend Modules

- `app/api`: HTTP routes.
- `app/models`: SQLAlchemy models and enums.
- `app/schemas`: Pydantic request/response contracts.
- `app/services/impact_analysis.py`: asset dependency traversal and failure mode prediction.
- `app/services/risk_engine.py`: deterministic category-capped rule engine.
- `app/services/similarity.py`: deterministic historical similarity.
- `app/services/analytics.py`: Human Error Intelligence analytics.
- `app/services/demo_assets.py`: idempotent synthetic asset graph seed and demo change linking.
- `app/rules/change_risk_rules.yaml`: explainable risk rules.
- `app/rules/failure_mode_rules.yaml`: explainable failure mode rules.

## Deployment

`docker compose up --build` starts:

- `db`: PostgreSQL 16
- `backend`: FastAPI, Alembic migration, demo seed, API
- `frontend`: Next.js UI

The backend entrypoint runs migrations and idempotent demo seed before starting the API.
