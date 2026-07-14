export type Environment = "entra_id" | "microsoft_365" | "defender" | "azure" | "other";
export type ChangeType =
  | "mfa_rollout"
  | "conditional_access"
  | "legacy_authentication_block"
  | "admin_role_change"
  | "guest_access_change"
  | "defender_policy_change"
  | "device_compliance"
  | "password_policy"
  | "other";
export type ChangeStatus =
  | "draft"
  | "analyzing"
  | "review_required"
  | "approved"
  | "rejected"
  | "completed"
  | "failed";

export type ChangeRequest = {
  id: string;
  title: string;
  description: string;
  environment: Environment;
  change_type: ChangeType;
  planned_start: string;
  planned_end: string;
  affected_scope: string;
  rollback_plan: string;
  maintenance_window: boolean;
  pilot_enabled: boolean;
  report_only_mode: boolean;
  status: ChangeStatus;
  created_at: string;
  updated_at: string;
  risk_assessments: RiskAssessment[];
};

export type ChangeRequestCreate = Omit<
  ChangeRequest,
  "id" | "created_at" | "updated_at" | "risk_assessments"
>;

export type RiskFactor = {
  id: string;
  risk_assessment_id: string;
  code: string;
  title: string;
  description: string;
  category: string;
  category_cap: number;
  points: number;
  evidence: string | null;
};

export type ChecklistItem = {
  id: string;
  risk_assessment_id: string;
  code: string;
  title: string;
  description: string;
  priority: string;
  status: string;
};

export type RiskAssessment = {
  id: string;
  change_request_id: string;
  score: number;
  raw_score: number;
  capped_score: number;
  level: "low" | "medium" | "high" | "critical";
  recommendation: string;
  confidence: number;
  category_scores: Record<string, { raw: number; capped: number; cap: number }>;
  formula_explanation: string;
  created_at: string;
  formula: string;
  risk_factors: RiskFactor[];
  checklist_items: ChecklistItem[];
  similar_changes: SimilarHistoricalChange[];
  directly_affected_assets: ImpactAsset[];
  dependent_assets: ImpactAsset[];
  affected_business_services: ImpactAsset[];
  impact_paths: ImpactPath[];
  predicted_failure_modes: FailureMode[];
  blast_radius: BlastRadius;
  missing_context: string[];
};

export type HistoricalChange = {
  id: string;
  title: string;
  description: string;
  environment: Environment;
  change_type: ChangeType;
  outcome: string;
  incident_occurred: boolean;
  downtime_minutes: number;
  rollback_required: boolean;
  root_cause: string | null;
  lessons_learned: string | null;
  trigger: string | null;
  technical_cause: string | null;
  process_failure: string | null;
  business_impact: string | null;
  preventive_control: string | null;
  created_at: string;
};

export type SimilarHistoricalChange = {
  historical_change_id: string;
  title: string;
  similarity_score: number;
  matching_factors: string[];
  outcome: string;
  incident_occurred: boolean;
  root_cause: string | null;
  downtime_minutes: number;
  rollback_required: boolean;
  lessons_learned: string | null;
  historical_failure_signal: boolean;
  historical_severity: "low" | "medium" | "high" | "critical";
};

export type ImpactAsset = {
  id?: string;
  name: string;
  asset_type: string;
  environment?: string;
  description?: string;
  business_service?: string | null;
  owner?: string | null;
  criticality: string;
  authentication_method?: string | null;
  is_legacy?: boolean;
  is_privileged?: boolean;
  asset_metadata?: Record<string, unknown>;
  relationship_type?: string;
  evidence?: string;
};

export type ImpactPath = {
  change: string;
  path: string[];
  dependency_types: string[];
  business_service: string;
  evidence: string;
};

export type FailureMode = {
  code: string;
  failure_mode: string;
  affected_asset: string;
  asset_type: string;
  business_service: string | null;
  business_impact: string;
  evidence: string;
  recommended_actions: string[];
};

