"use client";

import { useState } from "react";
import Link from "next/link";
import type { PatientTrialEligibilityData } from "@/lib/eligibility";
import { FactMatchBar } from "@/components/patients/FactMatchBar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { matchPath } from "@/lib/types";
import { scoreColor, tierColor, tierLabel } from "@/lib/utils";

interface PatientTrialEligibilityProps {
  trials: PatientTrialEligibilityData[];
}

export function PatientTrialEligibility({ trials }: PatientTrialEligibilityProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (trials.length === 0) {
    return (
      <section className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center">
        <p className="text-sm text-slate-600">
          No trial matches for this patient yet.
        </p>
      </section>
    );
  }

  const active = trials[activeIndex] ?? trials[0];
  const { match, facts, summary, highlights } = active;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            Trial eligibility
          </h3>
          <p className="text-sm text-slate-500">
            How each clinical fact maps to trial criteria
          </p>
        </div>
        <StatusBadge
          label={tierLabel[match.tier]}
          className={tierColor[match.tier]}
        />
      </div>

      {trials.length > 1 && (
        <div className="-mx-1 flex gap-2 overflow-x-auto pb-1">
          {trials.map((trial, index) => (
            <button
              key={`${trial.match.trial_id}-${index}`}
              type="button"
              onClick={() => setActiveIndex(index)}
              className={`shrink-0 rounded-lg border px-3 py-2 text-left text-sm transition ${
                index === activeIndex
                  ? "border-blue-300 bg-blue-50 text-blue-900"
                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
              }`}
            >
              <p className="font-medium">{trial.match.trial_id}</p>
              <p className="line-clamp-1 text-xs opacity-80">
                {trial.match.trial_title}
              </p>
            </button>
          ))}
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-600">
              {match.trial_id}
            </p>
            <p className="mt-1 font-semibold text-slate-900">
              {match.trial_title}
            </p>
          </div>
          <div className="text-right text-sm">
            <p className={`font-semibold ${scoreColor(match.score)}`}>
              Score {match.score}
            </p>
            <p className="text-xs text-slate-500">
              {match.soft_rules_met}/{match.soft_rules_total} soft rules
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
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

      <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-5">
        <h4 className="text-sm font-semibold text-slate-900">
          Why this patient was matched
        </h4>
        <p className="mt-2 text-sm leading-relaxed text-slate-700">
          {summary}
        </p>
        {highlights.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {highlights.map((item) => (
              <li
                key={item}
                className="flex gap-2 text-sm text-slate-600 before:content-['•']"
              >
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
        <Link
          href={matchPath(match.patient_id, match.trial_id)}
          className="mt-4 inline-flex text-sm font-medium text-blue-700 hover:underline"
        >
          View full audit trail →
        </Link>
      </div>
    </section>
  );
}
