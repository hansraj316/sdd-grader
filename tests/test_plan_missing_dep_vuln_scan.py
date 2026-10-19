"""Tests for PLAN-MISSING-DEPENDENCY-VULNERABILITY-SCAN pitfall."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_dependency_vulnerability_scan
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL_ID = "PLAN-MISSING-DEPENDENCY-VULNERABILITY-SCAN"


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _findings(raw: str):
    art = _plan(raw)
    return _plan_missing_dependency_vulnerability_scan(art, CATALOG)


# ---------------------------------------------------------------------------
# Fire cases
# ---------------------------------------------------------------------------

def test_fire_npm_install_no_scan():
    """npm install present, no scanning vocabulary → fires."""
    md = """\
    ## Deployment

    We deploy to the production server.
    Run npm install to install dependencies.
    """
    assert _findings(md), "Should fire: npm install with no vuln scan"


def test_fire_pip_install_no_scan():
    """pip install present, no scanning vocabulary → fires."""
    md = """\
    ## Deployment Steps

    Deploy the service to the production environment.
    pip install -r requirements.txt
    """
    assert _findings(md), "Should fire: pip install with no vuln scan"


def test_fire_yarn_add_no_scan():
    """yarn add present, no scanning vocabulary → fires."""
    md = """\
    ## Release Process

    Deploy the application.
    Run yarn add react react-dom to install front-end dependencies.
    """
    assert _findings(md), "Should fire: yarn add with no vuln scan"


def test_fire_new_package_no_scan():
    """Generic 'new package' phrase, no scanning vocabulary → fires."""
    md = """\
    ## Deployment

    Deploy microservices to the staging environment.
    We're adding a new package for PDF generation.
    """
    assert _findings(md), "Should fire: new package with no vuln scan"


def test_fire_apt_get_install_no_scan():
    """apt-get install present, no scanning vocabulary → fires."""
    md = """\
    ## Infrastructure Deployment

    Deploy services to production.
    apt-get install libssl-dev libffi-dev to install system dependencies.
    """
    assert _findings(md), "Should fire: apt-get install with no vuln scan"


def test_fire_add_dependency_no_scan():
    """add dependency phrasing, no scanning vocabulary → fires."""
    md = """\
    ## Deployment

    Release to production environment.
    We need to add a new dependency for image processing.
    """
    assert _findings(md), "Should fire: add dependency with no vuln scan"


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------

def test_silent_snyk_present():
    """npm install present but snyk mentioned → silent."""
    md = """\
    ## Deployment

    Deploy to production.
    npm install to install all packages.
    Run snyk test to scan for vulnerabilities before deploying.
    """
    assert not _findings(md), "Should be silent: snyk mentioned"


def test_silent_npm_audit_present():
    """pip install present but npm audit mentioned → silent."""
    md = """\
    ## Deployment

    Deploy to production environment.
    pip install -r requirements.txt
    Run npm audit to check for known vulnerabilities.
    """
    assert not _findings(md), "Should be silent: npm audit mentioned"


def test_silent_dependabot_present():
    """yarn add present but dependabot mentioned → silent."""
    md = """\
    ## Release Process

    Deploy the service to production.
    yarn add @mui/material
    Dependabot is configured to monitor dependencies weekly.
    """
    assert not _findings(md), "Should be silent: dependabot mentioned"


def test_silent_trivy_present():
    """npm install present but trivy mentioned → silent."""
    md = """\
    ## Deployment Pipeline

    Deploy to staging environment.
    npm install to set up the node environment.
    Use trivy to scan container images for vulnerabilities.
    """
    assert not _findings(md), "Should be silent: trivy mentioned"


def test_silent_sbom_present():
    """pip install but SBOM mentioned → silent."""
    md = """\
    ## Deployment

    Deploy to production.
    pip install -r requirements.txt
    Generate an SBOM as part of the release artifact.
    """
    assert not _findings(md), "Should be silent: SBOM mentioned"


def test_silent_no_deploy_vocab():
    """npm install present but no deployment vocabulary → silent (no deploy guard)."""
    md = """\
    ## Local Development Setup

    npm install to set up the project.
    Useful for local testing only.
    """
    assert not _findings(md), "Should be silent: no deploy vocabulary"


def test_silent_no_package_vocab():
    """Deploy vocab present but no new-package vocabulary → silent."""
    md = """\
    ## Deployment

    Deploy to production environment.
    Configure the server and set environment variables.
    """
    assert not _findings(md), "Should be silent: no package install vocabulary"


def test_silent_fenced_install():
    """npm install inside fenced code block → trigger excluded → silent."""
    md = """\
    ## Deployment

    Deploy to production.

    ```bash
    npm install
    ```

    No vulnerability scanning strategy needed here.
    """
    assert not _findings(md), "Should be silent: npm install only in fenced block"
