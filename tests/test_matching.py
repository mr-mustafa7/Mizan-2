"""Tests for Mizan matching logic (Prometheux Vadalog alignment)."""

import unittest

from mizan.evaluator import CriterionResult, evaluate_criterion
from mizan.loader import EligibilityCriterion, MizanData, Patient, PatientFact, Trial
from mizan.matcher import MatchTier, match_patient_trial


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


if __name__ == "__main__":
    unittest.main()
