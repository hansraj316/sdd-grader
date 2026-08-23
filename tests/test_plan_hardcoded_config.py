"""Tests for PLAN-HARDCODED-CONFIG pitfall.

Detects non-fenced plan lines that contain either:
  (A) a literal IPv4:port pattern (e.g., 192.168.1.50:5432), or
  (B) a credential assignment not masked by a placeholder
      (e.g., password=Secr3t, api_key=abc123).

Fenced blocks and sections titled 'Example'/'Sample'/'Reference' are excluded.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_hardcoded_config
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-HARDCODED-CONFIG"


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
    return [f.pitfall_id for f in _plan_hardcoded_config(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases (≥ 5)
# ---------------------------------------------------------------------------

def test_ipv4_port_prose_fires():
    """IPv4:port literal on a plain prose line fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Connect to the database at 192.168.1.50:5432 and run migrations.
    """)
    assert PITFALL in _ids(art)


def test_private_ip_high_port_fires():
    """10.x.x.x:port on a prose line fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The cache layer lives at 10.0.0.8:6379; flush it before the migration.
    """)
    assert PITFALL in _ids(art)


def test_password_credential_fires():
    """password= with a real value fires."""
    art = _plan("""
        # Deployment Plan

        ## Database Setup

        Connect with: password=Secr3tPa55!
    """)
    assert PITFALL in _ids(art)


def test_api_key_credential_fires():
    """api_key= with a non-placeholder value fires."""
    art = _plan("""
        # Deployment Plan

        ## Integrations

        Set api_key=xK9mZ3tQpR7 in the service config.
    """)
    assert PITFALL in _ids(art)


def test_private_key_credential_fires():
    """private_key= with a value fires."""
    art = _plan("""
        # Deployment Plan

        ## TLS Setup

        Set private_key=MIIG in the config file.
    """)
    assert PITFALL in _ids(art)


def test_db_password_credential_fires():
    """db_password= with a non-placeholder value fires."""
    art = _plan("""
        # Deployment Plan

        ## Config

        Use db_password=my_db_secret for the staging connection.
    """)
    assert PITFALL in _ids(art)


def test_localhost_ipv4_port_fires():
    """127.0.0.1:port is still a hard-coded address and fires."""
    art = _plan("""
        # Deployment Plan

        ## Local Bootstrap

        The health-check hits 127.0.0.1:8080/health after start-up.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases (≥ 7)
# ---------------------------------------------------------------------------

def test_no_config_leakage_silent():
    """Plan with no hard-coded config is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Connect using DATABASE_URL from the secrets manager.
        Credentials are injected at deploy time via environment variables.
    """)
    assert PITFALL not in _ids(art)


def test_fenced_ipv4_silent():
    """IPv4:port inside a fenced code block is not flagged."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        ```bash
        psql 10.0.1.15:5432 -U admin
        ```

        Use environment variables for real deployments.
    """)
    assert PITFALL not in _ids(art)


def test_fenced_credential_silent():
    """Credential inside a fenced block is not flagged."""
    art = _plan("""
        # Deployment Plan

        ## Setup

        ```env
        password=example_password
        ```

        Replace the value with the real secret from Vault.
    """)
    assert PITFALL not in _ids(art)


def test_placeholder_masked_password_silent():
    """password=***** (masked placeholder) is not flagged."""
    art = _plan("""
        # Deployment Plan

        ## Config

        The DB connection uses password=***** (injected from Vault).
    """)
    assert PITFALL not in _ids(art)


def test_env_var_reference_silent():
    """Credential referenced as ${SECRET} env-var syntax is not flagged."""
    art = _plan("""
        # Deployment Plan

        ## Config

        Set api_key=${API_KEY} in the environment.
    """)
    assert PITFALL not in _ids(art)


def test_angle_bracket_placeholder_silent():
    """password=<YOUR_PASSWORD> template syntax is not flagged."""
    art = _plan("""
        # Deployment Plan

        ## Config

        Set password=<YOUR_DB_PASSWORD> in the .env file before running migrations.
    """)
    assert PITFALL not in _ids(art)


def test_example_section_ipv4_silent():
    """IPv4:port in an 'Example' section is not flagged."""
    art = _plan("""
        # Deployment Plan

        ## Example Connection String

        In development you might connect to 192.168.50.10:3306.

        ## Deployment

        Use DATABASE_URL from the secrets manager.
    """)
    assert PITFALL not in _ids(art)


def test_plain_ipv4_no_port_silent():
    """Plain IPv4 address without a port does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Network

        Traffic originates from 203.0.113.1 (NAT gateway IP).
    """)
    assert PITFALL not in _ids(art)


def test_spec_artifact_silent():
    """Check does not fire on a spec artifact (plans only)."""
    raw = textwrap.dedent("""
        # Feature Spec

        ## Requirements

        Connect to 10.0.0.1:5432 as referenced in NFR-01.
    """).strip()
    art = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in [f.pitfall_id for f in _plan_hardcoded_config(art, CATALOG)]


def test_finding_line_anchored_to_first_hit():
    """The finding is anchored to the first offending line."""
    art = _plan("""
        # Plan

        ## Deploy

        Use DATABASE_URL for the connection string.
        Connect to the replica at 10.10.10.5:5432 for read queries.
        Also api_key=leaked_key on this line.
    """)
    findings = _plan_hardcoded_config(art, CATALOG)
    hits = [f for f in findings if f.pitfall_id == PITFALL]
    assert hits, "Expected at least one finding"
    assert hits[0].line is not None
    assert hits[0].line >= 1
