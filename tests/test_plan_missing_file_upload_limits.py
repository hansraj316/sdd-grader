"""Tests for PLAN-MISSING-FILE-UPLOAD-LIMITS pitfall check.

Fires when a deployment plan mentions file-upload functionality but has no
file size limits, allowed MIME types, or virus/malware scanning strategy.

Sources: OWASP Unrestricted File Upload (OTG-BUSLOGIC-008);
OWASP A04:2021 Insecure Design; Kiro production-readiness security checklist.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_file_upload_limits
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-FILE-UPLOAD-LIMITS"


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
    return [f.pitfall_id for f in _plan_missing_file_upload_limits(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------

def test_fires_file_upload_no_limits():
    """Plan mentions file upload with no size/type/scan constraints."""
    art = _plan("""
        ## Deployment

        Users can submit a file upload via POST /upload.
        Files are stored in S3 under the /uploads/ prefix.
    """)
    assert PITFALL in _ids(art)


def test_fires_multipart_form_data_no_constraints():
    """Plan mentions multipart/form-data with no constraints."""
    art = _plan("""
        ## Deployment Plan

        The service accepts document submissions via multipart/form-data.
        Files are stored in the database as BLOBs.
    """)
    assert PITFALL in _ids(art)


def test_fires_image_upload_no_limits():
    """Plan mentions image upload with no constraints."""
    art = _plan("""
        ## Deployment

        Administrators can perform image upload to update product photos.
        Images are stored in GCS and served via the product API.
    """)
    assert PITFALL in _ids(art)


def test_fires_attachment_upload_no_limits():
    """Plan mentions attachment upload with no constraints."""
    art = _plan("""
        ## Deployment Plan

        Support tickets allow attachment upload for screenshots and logs.
        Attachments are linked to tickets in the database.
    """)
    assert PITFALL in _ids(art)


def test_fires_stores_uploads_no_constraints():
    """Plan mentions storing uploads with no constraints."""
    art = _plan("""
        ## Deployment

        The API stores uploads in a dedicated S3 bucket.
        No retention policy has been defined.
    """)
    assert PITFALL in _ids(art)


def test_fires_upload_endpoint_no_constraints():
    """Plan mentions upload endpoint with no constraints."""
    art = _plan("""
        ## Deployment Plan

        The upload endpoint accepts files and returns a signed URL for download.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------

def test_silent_file_size_limit_mentioned():
    """Max file size mentioned — no finding."""
    art = _plan("""
        ## Deployment

        Users can upload profile images. Max file size: 10 MB enforced at gateway.
    """)
    assert PITFALL not in _ids(art)


def test_silent_allowed_types_mentioned():
    """Allowed file types mentioned — no finding."""
    art = _plan("""
        ## Deployment Plan

        File upload endpoint: allowed file types are image/jpeg and image/png only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_virus_scan_mentioned():
    """Virus scan mentioned — no finding."""
    art = _plan("""
        ## Deployment

        Document uploads are accepted; files undergo virus scan via ClamAV on ingest.
    """)
    assert PITFALL not in _ids(art)


def test_silent_clamav_mentioned():
    """ClamAV mentioned — no finding."""
    art = _plan("""
        ## Deployment Plan

        Profile image uploads stored in S3; ClamAV scans each object on upload.
    """)
    assert PITFALL not in _ids(art)


def test_silent_mime_type_mentioned():
    """MIME type validation mentioned — no finding."""
    art = _plan("""
        ## Deployment

        The upload API validates mime type on the server before storing the file.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_upload_vocab():
    """Plan has no file-upload vocabulary — no finding."""
    art = _plan("""
        ## Deployment Plan

        The API exposes GET /products and POST /orders. No file handling.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_guard():
    """Plan with no deploy vocabulary — deploy guard blocks the check."""
    art = _plan("""
        Users upload profile images via the web UI.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block_excluded():
    """Upload vocabulary inside fenced code block is excluded."""
    art = _plan("""
        ## Deployment Plan

        ```
        POST /upload — accepts multipart/form-data file upload
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_heading_line_excluded():
    """Upload vocabulary on a heading line is excluded; body has size limit."""
    art = _plan("""
        ## Deployment Plan

        ### File Upload

        Files are stored securely with max size: 10 MB limit enforced.
    """)
    assert PITFALL not in _ids(art)


def test_silent_magic_byte_mentioned():
    """Magic-byte inspection mentioned — no finding."""
    art = _plan("""
        ## Deployment

        Image uploads validated via magic byte inspection; JPEG and PNG only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_extension_allowlist_mentioned():
    """Extension allowlist mentioned — no finding."""
    art = _plan("""
        ## Deployment Plan

        Document upload restricted via extension allowlist: pdf, docx, xlsx only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact_not_checked():
    """SPEC artifact is not checked for this pitfall."""
    art = _spec("""
        ## Deployment Plan

        Users can upload files via multipart/form-data.
    """)
    assert PITFALL not in _ids(art)
