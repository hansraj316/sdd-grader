"""Tests for PLAN-MISSING-AUDIT-LOG pitfall.

Fires when a plan.md with deployment vocabulary AND privileged/admin operation
vocabulary (admin dashboard/panel/console, role assignment/management, user
management, account lifecycle, password reset, bulk data operations, privileged
access) has no audit-log or audit-trail strategy anywhere in the non-fenced text.

Source: ISO 27001:2022 A.12.4.1 (Event Logging), GDPR Art. 30 (Records of
        Processing Activities), OWASP Top 10:2021 A09, Kiro production-readiness
        audit-logging gate.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_audit_log
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-AUDIT-LOG"


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
    return [f.pitfall_id for f in _plan_missing_audit_log(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — privileged op vocab + deploy vocab, no audit-log silence
# ---------------------------------------------------------------------------

def test_fires_admin_dashboard_no_audit():
    """Plan describes admin dashboard with no audit log mention."""
    art = _plan("""
        ## Deployment Plan
        We will deploy the service to the production environment.
        The admin dashboard allows super-users to manage tenants and configurations.
        Role-based access will control which sections are visible.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_role_assignment_no_audit():
    """Plan describes role assignment with no audit log strategy."""
    art = _plan("""
        ## Production Release
        Release the IAM service to production this sprint.
        Administrators can perform role assignment for any user in the system.
        Permissions cascade from the assigned role automatically.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_user_management_no_audit():
    """Plan describes user management with no audit log."""
    art = _plan("""
        ## Deployment
        Deploy the platform admin service to staging and production.
        The user management interface lets admins create, suspend, and delete accounts.
        Changes take effect immediately without confirmation emails.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_password_reset_no_audit():
    """Plan describes password reset flow with no audit log."""
    art = _plan("""
        ## Release Plan
        Ship the authentication service to production.
        The password reset flow is triggered by the user via the forgot-password link.
        Tokens expire after 24 hours for security.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_bulk_delete_no_audit():
    """Plan describes bulk delete operation with no audit log."""
    art = _plan("""
        ## Deployment Plan
        Deploy the data-lifecycle microservice to production.
        Administrators can trigger bulk deletion of user records that have been
        inactive for more than two years via an admin console endpoint.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_account_deletion_no_audit():
    """Plan describes account deletion with no audit log strategy."""
    art = _plan("""
        ## Production Deployment
        Roll out the user-lifecycle service to production.
        Account deletion is performed immediately on admin request with no soft-delete.
        Deleted records are purged from the primary database within 30 days.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_permission_management_no_audit():
    """Plan describes permission management with no audit trail."""
    art = _plan("""
        ## Release
        Deploy the RBAC service to the production environment.
        The service provides permission management for all API resources.
        Admins can grant or revoke permissions on a per-user basis.
    """)
    assert _ids(art) == [PITFALL]


# ---------------------------------------------------------------------------
# Silent cases — audit-log vocab present or guard not met
# ---------------------------------------------------------------------------

def test_silent_when_audit_log_present():
    """'audit log' in the plan silences the check."""
    art = _plan("""
        ## Deployment Plan
        Deploy the admin service to production.
        The admin dashboard allows role assignment and user management.
        All admin actions are written to the audit log table (actor_id, action,
        target_id, timestamp) and shipped to the SIEM for 90-day retention.
    """)
    assert _ids(art) == []


def test_silent_when_audit_trail_present():
    """'audit trail' silences the check."""
    art = _plan("""
        ## Production Release
        Release the IAM service to production.
        Administrators can perform role assignment and permission management.
        An immutable audit trail is maintained for all privileged operations.
    """)
    assert _ids(art) == []


def test_silent_when_cloudtrail_present():
    """'cloudtrail' silences the check."""
    art = _plan("""
        ## Deployment Plan
        Deploy the admin console to the AWS production environment.
        The admin console enables account creation and password reset.
        All API calls are recorded via AWS CloudTrail for compliance.
    """)
    assert _ids(art) == []


def test_silent_when_activity_log_present():
    """'activity log' silences the check."""
    art = _plan("""
        ## Release Plan
        Ship the user management portal to production.
        The user management service lets super-admins create and delete accounts.
        Every action is written to the activity log with full request context.
    """)
    assert _ids(art) == []


def test_silent_when_auditing_present():
    """'auditing' silences the check."""
    art = _plan("""
        ## Production Deployment
        Deploy the bulk export service to production.
        Bulk export operations are available to admin users only.
        The service uses database-level auditing to record every export event.
    """)
    assert _ids(art) == []


def test_silent_when_no_privileged_op_vocab():
    """Plan with deploy vocab but no admin/privileged op — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the data pipeline service to production.
        The service reads from Kafka topics and writes to S3.
        Monitoring is configured via CloudWatch alarms.
    """)
    assert _ids(art) == []


def test_silent_when_no_deploy_vocab():
    """Plan with admin vocab but no deploy guard — should not fire."""
    art = _plan("""
        ## Architecture Overview
        The admin dashboard will provide role assignment capabilities.
        This document describes the system design only; operational concerns are
        covered in a separate document.
    """)
    assert _ids(art) == []


def test_silent_on_spec_artifact():
    """PLAN-MISSING-AUDIT-LOG must not fire on spec artifacts."""
    art = _spec("""
        ## Deployment Plan
        Deploy the admin service to production.
        The admin dashboard enables user management.
    """)
    assert _ids(art) == []


def test_silent_when_trigger_in_fenced_block():
    """Admin op vocab only inside a fenced block should not trigger the check."""
    art = _plan("""
        ## Deployment Plan
        Deploy the service to production this week.
        No admin operations are exposed in this release.

        ```markdown
        # Future feature: admin dashboard with role assignment
        The admin console will allow user management and bulk deletion.
        ```
    """)
    assert _ids(art) == []


def test_silent_when_event_log_present():
    """'event log' silences the check."""
    art = _plan("""
        ## Production Release
        Deploy the IAM service to production.
        Role assignment and permission changes are available to admins.
        All state changes are written to the event log (Kafka topic: iam.events).
    """)
    assert _ids(art) == []
