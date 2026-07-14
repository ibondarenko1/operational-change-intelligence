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
- Advanced charts

## Known Modeling Limits

- Demo assets are loaded from JSON, not persisted as first-class database entities.
- Similarity is keyword and metadata based, not semantic.
- Root-cause analytics depends on historical records being accurately tagged.
- Risk scoring is rule-based and should be calibrated with production incident data before operational use.
- Checklist items are generated from triggered rules and are not workflow tasks yet.
- Rollback validation is inferred from text, not verified against actual change evidence.

## Intended Next Steps

- Add real asset inventory model.
- Add Microsoft Graph connectors.
- Add Entra Conditional Access policy parser.
- Add Intune and Defender policy ingestion.
- Add evidence attachments.
- Add review workflow and approvals.
- Add role-based access control.
- Add calibrated scoring from production incident history.
