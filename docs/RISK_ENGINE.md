# Risk Engine

## Design

The risk engine is deterministic and does not use AI, LLMs, or embeddings.

Rules live in:

```text
backend/app/rules/change_risk_rules.yaml
```

Each rule includes:

- `code`
- `title`
- `description`
- `points`
- `conditions`
- `evidence_template`
- `checklist_items`

## Formula

```text
score = min(100, max(0, sum(risk_factors.points)))
```

Risk levels:

| Score | Level | Recommendation |
| ---: | --- | --- |
| 0-29 | low | proceed |
| 30-49 | medium | proceed_with_safeguards |
| 50-69 | high | pilot_first |
| 70-100 | critical | delay_and_investigate |

## Inputs

Risk analysis uses:

- current `ChangeRequest`
- all `HistoricalChange` records
- matching demo asset context, when available
- YAML rule definitions

## Current Rule Families

- privileged accounts affected
- service accounts affected
- break-glass accounts affected
- rollback missing
- broad scope
- legacy applications present
- outside maintenance window
- pilot missing or enabled
- report-only missing or enabled
- weak rollback validation
- similar historical failures found
- tested rollback

## Similar Failures

`similar_failures_found` uses `SimilarityService`, which scores historical records from 0 to 1 using:

- environment match
- change type match
- title keyword overlap
- description keyword overlap
- affected scope keyword overlap
- historical incident
- root cause
- rollback requirement

Risk points depend on both the number of failed similar changes and their similarity scores, with a configured maximum.

## Explainability

Each triggered rule creates a `RiskFactor` with:

- point value
- natural-language title
- description
- evidence string

Each triggered rule can also create checklist items.
