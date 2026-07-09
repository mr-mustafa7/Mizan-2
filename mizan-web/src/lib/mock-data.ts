import patients from "../../public/mocks/patients.json";
import patientP001 from "../../public/mocks/patient-P001.json";
import patientP006 from "../../public/mocks/patient-P006.json";
import patientP008 from "../../public/mocks/patient-P008.json";
import trials from "../../public/mocks/trials.json";
import trialNCT001 from "../../public/mocks/trial-NCT001.json";
import matches from "../../public/mocks/matches.json";
import auditTrailP001NCT001 from "../../public/mocks/audit-trail-P001-NCT001.json";
import coordinatorDashboard from "../../public/mocks/coordinator-dashboard.json";
import atRiskTrials from "../../public/mocks/at-risk-trials.json";
import trialSummary from "../../public/mocks/trial-summary.json";
import diagnosisSummary from "../../public/mocks/diagnosis-summary.json";

import type {
  AtRiskTrial,
  AuditRecord,
  CoordinatorDashboardRow,
  DiagnosisSummaryRow,
  Patient,
  PatientDetail,
  PatientTrialMatch,
  Trial,
  TrialDetail,
  TrialSummaryRow,
} from "@/lib/types";

const patientDetails: Record<string, PatientDetail> = {
  P001: patientP001 as PatientDetail,
  P006: patientP006 as PatientDetail,
  P008: patientP008 as PatientDetail,
};

const trialDetails: Record<string, TrialDetail> = {
  NCT001: trialNCT001 as TrialDetail,
};

const auditTrails: Record<string, AuditRecord[]> = {
  "P001/NCT001": auditTrailP001NCT001 as AuditRecord[],
};

function auditKey(patientId: string, trialId: string): string {
  return `${patientId}/${trialId}`;
}

export function getPatientById(patientId: string): Patient | undefined {
  return (patients as Patient[]).find((p) => p.patient_id === patientId);
}

export function getTrialById(trialId: string): Trial | undefined {
  return (trials as Trial[]).find((t) => t.trial_id === trialId);
}

export function getMatch(
  patientId: string,
  trialId: string
): PatientTrialMatch | undefined {
  return (matches as PatientTrialMatch[]).find(
    (m) => m.patient_id === patientId && m.trial_id === trialId
  );
}

export const mockApi = {
  getHealth() {
    return { status: "ok" };
  },

  getPatients(): Patient[] {
    return patients as Patient[];
  },

  getPatient(patientId: string): PatientDetail | null {
    const base = getPatientById(patientId);
    if (!base) return null;
    return (
      patientDetails[patientId] ?? {
        patient: base,
        facts: [],
      }
    );
  },

  getTrials(): Trial[] {
    return trials as Trial[];
  },

  getTrial(trialId: string): TrialDetail | null {
    const base = getTrialById(trialId);
    if (!base) return null;
    return (
      trialDetails[trialId] ?? {
        trial: base,
        criteria: [],
        sites: [],
      }
    );
  },

  getMatches(params?: {
    patient_id?: string;
    trial_id?: string;
    tier?: string;
  }): PatientTrialMatch[] {
    let filtered = [...(matches as PatientTrialMatch[])];
    if (params?.patient_id) {
      filtered = filtered.filter((m) => m.patient_id === params.patient_id);
    }
    if (params?.trial_id) {
      filtered = filtered.filter((m) => m.trial_id === params.trial_id);
    }
    if (params?.tier) {
      filtered = filtered.filter((m) => m.tier === params.tier);
    }
    return filtered;
  },

  getMatch(patientId: string, trialId: string): PatientTrialMatch | null {
    return getMatch(patientId, trialId) ?? null;
  },

  getAuditTrail(patientId: string, trialId: string): AuditRecord[] {
    return auditTrails[auditKey(patientId, trialId)] ?? [];
  },

  getAllAuditRecords(): AuditRecord[] {
    return Object.values(auditTrails).flat();
  },

  getCoordinatorDashboard(): CoordinatorDashboardRow[] {
    return coordinatorDashboard as CoordinatorDashboardRow[];
  },

  getAtRiskTrials(): AtRiskTrial[] {
    return atRiskTrials as AtRiskTrial[];
  },

  getTrialSummary(): TrialSummaryRow[] {
    return trialSummary as TrialSummaryRow[];
  },

  getDiagnosisSummary(): DiagnosisSummaryRow[] {
    return diagnosisSummary as DiagnosisSummaryRow[];
  },
};
