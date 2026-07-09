"""Trial-level composite scoring (foundation formula from TrialMatchAI Methods).

S_inc = met inclusion criteria / valid inclusion criteria
S_exc = passed exclusion criteria / valid exclusion criteria
S     = (S_inc + S_exc) / 2

UNKNOWN and NOT_APPLICABLE criteria are excluded from denominators
(missing data is never treated as failure).
"""

from __future__ import annotations

from dataclasses import dataclass

from mizan.evaluator import CriterionResult, EvaluationOutcome
from mizan.loader import EligibilityCriterion


@dataclass(frozen=True)
class CompositeScore:
    inclusion_score: float
    exclusion_score: float
    composite_score: float
    inclusion_met: int
    inclusion_total: int
    exclusion_met: int
    exclusion_total: int
    location_bonus: float

    @property
    def final_score(self) -> float:
        return round(self.composite_score + self.location_bonus, 2)


def _criterion_contributes(result: CriterionResult) -> bool:
    return result not in (CriterionResult.UNKNOWN, CriterionResult.NOT_APPLICABLE)


def _inclusion_met(result: CriterionResult) -> bool:
    return result == CriterionResult.MET


def _exclusion_met(result: CriterionResult) -> bool:
    """For exclusions, MET means the patient passes (is not excluded)."""
    return result == CriterionResult.MET


def composite_score(
    outcomes: list[tuple[EligibilityCriterion, EvaluationOutcome]],
    location_bonus: float = 0.0,
) -> CompositeScore:
    inclusion = [(c, o) for c, o in outcomes if c.rule_type == "inclusion" and _criterion_contributes(o.result)]
    exclusion = [(c, o) for c, o in outcomes if c.rule_type == "exclusion" and _criterion_contributes(o.result)]

    inc_met = sum(1 for _, o in inclusion if _inclusion_met(o.result))
    inc_total = len(inclusion)
    exc_met = sum(1 for _, o in exclusion if _exclusion_met(o.result))
    exc_total = len(exclusion)

    s_inc = (inc_met / inc_total) if inc_total else 1.0
    s_exc = (exc_met / exc_total) if exc_total else 1.0
    composite = ((s_inc + s_exc) / 2) * 100.0

    return CompositeScore(
        inclusion_score=round(s_inc * 100, 2),
        exclusion_score=round(s_exc * 100, 2),
        composite_score=round(composite, 2),
        inclusion_met=inc_met,
        inclusion_total=inc_total,
        exclusion_met=exc_met,
        exclusion_total=exc_total,
        location_bonus=location_bonus,
    )
