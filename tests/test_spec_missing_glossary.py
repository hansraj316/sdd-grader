"""Tests for SPEC-MISSING-GLOSSARY pitfall.

Fires when a spec has ≥3 non-fenced FR-/NFR- requirement lines but no
Glossary / Definitions / Terms-and-Definitions / Abbreviations section heading.

Sources:
  - ISO/IEC/IEEE 29148:2018 §5.2.1 Terms and Definitions
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_glossary
from sddgrade.model import Artifact, ArtifactType


def _make_spec(raw: str) -> Artifact:
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# FIRE cases — check should trigger
# ---------------------------------------------------------------------------


def test_three_fr_lines_no_glossary_fires() -> None:
    """Spec with exactly 3 FR- lines and no glossary heading → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Overview\n\nThis feature enables task export.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks as CSV.\n"
        "- FR-002: The system shall filter exports by status.\n"
        "- FR-003: The system shall escape CSV field values per RFC 4180.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-GLOSSARY"
    assert "glossary" in findings[0].message.lower()


def test_five_fr_lines_no_glossary_fires_once() -> None:
    """Spec with 5 FR- lines and no glossary heading → fires exactly once."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Overview\n\nBulk task operations.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall list all tasks.\n"
        "- FR-002: The system shall mark tasks complete.\n"
        "- FR-003: The system shall delete tasks.\n"
        "- FR-004: The system shall archive tasks.\n"
        "- FR-005: The system shall restore archived tasks.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-GLOSSARY"


def test_finding_anchored_to_line_1() -> None:
    """Aggregate finding is anchored to line 1."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do A.\n"
        "- FR-002: The system shall do B.\n"
        "- FR-003: The system shall do C.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 1


def test_nfr_lines_trigger_guard() -> None:
    """NFR- lines count toward the ≥3 guard threshold."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall respond in < 200 ms.\n"
        "- NFR-002: The system shall achieve 99.9% uptime.\n"
        "- NFR-003: The system shall encrypt data at rest with AES-256.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-GLOSSARY"


def test_mixed_fr_nfr_lines_trigger_guard() -> None:
    """A mix of FR- and NFR- lines still triggers the guard when total ≥ 3."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export data.\n"
        "- NFR-001: The system shall respond in < 300 ms.\n"
        "- FR-002: The system shall filter by date range.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-GLOSSARY"


def test_heading_sections_without_requirements_context_fires() -> None:
    """Headings like Overview, Requirements, Success Criteria but no glossary → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Overview\n\nProvides search capability.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall index documents.\n"
        "- FR-002: The system shall support full-text search.\n"
        "- FR-003: The system shall rank results by relevance.\n\n"
        "## Success Criteria\n\n"
        "- Search returns results in < 1 s for 99% of queries.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# PASS cases — check should be silent
# ---------------------------------------------------------------------------


def test_glossary_heading_silences_check() -> None:
    """Spec with `## Glossary` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks as CSV.\n"
        "- FR-002: The system shall filter exports by status.\n"
        "- FR-003: The system shall escape CSV field values per RFC 4180.\n\n"
        "## Glossary\n\n"
        "- CSV: Comma-Separated Values format per RFC 4180.\n"
        "- FR: Functional Requirement.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert findings == []


def test_definitions_heading_silences_check() -> None:
    """Spec with `## Definitions` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n"
        "- FR-002: The system shall issue JWT tokens.\n"
        "- FR-003: The system shall revoke sessions.\n\n"
        "## Definitions\n\n"
        "- JWT: JSON Web Token.\n"
        "- Session: An authenticated user context.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert findings == []


def test_terms_and_definitions_heading_silences_check() -> None:
    """Spec with `## Terms and Definitions` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export data.\n"
        "- FR-002: The system shall import data.\n"
        "- FR-003: The system shall validate data integrity.\n\n"
        "## Terms and Definitions\n\n"
        "- Data: User-supplied records.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert findings == []


def test_abbreviations_heading_silences_check() -> None:
    """Spec with `## Abbreviations` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall send email notifications.\n"
        "- FR-002: The system shall queue notifications via the MQ.\n"
        "- NFR-001: The system shall deliver notifications within 30 s.\n\n"
        "## Abbreviations\n\n"
        "- MQ: Message Queue.\n"
        "- SLA: Service-Level Agreement.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert findings == []


def test_fewer_than_three_req_lines_is_silent() -> None:
    """Spec with fewer than 3 FR-/NFR- lines does not fire."""
    spec = _make_spec(
        "# Minimal Spec\n\n"
        "## Overview\n\nSmall feature.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do A.\n"
        "- FR-002: The system shall do B.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert findings == []


def test_no_fr_lines_at_all_is_silent() -> None:
    """Spec with no formal FR-/NFR- identifiers → guard does not trip → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Overview\n\nDescribes something.\n\n"
        "## Requirements\n\n"
        "The system shall authenticate users.\n"
        "The system shall log errors.\n"
    )
    findings = _spec_missing_glossary(spec, CATALOG)
    assert findings == []


def test_fr_lines_inside_code_fence_not_counted() -> None:
    """FR- identifiers inside a code fence do not count toward the guard."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Overview\n\n"
        "```\n"
        "- FR-001: example\n"
        "- FR-002: example\n"
        "- FR-003: example\n"
        "- FR-004: example\n"
        "```\n"
        "\n"
        "## Requirements\n\n"
        "Only two real requirements:\n"
        "- FR-001: The system shall do A.\n"
        "- FR-002: The system shall do B.\n"
    )
    # Only 2 non-fenced FR- lines → guard should NOT fire.
    findings = _spec_missing_glossary(spec, CATALOG)
    assert findings == []


def test_non_spec_artifact_type_is_silent() -> None:
    """The check only applies to SPEC artifacts; plan artifacts are silenced."""
    from sddgrade.model import ArtifactType
    art = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "## Plan\n\n"
            "- FR-001: The system shall do A.\n"
            "- FR-002: The system shall do B.\n"
            "- FR-003: The system shall do C.\n"
        ),
        sections=parse_sections(
            "## Plan\n\n"
            "- FR-001: The system shall do A.\n"
            "- FR-002: The system shall do B.\n"
            "- FR-003: The system shall do C.\n"
        ),
    )
    findings = _spec_missing_glossary(art, CATALOG)
    assert findings == []
