# MVP Demo Scenario

## Scenario

Title: `Enable MFA for all contractors`

Description: `Require MFA for all external contractor accounts and block legacy authentication.`

Environment: `entra_id`

Change type: `mfa_rollout`

Affected scope: `All contractor accounts, VPN access, Microsoft 365, legacy business applications.`

Rollback plan: `Disable the new Conditional Access policy.`

Pilot enabled: `false`

Report-only mode: `false`

Maintenance window: `false`

## Related Demo Assets

The scenario is enriched by `demo-data/demo_assets.json`.

| Asset group | Count | Why it matters |
| --- | ---: | --- |
| Contractor accounts | 127 | Broad identity population with external users. |
| Legacy applications | 4 | Legacy auth dependencies can break during MFA enforcement. |
| Service accounts | 3 | Automation identities may fail interactive MFA requirements. |
| Break-glass accounts | 2 | Emergency access must be excluded and validated. |
| Legacy VPN integration | 1 | VPN/RADIUS behavior can depend on legacy auth flows. |

## Expected Detection

The risk engine should trigger at least these factors:

- `broad_scope`
- `legacy_applications_present`
- `service_accounts_affected`
- `break_glass_accounts_affected`
- `outside_maintenance_window`
- `pilot_missing`
- `report_only_missing`
- `weak_rollback_validation`
- `similar_failures_found`

Expected result:

- Risk level: `high` or `critical`
- Recommendation: `pilot_first` or `delay_and_investigate`
- At least five risk factors
- At least six checklist items
- At least three similar historical changes
- At least two similar failed historical changes

## Demo Flow

1. Open `http://localhost:3000`.
2. Go to `New Change`.
3. Select `Load demo scenario`.
4. Create the change.
5. Open the created change detail page.
6. Select `Run analysis`.
7. Review risk score, factors, evidence, checklist, similar changes, incidents, and lessons learned.

## API Flow

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

```bash
curl -X POST http://localhost:8000/api/v1/changes/{id}/analyze
curl "http://localhost:8000/api/v1/changes/{id}/similar?limit=5"
```
