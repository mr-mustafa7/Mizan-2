import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { PatientTrialMatch } from "@/lib/types";
import { matchPath } from "@/lib/types";
import { getPatientById } from "@/lib/mock-data";
import { patientLabel, scoreColor, tierColor, tierLabel } from "@/lib/utils";

interface MatchTableProps {
  matches: PatientTrialMatch[];
  showPatient?: boolean;
  showTrial?: boolean;
}

export function MatchTable({
  matches,
  showPatient = true,
  showTrial = true,
}: MatchTableProps) {
  if (matches.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">
        No matches found.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-[640px] w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {showPatient && (
              <th className="px-4 py-3 text-left font-medium text-slate-600">
                Patient
              </th>
            )}
            {showTrial && (
              <th className="px-4 py-3 text-left font-medium text-slate-600">
                Trial
              </th>
            )}
            <th className="px-4 py-3 text-left font-medium text-slate-600">
              Tier
            </th>
            <th className="px-4 py-3 text-left font-medium text-slate-600">
              Rules
            </th>
            <th className="px-4 py-3 text-left font-medium text-slate-600">
              Score
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {matches.map((match) => {
            const patient = getPatientById(match.patient_id);
            return (
              <tr key={`${match.patient_id}-${match.trial_id}`} className="hover:bg-slate-50">
                {showPatient && (
                  <td className="px-4 py-3">
                    <Link
                      href={matchPath(match.patient_id, match.trial_id)}
                      className="font-medium text-teal-700 hover:underline"
                    >
                      {match.patient_id}
                    </Link>
                    {patient && (
                      <p className="text-xs text-slate-500">
                        {patientLabel(
                          patient.patient_id,
                          patient.age,
                          patient.sex
                        )}
                      </p>
                    )}
                  </td>
                )}
                {showTrial && (
                  <td className="px-4 py-3">
                    <p className="line-clamp-1 font-medium text-slate-800">
                      {match.trial_title}
                    </p>
                    <p className="text-xs text-slate-500">{match.trial_id}</p>
                  </td>
                )}
                <td className="px-4 py-3">
                  <StatusBadge
                    label={tierLabel[match.tier]}
                    className={tierColor[match.tier]}
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1.5 text-xs">
                    {match.hard_failures > 0 && (
                      <span className="rounded bg-rose-100 px-1.5 py-0.5 text-rose-700">
                        {match.hard_failures} hard fail
                      </span>
                    )}
                    {match.hard_unknowns > 0 && (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700">
                        {match.hard_unknowns} hard unknown
                      </span>
                    )}
                    {match.soft_rules_unknown > 0 && (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700">
                        {match.soft_rules_unknown} soft unknown
                      </span>
                    )}
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
                      {match.soft_rules_met}/{match.soft_rules_total} soft met
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`font-semibold ${scoreColor(match.score)}`}>
                    {match.score}
                  </span>
                  {match.location_bonus > 0 && (
                    <p className="text-xs text-slate-400">
                      +{match.location_bonus} location
                    </p>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
