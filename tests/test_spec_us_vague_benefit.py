"""Tests for SPEC-US-VAGUE-BENEFIT pitfall.

A user story whose 'so that' clause uses vague, unmeasurable benefit language
(e.g., 'more efficiently', 'better', 'seamlessly') without a concrete metric
fires this check. A digit or '%' on the same clause silences it.

Source: INVEST Valuable criterion, Canon Volere Fit Criterion,
        ISO/IEC/IEEE 29148:2018 §5.2.5(a), IBM RQA Clarity checklist.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_us_vague_benefit
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-US-VAGUE-BENEFIT"


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
    return [f.pitfall_id for f in _spec_us_vague_benefit(art, CATALOG)]


# ── fires cases ───────────────────────────────────────────────────────────────

def test_fires_more_efficiently():
    art = _spec("""
        ## Requirements
        - As an accountant I want bulk-import so that I can work more efficiently.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_better():
    art = _spec("""
        ## Requirements
        - As a manager I want dashboards so that I can better understand performance.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_seamlessly():
    art = _spec("""
        ## Requirements
        As a customer I want notifications so that I can seamlessly track orders.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_more_easily():
    art = _spec("""
        ## Requirements
        As a developer I want auto-complete so that I can code more easily.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_improve():
    art = _spec("""
        ## Requirements
        As a sales rep I want CRM filters so that I can improve my pipeline visibility.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_multiple_stories_one_finding():
    art = _spec("""
        ## Requirements
        As an accountant I want bulk-import so that I can work more efficiently.
        As a manager I want dashboards so that I can better understand KPIs.
    """)
    findings = _spec_us_vague_benefit(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_fires_enhance():
    art = _spec("""
        ## Requirements
        As a user I want search so that I can enhance my experience.
    """)
    assert _ids(art) == [PITFALL]


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_concrete_metric_digit():
    """A concrete number on the clause silences the check."""
    art = _spec("""
        ## Requirements
        As an accountant I want bulk-import so that I can process 200 invoices per hour.
    """)
    assert _ids(art) == []


def test_silent_percent():
    """A percentage on the clause silences the check."""
    art = _spec("""
        ## Requirements
        As an admin I want audit logs so that error rates drop by 40%.
    """)
    assert _ids(art) == []


def test_silent_no_so_that():
    """A story with no 'so that' clause is handled by SPEC-STORY-NO-BENEFIT, not this check."""
    art = _spec("""
        ## Requirements
        As a customer I want notifications.
    """)
    assert _ids(art) == []


def test_silent_no_stories_at_all():
    """No story opener = no check fires."""
    art = _spec("""
        ## Requirements
        FR-001: The system shall export data.
        FR-002: The system shall validate input.
    """)
    assert _ids(art) == []


def test_silent_specific_benefit():
    """Non-vague benefit: meaningful description without matching tokens."""
    art = _spec("""
        ## Requirements
        As a payroll manager I want bulk export so that quarterly tax filings complete in under 5 minutes.
    """)
    assert _ids(art) == []


def test_silent_plan_artifact():
    """Plan artifacts are not subject to this check."""
    art = _plan("""
        ## Deployment
        Deploy to production.
        As a user I want notifications so that I can work more efficiently.
    """)
    assert _ids(art) == []


def test_silent_fenced_block():
    """Story inside a fenced code block is not checked."""
    art = _spec("""
        ## Requirements
        FR-001: The system shall allow export.

        ```
        As a user I want export so that I can work more efficiently.
        ```
    """)
    assert _ids(art) == []
