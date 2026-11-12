"""Tests for SPEC-NFR-SCALABILITY-NO-METRIC pitfall check.

Fires when a normative requirement asserts scalability without a numeric
scale target (ISO/IEC 25010 §6.2.2; QVscribe QV-104).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_scalability_no_metric
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-NFR-SCALABILITY-NO-METRIC"


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
    return [f.pitfall_id for f in _spec_nfr_scalability_no_metric(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases — scalability claim with no digit on the line
# ---------------------------------------------------------------------------

def test_fire_bare_scalable():
    """'scalable' with no number fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall be scalable.
    """)
    assert PITFALL in _ids(art)


def test_fire_horizontally_scalable():
    """'horizontally scalable' with no number fires."""
    art = _spec("""
        ## Requirements

        - NFR-002: The API tier shall be horizontally scalable.
    """)
    assert PITFALL in _ids(art)


def test_fire_vertically_scalable():
    """'vertically scalable' with no number fires."""
    art = _spec("""
        ## Requirements

        - NFR-003: The database shall be vertically scalable to handle growth.
    """)
    assert PITFALL in _ids(art)


def test_fire_elastic_scaling():
    """'elastic scaling' with no number fires."""
    art = _spec("""
        ## Non-Functional Requirements

        - NFR-004: The API shall support elastic scaling.
    """)
    assert PITFALL in _ids(art)


def test_fire_can_scale():
    """'can scale' phrase with no number fires."""
    art = _spec("""
        ## Performance

        - NFR-005: The platform must can scale to meet peak traffic demands.
    """)
    assert PITFALL in _ids(art)


def test_fire_scales_elastically():
    """'scale elastically' with no number fires."""
    art = _spec("""
        ## Requirements

        - NFR-006: The system shall scale elastically to meet demand.
    """)
    assert PITFALL in _ids(art)


def test_fire_scales_out():
    """'scales out' with no number fires."""
    art = _spec("""
        ## Requirements

        - NFR-007: The service must scale out automatically under load.
    """)
    assert PITFALL in _ids(art)


def test_fire_multiple_lines_one_finding_each():
    """Two scalability claims without numbers → two findings."""
    art = _spec("""
        ## Requirements

        - NFR-008: The system shall be scalable.
        - NFR-009: The service shall be horizontally scalable.
    """)
    assert _ids(art).count(PITFALL) == 2


# ---------------------------------------------------------------------------
# SILENT cases — digit present silences the check
# ---------------------------------------------------------------------------

def test_silent_scale_to_n_users():
    """Explicit user count → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall scale horizontally to 50000 concurrent users.
    """)
    assert PITFALL not in _ids(art)


def test_silent_scale_10x():
    """10x multiplier present → silent."""
    art = _spec("""
        ## Requirements

        - NFR-002: The API shall scale to 10x the current baseline load.
    """)
    assert PITFALL not in _ids(art)


def test_silent_scale_100_nodes():
    """Node count present → silent."""
    art = _spec("""
        ## Requirements

        - NFR-003: The cluster shall scale out to 100 nodes automatically.
    """)
    assert PITFALL not in _ids(art)


def test_silent_scalable_with_rps():
    """RPS number present → silent."""
    art = _spec("""
        ## Requirements

        - NFR-004: The service shall be scalable to 5000 requests per second.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_normative_line():
    """Non-normative prose line (no shall/must/NFR-/FR-) → silent."""
    art = _spec("""
        ## Background

        The system is designed to be horizontally scalable in future iterations.
    """)
    assert PITFALL not in _ids(art)


def test_silent_in_fenced_block():
    """Scalability claim inside a fenced code block → silent."""
    art = _spec("""
        ## Requirements

        ```
        NFR-005: The system shall be scalable.
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifact → check does not apply."""
    art = _plan("NFR-001: The system shall be scalable.")
    assert PITFALL not in _ids(art)


def test_silent_scalable_with_gb():
    """Storage GB target → silent."""
    art = _spec("""
        ## Requirements

        - NFR-006: The storage layer shall be scalable to 500 GB per tenant.
    """)
    assert PITFALL not in _ids(art)


def test_silent_elastic_scaling_with_number():
    """Instance count in elastic scaling line → silent."""
    art = _spec("""
        ## Requirements

        - NFR-007: The queue workers shall support elastic scaling up to 20 instances.
    """)
    assert PITFALL not in _ids(art)