export type BlastRadius = {
  users_count?: number;
  applications_count?: number;
  service_accounts_count?: number;
  business_services_count?: number;
  critical_assets_count?: number;
};

export type AnalyticsSummary = {
  total_changes: number;
  successful_changes: number;
  failed_changes: number;
  failure_rate: number;
  changes_with_incidents: number;
  average_downtime_minutes: number;
  most_common_root_cause: string | null;
  highest_risk_change_type: ChangeType | null;
  common_process_failures: string[];
  common_preventive_controls: string[];
  common_business_impacts: string[];
};

export type RootCauseAnalytics = {
  root_cause: string;
  count: number;
  percentage: number;
  average_downtime: number;
  rollback_rate: number;
  affected_change_types: ChangeType[];
};

export type ChangeTypeAnalytics = {
  change_type: ChangeType;
  total: number;
  successful: number;
  failed: number;
  failure_rate: number;
  average_downtime: number;
  common_root_causes: string[];
};

export type FailurePattern = {
  pattern_type: string;
  title: string;
  description: string;
  count: number;
  rate: number | null;
  average_downtime: number | null;
  severity_score: number;
  affected_change_types: ChangeType[];
  root_causes: string[];
  evidence: string[];
  process_failure: string | null;
  technical_cause: string | null;
  business_impact: string | null;
  preventive_control: string | null;
};

export type HistoricalFilters = {
  environment?: Environment | "";
  change_type?: ChangeType | "";
  incident_occurred?: "true" | "false" | "";
  root_cause?: string;
  outcome?: string;
};

export const environments: Environment[] = ["entra_id", "microsoft_365", "defender", "azure", "other"];
export const changeTypes: ChangeType[] = [
  "mfa_rollout",
  "conditional_access",
  "legacy_authentication_block",
  "admin_role_change",
  "guest_access_change",
  "defender_policy_change",
  "device_compliance",
  "password_policy",
  "other",
];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const payload = await response.json();
      message = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    } catch {
      // Keep the HTTP status text.
    }
    throw new ApiError(response.status, message);
  }

  return (await response.json()) as T;
}

function queryString(params: Record<string, string | number | boolean | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") {
      continue;
    }
    query.set(key, String(value));
  }
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

export const api = {
  getSummary: () => fetchJson<AnalyticsSummary>("/api/v1/analytics/summary"),
  getRootCauses: () => fetchJson<RootCauseAnalytics[]>("/api/v1/analytics/root-causes"),
  getChangeTypeAnalytics: () => fetchJson<ChangeTypeAnalytics[]>("/api/v1/analytics/change-types"),
  getFailurePatterns: () => fetchJson<FailurePattern[]>("/api/v1/analytics/failure-patterns"),
  listChanges: (limit = 100) => fetchJson<ChangeRequest[]>(`/api/v1/changes${queryString({ limit })}`),
  getChange: (id: string) => fetchJson<ChangeRequest>(`/api/v1/changes/${id}`),
  createChange: (payload: ChangeRequestCreate) =>
    fetchJson<ChangeRequest>("/api/v1/changes", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  analyzeChange: (id: string) =>
    fetchJson<RiskAssessment>(`/api/v1/changes/${id}/analyze`, {
      method: "POST",
    }),
  getAssessment: (id: string) => fetchJson<RiskAssessment>(`/api/v1/changes/${id}/assessment`),
  getSimilar: (id: string, limit = 5) =>
    fetchJson<SimilarHistoricalChange[]>(`/api/v1/changes/${id}/similar${queryString({ limit })}`),
  listHistorical: (filters: HistoricalFilters = {}, limit = 100) =>
    fetchJson<HistoricalChange[]>(
      `/api/v1/historical-changes${queryString({
        ...filters,
        limit,
      })}`,
    ),
};

export function formatLabel(value: string | null | undefined): string {
  if (!value) {
    return "None";
  }
  return value.replaceAll("_", " ");
}
