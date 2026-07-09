"use client";

import { useState } from "react";
import type {
  AtRiskTrial,
  AuditRecord,
  CoordinatorDashboardRow,
  DiagnosisSummaryRow,
  PatientTrialMatch,
  TrialSummaryRow,
} from "@/lib/types";
import { tierColor, tierLabel } from "@/lib/utils";
import { DataTable, type DataTableColumn } from "@/components/control/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";

export type ControlTab =
  | "at-risk"
  | "eligibility"
  | "audit"
  | "summaries";

const tabs: { id: ControlTab; label: string; icon: string }[] = [
  { id: "at-risk", label: "At-Risk Trials", icon: "⚠" },
  { id: "eligibility", label: "Patient Eligibility", icon: "👥" },
  { id: "audit", label: "Audit Trail", icon: "📋" },
  { id: "summaries", label: "Summaries", icon: "📊" },
];

interface ControlPanelProps {
  atRiskTrials: AtRiskTrial[];
  coordinatorDashboard: CoordinatorDashboardRow[];
  matches: PatientTrialMatch[];
  auditRecords: AuditRecord[];
  trialSummary: TrialSummaryRow[];
  diagnosisSummary: DiagnosisSummaryRow[];
  kpis: {
    totalShortfall: number;
    eligiblePatients: number;
    reviewPatients: number;
    topAtRiskTrialId: string;
  };
}

const atRiskColumns: DataTableColumn<AtRiskTrial>[] = [
  {
    key: "trial_id",
    header: "Trial_id",
    render: (r) => <span className="font-mono text-blue-300">{r.trial_id}</span>,
    searchValue: (r) => r.trial_id,
  },
  {
    key: "title",
    header: "Title",
    render: (r) => <span className="max-w-xs truncate">{r.title}</span>,
    searchValue: (r) => r.title,
  },
  {
    key: "therapeutic_area",
    header: "Therapeutic_area",
    render: (r) => r.therapeutic_area,
    searchValue: (r) => r.therapeutic_area,
  },
  { key: "phase", header: "Phase", render: (r) => r.phase },
  { key: "sponsor", header: "Sponsor", render: (r) => r.sponsor },
  {
    key: "enrollment_count",
    header: "Enrollment_count",
    render: (r) => r.enrollment_count,
  },
  {
    key: "target_enrollment",
    header: "Target_enrollment",
    render: (r) => r.target_enrollment,
  },
  {
    key: "shortfall",
    header: "Shortfall",
    render: (r) => (
      <span className="font-semibold text-red-400">{r.shortfall}</span>
    ),
  },
];

const eligibilityColumns: DataTableColumn<PatientTrialMatch>[] = [
  {
    key: "patient_id",
    header: "Patient_id",
    render: (r) => <span className="font-mono">{r.patient_id}</span>,
    searchValue: (r) => r.patient_id,
  },
  {
    key: "trial_id",
    header: "Trial_id",
    render: (r) => <span className="font-mono text-blue-300">{r.trial_id}</span>,
    searchValue: (r) => r.trial_id,
  },
  {
    key: "trial_title",
    header: "Trial_title",
    render: (r) => <span className="max-w-xs truncate">{r.trial_title}</span>,
    searchValue: (r) => r.trial_title,
  },
  {
    key: "tier",
    header: "Tier",
    render: (r) => (
      <StatusBadge label={tierLabel[r.tier]} className={tierColor[r.tier]} />
    ),
    searchValue: (r) => r.tier,
  },
  {
    key: "score",
    header: "Score",
    render: (r) => <span className="font-semibold">{r.score}</span>,
  },
  {
    key: "hard_failures",
    header: "Hard_failures",
    render: (r) => r.hard_failures,
  },
  {
    key: "hard_unknowns",
    header: "Hard_unknowns",
    render: (r) => r.hard_unknowns,
  },
];

const auditColumns: DataTableColumn<AuditRecord>[] = [
  {
    key: "patient_id",
    header: "Patient_id",
    render: (r) => <span className="font-mono">{r.patient_id}</span>,
    searchValue: (r) => r.patient_id,
  },
  {
    key: "trial_id",
    header: "Trial_id",
    render: (r) => <span className="font-mono text-blue-300">{r.trial_id}</span>,
    searchValue: (r) => r.trial_id,
  },
  {
    key: "criterion_id",
    header: "Criterion_id",
    render: (r) => r.criterion_id,
    searchValue: (r) => r.criterion_id,
  },
  {
    key: "rule_type",
    header: "Rule_type",
    render: (r) => r.rule_type,
  },
  {
    key: "result",
    header: "Result",
    render: (r) => (
      <span
        className={
          r.result === "MET"
            ? "text-emerald-400"
            : r.result === "NOT_MET"
              ? "text-red-400"
              : "text-amber-400"
        }
      >
        {r.result}
      </span>
    ),
    searchValue: (r) => r.result,
  },
  {
    key: "reason",
    header: "Reason",
    render: (r) => <span className="max-w-md truncate">{r.reason}</span>,
    searchValue: (r) => r.reason,
  },
];

type SummaryRow = {
  id: string;
  category: string;
  label: string;
  eligible: number;
  needs_screening: number;
  review: number;
  not_eligible: number;
};

