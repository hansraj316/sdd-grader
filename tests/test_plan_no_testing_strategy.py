"""Tests for PLAN-NO-TESTING-STRATEGY — multi-phase plans with no testing vocabulary."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_testing_strategy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-TESTING-STRATEGY"


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _plan_no_testing_strategy(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_two_phase_headings_no_testing():
    """Plan has Phase 1 and Phase 2 headings but no testing mention — fires."""
    art = _plan("""
        ## Phase 1: Implement API

        Build the REST endpoints.

        ## Phase 2: Deploy

        Ship the service to production.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_step_headings_no_testing():
    """Plan uses Step headings instead of Phase — still fires."""
    art = _plan("""
        ## Step 1: Database Migration

        Run the migration scripts.

        ## Step 2: Service Update

        Deploy the updated service container.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_three_phases_no_testing():
    """Three Phase headings, no testing vocabulary — fires exactly once."""
    art = _plan("""
        ## Phase 1: Design

        Create the architecture diagram.

        ## Phase 2: Build

        Implement the feature modules.

        ## Phase 3: Deploy

        Release to production environment.
    """)
    findings = _plan_no_testing_strategy(art, CATALOG)
    assert len(findings) == 1
    assert PITFALL in [f.pitfall_id for f in findings]


def test_fires_message_content():
    """Finding message mentions testing or verification."""
    art = _plan("""
        ## Phase 1: Setup

        Configure the environment.

        ## Phase 2: Implementation

        Write the code.
    """)
    findings = _plan_no_testing_strategy(art, CATALOG)
    assert findings
    assert "testing" in findings[0].message.lower() or "verification" in findings[0].message.lower()


# ------------------------------------------------------------------ silent cases

def test_silent_when_test_keyword_present():
    """'tests' anywhere in the document silences the check."""
    art = _plan("""
        ## Phase 1: Build

        Implement the feature.

        ## Phase 2: Verify

        Run unit tests and integration tests.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_testing_keyword_present():
    """'testing' mentioned in passing — check is silent."""
    art = _plan("""
        ## Phase 1: Development

        Code the module.

        ## Phase 2: Deployment

        Ship to prod. Manual testing performed before release.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_coverage_mentioned():
    """'coverage' target satisfies the testing vocabulary check."""
    art = _plan("""
        ## Phase 1: Implement

        Build the endpoints.

        ## Phase 2: Release

        Target 80% coverage before merging.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_validate_mentioned():
    """'validate' appears — no finding."""
    art = _plan("""
        ## Phase 1: Build

        Implement the module.

        ## Phase 2: Ship

        Validate the output before deployment.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_verify_mentioned():
    """'verify' appears — no finding."""
    art = _plan("""
        ## Phase 1: Setup

        Install dependencies.

        ## Phase 2: Migrate

        Verify the database schema is correct after migration.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_single_phase_heading():
    """Only one Phase heading — guard not met, no finding."""
    art = _plan("""
        ## Phase 1: Deploy

        Run the release script.

        ## Background

        This replaces the legacy service.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_no_phase_headings():
    """Plan has no Phase or Step headings — check does not fire."""
    art = _plan("""
        ## Implementation

        Build the module.

        ## Deployment

        Ship to production.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_spec_artifact():
    """Check only applies to plan.md — spec artifacts are skipped."""
    art = _spec("""
        ## Phase 1: Feature Description

        Describe what the feature does.

        ## Phase 2: Acceptance

        Define acceptance criteria.
    """)
    assert PITFALL not in _ids(art)


def test_fires_once_not_multiple_times():
    """Even with many phases and no testing, fires exactly once."""
    phases = "\n\n".join(
        f"## Phase {i}: Task {i}\n\nDo work." for i in range(1, 6)
    )
    art = _plan(phases)
    findings = _plan_no_testing_strategy(art, CATALOG)
    assert findings.count(findings[0]) == 1 if findings else True
    assert len(findings) == 1
