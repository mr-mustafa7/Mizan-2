import Link from "next/link";
import { notFound } from "next/navigation";
import { AuditCriteriaList } from "@/components/matches/AuditCriteriaList";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api } from "@/lib/api";
import { getPatientById } from "@/lib/mock-data";
import { patientLabel, scoreColor, tierColor, tierLabel } from "@/lib/utils";

interface MatchDetailPageProps {
  params: Promise<{ patientId: string; trialId: string }>;
}

export default async function MatchDetailPage({ params }: MatchDetailPageProps) {
  const { patientId, trialId } = await params;
  const [match, auditRecords, patientDetail] = await Promise.all([
    api.getMatch(patientId, trialId),
    api.getAuditTrail(patientId, trialId),
    api.getPatient(patientId),
  ]);

  if (!match) notFound();

  const patient =
    patientDetail?.patient ?? getPatientById(patientId);

  return (
    <div className="space-y-8">
      <div>
        <Link href="/matches" className="text-sm text-teal-700 hover:underline">
          ← Matches
        </Link>
        <h2 className="mt-2 text-2xl font-semibold text-slate-900">
          {patientId} → {trialId}
        </h2>
        {patient && (
          <p className="mt-1 text-sm text-slate-500">
            {patientLabel(patient.patient_id, patient.age, patient.sex)}
            {patient.city ? ` · ${patient.city}, ${patient.country}` : ""}
          </p>
        )}
        <p className="mt-3 text-lg text-slate-800">{match.trial_title}</p>
      </div>

      <section className="grid gap-4 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Tier</p>
          <div className="mt-2">
            <StatusBadge
              label={tierLabel[match.tier]}
              className={tierColor[match.tier]}
            />
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Score</p>
          <p className={`mt-2 text-2xl font-semibold ${scoreColor(match.score)}`}>
            {match.score}
          </p>
          {match.location_bonus > 0 && (
            <p className="text-xs text-slate-500">
              includes +{match.location_bonus} location bonus
            </p>
          )}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Hard gates</p>
          <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
            <span className="rounded bg-rose-100 px-1.5 py-0.5 text-rose-700">
              {match.hard_failures} failures
            </span>
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700">
              {match.hard_unknowns} unknowns
            </span>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Soft rules</p>
          <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-700">
              {match.soft_rules_met}/{match.soft_rules_total} met
            </span>
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700">
              {match.soft_rules_unknown} unknown
            </span>
            <span className="rounded bg-rose-100 px-1.5 py-0.5 text-rose-700">
              {match.soft_failures} failures
            </span>
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-3 text-sm">
        <Link
          href={`/patients/${patientId}`}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 font-medium text-slate-700 hover:border-teal-300"
        >
          View patient
        </Link>
        <Link
          href={`/trials/${trialId}`}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 font-medium text-slate-700 hover:border-teal-300"
        >
          View trial
        </Link>
      </div>

      <section>
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-slate-900">
            Audit trail
          </h3>
          <p className="text-sm text-slate-500">
            Per-criterion evaluation from{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">
              GET /api/matches/{"{patient_id}"}/{"{trial_id}"}/audit
            </code>
            . Grouped by hard gate; inclusion rules first.
          </p>
        </div>
        <AuditCriteriaList records={auditRecords} />
      </section>
    </div>
  );
}
