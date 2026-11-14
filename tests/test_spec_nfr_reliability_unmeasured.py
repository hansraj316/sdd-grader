"""Tests for SPEC-NFR-RELIABILITY-UNMEASURED pitfall check.

Fires when a normative requirement asserts reliability, fault-tolerance, or
resilience without a measurable metric (ISO/IEC 25010:2023 §4.2; Volere Canon;
QVscribe QV-104; ISO 29148 §5.2.5(i)).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_reliability_unmeasured
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-NFR-RELIABILITY-UNMEASURED"


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
    return [f.pitfall_id for f in _spec_nfr_reliability_unmeasured(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases — reliability keyword with no measurable metric
# ---------------------------------------------------------------------------

def test_fire_bare_reliable():
    """'reliable' with no metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall be reliable.
    """)
    assert PITFALL in _ids(art)


def test_fire_bare_reliability():
    """'reliability' with no metric fires."""
    art = _spec("""
        ## Non-Functional Requirements

        - NFR-002: The service shall ensure high reliability.
    """)
    assert PITFALL in _ids(art)


def test_fire_fault_tolerant():
    """'fault-tolerant' with no metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-003: The system shall be fault-tolerant.
    """)
    assert PITFALL in _ids(art)


def test_fire_fault_tolerance():
    """'fault tolerance' noun phrase with no metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-004: The platform shall provide fault tolerance.
    """)
    assert PITFALL in _ids(art)


def test_fire_resilient():
    """'resilient' with no metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-005: The service shall be resilient under load.
    """)
    assert PITFALL in _ids(art)


def test_fire_resilience():
    """'resilience' noun with no metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-006: The system shall demonstrate resilience.
    """)
    assert PITFALL in _ids(art)


def test_fire_mtbf_no_value():
    """MTBF keyword with no numeric value fires."""
    art = _spec("""
        ## Requirements

        - NFR-007: MTBF shall be acceptable.
    """)
    assert PITFALL in _ids(art)


def test_fire_multiple_lines_one_finding_each():
    """Two reliability claims without metrics → two findings."""
    art = _spec("""
        ## Requirements

        - NFR-008: The system shall be reliable.
        - NFR-009: The backend shall be fault-tolerant.
    """)
    assert _ids(art).count(PITFALL) == 2


# ---------------------------------------------------------------------------
# SILENT cases — metric present, non-normative context, or wrong artifact
# ---------------------------------------------------------------------------

def test_silent_mtbf_with_hours():
    """MTBF with hour target → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall achieve MTBF > 2000 hours.
    """)
    assert PITFALL not in _ids(art)


def test_silent_mttr_with_seconds():
    """MTTR with second target → silent."""
    art = _spec("""
        ## Requirements

        - NFR-002: The system shall recover from failure with MTTR < 30 seconds.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fault_rate_with_percent():
    """Fault rate percentage → silent."""
    art = _spec("""
        ## Requirements

        - NFR-003: The system shall be fault-tolerant with an error rate of less than 0.1%.
    """)
    assert PITFALL not in _ids(art)


def test_silent_error_rate_digit():
    """'error rate' with a digit on the same line → silent."""
    art = _spec("""
        ## Requirements

        - NFR-004: The system shall maintain a failure rate below 2 errors per million requests.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_normative_prose():
    """Non-normative prose line (no shall/must) → silent."""
    art = _spec("""
        ## Background

        The architecture is designed to be reliable and resilient across regions.
    """)
    assert PITFALL not in _ids(art)


def test_silent_in_fenced_block():
    """Reliability claim inside a fenced code block → silent."""
    art = _spec("""
        ## Requirements

        ```
        NFR-005: The system shall be fault-tolerant.
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifact → check does not apply."""
    art = _plan("NFR-001: The system shall be reliable.")
    assert PITFALL not in _ids(art)


def test_silent_reliable_with_hours():
    """'reliable' with uptime hours in same line → silent."""
    art = _spec("""
        ## Requirements

        - NFR-006: The system shall be reliable for at least 8,760 hours per year.
    """)
    assert PITFALL not in _ids(art)


def test_silent_resilient_less_than_n():
    """'less than N failures' construction → silent."""
    art = _spec("""
        ## Requirements

        - NFR-007: The system shall be resilient, tolerating no more than 3 failures per day.
    """)
    assert PITFALL not in _ids(art)
