import Link from "next/link";
import { notFound } from "next/navigation";
import { MatchTable } from "@/components/matches/MatchTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api } from "@/lib/api";
import { enrollmentFill, formatPercent } from "@/lib/utils";

interface TrialDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function TrialDetailPage({ params }: TrialDetailPageProps) {
  const { id } = await params;
  const [detail, matches] = await Promise.all([
    api.getTrial(id),
    api.getMatches({ trial_id: id }),
  ]);

  if (!detail) notFound();

  const { trial, criteria, sites } = detail;
  const fill = enrollmentFill(trial.enrollment_count, trial.target_enrollment);

  return (
    <div className="space-y-8">
      <div>
        <Link href="/trials" className="text-sm text-teal-700 hover:underline">
          ← Trials
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <p className="text-sm font-medium text-teal-700">
            {trial.trial_id} · {trial.phase}
          </p>
          <StatusBadge
            label={trial.status}
            className="border-slate-200 bg-slate-100 text-slate-700 capitalize"
          />
        </div>
        <h2 className="mt-2 text-2xl font-semibold text-slate-900">
          {trial.title}
        </h2>
        <p className="mt-2 text-slate-600">
          {trial.therapeutic_area} · {trial.sponsor}
        </p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Enrollment
        </h3>
        <dl className="mt-4 grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-slate-500">Enrolled</dt>
            <dd className="text-sm font-medium text-slate-900">
              {trial.enrollment_count} / {trial.target_enrollment}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Fill rate</dt>
            <dd className="text-sm font-medium text-slate-900">
              {formatPercent(fill)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Sites</dt>
            <dd className="text-sm font-medium text-slate-900">
              {sites.length > 0 ? sites.length : "—"}
            </dd>
          </div>
        </dl>
      </section>

      {criteria.length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Eligibility criteria ({criteria.length})
          </h3>
          <ul className="space-y-2">
            {criteria.map((c) => (
              <li
                key={c.criterion_id}
                className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3 text-sm"
              >
                <span
                  className={`mr-2 rounded px-1.5 py-0.5 text-xs uppercase ${
                    c.rule_type === "inclusion"
                      ? "bg-teal-100 text-teal-800"
                      : "bg-rose-100 text-rose-800"
                  }`}
                >
                  {c.rule_type}
                </span>
                {c.criterion_text}
                {c.hard_gate && (
                  <span className="ml-2 text-xs text-slate-500">hard gate</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {sites.length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Sites
          </h3>
          <ul className="grid gap-2 sm:grid-cols-2">
            {sites.map((site) => (
              <li
                key={site.site_id}
                className="rounded-lg border border-slate-100 px-4 py-3 text-sm"
              >
                <p className="font-medium text-slate-800">{site.site_name}</p>
                <p className="text-slate-500">
                  {site.city}, {site.country}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h3 className="mb-4 text-lg font-semibold text-slate-900">
          Patient matches ({matches.length})
        </h3>
        <MatchTable matches={matches} showPatient showTrial={false} />
      </section>
    </div>
  );
}
