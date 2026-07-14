# Limitations

This MVP is intentionally deterministic and scoped.

## Not Included

- Authentication and authorization
- Multi-tenant user management
- Real Microsoft Graph ingestion
- Entra ID live policy inspection
- Intune or Defender live policy inspection
- CMDB integration
- Ticketing integration
- LLM reasoning
- Embeddings
- Neo4j or graph analysis
- Automatic remediation
- Automatic approval
- Advanced charts

## Known Modeling Limits

- Demo assets are first-class database records, but they are synthetic and not imported from a real CMDB or Microsoft Graph.
- Dependency traversal is deterministic and shallow; it is not a full production graph simulator.
- Similarity is keyword and metadata based, not semantic.
- Historical outcome data is curated demo data, not calibrated production incident history.
- Root-cause and causal-chain analytics depend on historical records being accurately tagged.
- Risk scoring is rule-based and should be calibrated with production incident data before operational use.
- Checklist items are generated from triggered rules and are not workflow tasks yet.
- Rollback validation is inferred from text, not verified against attached evidence.
- The impact analysis explains plausible operational failure paths; it does not prove that a failure will occur.
- Change-to-asset linkage is currently populated only when a change exactly matches a curated demo scenario (title, environment, and change type). A user-entered change that does not match a demo scenario has no linked assets yet, so its impact analysis is empty. A UI and API to attach specific assets to any change is future work; the graph traversal itself is already asset-driven, not keyword-driven.
- Business service is represented in two ways: an `Asset.business_service` string and a first-class `business_service` asset reached through a `supports` dependency. The engine merges both, but the string field duplicates the graph and should converge on the graph representation as the model matures.
- Assessment collections (directly affected assets, dependent assets, impact paths, predicted failure modes, similar changes, blast radius, missing context) are stored as JSON columns on `risk_assessments`. This is adequate for the MVP but will make querying, cross-assessment analytics, versioning, and change auditing harder later; these should move to relational tables before that need arrives.

## Intended Next Steps

- Add real asset inventory ingestion.
- Add Microsoft Graph connectors.
- Add Entra Conditional Access policy parser.
- Add Intune and Defender policy ingestion.
- Add evidence attachments.
- Add review workflow and approvals.
- Add role-based access control.
- Add calibrated scoring from production incident history.
