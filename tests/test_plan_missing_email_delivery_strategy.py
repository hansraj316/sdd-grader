"""Tests for PLAN-MISSING-EMAIL-DELIVERY-STRATEGY pitfall check.

Fires when a deployment plan mentions sending email but names no email delivery
service (SES, SendGrid, Postmark, etc.) or bounce/unsubscribe handling strategy.

Sources: Kiro production-readiness (email delivery gate);
CAN-SPAM Act §7; GDPR Art. 6/7; RFC 5321; RFC 8058.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_email_delivery_strategy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-EMAIL-DELIVERY-STRATEGY"


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
    return [f.pitfall_id for f in _plan_missing_email_delivery_strategy(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------

def test_fires_sends_email_smtp():
    """Password reset email via bare SMTP with no delivery service → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The system sends a password reset email via SMTP to the user's registered address.
        The backend connects to the SMTP server on port 587.
    """)
    assert PITFALL in _ids(art)


def test_fires_welcome_email_no_provider():
    """Welcome email on account creation with no delivery strategy → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Welcome emails are sent on account creation.
        Email notifications are sent for order status updates.
    """)
    assert PITFALL in _ids(art)


def test_fires_transactional_email():
    """Transactional email mention with no ESP → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Transactional email is handled by the notification service.
        The service connects directly to the mail server.
    """)
    assert PITFALL in _ids(art)


def test_fires_email_notification():
    """Email notification vocabulary with no delivery infrastructure → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The app sends email notifications to users when their subscription expires.
    """)
    assert PITFALL in _ids(art)


def test_fires_email_confirmation():
    """Email confirmation mention with no provider → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        An email confirmation is sent after successful registration.
        The app server connects to the SMTP relay.
    """)
    assert PITFALL in _ids(art)


def test_fires_email_alert():
    """Email alert with no delivery service → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The monitoring system sends an email alert to the on-call engineer on failure.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# NO-FIRE cases
# ---------------------------------------------------------------------------

def test_no_fire_sendgrid():
    """SendGrid named → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Transactional email sent via SendGrid; DKIM configured; bounces handled via webhook.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_ses_dkim():
    """AWS SES + DKIM → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Password reset emails sent via AWS SES; DKIM and SPF record configured;
        bounce and complaint webhooks feed a suppression list.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_postmark():
    """Postmark ESP → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Transactional email via Postmark; unsubscribe link included in all marketing emails.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_mailgun():
    """Mailgun named → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Email notifications sent through Mailgun; bounce handling via Mailgun webhooks.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_unsubscribe():
    """Unsubscribe mention present → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Email confirmation sent on registration; email service includes unsubscribe
        link in footer per CAN-SPAM requirements.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_dmarc():
    """DMARC configured → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Sending email notifications via SMTP relay; DMARC policy is set to reject.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_bounce_handling():
    """Bounce handling mentioned → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Welcome email sent on signup; bounce handling is configured via SNS notifications.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_no_email_vocab():
    """Plan with no email vocabulary → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the API server to Kubernetes.
        Run database migrations before cutover.
        Enable health checks on /healthz.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_no_deploy_guard():
    """Plan with email but no deploy vocabulary → guard blocks firing."""
    art = _plan("""
        # Feature Spec

        The user receives an email notification on order completion.
        No delivery service is named here.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_spec_artifact():
    """Check only applies to plan artifacts, not spec."""
    art = _spec("""
        # Spec

        ## Deployment

        The system sends email notifications; no ESP named.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_fenced_trigger():
    """Email vocabulary inside a fenced code block → no firing."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Configure the mailer:

        ```python
        # sends email via SMTP
        smtp.send(to=user.email, subject="Welcome email")
        ```
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_resend_provider():
    """Resend ESP named → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Transactional email sent via Resend; DKIM and SPF configured.
        Email confirmation sent on registration.
    """)
    assert PITFALL not in _ids(art)


def test_fires_at_first_trigger_line():
    """Finding anchors to the first trigger line."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Provision the database cluster.
        The system sends a password reset email via SMTP.
        Email notifications are also sent for subscription renewals.
    """)
    findings = _plan_missing_email_delivery_strategy(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 6
