"""Decision narrative / match explanation for the coordinator UI.

Turns the deterministic `criterion_evaluation` + `pair_assessment` results into a
human-readable, step-by-step rationale for *why* a patient matched, needs
screening, is flagged for review, or was rejected for each trial.

This is decision support only — the coordinator reviews and approves. Every
statement is derived from an evaluated criterion (rule text + patient value +
result + reason), so the reasoning can be independently verified (FDA CDS
Criterion 4, EU AI Act Art. 13/14, ICH GCP audit trail).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from mizan.evaluator import CriterionResult, evaluate_criterion
from mizan.loader import EligibilityCriterion, MizanData, Patient
from mizan.matcher import (
    MatchTier,
    _city_match,
    _country_match,
    _criteria_for_trial,
    _patient_lookup,
    _soft_pct,
    _trial_lookup,
    match_patient_trial,
)

# Match-bar colour per criterion result (frontend FactMatchBar).
BAR_COLOR = {
    CriterionResult.MET: "green",
    CriterionResult.UNKNOWN: "amber",
    CriterionResult.NOT_MET: "red",
}


@dataclass(frozen=True)
class FactExplanation:
    field_checked: str
    patient_value: str
    result: str
    bar: str  # green | amber | red
    hard_gate: bool
    polarity: str  # inclusion | exclusion
    criterion_id: str
    criterion_text: str
    reason: str


@dataclass(frozen=True)
class NarrativeStep:
    step: int
    title: str
    detail: str


@dataclass
class MatchExplanation:
    patient_id: str
    trial_id: str
    trial_title: str
    tier: str
    score: float
    soft_rules_met: int
    soft_rules_total: int
    location_bonus: float
    summary: str
    highlights: list[str] = field(default_factory=list)
    decisive_factors: list[str] = field(default_factory=list)
    facts: list[FactExplanation] = field(default_factory=list)
    steps: list[NarrativeStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _patient_value(data: MizanData, patient: Patient, criterion: EligibilityCriterion) -> str:
    """Best-effort display value for the field this criterion checks."""
    field_name = criterion.field_checked.lower()
    if field_name == "age":
        return str(patient.age)
    if field_name == "sex":
        return patient.sex
    values: list[str] = []
    for fact in data.patient_facts:
        if fact.patient_id != patient.patient_id or fact.field_name != criterion.field_checked:
            continue
        if fact.negated:
            values.append(f"{fact.str_value or fact.field_name} (negated)")
        elif fact.str_value:
            values.append(fact.str_value)
        elif fact.num_value is not None:
            values.append(_fmt_num(fact.num_value))
    if not values:
        return "not on record"
    return "; ".join(values)


def _fmt_num(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _location_phrase(data: MizanData, patient: Patient, trial_id: str) -> str | None:
    if _city_match(data, patient, trial_id):
        return f"+25 location bonus (same city as a trial site: {patient.city})"
    if _country_match(data, patient, trial_id):
        return f"+15 location bonus (same country as a trial site: {patient.country})"
    return None


def build_match_explanation(
    data: MizanData, patient_id: str, trial_id: str
) -> MatchExplanation | None:
    """Build the full 'why this patient matched' explanation for one pair."""
    trial = _trial_lookup(data, trial_id)
    patient = _patient_lookup(data, patient_id)
    if trial is None or patient is None:
        return None

    # Single source of truth for tier / score / counts (identical to pair_assessment).
    match = match_patient_trial(data, patient_id, trial_id)
    if match is None:
        return None

    outcomes: list[tuple[EligibilityCriterion, "object"]] = []
    for criterion in _criteria_for_trial(data, trial_id):
        outcome = evaluate_criterion(data, patient_id, criterion)
        if outcome is not None:
            outcomes.append((criterion, outcome))
    if not outcomes:
        return None

    hard = [(c, o) for c, o in outcomes if c.hard_gate]
    soft = [(c, o) for c, o in outcomes if not c.hard_gate]
    hard_fail = [(c, o) for c, o in hard if o.result == CriterionResult.NOT_MET]
    hard_unknown = [(c, o) for c, o in hard if o.result == CriterionResult.UNKNOWN]
    hard_passed = [(c, o) for c, o in hard if o.result == CriterionResult.MET]

    tier = match.tier
    soft_met = match.soft_rules_met
    soft_total = match.soft_rules_total
    loc_bonus = int(match.location_bonus)
    score = match.score
    pct = _soft_pct(soft_met, soft_total)

    facts = [
        FactExplanation(
            field_checked=c.field_checked,
            patient_value=_patient_value(data, patient, c),
            result=o.result.value,
            bar=BAR_COLOR[o.result],
            hard_gate=c.hard_gate,
            polarity=c.rule_type,
            criterion_id=c.criterion_id,
            criterion_text=o.source_text,
            reason=o.reason,
        )
        for c, o in outcomes
    ]

    summary = _summary(patient_id, trial.title, tier, hard, hard_fail, hard_unknown, soft_met, soft_total, loc_bonus)
    highlights = _highlights(hard_passed, hard_fail, hard_unknown, soft_met, soft_total, data, patient, trial_id)
    decisive = _decisive_factors(tier, hard_fail, hard_unknown)
    steps = _steps(data, patient, trial_id, tier, hard, hard_fail, hard_unknown, hard_passed, soft, soft_met, soft_total, pct, loc_bonus, score)

    return MatchExplanation(
        patient_id=patient_id,
        trial_id=trial_id,
        trial_title=trial.title,
        tier=tier.value,
        score=score,
        soft_rules_met=soft_met,
        soft_rules_total=soft_total,
        location_bonus=float(loc_bonus),
        summary=summary,
        highlights=highlights,
        decisive_factors=decisive,
        facts=facts,
        steps=steps,
    )


def _summary(pid, title, tier, hard, hard_fail, hard_unknown, soft_met, soft_total, loc_bonus) -> str:
    n_hard = len(hard)
    bonus = f", with a +{loc_bonus} location bonus" if loc_bonus else ""
    if tier == MatchTier.ELIGIBLE:
        return (
            f"{pid} is ELIGIBLE for {title}: all {n_hard} mandatory criteria passed and "
            f"{soft_met} of {soft_total} preference criteria met{bonus}."
        )
    if tier == MatchTier.NEEDS_SCREENING:
        fields = ", ".join(sorted({c.field_checked for c, _ in hard_unknown}))
        return (
            f"{pid} NEEDS SCREENING for {title}: no mandatory criteria failed, but "
            f"{len(hard_unknown)} could not be confirmed due to missing data ({fields}). "
            f"Collect this data to finalize eligibility."
        )
    if tier == MatchTier.REVIEW:
        return (
            f"{pid} is flagged for REVIEW for {title}: all {n_hard} mandatory criteria passed, "
            f"but only {soft_met} of {soft_total} preference criteria met (below 50%). "
            f"Coordinator judgment recommended."
        )
    fields = ", ".join(sorted({c.field_checked for c, _ in hard_fail}))
    return (
        f"{pid} is NOT ELIGIBLE for {title}: {len(hard_fail)} mandatory criteria failed ({fields})."
    )


def _highlights(hard_passed, hard_fail, hard_unknown, soft_met, soft_total, data, patient, trial_id) -> list[str]:
    out: list[str] = []
    if hard_passed:
        out.append(f"{len(hard_passed)} of {len(hard_passed) + len(hard_fail) + len(hard_unknown)} hard gates passed")
    for c, o in hard_fail:
        out.append(f"FAILED hard gate — {c.field_checked}: {o.reason}")
    for c, o in hard_unknown:
        out.append(f"MISSING data (hard gate) — {c.field_checked}: {o.reason}")
    if soft_total:
        out.append(f"{soft_met}/{soft_total} preference criteria met")
    phrase = _location_phrase(data, patient, trial_id)
    if phrase and not hard_fail:
        out.append(phrase)
    return out


def _decisive_factors(tier, hard_fail, hard_unknown) -> list[str]:
    if tier == MatchTier.NOT_ELIGIBLE:
        return [f"{c.field_checked}: {o.reason}" for c, o in hard_fail]
    if tier == MatchTier.NEEDS_SCREENING:
        return [f"{c.field_checked}: {o.reason}" for c, o in hard_unknown]
    return []


def _steps(data, patient, trial_id, tier, hard, hard_fail, hard_unknown, hard_passed, soft, soft_met, soft_total, pct, loc_bonus, score) -> list[NarrativeStep]:
    steps: list[NarrativeStep] = []

    # Step 1 — data quality
    has_diag = any(
        f.patient_id == patient.patient_id and f.field_name == "diagnosis" and not f.negated and f.str_value
        for f in data.patient_facts
    )
    has_ecog = any(
        f.patient_id == patient.patient_id and f.field_name == "ecog" and f.num_value is not None
        for f in data.patient_facts
    )
    dq = "scoreable (diagnosis and ECOG on record)" if (has_diag and has_ecog) else "missing mandatory data"
    steps.append(NarrativeStep(1, "Data quality gate", f"Patient {patient.patient_id} is {dq}."))

    # Step 2 — hard gates
    hg_detail = (
        f"{len(hard_passed)} passed, {len(hard_fail)} failed, {len(hard_unknown)} unknown "
        f"out of {len(hard)} mandatory criteria."
    )
    steps.append(NarrativeStep(2, "Mandatory (hard) gates", hg_detail))

    # Step 3 — decisive factor
    if hard_fail:
        detail = "; ".join(f"{c.field_checked} — {o.reason}" for c, o in hard_fail)
        steps.append(NarrativeStep(3, "Decisive factor", f"Rejected because: {detail}."))
    elif hard_unknown:
        detail = "; ".join(f"{c.field_checked} — {o.reason}" for c, o in hard_unknown)
        steps.append(NarrativeStep(3, "Decisive factor", f"Needs screening because: {detail}."))
    else:
        steps.append(NarrativeStep(3, "Decisive factor", "All mandatory gates satisfied."))

    # Step 4 — soft scoring
    if hard_fail:
        steps.append(NarrativeStep(4, "Preference scoring", "Skipped — score is 0 for hard-gate failures."))
    else:
        loc = f" + {loc_bonus} location bonus" if loc_bonus else ""
        steps.append(
            NarrativeStep(
                4,
                "Preference scoring",
                f"{soft_met}/{soft_total} soft criteria met = {pct}%{loc} → match score {score:g}.",
            )
        )

    # Step 5 — tier rule
    rule = {
        MatchTier.NOT_ELIGIBLE: "any hard gate NOT_MET → NOT_ELIGIBLE",
        MatchTier.NEEDS_SCREENING: "no hard fail, but a hard gate is UNKNOWN → NEEDS_SCREENING",
        MatchTier.ELIGIBLE: "all hard gates pass and ≥50% soft met → ELIGIBLE",
        MatchTier.REVIEW: "all hard gates pass but <50% soft met → REVIEW",
    }[tier]
    steps.append(NarrativeStep(5, "Tier assigned", f"{tier.value} ({rule})."))
    return steps


def build_all_explanations(
    data: MizanData, trial_ids: list[str] | None = None
) -> list[MatchExplanation]:
    """Explanations for every patient × active trial pair with evaluated criteria."""
    active = trial_ids or [t.trial_id for t in data.trials if t.status == "recruiting"]
    out: list[MatchExplanation] = []
    for patient in data.patients:
        for trial_id in active:
            exp = build_match_explanation(data, patient.patient_id, trial_id)
            if exp is not None:
                out.append(exp)
    out.sort(key=lambda e: (e.patient_id, -e.score, e.trial_id))
    return out


def render_text(exp: MatchExplanation) -> str:
    """Plain-text rendering for the CLI demo."""
    lines = [
        f"{exp.patient_id} × {exp.trial_id} — {exp.trial_title}",
        f"  Tier: {exp.tier}   Score: {exp.score:g}",
        f"  {exp.summary}",
        "  Steps:",
    ]
    for s in exp.steps:
        lines.append(f"    {s.step}. {s.title}: {s.detail}")
    if exp.highlights:
        lines.append("  Highlights:")
        for h in exp.highlights:
            lines.append(f"    - {h}")
    return "\n".join(lines)
