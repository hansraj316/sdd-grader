"""Tests for PLAN-NO-FEATURE-FLAG pitfall.

Fires when a plan.md with deployment vocabulary introduces a user-visible
feature or capability but has no phased-rollout or feature-flag strategy
(Amazon Kiro production-readiness, Tessl spec-first).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_feature_flag
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-FEATURE-FLAG"


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
    return [f.pitfall_id for f in _plan_no_feature_flag(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases
# ---------------------------------------------------------------------------

def test_fires_new_feature_no_flag():
    """Plan mentions deploying a new feature with no flag strategy."""
    art = _plan("""
        ## Deployment Plan
        We will deploy this change to production next Friday.
        A new feature will be introduced in this release for user preferences.
        No rollout strategy is specified.
    """)
    assert PITFALL in _ids(art)


def test_fires_launch_keyword():
    """Plan uses 'launch' without any feature-flag vocabulary."""
    art = _plan("""
        ## Deployment Plan
        The payment module will be deployed to production.
        We will launch the new checkout flow for all users simultaneously.
    """)
    assert PITFALL in _ids(art)


def test_fires_rollout_noun_no_strategy():
    """Plan mentions 'rollout' noun but no feature-flag vocabulary."""
    art = _plan("""
        ## Release Plan
        Staging deployment happens first.
        The rollout of the new dashboard will go live on Monday.
    """)
    assert PITFALL in _ids(art)


def test_fires_new_capability_no_flag():
    """Plan introduces a new capability without a feature-gate mechanism."""
    art = _plan("""
        ## Deployment
        Release to production on 2026-09-01.
        A new capability for bulk exports will be included in this release.
    """)
    assert PITFALL in _ids(art)


def test_fires_new_endpoint_no_flag():
    """New endpoint being shipped with no phased rollout mention."""
    art = _plan("""
        ## Release Checklist
        Staging to production deploy planned.
        A new endpoint /v2/reports is being shipped to production.
    """)
    assert PITFALL in _ids(art)


def test_fires_introduce_no_flag():
    """'Introducing' a feature with no rollout mitigation."""
    art = _plan("""
        ## Deployment Plan
        Deploy to production environment.
        We are introducing a new analytics module in this release.
    """)
    assert PITFALL in _ids(art)


def test_fires_shipping_new_feature():
    """'shipping the new feature' pattern without feature-flag."""
    art = _plan("""
        ## Deployment
        Production release scheduled.
        We are shipping the new feature for real-time notifications.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------

def test_silent_feature_flag_present():
    """Feature flag mentioned — check is silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploying to production.
        A new feature will be introduced behind a feature flag (analytics_v2).
        The flag is off by default and toggled per user cohort.
    """)
    assert PITFALL not in _ids(art)


def test_silent_canary_present():
    """Canary release mentioned — check is silenced."""
    art = _plan("""
        ## Deployment Plan
        Production deploy scheduled.
        Launching the new payment flow via a canary release to 5% of traffic.
    """)
    assert PITFALL not in _ids(art)


def test_silent_blue_green():
    """Blue-green deployment mentioned — check is silenced."""
    art = _plan("""
        ## Release Plan
        Staging: new feature release.
        Production: blue-green deployment of the new checkout feature.
    """)
    assert PITFALL not in _ids(art)


def test_silent_phased_rollout():
    """'phased rollout' mentioned — check is silenced."""
    art = _plan("""
        ## Deployment
        Deploy to production.
        We will introduce a new capability with a phased rollout over 4 weeks.
    """)
    assert PITFALL not in _ids(art)


def test_silent_kill_switch():
    """Kill switch mentioned — check is silenced."""
    art = _plan("""
        ## Deployment Plan
        Production release.
        Launching new endpoint with a kill switch if errors spike.
    """)
    assert PITFALL not in _ids(art)


def test_silent_percentage_of_users():
    """'percentage of users' traffic-split silences the check."""
    art = _plan("""
        ## Deployment Plan
        Production deploy on Friday.
        New feature rollout to 10 percentage of users initially.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """No deployment vocabulary — guard prevents false positive."""
    art = _plan("""
        ## Overview
        We plan to introduce a new feature in Q4.
        The team will work on the new capability over the next sprint.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_feature_launch():
    """Deploy vocab present but no feature-launch language."""
    art = _plan("""
        ## Deployment Plan
        Deploy to production on Friday.
        This is a bug-fix release with no new features.
    """)
    assert PITFALL not in _ids(art)


def test_silent_in_fenced_block():
    """Feature-launch vocab only inside a fenced code block — not a real plan statement."""
    art = _plan("""
        ## Deployment Plan
        Deploy to production.
        ```
        # we will launch the new feature here
        rollout: "none"
        ```
        No actual new features in this release.
    """)
    assert PITFALL not in _ids(art)


def test_silent_feature_toggle():
    """'feature toggle' vocabulary silences the check."""
    art = _plan("""
        ## Deployment Plan
        Production staging deploy.
        Introducing a new dashboard feature behind a feature toggle.
    """)
    assert PITFALL not in _ids(art)


def test_silent_dark_launch():
    """Dark launch vocabulary silences the check."""
    art = _plan("""
        ## Release
        Deploy to production.
        The new capability will be dark-launched for 2 weeks before full exposure.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """PLAN-NO-FEATURE-FLAG must not fire on spec artifacts."""
    art = _spec("""
        ## Requirements
        We will introduce a new feature for bulk exports.
        Deploy to production next sprint.
    """)
    assert PITFALL not in _ids(art)


def test_finding_line_is_feature_launch_line():
    """Finding anchored at the feature-launch line, not line 1."""
    art = _plan("""
        ## Deployment Plan
        Deploy to production.
        Nothing to flag here.
        We will launch the new analytics dashboard to all users.
        No rollout mitigation is in place.
    """)
    findings = _plan_no_feature_flag(art, CATALOG)
    hits = [f for f in findings if f.pitfall_id == PITFALL]
    assert hits, "Expected a finding"
    assert hits[0].line == 4, f"Expected line 4 (after strip/dedent), got {hits[0].line}"
