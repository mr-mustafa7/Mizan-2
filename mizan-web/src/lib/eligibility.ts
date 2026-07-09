import type {
  AuditRecord,
  CriterionResult,
  Patient,
  PatientFact,
  PatientTrialMatch,
  Trial,
} from "@/lib/types";

export interface FactCriterionLink {
  criterion_id: string;
  criterion_text: string;
  result: CriterionResult;
  reason: string;
  rule_type: AuditRecord["rule_type"];
  hard_gate: boolean;
}

export interface FactEligibilityItem {
  id: string;
  field_name: string;
  label: string;
  value: string;
  source?: string;
  confidence?: string;
  criteria: FactCriterionLink[];
  overallResult: CriterionResult;
  matchScore: number;
}

export interface PatientTrialEligibilityData {
  match: PatientTrialMatch;
  facts: FactEligibilityItem[];
  summary: string;
  highlights: string[];
}

export interface UnmatchedPatientData {
  facts: FactEligibilityItem[];
  summary: string;
  highlights: string[];
  trialsScreened: number;
}

const fieldLabels: Record<string, string> = {
  diagnosis: "Diagnosis",
  ecog: "ECOG status",
  cancer_stage: "Cancer stage",
  biomarker_egfr: "EGFR biomarker",
  prior_treatments: "Prior treatments",
  lab_hemoglobin: "Hemoglobin",
  age: "Age",
  sex: "Sex",
};

function factDisplayValue(fact: PatientFact): string {
  if (fact.num_value !== "" && fact.num_value !== null) {
    const unit = fact.unit || fact.str_value;
    return unit ? `${fact.num_value} ${unit}`.trim() : String(fact.num_value);
  }
  return fact.str_value || "—";
}

function worstResult(results: CriterionResult[]): CriterionResult {
  if (results.includes("NOT_MET")) return "NOT_MET";
  if (results.includes("UNKNOWN")) return "UNKNOWN";
  if (results.every((r) => r === "NOT_APPLICABLE")) return "NOT_APPLICABLE";
  return "MET";
}

export function resultToMatchScore(result: CriterionResult): number {
  switch (result) {
    case "MET":
      return 100;
    case "NOT_MET":
      return 0;
    case "UNKNOWN":
      return 45;
    case "NOT_APPLICABLE":
      return 0;
  }
}

export function buildFactEligibility(
  patient: Patient,
  facts: PatientFact[],
  auditRecords: AuditRecord[]
): FactEligibilityItem[] {
  const byField = new Map<string, FactCriterionLink[]>();

  for (const record of auditRecords) {
    const list = byField.get(record.field_checked) ?? [];
    list.push({
      criterion_id: record.criterion_id,
      criterion_text: record.criterion_text,
      result: record.result,
      reason: record.reason,
      rule_type: record.rule_type,
      hard_gate: record.hard_gate,
    });
    byField.set(record.field_checked, list);
  }

  const items: FactEligibilityItem[] = [];
  const seenFields = new Set<string>();

  if (byField.has("age")) {
    const criteria = byField.get("age")!;
    const overall = worstResult(criteria.map((c) => c.result));
    items.push({
      id: "demographic-age",
      field_name: "age",
      label: fieldLabels.age,
      value: `${patient.age} years`,
      source: "demographics",
      confidence: "high",
      criteria,
      overallResult: overall,
      matchScore: resultToMatchScore(overall),
    });
    seenFields.add("age");
  }

  for (const fact of facts) {
    seenFields.add(fact.field_name);
    const criteria = byField.get(fact.field_name) ?? [];
    const overall =
      criteria.length > 0
        ? worstResult(criteria.map((c) => c.result))
        : "UNKNOWN";

    items.push({
      id: fact.fact_id,
      field_name: fact.field_name,
      label: fieldLabels[fact.field_name] ?? fact.field_name,
      value: factDisplayValue(fact),
      source: fact.source,
      confidence: fact.confidence,
      criteria,
      overallResult: overall,
      matchScore:
        criteria.length > 0 ? resultToMatchScore(overall) : 0,
    });
  }

  for (const [field, criteria] of byField) {
    if (seenFields.has(field)) continue;
    const overall = worstResult(criteria.map((c) => c.result));
    items.push({
      id: `audit-${field}`,
      field_name: field,
      label: fieldLabels[field] ?? field,
      value: criteria[0]?.reason.split("'")[1] ?? "See audit",
      criteria,
      overallResult: overall,
      matchScore: resultToMatchScore(overall),
    });
  }

  return items;
}

