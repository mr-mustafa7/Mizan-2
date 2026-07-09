import { StatusBadge } from "@/components/ui/StatusBadge";
import type { AuditRecord } from "@/lib/types";
import { resultColor, resultLabel } from "@/lib/utils";

interface AuditCriteriaListProps {
  records: AuditRecord[];
}

function RecordGroup({
  title,
  items,
}: {
  title: string;
  items: AuditRecord[];
}) {
  if (items.length === 0) return null;

  return (
    <section>
      <h3 className="mb-3 text-sm font-semibold text-slate-800">{title}</h3>
      <ul className="space-y-3">
        {items.map((record) => (
          <li
            key={record.criterion_id}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs uppercase tracking-wide ${
                      record.rule_type === "inclusion"
                        ? "bg-teal-100 text-teal-800"
                        : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {record.rule_type}
                  </span>
                  <span className="text-xs text-slate-500">
                    {record.field_checked}
                    {record.hard_gate ? " · hard gate" : " · soft rule"}
                  </span>
                </div>
                <p className="mt-2 text-sm font-medium text-slate-900">
                  {record.criterion_text}
                </p>
                <p className="mt-2 text-sm text-slate-700">
                  <span className="font-medium">Reason: </span>
                  {record.reason}
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  <span className="font-medium text-slate-600">Patient data: </span>
                  {record.patient_info}
                </p>
              </div>
              <StatusBadge
                label={resultLabel[record.result]}
                className={resultColor[record.result]}
              />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function AuditCriteriaList({ records }: AuditCriteriaListProps) {
  const hardGates = records
    .filter((r) => r.hard_gate)
    .sort((a, b) => {
      if (a.rule_type !== b.rule_type) {
        return a.rule_type === "inclusion" ? -1 : 1;
      }
      return a.criterion_id.localeCompare(b.criterion_id);
    });

  const softRules = records
    .filter((r) => !r.hard_gate)
    .sort((a, b) => {
      if (a.rule_type !== b.rule_type) {
        return a.rule_type === "inclusion" ? -1 : 1;
      }
      return a.criterion_id.localeCompare(b.criterion_id);
    });

  if (records.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-8 text-center text-sm text-slate-500">
        No audit records for this patient–trial pair.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <RecordGroup title="Hard gates" items={hardGates} />
      <RecordGroup title="Soft rules" items={softRules} />
    </div>
  );
}
