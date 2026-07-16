"""Tests for REQ-UNBOUNDED-SCOPE — open-ended enumerations in requirement lines."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _unbounded_scope
from sddgrade.model import Artifact, ArtifactType


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


CATALOG = load_catalog()
PITFALL = "REQ-UNBOUNDED-SCOPE"


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _unbounded_scope(art, CATALOG)]


# ---- fires on open-ended markers in requirement lines -----------------------

def test_fires_on_etc_in_shall_line():
    art = _spec("## FR\nThe system shall support PNG, JPEG, GIF, etc.")
    assert PITFALL in _ids(art)


def test_fires_on_and_so_on_in_must_line():
    art = _spec("## FR\nThe API must accept JSON, XML, and so on.")
    assert PITFALL in _ids(art)


def test_fires_on_and_others_in_should_line():
    art = _spec("## FR\nThe form should validate email, phone, and others.")
    assert PITFALL in _ids(art)


def test_fires_on_and_more_in_will_line():
    art = _spec("## FR\nUsers will configure alerts, notifications, and more.")
    assert PITFALL in _ids(art)


def test_fires_on_including_but_not_limited_to():
    art = _spec(
        "## FR\nThe export shall support formats including but not limited to CSV and XLSX."
    )
    assert PITFALL in _ids(art)


def test_fires_on_or_similar_in_fr_labeled_line():
    art = _spec("## FR\nFR-001: The UI shall render charts, graphs, or similar.")
    assert PITFALL in _ids(art)


def test_fires_on_want_line_with_etc():
    art = _spec("## US\nAs a user I want to export CSV, XLSX, etc.")
    assert PITFALL in _ids(art)


def test_fires_also_on_plan_artifact():
    art = _plan("## Deployment\nThe service shall deploy to AWS, GCP, etc.")
    assert PITFALL in _ids(art)


def test_reports_count_of_affected_lines():
    art = _spec(
        "## FR\n"
        "The system shall support PNG, GIF, etc.\n"
        "The system must accept JSON, XML, and so on.\n"
    )
    findings = _unbounded_scope(art, CATALOG)
    assert len(findings) == 1
    assert "2 line(s)" in findings[0].message


# ---- silent when no open-ended marker in requirement lines ------------------

def test_silent_on_bounded_enumeration():
    art = _spec("## FR\nThe system shall support PNG, JPEG, and GIF.")
    assert PITFALL not in _ids(art)


def test_silent_on_etc_in_prose_non_requirement_line():
    art = _spec(
        "## Background\n"
        "This covers many formats, etc., as needed.\n"
        "## FR\nThe system shall export only CSV.\n"
    )
    assert PITFALL not in _ids(art)


def test_silent_on_spec_with_no_requirements():
    art = _spec("## Overview\nThis feature adds a dashboard.")
    assert PITFALL not in _ids(art)
