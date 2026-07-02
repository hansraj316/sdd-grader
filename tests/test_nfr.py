"""Unit test for the NFR-without-threshold check (SPEC-NFR-NO-THRESHOLD)."""

from __future__ import annotations

from pathlib import Path

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _nfr_without_threshold
from sddgrade.model import Artifact, ArtifactType


def _spec(text: str) -> Artifact:
    return Artifact(
        path="spec.md", type=ArtifactType.SPEC, feature_id="x",
        raw=text, sections=parse_sections(text),
    )


def test_nfr_without_threshold_fires():
    art = _spec("# Spec\n\n- FR-001: The system shall have low latency and high availability.\n")
    findings = _nfr_without_threshold(art, load_catalog())
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-THRESHOLD"
    assert findings[0].suggestion


def test_nfr_with_threshold_is_clean():
    art = _spec("# Spec\n\n- FR-001: The system shall keep p95 latency under 200ms.\n")
    assert _nfr_without_threshold(art, load_catalog()) == []


def test_non_requirement_nfr_word_ignored():
    # Prose mentioning latency, but not a requirement line → no false positive.
    art = _spec("# Spec\n\nWe care about latency in general.\n")
    assert _nfr_without_threshold(art, load_catalog()) == []
