"""Tests for the SPEC-FUTURE-TENSE-REQ pitfall (future-tense in requirement lines)."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _future_tense_req
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-FUTURE-TENSE-REQ"


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _future_tense_req(art, CATALOG)]


# ── fires cases ───────────────────────────────────────────────────────────────

def test_will_be_in_fr_label():
    """FR-labelled line using 'will be' fires SPEC-FUTURE-TENSE-REQ."""
    art = _spec("""
        ## Requirements

        FR-01: The system will be able to process payments.
    """)
    assert PITFALL in _ids(art)


def test_will_be_in_nfr_label():
    """NFR-labelled line with 'will be' fires."""
    art = _spec("""
        ## Requirements

        NFR-02: The API will be available 99.9% of the time.
    """)
    assert PITFALL in _ids(art)


def test_would_be_in_fr_label():
    """'would be' on a requirement line fires."""
    art = _spec("""
        ## Requirements

        FR-03: The response would be returned within 200ms.
    """)
    assert PITFALL in _ids(art)


def test_will_support_in_requirements_section():
    """'will support' inside a Requirements section fires."""
    art = _spec("""
        ## Requirements

        The system will support multiple authentication methods.
    """)
    assert PITFALL in _ids(art)


def test_will_allow_in_acceptance_section():
    """'will allow' inside an Acceptance Criteria section fires."""
    art = _spec("""
        ## Acceptance Criteria

        The interface will allow users to reset their password.
    """)
    assert PITFALL in _ids(art)


def test_will_provide_in_requirements_section():
    """'will provide' in a Requirements section fires."""
    art = _spec("""
        ## Requirements

        The service will provide real-time notifications.
    """)
    assert PITFALL in _ids(art)


def test_will_enable_in_fr_label():
    """'will enable' on an FR-labelled line fires."""
    art = _spec("FR-05: The module will enable batch processing.")
    assert PITFALL in _ids(art)


def test_will_handle_in_requirements_section():
    """'will handle' in a Requirements section fires."""
    art = _spec("""
        ## Requirements

        The system will handle up to 10000 concurrent requests.
    """)
    assert PITFALL in _ids(art)


def test_multiple_hits_produce_one_finding():
    """Multiple future-tense lines produce exactly one finding (one-per-artifact)."""
    art = _spec("""
        ## Requirements

        FR-01: The system will be scalable.
        FR-02: The system will provide logs.
    """)
    findings = _future_tense_req(art, CATALOG)
    assert len(findings) == 1


def test_message_contains_hit_count():
    """Finding message includes the count of affected lines."""
    art = _spec("""
        ## Requirements

        FR-01: The system will be scalable.
        FR-02: The system will allow exports.
    """)
    findings = _future_tense_req(art, CATALOG)
    assert findings
    assert "2" in findings[0].message


def test_line_number_reported():
    """Finding anchors to the first hit's line number."""
    art = _spec("""
        ## Requirements

        FR-01: The system will be able to scale.
    """)
    findings = _future_tense_req(art, CATALOG)
    assert findings
    assert findings[0].line is not None


# ── does-not-fire cases ───────────────────────────────────────────────────────

def test_shall_present_tense_no_fire():
    """Normative 'shall' does not fire."""
    art = _spec("""
        ## Requirements

        FR-01: The system shall process payments synchronously.
    """)
    assert PITFALL not in _ids(art)


def test_must_present_tense_no_fire():
    """Normative 'must' does not fire."""
    art = _spec("""
        ## Requirements

        FR-01: The system must validate all inputs.
    """)
    assert PITFALL not in _ids(art)


def test_will_be_plus_shall_no_fire():
    """A line with both 'shall' and 'will be' is skipped (mixed normative statement)."""
    art = _spec("""
        ## Requirements

        FR-01: The system shall store data and will be encrypted at rest.
    """)
    assert PITFALL not in _ids(art)


def test_will_be_plus_must_no_fire():
    """A line with both 'must' and 'will be' is skipped."""
    art = _spec("""
        ## Requirements

        FR-01: Tokens must expire and will be refreshed automatically.
    """)
    assert PITFALL not in _ids(art)


def test_future_tense_outside_req_section_no_fire():
    """Future-tense prose outside a requirements section and without FR-/NFR- label does not fire."""
    art = _spec("""
        ## Overview

        This project will be built using Python.
    """)
    assert PITFALL not in _ids(art)


def test_future_tense_in_fenced_block_no_fire():
    """Future-tense inside a fenced code block is excluded."""
    art = _spec("""
        ## Requirements

        ```
        The system will be able to handle this.
        ```
    """)
    assert PITFALL not in _ids(art)


def test_non_spec_artifact_no_fire():
    """Plan artifacts are not checked for SPEC-FUTURE-TENSE-REQ."""
    art = _plan("""
        ## Requirements

        FR-01: The system will be deployed to production.
    """)
    assert PITFALL not in _ids(art)


def test_empty_spec_no_fire():
    """Empty spec produces no findings."""
    art = _spec("")
    assert PITFALL not in _ids(art)
