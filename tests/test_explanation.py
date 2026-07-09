"""Tests for the match explanation / decision narrative."""

import unittest

from mizan.explanation import build_match_explanation
from mizan.loader import EligibilityCriterion, MizanData, Patient, PatientFact, Site, Trial


def _eligible_data() -> MizanData:
    return MizanData(
        patients=[Patient("P1", 67, "F", "Boston", "USA")],
        patient_facts=[
            PatientFact("P1", "F1", "diagnosis", None, "NSCLC adenocarcinoma", "", False, "high", "path"),
            PatientFact("P1", "F2", "ecog", 1, "", "", False, "high", "clinic"),
            PatientFact("P1", "F3", "biomarker_egfr", None, "L858R mutation", "", False, "high", "mol"),
            PatientFact("P1", "F4", "cancer_stage", None, "Stage IIIB", "", False, "high", "img"),
        ],
        eligibility_criteria=[
            EligibilityCriterion("C1", "T1", "inclusion", "diagnosis", "contains", "NSCLC", True, "Confirmed NSCLC"),
            EligibilityCriterion("C2", "T1", "inclusion", "age", "ge", "18", True, "Adult"),
            EligibilityCriterion("C3", "T1", "inclusion", "biomarker_egfr", "positive", "mutation", True, "EGFR+"),
            EligibilityCriterion("C4", "T1", "inclusion", "cancer_stage", "contains", "Stage", False, "Stage documented"),
        ],
        trials=[Trial("T1", "EGFR Study", "II", "Sp", "lung", "recruiting", 1, 10)],
        sites=[Site("S1", "T1", "MGH", "Boston", "USA")],
    )


class ExplanationTests(unittest.TestCase):
    def test_eligible_summary_and_facts(self) -> None:
        exp = build_match_explanation(_eligible_data(), "P1", "T1")
        assert exp is not None
        self.assertEqual(exp.tier, "ELIGIBLE")
        self.assertEqual(exp.score, 125.0)
        self.assertIn("ELIGIBLE", exp.summary)
        # One fact per evaluated criterion, all green here.
        self.assertEqual(len(exp.facts), 4)
        self.assertTrue(all(f.bar == "green" for f in exp.facts))
        diag = next(f for f in exp.facts if f.field_checked == "diagnosis")
        self.assertEqual(diag.patient_value, "NSCLC adenocarcinoma")
        # Five ordered reasoning steps.
        self.assertEqual([s.step for s in exp.steps], [1, 2, 3, 4, 5])

    def test_not_eligible_has_decisive_factor(self) -> None:
        data = _eligible_data()
        # Flip EGFR to wild type -> hard inclusion fails.
        data.patient_facts = [
            f for f in data.patient_facts if f.field_name != "biomarker_egfr"
        ] + [PatientFact("P1", "F3", "biomarker_egfr", None, "wild type", "", False, "high", "mol")]
        exp = build_match_explanation(data, "P1", "T1")
        assert exp is not None
        self.assertEqual(exp.tier, "NOT_ELIGIBLE")
        self.assertEqual(exp.score, 0.0)
        self.assertTrue(exp.decisive_factors)
        self.assertTrue(any(f.bar == "red" for f in exp.facts))

    def test_needs_screening_marks_missing_as_amber(self) -> None:
        data = _eligible_data()
        # Remove EGFR fact entirely -> hard gate UNKNOWN.
        data.patient_facts = [f for f in data.patient_facts if f.field_name != "biomarker_egfr"]
        exp = build_match_explanation(data, "P1", "T1")
        assert exp is not None
        self.assertEqual(exp.tier, "NEEDS_SCREENING")
        egfr = next(f for f in exp.facts if f.field_checked == "biomarker_egfr")
        self.assertEqual(egfr.result, "UNKNOWN")
        self.assertEqual(egfr.bar, "amber")
        self.assertEqual(egfr.patient_value, "not on record")
        self.assertTrue(exp.decisive_factors)


if __name__ == "__main__":
    unittest.main()
