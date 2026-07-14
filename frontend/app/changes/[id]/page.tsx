"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { OutcomeBadge, RiskBadge } from "@/components/Badges";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateBlocks";
import {
  api,
  ApiError,
  ChangeRequest,
  formatLabel,
  RiskAssessment,
  SimilarHistoricalChange,
} from "@/lib/api";

export default function ChangeDetailsPage() {
  const params = useParams<{ id: string }>();
  const changeId = params.id;
  const [change, setChange] = useState<ChangeRequest | null>(null);
  const [assessment, setAssessment] = useState<RiskAssessment | null>(null);
  const [similar, setSimilar] = useState<SimilarHistoricalChange[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [changeResponse, similarResponse] = await Promise.all([
        api.getChange(changeId),
        api.getSimilar(changeId, 8),
      ]);
      setChange(changeResponse);
      setSimilar(similarResponse);

      try {
        const assessmentResponse = await api.getAssessment(changeId);
        setAssessment(assessmentResponse);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setAssessment(null);
        } else {
          throw err;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load change details");
    } finally {
      setLoading(false);
    }
  }, [changeId]);

  useEffect(() => {
    load();
  }, [load]);

  async function runAnalysis() {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await api.analyzeChange(changeId);
      setAssessment(result);
      setSimilar(await api.getSimilar(changeId, 8));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to analyze change");
    } finally {
      setAnalyzing(false);
    }
  }

  if (loading) {
    return <LoadingState title="Loading change details" />;
  }

  if (error) {
    return <ErrorState title="Change details unavailable" message={error} />;
  }

  if (!change) {
    return <EmptyState title="Change not found" message="The requested change request does not exist." />;
  }

  const historicalEvidence = assessment?.similar_changes?.length ? assessment.similar_changes : similar;
  const incidents = historicalEvidence.filter((item) => item.historical_failure_signal);

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <h1>{change.title}</h1>
          <p>
            {formatLabel(change.environment)} / {formatLabel(change.change_type)} /{" "}
            {formatLabel(change.status)}
          </p>
        </div>
        <div className="actions">
          <button className="button" type="button" onClick={runAnalysis} disabled={analyzing}>
            {analyzing ? "Analyzing" : "Run analysis"}
          </button>
          <Link className="button-secondary" href="/changes/new">
            New Change
          </Link>
        </div>
      </header>

      <section className="section grid-2">
        <div>
          <h2>Description</h2>
          <p>{change.description}</p>
          <h3>Affected scope</h3>
          <p>{change.affected_scope}</p>
        </div>
        <div>
          <h2>Implementation</h2>
          <p>
            <strong>Planned:</strong> {new Date(change.planned_start).toLocaleString()} -{" "}
            {new Date(change.planned_end).toLocaleString()}
          </p>
          <p>
            <strong>Rollback:</strong> {change.rollback_plan}
          </p>
          <p className="muted">
            Maintenance window: {change.maintenance_window ? "yes" : "no"} / Pilot:{" "}
            {change.pilot_enabled ? "yes" : "no"} / Report-only: {change.report_only_mode ? "yes" : "no"}
          </p>
        </div>
      </section>

      {assessment ? (
        <section className="section grid-2">
          <div className="score-block">
            <h2>Risk Assessment</h2>
            <span className="score-number">{assessment.score}</span>
            <RiskBadge level={assessment.level} />
            <strong>{formatLabel(assessment.recommendation)}</strong>
            <span className="muted">Confidence: {Math.round(assessment.confidence * 100)}%</span>
            <span className="muted">
              Raw score: {assessment.raw_score} / Capped score: {assessment.capped_score}
            </span>
            <div className="formula">{assessment.formula}</div>
            <p className="muted">{assessment.formula_explanation}</p>
          </div>
          <div>
            <h2>Risk Factors</h2>
            {assessment.risk_factors.length === 0 ? (
              <EmptyState title="No risk factors" message="No deterministic rules were triggered." />
            ) : (
              <ul className="list">
                {assessment.risk_factors.map((factor) => (
                  <li className="list-item" key={factor.id}>
                    <header>
                      <strong>{factor.title}</strong>
                      <span className="points">{factor.points > 0 ? `+${factor.points}` : factor.points}</span>
                    </header>
                    <p>
                      <strong>Category:</strong> {formatLabel(factor.category)} / cap {factor.category_cap}
                    </p>
                    <p>{factor.description}</p>
                    <p>
                      <strong>Evidence:</strong> {factor.evidence ?? "No evidence recorded"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : (
        <EmptyState
          title="No assessment yet"
          message="Run analysis to calculate risk score, factors, evidence, and checklist."
        />
      )}

      {assessment ? (
        <section className="section">
          <div className="section-header">
            <div>
              <h2>Impact Summary</h2>
              <p>Concrete blast radius derived from linked assets and dependencies.</p>
            </div>
          </div>
          <div className="metrics-grid">
            <div className="metric-card">
              <span>Users</span>
              <strong>{assessment.blast_radius.users_count ?? 0}</strong>
            </div>
            <div className="metric-card">
              <span>Applications</span>
              <strong>{assessment.blast_radius.applications_count ?? 0}</strong>
            </div>
            <div className="metric-card">
              <span>Service accounts</span>
              <strong>{assessment.blast_radius.service_accounts_count ?? 0}</strong>
            </div>
            <div className="metric-card">
              <span>Business services</span>
              <strong>{assessment.blast_radius.business_services_count ?? 0}</strong>
            </div>
            <div className="metric-card">
              <span>Critical assets</span>
              <strong>{assessment.blast_radius.critical_assets_count ?? 0}</strong>
            </div>
          </div>
        </section>
      ) : null}

      {assessment ? (
        <section className="section grid-2">
          <div>
            <h2>Affected Assets</h2>
            {assessment.directly_affected_assets.length === 0 ? (
              <EmptyState title="No direct assets" message="No assets are linked to this change request." />
            ) : (
              <ul className="list">
                {assessment.directly_affected_assets.map((asset) => (
                  <li className="list-item" key={`${asset.name}-${asset.relationship_type}`}>
                    <header>
                      <strong>{asset.name}</strong>
                      <span className="badge risk-high">{formatLabel(asset.criticality)}</span>
                    </header>
                    <p>
                      {formatLabel(asset.asset_type)} / auth: {asset.authentication_method ?? "none"}
                    </p>
                    <p>{asset.evidence}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h2>Dependent Assets</h2>
            {assessment.dependent_assets.length === 0 ? (
              <EmptyState title="No dependencies" message="No downstream dependencies were discovered." />
            ) : (
              <ul className="list">
                {assessment.dependent_assets.map((asset) => (
                  <li className="list-item" key={asset.name}>
                    <header>
                      <strong>{asset.name}</strong>
                      <span className="badge risk-medium">{formatLabel(asset.criticality)}</span>
                    </header>
                    <p>
                      {formatLabel(asset.asset_type)} / business: {asset.business_service ?? "unknown"}
                    </p>
                    <p className="muted">{asset.description}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : null}

      {assessment ? (
        <section className="section">
          <div className="section-header">
            <div>
              <h2>Dependency Paths</h2>
              <p>Explainable chains from the change to assets and business services.</p>
            </div>
          </div>
          {assessment.impact_paths.length === 0 ? (
            <EmptyState title="No impact paths" message="No business service dependency path was found." />
          ) : (
            <ul className="list">
              {assessment.impact_paths.map((path) => (
                <li className="list-item" key={path.path.join("->")}>
                  <header>
                    <strong>{path.business_service}</strong>
                    <span className="points">{path.path.length - 1} hops</span>
                  </header>
                  <p className="path-line">{path.path.join(" -> ")}</p>
                  <p>
                    <strong>Evidence:</strong> {path.evidence}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {assessment ? (
        <section className="section">
          <div className="section-header">
            <div>
              <h2>Predicted Failure Modes</h2>
              <p>Rule-based operational failure predictions from affected assets and dependencies.</p>
            </div>
          </div>
          {assessment.predicted_failure_modes.length === 0 ? (
            <EmptyState title="No failure modes" message="No failure mode rules matched this change." />
          ) : (
            <ul className="list">
              {assessment.predicted_failure_modes.map((mode) => (
                <li className="list-item" key={`${mode.code}-${mode.affected_asset}`}>
                  <header>
                    <strong>{mode.failure_mode}</strong>
                    <span className="badge risk-high">{formatLabel(mode.asset_type)}</span>
                  </header>
                  <p>
                    <strong>Affected asset:</strong> {mode.affected_asset}
                    {mode.business_service ? ` / ${mode.business_service}` : ""}
                  </p>
                  <p>
                    <strong>Business impact:</strong> {mode.business_impact}
                  </p>
                  <p>
                    <strong>Evidence:</strong> {mode.evidence}
                  </p>
                  <p>
                    <strong>Recommended action:</strong> {mode.recommended_actions.join("; ")}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {assessment ? (
        <section className="section grid-2">
          <div>
            <h2>Risk Breakdown</h2>
            {Object.entries(assessment.category_scores).length === 0 ? (
              <EmptyState title="No category scores" message="No risk categories were triggered." />
            ) : (
              <ul className="list">
                {Object.entries(assessment.category_scores).map(([category, values]) => (
                  <li className="list-item" key={category}>
                    <header>
                      <strong>{formatLabel(category)}</strong>
                      <span className="points">{values.capped}</span>
                    </header>
                    <p>
                      Raw: {values.raw} / Capped: {values.capped} / Cap: {values.cap}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h2>Missing Context</h2>
            {assessment.missing_context.length === 0 ? (
              <EmptyState title="No missing context" message="Required context is present for this analysis." />
            ) : (
              <ul className="list">
                {assessment.missing_context.map((item) => (
                  <li className="list-item" key={item}>
                    <p>{item}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : null}

      {assessment ? (
        <section className="section">
          <div className="section-header">
            <div>
              <h2>Checklist</h2>
              <p>Generated from triggered deterministic rules.</p>
            </div>
          </div>
          {assessment.checklist_items.length === 0 ? (
            <EmptyState title="No checklist items" message="No rule generated a checklist item." />
          ) : (
            <ul className="list">
              {assessment.checklist_items.map((item) => (
                <li className="list-item" key={item.id}>
                  <header>
                    <strong>{item.title}</strong>
                    <span className="badge risk-medium">{item.priority}</span>
                  </header>
                  <p>{item.description}</p>
                  <p className="muted">Status: {formatLabel(item.status)}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Similar Historical Changes</h2>
            <p>Similarity is deterministic and independent from the historical outcome.</p>
          </div>
        </div>
        {historicalEvidence.length === 0 ? (
          <EmptyState title="No similar changes" message="Seed historical changes to compare this request." />
        ) : (
          <ul className="list">
            {historicalEvidence.map((item) => (
              <li className="list-item" key={item.historical_change_id}>
                <header>
                  <strong>{item.title}</strong>
                  <span className="points">{item.similarity_score.toFixed(2)}</span>
                </header>
                <OutcomeBadge outcome={item.outcome} incident={item.incident_occurred} />
                <p>
                  <strong>Why similar:</strong> {item.matching_factors.join("; ")}
                </p>
                <p>
                  <strong>Past outcome:</strong> {formatLabel(item.outcome)} / severity:{" "}
                  {formatLabel(item.historical_severity)} / downtime: {item.downtime_minutes}m
                </p>
                <p>
                  <strong>Root cause:</strong> {formatLabel(item.root_cause)}
                </p>
                <p>
                  <strong>Lessons:</strong> {item.lessons_learned ?? "No lesson recorded"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Past Incidents</h2>
            <p>Similar failed or incident historical records.</p>
          </div>
        </div>
        {incidents.length === 0 ? (
          <EmptyState title="No past incidents in similar results" message="No failed similar changes were returned." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Change</th>
                  <th>Root cause</th>
                  <th>Downtime</th>
                  <th>Lessons learned</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((incident) => (
                  <tr key={incident.historical_change_id}>
                    <td>{incident.title}</td>
                    <td>{formatLabel(incident.root_cause)}</td>
                    <td>{incident.downtime_minutes}m</td>
                    <td>{incident.lessons_learned ?? "None"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
