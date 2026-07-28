"""Tests for PLAN-THIRD-PARTY-NO-FALLBACK — integration plans referencing external services with no resilience vocabulary."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_third_party_no_fallback
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-THIRD-PARTY-NO-FALLBACK"


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
    return [f.pitfall_id for f in _plan_third_party_no_fallback(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_github_api_no_resilience():
    """Plan mentions 'GitHub API' but has no retry/timeout/fallback."""
    art = _plan("""
        ## Integration

        The service calls the GitHub API to fetch repository metadata.
        Results are cached in Redis.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_oauth_provider_no_resilience():
    """Plan mentions OAuth but lacks resilience vocabulary."""
    art = _plan("""
        ## Authentication

        Users authenticate via OAuth with the identity provider.
        Access tokens are stored in the session.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_webhook_no_resilience():
    """Plan mentions webhook but has no resilience vocabulary."""
    art = _plan("""
        ## Notifications

        When a payment is processed, the payment processor sends a webhook
        to our endpoint at /api/webhooks/payment.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_third_party_no_resilience():
    """Plan mentions 'third-party' without any resilience vocabulary."""
    art = _plan("""
        ## Dependencies

        The feature depends on a third-party analytics provider for event tracking.
        Events are posted on each page view.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_external_service_no_resilience():
    """Plan mentions 'external service' without any resilience vocabulary."""
    art = _plan("""
        ## Architecture

        Data is enriched by calling an external service that provides geolocation
        lookups. Results feed into the recommendation engine.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_stripe_api_no_resilience():
    """Plan mentions 'Stripe API' with no resilience vocabulary."""
    art = _plan("""
        ## Payment Flow

        Charges are created via the Stripe API.
        The plan.md triggers charge.create on checkout submission.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_external_endpoint_no_resilience():
    """Plan mentions 'external endpoint' without resilience vocabulary."""
    art = _plan("""
        ## Steps

        Call the external endpoint to retrieve account data.
        Parse the JSON response and store it in the database.
    """)
    assert PITFALL in _ids(art)


def test_message_references_resilience():
    """Finding message mentions retry/timeout/fallback."""
    art = _plan("""
        ## Integration

        The service calls the GitHub API for repository metadata.
    """)
    findings = _plan_third_party_no_fallback(art, CATALOG)
    assert findings
    msg = findings[0].message.lower()
    assert any(word in msg for word in ("retry", "timeout", "fallback", "resilience", "circuit"))


# ------------------------------------------------------------------ silent cases

def test_silent_on_retry_present():
    """Plan that names an API and includes retry vocabulary should not fire."""
    art = _plan("""
        ## Integration

        The service calls the GitHub API to fetch repository metadata.
        Requests are retried with exponential backoff on failure.
    """)
    assert _ids(art) == []


def test_silent_on_timeout_present():
    """Plan with an API mention and timeout vocabulary should not fire."""
    art = _plan("""
        ## Integration

        Data is fetched from the Stripe API.
        All outbound calls have a 5-second timeout.
    """)
    assert _ids(art) == []


def test_silent_on_fallback_present():
    """Plan with 'fallback' vocabulary should not fire."""
    art = _plan("""
        ## Integration

        Uses the SendGrid API to send transactional emails.
        Falls back to a secondary SMTP provider if SendGrid is unavailable.
    """)
    assert _ids(art) == []


def test_silent_on_circuit_breaker():
    """Plan with 'circuit breaker' vocabulary should not fire."""
    art = _plan("""
        ## Integration

        Calls the external service for geolocation lookups.
        A circuit breaker trips after 5 consecutive failures.
    """)
    assert _ids(art) == []


def test_silent_on_graceful_degradation():
    """Plan with 'graceful degradation' should not fire."""
    art = _plan("""
        ## Payment

        Integrates with Stripe API for charging.
        On outage, the system degrades gracefully and queues charges for retry.
    """)
    assert _ids(art) == []


def test_silent_on_no_third_party_vocab():
    """Plan with no third-party vocabulary at all should not fire."""
    art = _plan("""
        ## Steps

        1. Rename the UserService class to AccountService.
        2. Update all import references.
        3. Run unit tests to confirm nothing broke.
    """)
    assert _ids(art) == []


def test_silent_on_spec_artifact():
    """Check should only apply to plan artifacts, not spec."""
    art = _spec("""
        ## Requirements

        FR-01: The system shall integrate with the GitHub API.
        FR-02: Error handling shall be provided.
    """)
    assert _ids(art) == []


def test_fires_exactly_once():
    """Finding fires at most once per artifact, even with multiple API mentions."""
    art = _plan("""
        ## Integration

        The service calls the GitHub API for commits and the Slack API for
        notifications. Results are stored in the database.
    """)
    findings = _plan_third_party_no_fallback(art, CATALOG)
    assert findings.count == findings.count  # list
    assert len([f for f in findings if f.pitfall_id == PITFALL]) == 1


def test_silent_on_error_handling_present():
    """Plan with 'error handling' vocabulary should not fire."""
    art = _plan("""
        ## Integration

        Calls the Twilio API to send SMS notifications.
        Proper error handling ensures failed deliveries are retried.
    """)
    assert _ids(art) == []
