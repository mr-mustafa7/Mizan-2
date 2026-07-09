import Link from "next/link";
import { notFound } from "next/navigation";
import { PatientTrialEligibility } from "@/components/patients/PatientTrialEligibility";
import { PatientUnmatchedPanel } from "@/components/patients/PatientUnmatchedPanel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api } from "@/lib/api";
import {
  buildPatientTrialEligibility,
  buildUnmatchedPatientData,
} from "@/lib/eligibility";
import { patientLabel } from "@/lib/utils";

interface PatientDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function PatientDetailPage({
  params,
}: PatientDetailPageProps) {
  const { id } = await params;
  const [detail, matches, trials] = await Promise.all([
    api.getPatient(id),
    api.getMatches({ patient_id: id }),
    api.getTrials(),
  ]);

  if (!detail) notFound();

  const { patient, facts } = detail;

  const trialEligibility = await Promise.all(
    matches.map(async (match) => {
      const audit = await api.getAuditTrail(match.patient_id, match.trial_id);
      return buildPatientTrialEligibility(patient, facts, match, audit);
    })
  );

  const unmatchedData =
    matches.length === 0
      ? buildUnmatchedPatientData(patient, facts, trials)
      : null;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/patients"
            className="text-sm text-blue-700 hover:underline"
          >
            ← Patients
          </Link>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">
            {patient.patient_id}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {patientLabel(patient.patient_id, patient.age, patient.sex)}
          </p>
        </div>
        <StatusBadge
          label={`${patient.city}, ${patient.country}`}
          className="border-slate-200 bg-slate-100 text-slate-700"
        />
      </div>

      {matches.length > 0 && trialEligibility.length > 0 ? (
        <PatientTrialEligibility trials={trialEligibility} />
      ) : unmatchedData ? (
        <PatientUnmatchedPanel data={unmatchedData} />
      ) : null}
    </div>
  );
}
