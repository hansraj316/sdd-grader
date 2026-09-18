"""Tests for PLAN-NO-CACHING-STRATEGY pitfall.

Fires when a plan.md with deployment vocabulary AND caching vocabulary
(Redis, Memcached, CDN, Varnish, etc.) has NO cache-invalidation, TTL,
eviction, or stale-data strategy anywhere in the document.

Sources: Tessl (infrastructure-drift prevention),
         Twelve-Factor App — Factor VI (stateless processes),
         ISO 25010:2023 Reliability/Consistency.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_caching_strategy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-CACHING-STRATEGY"


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
    return [f.pitfall_id for f in _plan_no_caching_strategy(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — caching vocab present, no invalidation/TTL strategy
# ---------------------------------------------------------------------------


def test_fires_redis_no_strategy():
    """Plan uses Redis but says nothing about invalidation or TTL."""
    art = _plan("""
        ## Deployment Plan
        Deploy the product service to production.
        Product listings are cached in Redis to reduce database load.
        The Redis instance is provisioned on Elasticache with 4 GB memory.
        Deployment proceeds with a rolling update, one instance at a time.
    """)
    assert PITFALL in _ids(art)


def test_fires_cdn_no_ttl():
    """Plan mentions a CDN but provides no cache-control or TTL policy."""
    art = _plan("""
        ## Release Plan
        Deploy the static assets to production via CloudFront.
        Static files will be served from the CDN to reduce origin load.
        The deployment pipeline invalidates the old build artifacts.
        A rolling release to production is scheduled for Friday.
    """)
    assert PITFALL in _ids(art)


def test_fires_memcached_no_eviction():
    """Plan mentions Memcached but no eviction or expiry strategy."""
    art = _plan("""
        ## Deployment Plan
        Roll out the session service to production.
        User sessions are stored in Memcached for fast retrieval.
        A new Memcached cluster (3 nodes, r5.large) is provisioned.
        Deployment: blue-green swap after smoke tests pass.
    """)
    assert PITFALL in _ids(art)


def test_fires_varnish_no_purge():
    """Plan adds Varnish in front of the API but no purge/invalidation."""
    art = _plan("""
        ## Infrastructure Deployment
        Deploy Varnish as a reverse proxy in front of the API tier.
        Varnish will cache responses to reduce backend load.
        Production cutover is scheduled after the load test completes.
        Traffic will be routed via the load balancer to the Varnish nodes.
    """)
    assert PITFALL in _ids(art)


def test_fires_nginx_cache_no_strategy():
    """Plan adds nginx cache but no invalidation strategy."""
    art = _plan("""
        ## Release Plan
        Deploy updated nginx configuration to staging then production.
        Enable nginx-cache for image and thumbnail responses.
        The cache is stored on an SSD-backed volume attached to each node.
        Rollout proceeds instance by instance across the fleet.
    """)
    assert PITFALL in _ids(art)


def test_fires_cloudfront_no_max_age():
    """Plan deploys CloudFront but no max-age or cache strategy."""
    art = _plan("""
        ## Deployment Plan
        Deploy the media service to production behind CloudFront.
        All media assets will be served from CloudFront edge nodes.
        Origin failover is configured to a secondary S3 bucket.
        Release is scheduled for the next maintenance window.
    """)
    assert PITFALL in _ids(art)


def test_fires_edge_cache_no_lifecycle():
    """Plan mentions edge-cache with no lifecycle."""
    art = _plan("""
        ## Production Deployment
        Enable the edge-cache layer for authenticated API responses.
        This will reduce latency for users in Europe and Asia.
        The cache is backed by the distributed key-value store.
        Deploy in canary mode: 5% traffic for 30 minutes before full cutover.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — caching vocab present WITH a management strategy
# ---------------------------------------------------------------------------


def test_silent_redis_with_ttl():
    """Plan mentions Redis AND a TTL — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the session service to production.
        Session tokens are cached in Redis with a TTL of 24 hours.
        On session revocation the key is deleted immediately.
        Rolling deployment with health checks at each step.
    """)
    assert PITFALL not in _ids(art)


def test_silent_cdn_with_cache_invalidation():
    """Plan uses CDN and mentions cache-invalidation — silent."""
    art = _plan("""
        ## Release Plan
        Deploy static assets to CloudFront CDN.
        After each deployment a cache-invalidation job runs to purge stale files.
        Rolling release to production after smoke tests pass.
    """)
    assert PITFALL not in _ids(art)


def test_silent_redis_with_eviction_policy():
    """Plan mentions Redis eviction policy — silent."""
    art = _plan("""
        ## Infrastructure Deployment
        Deploy the product catalog service to production.
        Product data is cached in Redis using an allkeys-lru eviction policy.
        The Redis cluster is provisioned with 8 GB memory.
        Deployment proceeds via blue-green swap.
    """)
    assert PITFALL not in _ids(art)


def test_silent_cdn_with_max_age():
    """Plan sets max-age headers — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the content service to production.
        API responses include a Cache-Control: max-age=300 header.
        Static assets are served from CloudFront with long max-age.
        Deployment is automated via the CI/CD pipeline.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_caching_vocab():
    """Plan has no caching vocabulary at all — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the billing service to production.
        Payments are processed synchronously via Stripe.
        Database: PostgreSQL 15 on RDS.
        Deployment: blue-green with automated rollback on failure.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_guard():
    """Document has caching vocab but no deployment vocabulary — silent (not a plan)."""
    art = _plan("""
        ## Architecture Notes
        The system uses Redis for session storage.
        Memcached is used for product listings.
        This document is for reference purposes only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """Spec artifact — PLAN-NO-CACHING-STRATEGY does not apply."""
    art = _spec("""
        ## Requirements
        FR-001: The system SHALL cache product listings in Redis.
        FR-002: Cache entries SHALL expire after 5 minutes.
        No deployment plan is included.
    """)
    assert PITFALL not in _ids(art)


def test_silent_redis_with_write_through():
    """Plan uses Redis with write-through pattern — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the inventory service to production.
        Inventory counts are stored using a write-through cache pattern in Redis.
        The database and cache are updated atomically on every write.
        Rolling deployment with readiness probe on each pod.
    """)
    assert PITFALL not in _ids(art)


def test_silent_redis_in_fenced_code():
    """Redis mention is inside a fenced code block — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the recommendation service to production.
        The service is stateless; all state lives in the database.

        ```yaml
        # Example config snippet (not normative)
        cache:
          backend: redis
          host: localhost:6379
        ```

        Deployment: rolling update with health-check gate.
    """)
    assert PITFALL not in _ids(art)
