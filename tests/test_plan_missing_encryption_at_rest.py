"""Tests for PLAN-MISSING-ENCRYPTION-AT-REST pitfall.

Fires when a plan.md has:
  - deploy vocabulary (_DEPLOY_VOCAB_RE / _DEPLOY_SECTION_RE)
  - storage vocabulary (postgres/mysql/mongodb/redis/s3/blob/object-store/database)
  - sensitivity vocabulary (user data/PII/personal data/payment/email/health/GDPR)
  - NO at-rest encryption vocabulary (kms/aes-256/sse-/tde/encrypt.*rest/etc.)

Silent when: no deploy vocab, no storage vocab, no sensitivity vocab, or
encryption-at-rest vocabulary is present.

Source: OWASP Top 10:2021 A02 (Cryptographic Failures), GDPR Art. 32,
        SOC 2 CC6.1, Kiro security production-readiness gate.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_encryption_at_rest
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-ENCRYPTION-AT-REST"


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
    return [f.pitfall_id for f in _plan_missing_encryption_at_rest(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases
# ---------------------------------------------------------------------------

def test_fires_postgres_user_data_no_encryption():
    """Plan provisions postgres for user data with no encryption-at-rest."""
    art = _plan("""
        ## Deployment Plan
        We will deploy the service to production on AWS.

        ## Database
        We use PostgreSQL 15 to store user data including email address and profile.
        The database is hosted on RDS with automated backups enabled.

        ## Authentication
        JWT tokens are used for authentication with a 24h expiry.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_s3_pii_no_encryption():
    """Plan stores PII in S3 with no at-rest encryption strategy."""
    art = _plan("""
        ## Deployment
        Deploy to AWS ECS with a load balancer in front.

        ## Storage
        User uploads (containing personal data) are stored in an S3 bucket.
        We also maintain a database for user records and payment information.

        ## Security
        All API traffic uses HTTPS/TLS 1.3 in transit.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_mongodb_gdpr_no_encryption():
    """Plan uses MongoDB for GDPR-regulated data with no encryption mention."""
    art = _plan("""
        ## Release Plan
        This release deploys the consent management service to production.

        ## Data Storage
        Consent records are stored in MongoDB. GDPR requires these records to be
        retained for 7 years and auditable on request.

        ## Infrastructure
        Kubernetes cluster on GCP with 3 replicas per service.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_mysql_hipaa_no_encryption():
    """Plan stores HIPAA health records in MySQL without encryption-at-rest."""
    art = _plan("""
        ## Deployment

        The service deploys to production via Kubernetes.

        ## Database Layer
        Patient health records are stored in MySQL 8.0. HIPAA compliance requires
        strict access controls and data integrity. We use IAM roles for DB access.

        ## Monitoring
        CloudWatch dashboards track error rates and latency.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_redis_sensitive_data_no_encryption():
    """Plan uses Redis to cache sensitive data with no encryption-at-rest."""
    art = _plan("""
        ## Deployment Plan

        Deploy the caching layer to production AWS environment.

        ## Caching
        Redis is used to cache session data that includes sensitive data such as
        credit card tokens and personally identifiable information.

        ## Networking
        All services communicate over private VPC subnets.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_azure_blob_personal_data_no_encryption():
    """Plan uses Azure blob storage for personal data without encryption strategy."""
    art = _plan("""
        ## Release Plan
        Deploy the document management service to Azure.

        ## Storage
        Documents containing personal data (employee records, tax forms)
        are uploaded to Azure Blob storage containers.

        ## Access Control
        Role-based access control (RBAC) restricts document access to authorised users.
    """)
    assert _ids(art) == [PITFALL]


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------

def test_silent_when_kms_present():
    """Plan mentions KMS — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy to AWS ECS with RDS PostgreSQL.

        ## Data Storage
        User data (email address, phone number) is stored in PostgreSQL.
        All RDS volumes are encrypted using AWS KMS (AES-256 CMK).
        The KMS key is rotated annually. Backups inherit the same key.
    """)
    assert _ids(art) == []


def test_silent_when_aes256_present():
    """Plan explicitly uses AES-256 encryption — silenced."""
    art = _plan("""
        ## Deployment

        The service deploys via Helm to a Kubernetes cluster.

        ## Database
        PostgreSQL stores personal data including PII and payment details.
        All database volumes use AES-256 encryption at rest via RDS encryption.

        ## Networking
        Services communicate over mTLS within the cluster.
    """)
    assert _ids(art) == []


def test_silent_when_sse_s3_present():
    """Plan uses SSE-S3 for object storage — silenced."""
    art = _plan("""
        ## Release
        Deploy the file upload service to production.

        ## Storage
        User files are stored in S3. Sensitive data (personal data, GDPR scope)
        is protected via SSE-S3 with AES-256 server-side encryption applied
        automatically to all objects.
    """)
    assert _ids(art) == []


def test_silent_when_tde_present():
    """Plan uses TDE (transparent data encryption) — silenced."""
    art = _plan("""
        ## Deployment Plan

        Deploy to AWS production environment.

        ## Database
        Patient health records (HIPAA) are stored in MySQL. Transparent Data
        Encryption (TDE) is enabled on all database volumes. Keys are managed
        via AWS KMS.
    """)
    assert _ids(art) == []


def test_silent_no_sensitivity_vocab():
    """Plan has storage but no sensitivity vocabulary — silent."""
    art = _plan("""
        ## Deployment Plan

        Deploy to production ECS.

        ## Database
        PostgreSQL 15 is used to store application configuration and feature flags.
        No user-facing data is stored in this database. Read replicas are provisioned
        in each availability zone.
    """)
    assert _ids(art) == []


def test_silent_no_storage_vocab():
    """Plan has sensitivity vocab but no storage vocabulary — silent."""
    art = _plan("""
        ## Deployment Plan

        Deploy the authentication service to production.

        ## GDPR Compliance
        The service processes personal data and must comply with GDPR Art. 32.
        All API calls are authenticated with OAuth 2.0 and transport uses TLS 1.3.

        ## Logging
        Logs are shipped to Splunk with a 30-day retention policy.
    """)
    assert _ids(art) == []


def test_silent_no_deploy_vocab():
    """No deployment vocabulary — silent."""
    art = _plan("""
        # Notes

        This document describes the data model for user records including personal data.
        A PostgreSQL database stores email addresses and user profiles.
    """)
    assert _ids(art) == []


def test_silent_spec_artifact():
    """Spec artifact — check is plan-only."""
    art = _spec("""
        ## Deployment Plan
        PostgreSQL stores personal data (PII). No encryption strategy is specified.
    """)
    assert _ids(art) == []


def test_silent_encrypt_at_rest_phrase():
    """Plan explicitly says 'encrypt at rest' — silenced."""
    art = _plan("""
        ## Deployment

        Deploy the service to production Kubernetes cluster.

        ## Database
        User data (including GDPR personal data) is stored in PostgreSQL.
        All database volumes are encrypted at rest using AES-256 managed by the
        platform's built-in encryption service.
    """)
    assert _ids(art) == []


def test_silent_disk_encryption():
    """Plan uses disk encryption — silenced."""
    art = _plan("""
        ## Production Deployment

        Deploy to GCP with GKE.

        ## Storage
        User profile data (personal data, email address) is stored in Cloud SQL (MySQL).
        All persistent disks use disk encryption with customer-managed keys via
        GCP Cloud KMS.
    """)
    assert _ids(art) == []
