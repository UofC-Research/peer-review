from __future__ import annotations

from peer_elt.transform.methodology import (
    PREREGISTERED_INDICATORS,
    score_manuscript_pair,
    score_manuscript_version,
)
from peer_elt.transform.scoring import HybridScorer, RuleBasedScorer, default_rule_patterns


def _scorer() -> HybridScorer:
    return HybridScorer(RuleBasedScorer(default_rule_patterns()))


def test_version_scorecard_materializes_all_preregistered_indicators() -> None:
    """Methodology requires all V1-V10 scores, including absent indicators."""
    sections = {
        "methods": "We used a regression model.",
        "results": "The odds ratio was 1.45.",
        "statements": "",
    }

    scorecard = score_manuscript_version(
        manuscript_id="10.1101/example",
        version="preprint",
        sections=sections,
        scorer=_scorer(),
        document_format="pdf",
    )

    assert tuple(scorecard.as_dict()) == PREREGISTERED_INDICATORS
    assert scorecard.as_dict()["V1"].score == 2
    assert scorecard.as_dict()["V5"].score == 1
    assert scorecard.as_dict()["V2"].score == 0
    assert scorecard.raw_score == 3
    assert scorecard.zero_score_indicators
    assert scorecard.needs_document_completeness_review is True


def test_pair_scorecard_computes_deltas_and_pres_independently() -> None:
    """PRES is sum(published V1-V10) - sum(preprint V1-V10)."""
    preprint_sections = {
        "methods": "We used a regression model.",
        "results": "The odds ratio was 1.45.",
        "statements": "",
    }
    published_sections = {
        "methods": (
            "We used a regression model adjusted for covariate A. "
            "A power calculation assumed alpha 0.05 and effect size 0.4. "
            "Missing data were handled using multiple imputation."
        ),
        "results": "The odds ratio was 1.45 with 95% CI 1.10-1.90, p = 0.02.",
        "statements": "Data availability is provided on GitHub.",
    }

    pair = score_manuscript_pair(
        manuscript_id="10.1101/example",
        preprint_sections=preprint_sections,
        published_sections=published_sections,
        scorer=_scorer(),
        preprint_format="pdf",
        published_format="html",
    )

    assert pair.preprint.raw_score == 3
    assert pair.published.raw_score == 14
    assert pair.indicator_deltas["V1"] == 0
    assert pair.indicator_deltas["V2"] == 2
    assert pair.indicator_deltas["V4"] == 2
    assert pair.indicator_deltas["V6"] == 0
    assert pair.pres == 11


def test_pair_scorecard_exports_flat_record_and_evidence_rows() -> None:
    """Audit exports keep scores, deltas, formats, and evidence together."""
    pair = score_manuscript_pair(
        manuscript_id="10.1101/example",
        preprint_sections={
            "methods": "",
            "results": "The odds ratio was 1.45.",
            "statements": "",
        },
        published_sections={
            "methods": "",
            "results": "The odds ratio was 1.45 with 95% CI 1.10-1.90.",
            "statements": "",
        },
        scorer=_scorer(),
        preprint_format="pdf",
        published_format="pdf",
    )

    record = pair.to_record()
    evidence_rows = pair.evidence_rows()

    assert record["manuscript_id"] == "10.1101/example"
    assert record["preprint_document_format"] == "pdf"
    assert record["published_document_format"] == "pdf"
    assert record["V2_preprint"] == 0
    assert record["V2_published"] == 2
    assert record["V2_delta"] == 2
    assert record["PRES"] == 2
    assert evidence_rows
    assert {"manuscript_id", "version", "indicator", "score", "section", "text"} <= set(
        evidence_rows[0]
    )
