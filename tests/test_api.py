"""Contract tests for the Mizan HTTP API.

Assert response shapes match the frontend TypeScript interfaces
(mizan-web/src/lib/types.ts) and API.md, so the frontend can switch
from mock mode to the live backend without changes.
"""

import unittest

from fastapi.testclient import TestClient

from mizan.api import create_app

MATCH_KEYS = {
    "patient_id", "trial_id", "trial_title", "tier", "score",
    "soft_rules_met", "soft_rules_total", "soft_rules_unknown",
    "location_bonus", "hard_failures", "hard_unknowns", "soft_failures",
}
AUDIT_KEYS = {
    "patient_id", "trial_id", "criterion_id", "field_checked", "rule_type",
    "hard_gate", "result", "reason", "patient_info", "criterion_text",
}
PATIENT_KEYS = {"patient_id", "age", "sex", "city", "country"}
FACT_KEYS = {
    "patient_id", "fact_id", "field_name", "num_value", "str_value",
    "unit", "negated", "confidence", "source",
}
TRIAL_KEYS = {
    "trial_id", "title", "phase", "sponsor", "therapeutic_area",
    "status", "enrollment_count", "target_enrollment",
}
COORDINATOR_KEYS = {
    "trial_id", "title", "therapeutic_area", "phase", "sponsor",
    "enrollment_count", "target_enrollment", "shortfall", "fill_pct",
    "eligible_count", "needs_screening_count", "review_count",
}
TIERS = {"ELIGIBLE", "NEEDS_SCREENING", "REVIEW", "NOT_ELIGIBLE"}
RESULTS = {"MET", "NOT_MET", "UNKNOWN", "NOT_APPLICABLE"}


class MizanApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app())

    def test_health(self) -> None:
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_patients_list_shape(self) -> None:
        res = self.client.get("/api/patients")
        self.assertEqual(res.status_code, 200)
        rows = res.json()
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(set(row), PATIENT_KEYS)

    def test_patient_detail(self) -> None:
        res = self.client.get("/api/patients/P001")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(set(body), {"patient", "facts"})
        self.assertEqual(set(body["patient"]), PATIENT_KEYS)
        for fact in body["facts"]:
            self.assertEqual(set(fact), FACT_KEYS)

    def test_patient_not_found(self) -> None:
        res = self.client.get("/api/patients/NOPE")
        self.assertEqual(res.status_code, 404)
        self.assertIn("error", res.json())
        self.assertEqual(res.json()["error"]["code"], "NOT_FOUND")

    def test_trials_and_detail(self) -> None:
        res = self.client.get("/api/trials")
        self.assertEqual(res.status_code, 200)
        for row in res.json():
            self.assertEqual(set(row), TRIAL_KEYS)

        detail = self.client.get("/api/trials/NCT001").json()
        self.assertEqual(set(detail), {"trial", "criteria", "sites"})
        self.assertEqual(set(detail["trial"]), TRIAL_KEYS)
        self.assertTrue(detail["criteria"])

    def test_matches_shape_and_values(self) -> None:
        res = self.client.get("/api/matches")
        self.assertEqual(res.status_code, 200)
        rows = res.json()
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(set(row), MATCH_KEYS)
            self.assertIn(row["tier"], TIERS)

        p1 = self.client.get("/api/matches/P001/NCT001").json()
        self.assertEqual(p1["tier"], "ELIGIBLE")
        self.assertEqual(p1["location_bonus"], 25.0)
        # ELIGIBLE means all hard gates pass and >= half the soft rules are met.
        self.assertEqual(p1["hard_failures"], 0)
        self.assertEqual(p1["hard_unknowns"], 0)
        self.assertGreaterEqual(2 * p1["soft_rules_met"], p1["soft_rules_total"])
        # score = soft% (100*met/total) + location bonus
        expected_pct = 100 if p1["soft_rules_total"] == 0 else (100 * p1["soft_rules_met"]) // p1["soft_rules_total"]
        self.assertEqual(p1["score"], float(expected_pct + p1["location_bonus"]))

    def test_matches_tier_filter(self) -> None:
        res = self.client.get("/api/matches", params={"tier": "ELIGIBLE"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(all(m["tier"] == "ELIGIBLE" for m in res.json()))

        bad = self.client.get("/api/matches", params={"tier": "BOGUS"})
        self.assertEqual(bad.status_code, 400)

    def test_matches_patient_filter(self) -> None:
        res = self.client.get("/api/matches", params={"patient_id": "P001"})
        self.assertTrue(all(m["patient_id"] == "P001" for m in res.json()))

    def test_audit_shape(self) -> None:
        res = self.client.get("/api/matches/P001/NCT001/audit")
        self.assertEqual(res.status_code, 200)
        rows = res.json()
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(set(row), AUDIT_KEYS)
            self.assertIn(row["result"], RESULTS)
            self.assertIn(row["rule_type"], {"inclusion", "exclusion"})

    def test_coordinator_dashboard_shape(self) -> None:
        res = self.client.get("/api/dashboard/coordinator")
        self.assertEqual(res.status_code, 200)
        for row in res.json():
            self.assertEqual(set(row), COORDINATOR_KEYS)

    def test_at_risk_and_summaries(self) -> None:
        self.assertEqual(self.client.get("/api/dashboard/at-risk-trials").status_code, 200)
        ts = self.client.get("/api/dashboard/trial-summary").json()
        for row in ts:
            self.assertEqual(
                set(row),
                {"trial_id", "trial_title", "eligible_count",
                 "needs_screening_count", "review_count", "not_eligible_count"},
            )
        ds = self.client.get("/api/dashboard/diagnosis-summary").json()
        for row in ds:
            self.assertEqual(set(row), {"diagnosis", "eligible_patient_count"})

    def test_match_run(self) -> None:
        res = self.client.post("/api/match/run")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "completed")
        self.assertIn("run_id", body)
        self.assertIn("patient_trial_matches", body["output_row_counts"])


if __name__ == "__main__":
    unittest.main()
