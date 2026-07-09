import type { CriterionResult } from "@/lib/types";
import type { FactCriterionLink } from "@/lib/eligibility";
import { resultLabel } from "@/lib/utils";
import { cn } from "@/lib/cn";

const barFill: Record<CriterionResult, string> = {
  MET: "bg-emerald-500",
  NOT_MET: "bg-rose-500",
  UNKNOWN: "bg-amber-400",
  NOT_APPLICABLE: "bg-slate-400",
};

interface FactMatchBarProps {
  label: string;
  fieldName: string;
  value: string;
  source?: string;
  confidence?: string;
  matchScore: number;
  overallResult: CriterionResult;
  criteria?: FactCriterionLink[];
}

function fieldInitial(fieldName: string): string {
  return fieldName.slice(0, 2).toUpperCase();
}

export function FactMatchBar({
  label,
  fieldName,
  value,
  source,
  confidence,
  matchScore,
  overallResult,
  criteria = [],
}: FactMatchBarProps) {
  const hasCriterion = criteria.length > 0;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex gap-3">
        <div
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white",
            overallResult === "MET"
              ? "bg-emerald-500"
              : overallResult === "NOT_MET"
                ? "bg-rose-500"
                : overallResult === "UNKNOWN"
                  ? "bg-amber-500"
                  : "bg-slate-400"
          )}
          aria-hidden
        >
          {fieldInitial(fieldName)}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-slate-900">{label}</p>
              <p className="text-sm text-slate-600">{value}</p>
              {(source || confidence) && (
                <p className="mt-0.5 text-xs text-slate-400">
                  {source}
                  {confidence ? ` · ${confidence} confidence` : ""}
                </p>
              )}
            </div>
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-medium",
                overallResult === "MET"
                  ? "bg-emerald-100 text-emerald-800"
                  : overallResult === "NOT_MET"
                    ? "bg-rose-100 text-rose-800"
                    : overallResult === "UNKNOWN"
                      ? "bg-amber-100 text-amber-800"
                      : "bg-slate-100 text-slate-600"
              )}
            >
              {hasCriterion ? resultLabel[overallResult] : "Not checked"}
            </span>
          </div>

          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Trial match</span>
              <span>{hasCriterion ? `${matchScore}%` : "—"}</span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  hasCriterion ? barFill[overallResult] : "bg-slate-200"
                )}
                style={{ width: `${hasCriterion ? matchScore : 0}%` }}
              />
            </div>
          </div>

          {criteria.length > 0 && (
            <div className="mt-3 space-y-2">
              {criteria.map((criterion) => (
                <div
                  key={criterion.criterion_id}
                  className="rounded-lg bg-slate-50 px-3 py-2 text-sm"
                >
                  <p className="font-medium text-slate-800">
                    {criterion.rule_type === "exclusion" ? "Exclusion: " : ""}
                    {criterion.criterion_text}
                    {criterion.hard_gate && (
                      <span className="ml-1 text-xs font-normal text-slate-500">
                        (hard gate)
                      </span>
                    )}
                  </p>
                  <p className="mt-1 text-slate-600">{criterion.reason}</p>
                </div>
              ))}
            </div>
          )}

          {!hasCriterion && (
            <p className="mt-2 text-xs text-slate-500">
              No eligibility criterion evaluated this fact for the selected
              trial.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
