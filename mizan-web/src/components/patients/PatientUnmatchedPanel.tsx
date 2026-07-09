import type { UnmatchedPatientData } from "@/lib/eligibility";
import { FactMatchBar } from "@/components/patients/FactMatchBar";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface PatientUnmatchedPanelProps {
  data: UnmatchedPatientData;
}

export function PatientUnmatchedPanel({ data }: PatientUnmatchedPanelProps) {
  const { facts, summary, highlights, trialsScreened } = data;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            No trial matches
          </h3>
          <p className="text-sm text-slate-500">
            Profile screened against {trialsScreened} recruiting trials
          </p>
        </div>
        <StatusBadge
          label="Unmatched"
          className="border-rose-200 bg-rose-100 text-rose-800"
        />
      </div>

      <div className="space-y-3">
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Patient profile
        </h4>
        {facts.map((fact) => (
          <FactMatchBar
            key={fact.id}
            label={fact.label}
            fieldName={fact.field_name}
            value={fact.value}
            source={fact.source}
            confidence={fact.confidence}
            matchScore={fact.matchScore}
            overallResult={fact.overallResult}
            criteria={fact.criteria}
          />
        ))}
      </div>

      <div className="rounded-xl border border-rose-200 bg-rose-50/70 p-5">
        <h4 className="text-sm font-semibold text-slate-900">
          Why this patient was not matched
        </h4>
        <p className="mt-2 text-sm leading-relaxed text-slate-700">
          {summary}
        </p>
        {highlights.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {highlights.map((item) => (
              <li
                key={item}
                className="flex gap-2 text-sm text-slate-600 before:shrink-0 before:content-['•']"
              >
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
