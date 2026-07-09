"""Mizan foundation architecture — research-backed medtech structure.

Implements the Prometheux Vadalog `criterion_evaluation` + `pair_assessment`
model, framed with the TrialMatchAI clinical decision-support pipeline
(Nature Communications, 2026; doi:10.1038/s41467-026-70509-w) and
deterministic eligibility approaches (MatchMiner, ICH E6 GCP audit).

Five layers, no GPU / LLM required — suitable for coordinator demos.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Layer(str, Enum):
    """Foundation pipeline layers (maps to TrialMatchAI stages 1–4 + coordinator view)."""

    INGEST = "1_ingest"
    PREFILTER = "2_prefilter"
    ELIGIBILITY = "3_eligibility"
    RANKING = "4_ranking"
    DECISION_SUPPORT = "5_decision_support"


@dataclass(frozen=True)
class ResearchReference:
    title: str
    source: str
    url: str
    maps_to: str


FOUNDATION_REFERENCES: tuple[ResearchReference, ...] = (
    ResearchReference(
        title="TrialMatchAI end-to-end clinical trial matching",
        source="Nature Communications (2026)",
        url="https://doi.org/10.1038/s41467-026-70509-w",
        maps_to="Criterion-level eligibility, top-K shortlists, decision support (not autonomous enrollment)",
    ),
    ResearchReference(
        title="MatchMiner open-source precision oncology matching",
        source="npj Precision Oncology (2022)",
        url="https://doi.org/10.1038/s41598-022-23225-3",
        maps_to="Deterministic structured rules for genomic and clinical criteria",
    ),
    ResearchReference(
        title="ICH E6(R3) GCP — traceable eligibility decisions",
        source="ICH Guidelines",
        url="https://www.ich.org/",
        maps_to="Audit trail: one row per patient × criterion with plain-English reason",
    ),
)

LAYER_DESCRIPTIONS: dict[Layer, str] = {
    Layer.INGEST: "Load five CSV inputs + patient_data_quality gate (diagnosis + ECOG).",
    Layer.PREFILTER: "Fast deterministic filters — recruiting trials with supported criteria.",
    Layer.ELIGIBILITY: "criterion_evaluation: each criterion is MET / NOT_MET / UNKNOWN (missing data never NOT_MET).",
    Layer.RANKING: "pair_assessment: soft-rule % + location bonus; tier NOT_ELIGIBLE / NEEDS_SCREENING / ELIGIBLE / REVIEW.",
    Layer.DECISION_SUPPORT: "Coordinator dashboards, at-risk trials, rejection reasons, patient shortlists, audit trail.",
}

# TrialMatchAI validated top-20 as the clinically practical review window (WIDE cohort, NKI).
DEFAULT_SHORTLIST_SIZE = 20
