import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { CoordinatorDashboardRow } from "@/lib/types";
import { formatPercent } from "@/lib/utils";

interface CoordinatorDashboardTableProps {
  rows: CoordinatorDashboardRow[];
}

export function CoordinatorDashboardTable({
  rows,
}: CoordinatorDashboardTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-[520px] w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-slate-600">
              Trial
            </th>
            <th className="px-4 py-3 text-left font-medium text-slate-600">
              Enrollment
            </th>
            <th className="px-4 py-3 text-left font-medium text-slate-600">
              Eligible
            </th>
            <th className="px-4 py-3 text-left font-medium text-slate-600">
              Needs screening
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={row.trial_id} className="hover:bg-slate-50">
              <td className="px-4 py-3">
                <Link
                  href={`/trials/${row.trial_id}`}
                  className="font-medium text-teal-700 hover:underline"
                >
                  {row.title}
                </Link>
                <p className="text-xs text-slate-500">
                  {row.trial_id} · {row.phase} · {row.sponsor}
                </p>
              </td>
              <td className="px-4 py-3">
                <p className="font-medium text-slate-800">
                  {row.enrollment_count}/{row.target_enrollment}
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-teal-500"
                      style={{ width: `${Math.min(row.fill_pct, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-500">
                    {formatPercent(row.fill_pct)}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-rose-600">
                  {row.shortfall} short
                </p>
              </td>
              <td className="px-4 py-3">
                <StatusBadge
                  label={String(row.eligible_count)}
                  className="border-emerald-200 bg-emerald-100 text-emerald-800"
                />
              </td>
              <td className="px-4 py-3">
                <StatusBadge
                  label={String(row.needs_screening_count)}
                  className="border-amber-200 bg-amber-100 text-amber-800"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
