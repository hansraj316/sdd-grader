"""Tests for SPEC-QVSCRIBE-OPTIONAL-FEATURE pitfall check.

Fires when a normative requirement (SHALL/MUST) contains optional-feature
language that makes it non-mandatory (ISO 29148 §5.2.5(c); QVscribe Level-1
Clarity).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_optional_feature
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-QVSCRIBE-OPTIONAL-FEATURE"


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
    return [f.pitfall_id for f in _spec_qvscribe_optional_feature(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------

def test_fire_if_desired():
    """'if desired' in SHALL requirement fires."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall support dark mode, if desired.
    """)
    assert PITFALL in _ids(art)


def test_fire_optionally():
    """'optionally' in MUST requirement fires."""
    art = _spec("""
        ## Requirements

        - FR-002: The API must, optionally, return a summary field in responses.
    """)
    assert PITFALL in _ids(art)


def test_fire_if_feasible():
    """'if feasible' in SHALL requirement fires."""
    art = _spec("""
        ## Requirements

        - FR-003: The system shall cache responses if feasible.
    """)
    assert PITFALL in _ids(art)


def test_fire_as_needed():
    """'as needed' in SHALL requirement fires."""
    art = _spec("""
        ## Requirements

        - FR-004: The system shall scale horizontally as needed.
    """)
    assert PITFALL in _ids(art)


def test_fire_where_appropriate():
    """'where appropriate' in SHALL requirement fires."""
    art = _spec("""
        ## Requirements

        - FR-005: The system shall log errors where appropriate.
    """)
    assert PITFALL in _ids(art)


def test_fire_if_applicable():
    """'if applicable' in SHALL requirement fires."""
    art = _spec("""
        ## Requirements

        - FR-006: The system shall display a GDPR consent banner if applicable.
    """)
    assert PITFALL in _ids(art)


def test_fire_multiple_lines():
    """Multiple offending lines each produce a finding."""
    art = _spec("""
        ## Requirements

        - FR-010: The system shall support SSO if desired.
        - FR-011: The system shall emit metrics if feasible.
    """)
    findings = _ids(art)
    assert findings.count(PITFALL) == 2


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------

def test_silent_no_optional_phrase():
    """Plain normative requirement with no optional language is silent."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall authenticate users via OAuth 2.0.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block():
    """Optional-feature phrase inside a fenced code block is silent."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall support OAuth 2.0.

        ```
        # if desired configuration
        feature_flag = True
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_requirement_line():
    """Optional-feature phrase in prose (not a requirement line) is silent."""
    art = _spec("""
        ## Background

        The team discussed whether dark mode should be added if desired by users.

        ## Requirements

        - FR-001: The system shall support OAuth 2.0.
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifacts are not checked (spec-only)."""
    art = _plan("""
        ## Deployment Plan

        Deploy the service, optionally with a CDN if desired.
    """)
    assert PITFALL not in _ids(art)