export function buildMatchSummary(
  match: PatientTrialMatch,
  auditRecords: AuditRecord[],
  patient: Patient
): { summary: string; highlights: string[] } {
  const met = auditRecords.filter((r) => r.result === "MET");
  const failed = auditRecords.filter((r) => r.result === "NOT_MET");
  const unknown = auditRecords.filter((r) => r.result === "UNKNOWN");
  const hardGates = auditRecords.filter((r) => r.hard_gate);
  const hardMet = hardGates.filter((r) => r.result === "MET").length;

  const highlights: string[] = [];

  if (match.tier === "ELIGIBLE") {
    highlights.push(
      `All ${hardGates.length} hard gates passed`,
      `${match.soft_rules_met}/${match.soft_rules_total} soft rules met`
    );
    if (match.location_bonus > 0) {
      highlights.push(
        `+${match.location_bonus} location bonus (${patient.city})`
      );
    }
    const keyFacts = met
      .filter((r) => r.rule_type === "inclusion")
      .slice(0, 3)
      .map((r) => r.criterion_text);
    if (keyFacts.length) {
      highlights.push(...keyFacts);
    }
  } else if (match.tier === "NEEDS_SCREENING") {
    highlights.push(
      `${unknown.length} criterion(s) need coordinator screening`,
      `${match.soft_rules_unknown} soft rule(s) still unknown`
    );
  } else if (match.tier === "NOT_ELIGIBLE") {
    const failure = failed[0];
    if (failure) {
      highlights.push(`Failed: ${failure.criterion_text}`, failure.reason);
    }
    highlights.push(`${match.hard_failures} hard gate failure(s)`);
  }

  let summary = "";

  switch (match.tier) {
    case "ELIGIBLE":
      summary = `${patient.patient_id} is eligible for ${match.trial_title} (${match.trial_id}). All ${hardMet} hard gates are met and ${match.soft_rules_met} of ${match.soft_rules_total} soft rules passed, yielding a composite score of ${match.score}.`;
      break;
    case "NEEDS_SCREENING":
      summary = `${patient.patient_id} may qualify for ${match.trial_title}, but ${unknown.length || match.soft_rules_unknown} screening item(s) remain before enrollment. Hard gates are clear; confirm missing data before recommending.`;
      break;
    case "NOT_ELIGIBLE":
      summary = `${patient.patient_id} is not eligible for ${match.trial_title}. ${failed.length ? failed[0].reason : "One or more hard gates failed."} Match score is ${match.score}.`;
      break;
    case "REVIEW":
      summary = `${patient.patient_id} is borderline for ${match.trial_title} and needs coordinator review before a recommendation.`;
      break;
  }

  return { summary, highlights };
}

export function buildPatientTrialEligibility(
  patient: Patient,
  facts: PatientFact[],
  match: PatientTrialMatch,
  auditRecords: AuditRecord[]
): PatientTrialEligibilityData {
  const factItems = buildFactEligibility(patient, facts, auditRecords);
  const { summary, highlights } = buildMatchSummary(
    match,
    auditRecords,
    patient
  );

  return { match, facts: factItems, summary, highlights };
}

function factDisplay(fact: PatientFact): string {
  return factDisplayValue(fact);
}

function blockingCriterion(
  trial: Trial,
  criterionText: string,
  reason: string
): FactCriterionLink {
  return {
    criterion_id: `${trial.trial_id}-block`,
    criterion_text: `${trial.trial_id}: ${criterionText}`,
    result: "NOT_MET",
    reason,
    rule_type: "inclusion",
    hard_gate: true,
  };
}

