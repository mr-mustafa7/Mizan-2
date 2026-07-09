import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api } from "@/lib/api";
import { enrollmentFill, formatPercent } from "@/lib/utils";

export default async function TrialsPage() {
  const trials = await api.getTrials();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Trials</h2>
        <p className="mt-1 text-sm text-slate-600">
          Clinical trials in the matching pool.
        </p>
      </div>

      <div className="space-y-4">
        {trials.map((trial) => {
          const fill = enrollmentFill(
            trial.enrollment_count,
            trial.target_enrollment
          );
          return (
            <Link
              key={trial.trial_id}
              href={`/trials/${trial.trial_id}`}
              className="block rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-300 hover:shadow"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-teal-700">
                    {trial.trial_id} · {trial.phase}
                  </p>
                  <p className="mt-1 text-lg font-semibold text-slate-900">
                    {trial.title}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    {trial.therapeutic_area} · {trial.sponsor}
                  </p>
                </div>
                <StatusBadge
                  label={trial.status}
                  className="border-slate-200 bg-slate-100 text-slate-700 capitalize"
                />
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-slate-500">
                <span>
                  Enrollment {trial.enrollment_count}/{trial.target_enrollment}
                </span>
                <span>{formatPercent(fill)} filled</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
