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

The scenario is enriched by first-class `Asset`, `AssetDependency`, and `ChangeAsset` records loaded from `demo-data/demo_assets.json`.

Directly affected:

- Contractor Accounts
- svc-contractor-sync
- svc-vendor-billing
- svc-badge-provisioning
- breakglass-cloud-01
- breakglass-cloud-02

Dependent:

- Vendor Billing EWS Export
- Facilities Badge Provisioning
- Warehouse TimeClock Legacy Portal
- Contractor Document Intake
- Legacy Contractor VPN
- RADIUS authentication
- Conditional Access Exclusion

Affected business services:

- Contractor Onboarding
- Vendor Billing
- Badge Provisioning
- Remote Contractor Access

## Expected Detection

The system should detect:

- broad deployment scope;
- legacy application dependency;
- service account risk;
- break-glass account risk;
- missing pilot;
- missing report-only phase;
- weak rollback validation;
- similar previous failures.

Expected result:

- Risk level: `critical`
- Recommendation: `delay_and_investigate`
- At least five risk factors
- At least six checklist items
- At least three similar historical changes
- At least two similar failed historical changes
- At least four impact paths

Example impact path:

```text
mfa rollout
-> svc-vendor-billing
-> Vendor Billing EWS Export
-> Vendor Billing
```

Example predicted failure modes:

- Service account may fail authentication and stop automation.
- Contractor remote access may be disrupted.
- Legacy application authentication may fail.
- Emergency access may be blocked.

## Demo Flow

1. Open `http://localhost:3000`.
2. Go to `New Change`.
3. Select `Load demo scenario`.
4. Create the change.
5. Open the created change detail page.
6. Select `Run analysis`.
7. Review impact summary, affected assets, dependency paths, predicted failure modes, historical evidence, risk breakdown, missing context, and checklist.

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
curl http://localhost:8000/api/v1/changes/{id}/assessment
curl "http://localhost:8000/api/v1/changes/{id}/similar?limit=5"
```
