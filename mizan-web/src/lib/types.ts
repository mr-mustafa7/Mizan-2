export type MatchTier =
  | "ELIGIBLE"
  | "NEEDS_SCREENING"
  | "REVIEW"
  | "NOT_ELIGIBLE";

export type CriterionResult =
  | "MET"
  | "NOT_MET"
  | "UNKNOWN"
  | "NOT_APPLICABLE";

export type RuleType = "inclusion" | "exclusion";

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: string[];
  };
}

export interface Patient {
  patient_id: string;
  age: number;
  sex: string;
  city: string;
  country: string;
}

export interface PatientFact {
  patient_id: string;
  fact_id: string;
  field_name: string;
  num_value: number | string | null;
  str_value: string;
  unit: string;
  negated: boolean;
  confidence: string;
  source: string;
}

export interface PatientDetail {
  patient: Patient;
  facts: PatientFact[];
}

export interface Trial {
  trial_id: string;
  title: string;
  phase: string;
  sponsor: string;
  therapeutic_area: string;
  status: string;
  enrollment_count: number;
  target_enrollment: number;
}

export interface EligibilityCriterion {
  criterion_id: string;
  trial_id: string;
  rule_type: RuleType;
  sequence_num: string;
  field_checked: string;
  operator: string;
  value: string;
  unit?: string;
  time_window?: string;
  notes?: string;
  hard_gate: boolean;
  criterion_text: string;
}

export interface Site {
  site_id: string;
  trial_id: string;
  site_name: string;
  city: string;
  country: string;
}

export interface TrialDetail {
  trial: Trial;
  criteria: EligibilityCriterion[];
  sites: Site[];
}

export interface PatientTrialMatch {
  patient_id: string;
  trial_id: string;
  trial_title: string;
  tier: MatchTier;
  score: number;
  soft_rules_met: number;
  soft_rules_total: number;
  soft_rules_unknown: number;
  location_bonus: number;
  hard_failures: number;
  hard_unknowns: number;
  soft_failures: number;
}

export interface AuditRecord {
  patient_id: string;
  trial_id: string;
  criterion_id: string;
  field_checked: string;
  rule_type: RuleType;
  hard_gate: boolean;
  result: CriterionResult;
  reason: string;
  patient_info: string;
  criterion_text: string;
}

export interface CoordinatorDashboardRow {
  trial_id: string;
  title: string;
  therapeutic_area: string;
  phase: string;
  sponsor: string;
  enrollment_count: number;
  target_enrollment: number;
  shortfall: number;
  fill_pct: number;
  eligible_count: number;
  needs_screening_count: number;
  review_count: number;
}

export interface AtRiskTrial {
  trial_id: string;
  title: string;
  therapeutic_area: string;
  phase: string;
  sponsor: string;
  enrollment_count: number;
  target_enrollment: number;
  shortfall: number;
  fill_pct: number;
}

export interface TrialSummaryRow {
  trial_id: string;
  trial_title: string;
  eligible_count: number;
  needs_screening_count: number;
  review_count: number;
  not_eligible_count: number;
}

export interface DiagnosisSummaryRow {
  diagnosis: string;
  eligible_patient_count: number;
}

export interface HealthResponse {
  status: string;
}

export interface ImportResponse {
  status: string;
  message: string;
  inputs: Record<string, number>;
  output_row_counts: Record<string, number>;
}

export interface MatchRunResponse {
  status: string;
  run_id: string;
  duration_ms: number;
  output_row_counts: Record<string, number>;
}

export function matchPath(patientId: string, trialId: string): string {
  return `/matches/${patientId}/${trialId}`;
}