export function buildUnmatchedPatientData(
  patient: Patient,
  facts: PatientFact[],
  trials: Trial[]
): UnmatchedPatientData {
  const recruiting = trials.filter((t) => t.status === "recruiting");
  const diagnosis =
    facts.find((f) => f.field_name === "diagnosis")?.str_value?.toLowerCase() ??
    "";
  const ecogFact = facts.find((f) => f.field_name === "ecog");
  const ecog =
    ecogFact?.num_value !== "" && ecogFact?.num_value != null
      ? Number(ecogFact.num_value)
      : null;
  const egfrFact = facts.find((f) => f.field_name === "biomarker_egfr");
  const hemoglobinFact = facts.find((f) => f.field_name === "lab_hemoglobin");

  const factItems: FactEligibilityItem[] = [];

  const ageBlocks: FactCriterionLink[] = [];
  if (patient.age > 75) {
    for (const trial of recruiting.filter(
      (t) => t.therapeutic_area === "lung cancer"
    )) {
      ageBlocks.push(
        blockingCriterion(
          trial,
          "Age 75 or younger",
          `Age ${patient.age} exceeds the maximum age for ${trial.title}`
        )
      );
    }
  }

  factItems.push({
    id: "demographic-age",
    field_name: "age",
    label: fieldLabels.age,
    value: `${patient.age} years`,
    source: "demographics",
    confidence: "high",
    criteria: ageBlocks,
    overallResult: ageBlocks.length ? "NOT_MET" : "UNKNOWN",
    matchScore: ageBlocks.length ? 0 : 45,
  });

  factItems.push({
    id: "demographic-sex",
    field_name: "sex",
    label: "Sex",
    value: patient.sex,
    source: "demographics",
    confidence: "high",
    criteria: [],
    overallResult: "UNKNOWN",
    matchScore: 0,
  });

  factItems.push({
    id: "demographic-location",
    field_name: "location",
    label: "Location",
    value: `${patient.city}, ${patient.country}`,
    source: "demographics",
    confidence: "high",
    criteria: [],
    overallResult: "UNKNOWN",
    matchScore: 0,
  });

  for (const fact of facts) {
    const blocks: FactCriterionLink[] = [];

    if (fact.field_name === "diagnosis") {
      for (const trial of recruiting) {
        const area = trial.therapeutic_area.toLowerCase();
        const matchesArea =
          (area.includes("lung") && diagnosis.includes("nsclc")) ||
          (area.includes("lung") && diagnosis.includes("lung")) ||
          (area.includes("breast") && diagnosis.includes("breast"));

        if (!matchesArea) {
          blocks.push(
            blockingCriterion(
              trial,
              `Indication: ${trial.therapeutic_area}`,
              `Diagnosis '${fact.str_value}' does not match ${trial.therapeutic_area} trials`
            )
          );
        }
      }
    }

    if (fact.field_name === "ecog" && ecog !== null && ecog > 2) {
      for (const trial of recruiting.filter(
        (t) => t.therapeutic_area === "lung cancer"
      )) {
        blocks.push(
          blockingCriterion(
            trial,
            "ECOG performance status 0-2",
            `ECOG ${ecog} exceeds the performance status limit for ${trial.title}`
          )
        );
      }
    }

    if (fact.field_name === "biomarker_egfr" && egfrFact?.negated) {
      for (const trial of recruiting.filter((t) =>
        t.title.toLowerCase().includes("egfr")
      )) {
        blocks.push(
          blockingCriterion(
            trial,
            "Documented EGFR activating mutation required",
            "No EGFR mutation detected — required for EGFR-targeted trials"
          )
        );
      }
    }

    if (fact.field_name === "lab_hemoglobin" && hemoglobinFact) {
      const hb = Number(hemoglobinFact.num_value);
      if (hb < 10) {
        for (const trial of recruiting) {
          blocks.push(
            blockingCriterion(
              trial,
              "Hemoglobin at least 10 g/dL",
              `Hemoglobin ${hb} g/dL is below the protocol minimum for ${trial.title}`
            )
          );
        }
      }
    }

    const overall: CriterionResult =
      blocks.length > 0 ? "NOT_MET" : "UNKNOWN";

    factItems.push({
      id: fact.fact_id,
      field_name: fact.field_name,
      label: fieldLabels[fact.field_name] ?? fact.field_name,
      value: factDisplay(fact),
      source: fact.source,
      confidence: fact.confidence,
      criteria: blocks,
      overallResult: overall,
      matchScore: blocks.length > 0 ? 0 : 45,
    });
  }

  const blockingFacts = factItems.filter((f) => f.overallResult === "NOT_MET");
  const primaryBlock =
    blockingFacts.find((f) => f.field_name === "diagnosis") ??
    blockingFacts[0];

  const highlights: string[] = [];
  if (primaryBlock?.criteria[0]) {
    highlights.push(primaryBlock.criteria[0].reason);
  }
  for (const fact of blockingFacts.slice(0, 3)) {
    for (const c of fact.criteria.slice(0, 1)) {
      if (!highlights.includes(c.reason)) highlights.push(c.reason);
    }
  }
  highlights.push(
    `Screened against ${recruiting.length} recruiting trials — no eligible tier assigned`
  );

  let summary = `${patient.patient_id} was not matched to any active trial. `;
  if (primaryBlock) {
    summary += `The primary barrier is ${primaryBlock.label.toLowerCase()}: ${primaryBlock.value}. `;
  }
  if (patient.age > 75) {
    summary += `Age ${patient.age} exceeds limits on several oncology protocols. `;
  }
  summary += `After screening across ${recruiting.length} recruiting studies, no patient–trial pair met the minimum eligibility tier.`;

  return {
    facts: factItems,
    summary,
    highlights,
    trialsScreened: recruiting.length,
  };
}
