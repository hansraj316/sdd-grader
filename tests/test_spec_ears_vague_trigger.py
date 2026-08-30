"""Tests for SPEC-EARS-VAGUE-TRIGGER pitfall.

Fires when an EARS event-driven requirement (when/while/if ... shall) uses a
qualitative trigger condition (e.g. 'when the load is high', 'when traffic spikes')
that cannot be deterministically tested without a numeric threshold.

Guard conditions (all must hold on a non-fenced requirement-bearing line):
  1. Line contains 'shall'.
  2. Line matches a vague EARS trigger:
     - (when|while|if) ... (high|heavy|excessive|elevated|abnormal|peak)
       (load|traffic|demand|usage|volume)
     - OR: (load|traffic|demand|usage) spikes?

Silence: the line also contains a numeric threshold
  (digit + %, rps, qps, req, users?, connections?, ms, MB, GB, tps).

Applies to spec artifacts only.
"""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_ears_vague_trigger
from sddgrade.model import Artifact, ArtifactType


def _make_spec(raw: str) -> Artifact:
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


def _make_plan(raw: str) -> Artifact:
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# FIRE cases — check should trigger
# ---------------------------------------------------------------------------


def test_when_high_load_fires() -> None:
    """'When the load is high, the system shall shed requests' — qualitative trigger fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: When the load is high, the system shall shed requests gracefully.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-VAGUE-TRIGGER"


def test_when_heavy_traffic_fires() -> None:
    """'When traffic is heavy, the system shall activate rate limiting' — qualitative fires."""
    raw = (
        "## Requirements\n\n"
        "FR-010: When traffic is heavy, the system shall activate rate limiting.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-VAGUE-TRIGGER"


def test_while_excessive_demand_fires() -> None:
    """'While demand is excessive, the system shall queue requests' — qualitative fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-005: While demand is excessive, the system shall queue incoming requests.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1


def test_when_traffic_spikes_fires() -> None:
    """'When traffic spikes, the system shall scale out' — vague spike trigger fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-020: When traffic spikes, the system shall scale out automatically.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-VAGUE-TRIGGER"


def test_when_load_spikes_fires() -> None:
    """'When load spikes, the system shall alert operations' — fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-030: When load spikes, the system shall alert the operations team.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1


def test_if_elevated_usage_fires() -> None:
    """'If usage is elevated, the system shall throttle requests' — fires."""
    raw = (
        "## Requirements\n\n"
        "FR-015: If usage is elevated, the system shall throttle requests.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1


def test_when_abnormal_load_fires() -> None:
    """'When load is abnormal, the system shall reject new connections' — fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-007: When load is abnormal, the system shall reject new connections.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1


def test_multiple_vague_triggers_count() -> None:
    """Two vague trigger lines — finding count is reported correctly."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: When the load is high, the system shall shed requests.\n"
        "NFR-002: When traffic spikes, the system shall scale out.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1  # one aggregate finding
    assert "2" in findings[0].message  # count reported


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_numeric_threshold_silences_load() -> None:
    """'When CPU exceeds 80%, the system shall shed requests' — numeric grounds trigger."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: When CPU exceeds 80%, the system shall shed low-priority requests.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_numeric_rps_silences_spike() -> None:
    """'When request rate exceeds 1000 rps, the system shall scale out' — grounded → silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: When request rate exceeds 1000 rps, the system shall scale out.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_numeric_connections_silences() -> None:
    """'While concurrent connections exceed 5000, the system shall queue requests' — silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-005: While concurrent connections exceed 5000, the system shall queue requests.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_no_shall_silent() -> None:
    """Vague trigger but no 'shall' — not a normative requirement, silent."""
    raw = (
        "## Requirements\n\n"
        "When the load is high, the system may shed requests.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_plain_requirement_no_trigger_silent() -> None:
    """Normal requirement with no EARS trigger form — silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: The system shall process requests within 200ms (p95).\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_fenced_block_excluded() -> None:
    """Vague trigger inside a fenced code block — silent."""
    raw = (
        "## Requirements\n\n"
        "```\n"
        "NFR-001: When the load is high, the system shall shed requests.\n"
        "```\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_plan_artifact_silent() -> None:
    """Plan artifact — pitfall applies to spec only, silent."""
    raw = (
        "## Deployment\n\n"
        "NFR-001: When the load is high, the system shall shed requests.\n"
    )
    findings = _spec_ears_vague_trigger(_make_plan(raw), CATALOG)
    assert findings == []


def test_ms_threshold_silences() -> None:
    """'When response time exceeds 500ms, the system shall scale' — grounded → silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-010: When response time under heavy load exceeds 500ms, the system shall scale.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_users_threshold_silences() -> None:
    """'When concurrent users exceed 1000 users, ...' — grounded → silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-011: When concurrent users exceed 1000 users, the system shall activate auto-scaling.\n"
    )
    findings = _spec_ears_vague_trigger(_make_spec(raw), CATALOG)
    assert findings == []
