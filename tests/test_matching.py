"""Tests for Mizan matching logic (Prometheux Vadalog alignment)."""

import unittest

from mizan.evaluator import CriterionResult, evaluate_criterion
from mizan.loader import EligibilityCriterion, MizanData, Patient, PatientFact, Site, Trial
from mizan.matcher import (
    MatchTier,
    build_criterion_coverage,
    match_patient_trial,
)


def _minimal_data() -> MizanData:
    return MizanData(
        patients=[Patient("P1", 55, "F", "Boston", "USA")],
        patient_facts=[
            PatientFact("P1", "F1", "diagnosis", None, "NSCLC", "", False, "high", "path"),
            PatientFact("P1", "F2", "ecog", 1, "", "", False, "high", "clinic"),
            PatientFact("P1", "F3", "biomarker_egfr", None, "wild type", "", False, "high", "mol"),
        ],
        eligibility_criteria=[
            EligibilityCriterion(
                "C1", "T1", "inclusion", "biomarker_egfr", "positive", "mutation", True, "EGFR+"
            )
        ],
        trials=[],
        sites=[],
    )


class MizanMatchingTests(unittest.TestCase):
    def test_wild_type_counts_as_negative(self) -> None:
        data = _minimal_data()
        outcome = evaluate_criterion(data, "P1", data.eligibility_criteria[0])
        assert outcome is not None
        self.assertEqual(outcome.result, CriterionResult.NOT_MET)
        self.assertIn("wild type", outcome.reason.lower())

    def test_missing_biomarker_is_unknown_not_not_met(self) -> None:
        data = _minimal_data()
        data.patient_facts = [f for f in data.patient_facts if f.field_name != "biomarker_egfr"]
        outcome = evaluate_criterion(data, "P1", data.eligibility_criteria[0])
        assert outcome is not None
        self.assertEqual(outcome.result, CriterionResult.UNKNOWN)

    def test_missing_hard_info_yields_needs_screening(self) -> None:
        data = MizanData(
            patients=[Patient("P1", 55, "F", "Boston", "USA")],
            patient_facts=[
                PatientFact("P1", "F1", "diagnosis", None, "NSCLC", "", False, "high", "path"),
                PatientFact("P1", "F2", "ecog", 1, "", "", False, "high", "clinic"),
            ],
            eligibility_criteria=[
                EligibilityCriterion("C1", "T1", "inclusion", "biomarker_egfr", "positive", "mutation", True, "EGFR+"),
                EligibilityCriterion("C2", "T1", "inclusion", "age", "ge", "18", True, "Adult"),
            ],
            trials=[Trial("T1", "Test", "II", "Sp", "lung", "recruiting", 1, 10)],
            sites=[],
        )
        match = match_patient_trial(data, "P1", "T1")
        assert match is not None
        self.assertEqual(match.tier, MatchTier.NEEDS_SCREENING)

    def test_hard_failure_is_not_eligible(self) -> None:
        data = _minimal_data()
        data.trials = [Trial("T1", "Test", "II", "Sp", "lung", "recruiting", 1, 10)]
        match = match_patient_trial(data, "P1", "T1")
        assert match is not None
        self.assertEqual(match.tier, MatchTier.NOT_ELIGIBLE)

    def test_eligible_score_includes_city_bonus(self) -> None:
        data = MizanData(
            patients=[Patient("P1", 55, "F", "Boston", "USA")],
            patient_facts=[
                PatientFact("P1", "F1", "diagnosis", None, "NSCLC", "", False, "high", "path"),
                PatientFact("P1", "F2", "ecog", 1, "", "", False, "high", "clinic"),
                PatientFact("P1", "F3", "cancer_stage", None, "Stage IV", "", False, "high", "img"),
            ],
            eligibility_criteria=[
                EligibilityCriterion("C1", "T1", "inclusion", "diagnosis", "contains", "NSCLC", True, "NSCLC"),
                EligibilityCriterion("C2", "T1", "inclusion", "cancer_stage", "contains", "Stage", False, "Stage"),
            ],
            trials=[Trial("T1", "Test", "II", "Sp", "lung", "recruiting", 1, 10)],
            sites=[Site("S1", "T1", "Site", "Boston", "USA")],
        )
        match = match_patient_trial(data, "P1", "T1")
        assert match is not None
        self.assertEqual(match.tier, MatchTier.ELIGIBLE)
        # soft 1/1 = 100% + city bonus 25 = 125
        self.assertEqual(match.score, 125.0)
        self.assertEqual(match.location_bonus, 25.0)

    def test_review_when_soft_below_half(self) -> None:
        data = MizanData(
            patients=[Patient("P1", 55, "F", "Nowhere", "Narnia")],
            patient_facts=[
                PatientFact("P1", "F1", "diagnosis", None, "NSCLC", "", False, "high", "path"),
                PatientFact("P1", "F2", "ecog", 1, "", "", False, "high", "clinic"),
                PatientFact("P1", "F3", "cancer_stage", None, "unknown", "", False, "low", "img"),
                PatientFact("P1", "F4", "prior_treatments", None, "carboplatin", "", False, "high", "onc"),
            ],
            eligibility_criteria=[
                EligibilityCriterion("C1", "T1", "inclusion", "diagnosis", "contains", "NSCLC", True, "NSCLC"),
                EligibilityCriterion("C2", "T1", "inclusion", "cancer_stage", "contains", "Stage IV", False, "Stg"),
                EligibilityCriterion("C3", "T1", "inclusion", "prior_treatments", "contains", "osimertinib", False, "Osi"),
            ],
            trials=[Trial("T1", "Test", "II", "Sp", "lung", "recruiting", 1, 10)],
            sites=[],
        )
        match = match_patient_trial(data, "P1", "T1")
        assert match is not None
        # 0 of 2 soft met -> 2*0 < 2 -> REVIEW
        self.assertEqual(match.tier, MatchTier.REVIEW)

    def test_coverage_flags_unsupported_criteria(self) -> None:
        data = MizanData(
            patients=[Patient("P1", 55, "F", "Boston", "USA")],
            patient_facts=[],
            eligibility_criteria=[
                EligibilityCriterion("C1", "T1", "inclusion", "age", "ge", "18", True, "Adult"),
                EligibilityCriterion("C2", "T1", "inclusion", "lab_hemoglobin", "ge", "10", False, "Hgb"),
                EligibilityCriterion("C3", "T1", "exclusion", "age", "ge", "80", True, "Elderly"),
            ],
            trials=[Trial("T1", "Test", "II", "Sp", "lung", "recruiting", 1, 10)],
            sites=[],
        )
        coverage = {c.criterion_id: c for c in build_criterion_coverage(data, ["T1"])}
        self.assertEqual(coverage["C1"].evaluated, "YES")
        self.assertEqual(coverage["C2"].evaluated, "NO")
        self.assertEqual(coverage["C3"].evaluated, "NO")
        self.assertIn("lab", coverage["C2"].note)


if __name__ == "__main__":
    unittest.main()
