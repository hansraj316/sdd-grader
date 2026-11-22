"""Tests for PLAN-MISSING-SEARCH-INDEX-STRATEGY pitfall check.

Fires when a deployment plan exposes search endpoints or describes search
functionality but names no search-index or full-text search strategy.

Sources: ISO/IEC 25010:2023 §8.4 Performance Efficiency;
Tessl scale-readiness checklist; Kiro production-readiness (query performance).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_search_index_strategy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-SEARCH-INDEX-STRATEGY"


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
    return [f.pitfall_id for f in _plan_missing_search_index_strategy(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------

def test_fires_search_endpoint_no_index():
    """Plan mentions GET /search with no indexing strategy."""
    art = _plan("""
        ## Deployment

        The API exposes GET /search?q=... to find products by name or description.
        Results are returned as JSON arrays.
    """)
    assert PITFALL in _ids(art)


def test_fires_keyword_search_no_strategy():
    """Plan mentions keyword search with no index strategy."""
    art = _plan("""
        ## Deployment Plan

        Users can search for documents using keyword search via the search endpoint.
        The endpoint queries the database directly.
    """)
    assert PITFALL in _ids(art)


def test_fires_search_results_no_index():
    """Plan mentions search results with no index strategy."""
    art = _plan("""
        ## Deployment

        The product search results are paginated and sorted by relevance.
        No caching strategy has been defined.
    """)
    assert PITFALL in _ids(art)


def test_fires_search_bar_no_strategy():
    """Plan mentions a search bar with no index strategy."""
    art = _plan("""
        ## Deployment Plan

        The UI includes a search bar that queries the backend for matching records.
        Deploy on AWS ECS behind ALB.
    """)
    assert PITFALL in _ids(art)


def test_fires_search_functionality_no_index():
    """Plan mentions search functionality with no indexing."""
    art = _plan("""
        ## Deployment

        Search functionality allows users to find items by name, tag, or category.
        The deploy target is a Kubernetes cluster on GKE.
    """)
    assert PITFALL in _ids(art)


def test_fires_full_text_search_no_strategy():
    """Plan mentions full-text search with no engine named."""
    art = _plan("""
        ## Deployment Plan

        The API supports full-text search across all content fields.
        Deployed to Heroku via Docker container.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------

def test_silent_elasticsearch_mentioned():
    """Elasticsearch mentioned — no finding."""
    art = _plan("""
        ## Deployment

        Full-text search powered by Elasticsearch; product index refreshed
        every 5 minutes via CDC from PostgreSQL.
    """)
    assert PITFALL not in _ids(art)


def test_silent_opensearch_mentioned():
    """OpenSearch mentioned — no finding."""
    art = _plan("""
        ## Deployment Plan

        Search endpoint backed by OpenSearch cluster (3 nodes);
        indexes built from DynamoDB streams.
    """)
    assert PITFALL not in _ids(art)


def test_silent_algolia_mentioned():
    """Algolia mentioned — no finding."""
    art = _plan("""
        ## Deployment

        Product search uses Algolia indices synchronised via webhook on write.
        Search bar queries Algolia search API directly from the frontend.
    """)
    assert PITFALL not in _ids(art)


def test_silent_tsvector_mentioned():
    """Postgres tsvector mentioned — no finding."""
    art = _plan("""
        ## Deployment Plan

        Search functionality uses Postgres tsvector full-text index on the
        products table. GIN index refreshed via trigger.
    """)
    assert PITFALL not in _ids(art)


def test_silent_inverted_index_mentioned():
    """Inverted index mentioned — no finding."""
    art = _plan("""
        ## Deployment

        The search API is backed by an inverted index built nightly from the
        documents table. Query latency target: p99 < 100 ms.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_search_vocab():
    """Plan has no search vocabulary — no finding."""
    art = _plan("""
        ## Deployment Plan

        The API exposes GET /products and POST /orders.
        Deploy on AWS ECS behind ALB.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_guard():
    """Plan with no deploy vocabulary — deploy guard blocks the check."""
    art = _plan("""
        Users can search for products by keyword via the search bar.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block_excluded():
    """Search vocabulary inside a fenced code block is excluded."""
    art = _plan("""
        ## Deployment Plan

        ```
        GET /search?q=keyword — returns search results
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_heading_line_excluded():
    """Search vocabulary on a heading line is excluded."""
    art = _plan("""
        ## Deployment Plan

        ### Search Endpoint

        Backed by Elasticsearch cluster with product index.
    """)
    assert PITFALL not in _ids(art)


def test_silent_typesense_mentioned():
    """Typesense mentioned — no finding."""
    art = _plan("""
        ## Deployment

        The keyword search endpoint queries a Typesense collection.
        The collection is kept in sync via a Kafka consumer.
    """)
    assert PITFALL not in _ids(art)


def test_silent_meilisearch_mentioned():
    """Meilisearch mentioned — no finding."""
    art = _plan("""
        ## Deployment Plan

        Document search backed by Meilisearch; index built on deploy.
        Deploy to Kubernetes on EKS.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact_not_checked():
    """SPEC artifact is not checked for this pitfall."""
    art = _spec("""
        ## Deployment Plan

        The API exposes a search endpoint for product search results.
    """)
    assert PITFALL not in _ids(art)