export function ControlPanel({
  atRiskTrials,
  coordinatorDashboard,
  matches,
  auditRecords,
  trialSummary,
  diagnosisSummary,
  kpis,
}: ControlPanelProps) {
  const [activeTab, setActiveTab] = useState<ControlTab>("at-risk");

  const summaryRows: SummaryRow[] = [
    ...trialSummary.map((r) => ({
      id: `trial-${r.trial_id}`,
      category: "Trial",
      label: `${r.trial_id} — ${r.trial_title}`,
      eligible: r.eligible_count,
      needs_screening: r.needs_screening_count,
      review: r.review_count,
      not_eligible: r.not_eligible_count,
    })),
    ...diagnosisSummary.map((r) => ({
      id: `dx-${r.diagnosis}`,
      category: "Diagnosis",
      label: r.diagnosis,
      eligible: r.eligible_patient_count,
      needs_screening: 0,
      review: 0,
      not_eligible: 0,
    })),
  ];

  const summaryColumns: DataTableColumn<SummaryRow>[] = [
    {
      key: "category",
      header: "Category",
      render: (r) => r.category,
      searchValue: (r) => r.category,
    },
    {
      key: "label",
      header: "Label",
      render: (r) => r.label,
      searchValue: (r) => r.label,
    },
    {
      key: "eligible",
      header: "Eligible",
      render: (r) => (
        <span className="text-emerald-400">{r.eligible}</span>
      ),
    },
    {
      key: "needs_screening",
      header: "Needs_screening",
      render: (r) => (
        <span className="text-amber-400">{r.needs_screening}</span>
      ),
    },
    {
      key: "review",
      header: "Review",
      render: (r) => <span className="text-sky-400">{r.review}</span>,
    },
    {
      key: "not_eligible",
      header: "Not_eligible",
      render: (r) => <span className="text-red-400">{r.not_eligible}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <KpiCard
          label="Total shortfall"
          value={String(kpis.totalShortfall)}
          hint="Patients still needed across at-risk trials"
        />
        <KpiCard
          label="Eligible patients"
          value={String(kpis.eligiblePatients)}
          hint="Ready to enroll from this cohort"
          accent="success"
        />
        <KpiCard
          label="Review patients"
          value={String(kpis.reviewPatients)}
          hint="Borderline — worth a closer look"
          accent="warning"
        />
        <KpiCard
          label="At-risk trials"
          value={kpis.topAtRiskTrialId}
          hint="Trials below 50% enrollment target"
          accent="danger"
          mono
        />
      </div>

      <nav className="-mx-1 flex gap-2 overflow-x-auto border-b border-[#1e2d4a] pb-1 scrollbar-none">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex shrink-0 items-center gap-1.5 rounded-t-lg px-3 py-2.5 text-xs font-medium transition sm:gap-2 sm:px-4 sm:text-sm ${
              activeTab === tab.id
                ? "border border-b-0 border-[#1e2d4a] bg-[#111a2e] text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span>{tab.icon}</span>
            <span className="whitespace-nowrap">{tab.label}</span>
          </button>
        ))}
      </nav>

      <div className="rounded-xl border border-[#1e2d4a] bg-[#0f1729] p-3 sm:p-4">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
          <div>
            <h2 className="text-base font-semibold text-white">
              {tabs.find((t) => t.id === activeTab)?.label} — full detail
            </h2>
            <p className="text-xs text-slate-500">
              Read-only pipeline view · no actions · for project observability
            </p>
          </div>
          <span className="rounded-full border border-[#243552] bg-[#0b1220] px-3 py-1 text-xs text-slate-400">
            {coordinatorDashboard.length} trials monitored
          </span>
        </div>

        {activeTab === "at-risk" && (
          <DataTable
            rows={atRiskTrials}
            columns={atRiskColumns}
            rowKey={(r) => r.trial_id}
            searchPlaceholder="Filter trials…"
          />
        )}
        {activeTab === "eligibility" && (
          <DataTable
            rows={matches}
            columns={eligibilityColumns}
            rowKey={(r) => `${r.patient_id}-${r.trial_id}`}
            searchPlaceholder="Filter patient–trial pairs…"
          />
        )}
        {activeTab === "audit" && (
          <DataTable
            rows={auditRecords}
            columns={auditColumns}
            rowKey={(r) => `${r.patient_id}-${r.trial_id}-${r.criterion_id}`}
            searchPlaceholder="Filter audit records…"
            emptyMessage="No audit records loaded for the current mock dataset."
          />
        )}
        {activeTab === "summaries" && (
          <DataTable
            rows={summaryRows}
            columns={summaryColumns}
            rowKey={(r) => r.id}
            searchPlaceholder="Filter summaries…"
          />
        )}
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  hint,
  accent,
  mono,
}: {
  label: string;
  value: string;
  hint: string;
  accent?: "success" | "warning" | "danger";
  mono?: boolean;
}) {
  const valueColor =
    accent === "success"
      ? "text-emerald-400"
      : accent === "warning"
        ? "text-amber-400"
        : accent === "danger"
          ? "text-red-400"
          : "text-white";

  return (
    <div className="rounded-xl border border-[#1e2d4a] bg-[#111a2e] p-4 sm:p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p
        className={`mt-2 text-3xl font-semibold tracking-tight ${valueColor} ${mono ? "font-mono text-2xl" : ""}`}
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  );
}
