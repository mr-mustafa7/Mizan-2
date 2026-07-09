import type { CriterionResult, MatchTier } from "@/lib/types";

export const tierLabel: Record<MatchTier, string> = {
  ELIGIBLE: "Eligible",
  NEEDS_SCREENING: "Needs screening",
  REVIEW: "Review",
  NOT_ELIGIBLE: "Not eligible",
};

export const tierColor: Record<MatchTier, string> = {
  ELIGIBLE: "bg-emerald-100 text-emerald-800 border-emerald-200",
  NEEDS_SCREENING: "bg-amber-100 text-amber-800 border-amber-200",
  REVIEW: "bg-sky-100 text-sky-800 border-sky-200",
  NOT_ELIGIBLE: "bg-rose-100 text-rose-800 border-rose-200",
};

export const resultLabel: Record<CriterionResult, string> = {
  MET: "Met",
  NOT_MET: "Not met",
  UNKNOWN: "Unknown",
  NOT_APPLICABLE: "N/A",
};

export const resultColor: Record<CriterionResult, string> = {
  MET: "bg-emerald-100 text-emerald-800 border-emerald-200",
  NOT_MET: "bg-rose-100 text-rose-800 border-rose-200",
  UNKNOWN: "bg-amber-100 text-amber-800 border-amber-200",
  NOT_APPLICABLE: "bg-slate-100 text-slate-600 border-slate-200",
};

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function enrollmentFill(
  enrollmentCount: number,
  targetEnrollment: number
): number {
  if (targetEnrollment === 0) return 0;
  return (enrollmentCount / targetEnrollment) * 100;
}

export function scoreColor(score: number): string {
  if (score >= 100) return "text-emerald-600";
  if (score >= 50) return "text-amber-600";
  if (score > 0) return "text-sky-600";
  return "text-rose-600";
}

export function patientLabel(patientId: string, age: number, sex: string): string {
  return `${patientId} · ${age}y ${sex}`;
}
