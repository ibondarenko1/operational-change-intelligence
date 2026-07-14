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
- `category`
- `points`
- `category_cap`
- `conditions`
- `evidence_template`
- `checklist_items`

## Formula

The engine evaluates every matching rule, saves every triggered `RiskFactor`, then caps the score by category.

```text
score = min(100, sum(min(category_cap, max(0, sum(points by category)))))
```

The response includes:

- `raw_score`: uncapped sum of all factor points.
- `category_scores`: raw, capped, and cap per category.
- `capped_score`: sum of non-negative capped category scores before final 0-100 clamp.
- `formula_explanation`: readable category breakdown.

Category caps:

| Category | Cap |
| --- | ---: |
| `identity_scope` | 30 |
| `dependency` | 30 |
| `deployment_strategy` | 25 |
| `rollback` | 20 |
| `historical_evidence` | 20 |
| `timing` | 10 |

This prevents double-counting related signals, such as privileged accounts and break-glass accounts both inflating identity risk without limit.
It also prevents a net-negative category, such as deployment strategy after pilot and report-only controls, from reducing unrelated identity, dependency, rollback, historical, or timing risk.

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
- linked `Asset` records and dependency context
- all `HistoricalChange` records
- similarity results
- YAML risk rules
- impact analysis result

## Similarity Boundary

`SimilarityService` scores only similarity between changes:

- environment
- change type
- title keyword overlap
- description keyword overlap
- affected scope keyword overlap
- affected object types
- authentication methods
- policy type

Historical outcome is not part of `similarity_score`. Outcome, incident, root cause, downtime, rollback, `historical_failure_signal`, and `historical_severity` are returned separately as historical outcome context.

The risk engine first receives similar changes, then `similar_failures_found` adds risk only for similar records with a failure signal.

## Rollback Logic

`rollback_plan_missing` and `weak_rollback_validation` are mutually exclusive:

- missing or marker-only rollback plan triggers `rollback_plan_missing`;
- existing but weak rollback plan triggers `weak_rollback_validation`;
- tested and validated rollback can trigger `tested_rollback`, which reduces rollback category risk.

## Failure Mode Rules

Failure mode rules live in:

```text
backend/app/rules/failure_mode_rules.yaml
```

They are evaluated by `ImpactAnalysisService`, not by an LLM. They inspect change type, asset type, legacy status, authentication method, and dependency relationships to produce predicted failure modes and recommended actions.
