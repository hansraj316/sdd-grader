"""Tests for SPEC-MISSING-I18N-STRATEGY pitfall."""
from __future__ import annotations

import textwrap

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_i18n_strategy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-MISSING-I18N-STRATEGY"


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
    return [f.pitfall_id for f in _spec_missing_i18n_strategy(art, CATALOG)]


# ---------------------------------------------------------------------------
# Should FIRE
# ---------------------------------------------------------------------------

def test_fires_on_locale_in_fr():
    art = _spec("""
        ## Requirements
        FR-001: The system shall support locale-based formatting.
        FR-002: The system shall validate user input.
        FR-003: The system shall log all actions.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_currency_in_fr():
    art = _spec("""
        ## Requirements
        FR-001: The system shall display prices in the user's currency.
        FR-002: The system shall authenticate users.
        FR-003: The system shall store data securely.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_timezone_in_fr():
    art = _spec("""
        ## Requirements
        FR-001: The system shall convert timestamps to the user's timezone.
        FR-002: The system shall enforce access controls.
        FR-003: The system shall emit audit logs.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_multilingual():
    art = _spec("""
        ## Requirements
        FR-001: The UI shall be multilingual.
        FR-002: The system shall support search.
        FR-003: NFR-001: The system shall respond within 200ms.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_translation_noun():
    art = _spec("""
        ## Requirements
        FR-001: The system shall support translation of all UI labels.
        FR-002: The system shall validate inputs.
        FR-003: The system shall maintain an audit trail.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_time_zone_space():
    art = _spec("""
        ## Requirements
        FR-001: The system shall display dates in the user's time zone.
        FR-002: The system shall authenticate users.
        FR-003: The system shall emit metrics.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_multi_language():
    art = _spec("""
        ## Requirements
        FR-001: The app shall be multi-language capable.
        FR-002: The system shall enforce rate limits.
        FR-003: The system shall maintain an audit log.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Should NOT FIRE
# ---------------------------------------------------------------------------

def test_silent_when_i18n_strategy_present():
    art = _spec("""
        ## Requirements
        FR-001: The system shall support locale-based formatting.
        FR-002: The system shall validate user input.
        FR-003: The system shall log all actions.
        ## Internationalization
        The application uses react-intl for i18n with ICU MessageFormat patterns.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_l10n_mentioned():
    art = _spec("""
        ## Requirements
        FR-001: The system shall display prices in the user's currency.
        FR-002: The system shall authenticate users.
        FR-003: The system shall store data securely.
        ## Localization
        l10n is handled via locale bundles distributed with each release.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_gettext_mentioned():
    art = _spec("""
        ## Requirements
        FR-001: The UI shall support translation.
        FR-002: NFR-001: Response time shall be < 200ms.
        FR-003: The system shall log all mutations.
        ## i18n Strategy
        All strings are wrapped with GNU gettext and stored in locale files.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_no_i18n_vocab_in_reqs():
    art = _spec("""
        ## Requirements
        FR-001: The system shall allow users to log in.
        FR-002: The system shall validate input fields.
        FR-003: NFR-001: The system shall respond in < 500ms.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_fewer_than_3_req_lines():
    art = _spec("""
        ## Requirements
        FR-001: The system shall support locale.
        FR-002: The system shall validate inputs.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_i18n_vocab_only_in_fenced_block():
    art = _spec("""
        ## Requirements
        FR-001: The system shall allow login.
        FR-002: The system shall validate inputs.
        FR-003: The system shall log all actions.
        ```
        locale = 'en-US'
        currency = 'USD'
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_localization_in_doc():
    art = _spec("""
        ## Requirements
        FR-001: The system shall support multi-language labels.
        FR-002: The system shall validate user input.
        FR-003: The system shall respond within 500ms.
        ## Strategy
        Localization is handled via locale pack bundles per region.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_spec_artifact():
    raw = textwrap.dedent("""
        ## Plan
        FR-001: Support locale.
        FR-002: Support login.
        FR-003: Support search.
    """).strip()
    art = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in _ids(art)


def test_silent_when_formatjs_mentioned():
    art = _spec("""
        ## Requirements
        FR-001: The app shall display dates in the user's timezone.
        FR-002: The system shall authenticate users.
        FR-003: The system shall emit metrics.
        ## Internationalization
        All date/time formatting uses formatjs with locale-specific patterns.
    """)
    assert PITFALL not in _ids(art)
