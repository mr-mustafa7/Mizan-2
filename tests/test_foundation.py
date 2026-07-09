"""Tests for Mizan foundation architecture."""

import unittest

from mizan.architecture import Layer
from mizan.evaluator import CriterionResult, evaluate_criterion, is_supported_criterion
from mizan.loader import EligibilityCriterion, MizanData, Patient, PatientFact, Trial
from mizan.matcher import MatchTier, match_patient_trial
from mizan.quality import build_patient_data_quality
from mizan.stages import stage_ingest, stage_prefilter


class FoundationTests(unittest.TestCase):
    def test_five_layers_exist(self) -> None:
        self.assertEqual(len(Layer), 5)

    def test_ingest_and_prefilter(self) -> None:
        data, _ = stage_ingest("data")
        trial_ids, prefilter = stage_prefilter(data)
        self.assertGreater(len(trial_ids), 0)
        self.assertEqual(prefilter.layer, Layer.PREFILTER)

    def test_patient_data_quality_gate(self) -> None:
        data, _ = stage_ingest("data")
        quality = build_patient_data_quality(data)
        self.assertEqual(len(quality), len(data.patients))
        scoreable = [q for q in quality if q.scoreable == "YES"]
        self.assertGreater(len(scoreable), 0)

    def test_lab_criterion_not_in_vadalog(self) -> None:
        criterion = EligibilityCriterion(
            "C1", "T1", "inclusion", "lab_hemoglobin", "ge", "10", False, "Hgb"
        )
        self.assertFalse(is_supported_criterion(criterion))

    def test_wild_type_is_not_met_for_egfr_inclusion(self) -> None:
        data = MizanData(
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
            trials=[Trial("T1", "Test", "II", "Sp", "lung", "recruiting", 1, 10)],
            sites=[],
        )
        outcome = evaluate_criterion(data, "P1", data.eligibility_criteria[0])
        assert outcome is not None
        self.assertEqual(outcome.result, CriterionResult.NOT_MET)

    def test_missing_data_needs_screening(self) -> None:
        data = MizanData(
            patients=[Patient("P1", 55, "F", "Boston", "USA")],
            patient_facts=[
                PatientFact("P1", "F1", "diagnosis", None, "NSCLC", "", False, "high", "path"),
                PatientFact("P1", "F2", "ecog", 1, "", "", False, "high", "clinic"),
            ],
            eligibility_criteria=[
                EligibilityCriterion("C1", "T1", "inclusion", "biomarker_egfr", "positive", "mutation", True, "EGFR+"),
            ],
            trials=[Trial("T1", "Test", "II", "Sp", "lung", "recruiting", 1, 10)],
            sites=[],
        )
        match = match_patient_trial(data, "P1", "T1")
        assert match is not None
        self.assertEqual(match.tier, MatchTier.NEEDS_SCREENING)


if __name__ == "__main__":
    unittest.main()
