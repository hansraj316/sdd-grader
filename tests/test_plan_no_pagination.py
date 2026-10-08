"""Tests for PLAN-NO-PAGINATION pitfall.

Fires when a plan.md with deployment vocabulary AND list/search/collection
endpoint vocabulary has no pagination strategy anywhere in the non-fenced text.

Source: Kiro production-readiness checklist, Tessl API design checklist,
        OWASP API4:2023 Unrestricted Resource Consumption, CNCF API Guidelines.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_pagination
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-PAGINATION"


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
    return [f.pitfall_id for f in _plan_no_pagination(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — list/search endpoint vocab + deploy vocab, no pagination silence
# ---------------------------------------------------------------------------

def test_fires_list_endpoint_no_pagination():
    """Plan describes a list endpoint with no pagination strategy."""
    art = _plan("""
        ## Deployment Plan
        Deploy the orders API to production this sprint.
        The list endpoint returns all orders for a given account.
        Clients call GET /orders to retrieve results.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_search_endpoint_no_pagination():
    """Plan describes a search API with no pagination strategy."""
    art = _plan("""
        ## Production Release
        Release the product search service to production.
        The search API accepts keyword queries and returns matching products.
        A search endpoint is exposed at /api/v1/search.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_get_all_pattern_no_pagination():
    """Plan uses get-all pattern with no pagination."""
    art = _plan("""
        ## Deployment
        Deploy the user service to the staging environment.
        The admin panel calls get-all users to populate the dashboard table.
        No filtering is currently applied.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_rest_collection_get_no_pagination():
    """Plan describes REST GET on plural resource with no pagination."""
    art = _plan("""
        ## Release Plan
        Ship the inventory microservice.
        The client calls GET /products to retrieve the product catalogue.
        Response is a JSON array of product objects.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_returns_list_of_no_pagination():
    """Plan says endpoint returns a list of items with no pagination."""
    art = _plan("""
        ## Deployment
        Deploy the reporting service to production.
        The reports endpoint returns a list of report objects for the authenticated user.
        No additional query parameters are supported at this time.
    """)
    assert _ids(art) == [PITFALL]


# ---------------------------------------------------------------------------
# Silent cases — pagination vocabulary present
# ---------------------------------------------------------------------------

def test_silent_cursor_pagination():
    """Plan mentions cursor-based pagination — check silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the orders service to production.
        The list endpoint supports cursor-based pagination.
        Clients pass a cursor token to retrieve the next page of results.
        Default page size is 20; maximum is 100.
    """)
    assert _ids(art) == []


def test_silent_limit_offset():
    """Plan uses limit/offset pagination — check silenced."""
    art = _plan("""
        ## Production Release
        Release the product search service.
        The search endpoint accepts limit and offset parameters.
        All list API responses include total_count.
    """)
    assert _ids(art) == []


def test_silent_page_size():
    """Plan specifies page_size — check silenced."""
    art = _plan("""
        ## Deployment
        Deploy user service. The GET /users endpoint returns paginated results.
        The page_size parameter defaults to 25 and is capped at 200.
    """)
    assert _ids(art) == []


def test_silent_paginate_keyword():
    """Plan explicitly says 'paginate' — check silenced."""
    art = _plan("""
        ## Release Plan
        Deploy inventory service to production.
        The list endpoint will paginate results using keyset pagination.
        Clients pass after_id to fetch the next batch.
    """)
    assert _ids(art) == []


def test_silent_no_list_endpoint():
    """Plan has no list/search endpoint vocabulary — check does not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the notification service to production.
        The service sends email notifications for order confirmations.
        No read endpoints are exposed in this phase.
    """)
    assert _ids(art) == []


def test_silent_spec_artifact():
    """PLAN-NO-PAGINATION must not fire on a spec artifact."""
    art = _spec("""
        ## Deployment Plan
        Deploy the orders service to production.
        The list endpoint returns all orders for a given account.
        No pagination strategy is included yet.
    """)
    assert _ids(art) == []


def test_silent_no_deploy_vocab():
    """Plan artifact type but no deploy vocabulary — guard not satisfied."""
    art = _plan("""
        ## Architecture Notes
        This is a design sketch describing the system components.
        The repository layer fetches records from the database.
        No endpoints are described here.
    """)
    assert _ids(art) == []


def test_silent_fenced_trigger():
    """List endpoint vocab only inside fenced code block — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the user service to production this sprint.

        ```http
        GET /users
        The get-all endpoint returns all users.
        ```

        All read operations are internal; no externally-facing collection is exposed.
    """)
    assert _ids(art) == []


def test_silent_has_more_flag():
    """Plan uses has_more flag — silenced."""
    art = _plan("""
        ## Production Rollout
        Release the orders API.
        The list endpoint returns a JSON object with items and a has_more flag.
        Clients paginate by passing the last seen order_id.
    """)
    assert _ids(art) == []


def test_silent_next_token_pagination():
    """Plan uses nextToken pagination pattern — silenced."""
    art = _plan("""
        ## Deployment
        Release the jobs API to production.
        GET /jobs returns a list of jobs.
        The response includes a nextToken for fetching subsequent pages.
    """)
    assert _ids(art) == []
