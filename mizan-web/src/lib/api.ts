import { mockApi } from "@/lib/mock-data";
import type {
  AtRiskTrial,
  AuditRecord,
  CoordinatorDashboardRow,
  DiagnosisSummaryRow,
  HealthResponse,
  MatchTier,
  Patient,
  PatientDetail,
  PatientTrialMatch,
  Trial,
  TrialDetail,
  TrialSummaryRow,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_API !== "false";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    next: { revalidate: 30 },
  });

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  async getHealth(): Promise<HealthResponse> {
    if (USE_MOCK) return mockApi.getHealth();
    return fetchApi<HealthResponse>("/api/health");
  },

  async getPatients(): Promise<Patient[]> {
    if (USE_MOCK) return mockApi.getPatients();
    return fetchApi<Patient[]>("/api/patients");
  },

  async getPatient(patientId: string): Promise<PatientDetail | null> {
    if (USE_MOCK) return mockApi.getPatient(patientId);
    try {
      return await fetchApi<PatientDetail>(`/api/patients/${patientId}`);
    } catch {
      return null;
    }
  },

  async getTrials(): Promise<Trial[]> {
    if (USE_MOCK) return mockApi.getTrials();
    return fetchApi<Trial[]>("/api/trials");
  },

  async getTrial(trialId: string): Promise<TrialDetail | null> {
    if (USE_MOCK) return mockApi.getTrial(trialId);
    try {
      return await fetchApi<TrialDetail>(`/api/trials/${trialId}`);
    } catch {
      return null;
    }
  },

  async getMatches(params?: {
    patient_id?: string;
    trial_id?: string;
    tier?: MatchTier;
  }): Promise<PatientTrialMatch[]> {
    if (USE_MOCK) return mockApi.getMatches(params);
    const query = new URLSearchParams();
    if (params?.patient_id) query.set("patient_id", params.patient_id);
    if (params?.trial_id) query.set("trial_id", params.trial_id);
    if (params?.tier) query.set("tier", params.tier);
    const qs = query.toString();
    return fetchApi<PatientTrialMatch[]>(
      `/api/matches${qs ? `?${qs}` : ""}`
    );
  },

  async getMatch(
    patientId: string,
    trialId: string
  ): Promise<PatientTrialMatch | null> {
    if (USE_MOCK) return mockApi.getMatch(patientId, trialId);
    try {
      return await fetchApi<PatientTrialMatch>(
        `/api/matches/${patientId}/${trialId}`
      );
    } catch {
      return null;
    }
  },

  async getAuditTrail(
    patientId: string,
    trialId: string
  ): Promise<AuditRecord[]> {
    if (USE_MOCK) return mockApi.getAuditTrail(patientId, trialId);
    return fetchApi<AuditRecord[]>(
      `/api/matches/${patientId}/${trialId}/audit`
    );
  },

  async getCoordinatorDashboard(): Promise<CoordinatorDashboardRow[]> {
    if (USE_MOCK) return mockApi.getCoordinatorDashboard();
    return fetchApi<CoordinatorDashboardRow[]>("/api/dashboard/coordinator");
  },

  async getAtRiskTrials(): Promise<AtRiskTrial[]> {
    if (USE_MOCK) return mockApi.getAtRiskTrials();
    return fetchApi<AtRiskTrial[]>("/api/dashboard/at-risk-trials");
  },

  async getTrialSummary(): Promise<TrialSummaryRow[]> {
    if (USE_MOCK) return mockApi.getTrialSummary();
    return fetchApi<TrialSummaryRow[]>("/api/dashboard/trial-summary");
  },

  async getDiagnosisSummary(): Promise<DiagnosisSummaryRow[]> {
    if (USE_MOCK) return mockApi.getDiagnosisSummary();
    return fetchApi<DiagnosisSummaryRow[]>("/api/dashboard/diagnosis-summary");
  },
};
