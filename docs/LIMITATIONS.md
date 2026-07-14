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

## Intended Next Steps

- Add real asset inventory ingestion.
- Add Microsoft Graph connectors.
- Add Entra Conditional Access policy parser.
- Add Intune and Defender policy ingestion.
- Add evidence attachments.
- Add review workflow and approvals.
- Add role-based access control.
- Add calibrated scoring from production incident history.
