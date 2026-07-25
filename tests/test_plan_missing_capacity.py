"""Tests for PLAN-MISSING-CAPACITY pitfall.

The check fires when a plan.md uses scaling vocabulary (scale/replicas/instances/
nodes/pods/autoscal/horizontally/vertically) but states no capacity number
(a digit followed by a resource unit such as replicas, GB, RAM, vCPU, etc.).
"""

from __future__ import annotations

import pytest

from sddgrade.engine.lint import _plan_missing_capacity
from sddgrade.catalog import load_catalog
from sddgrade.model import Artifact, ArtifactType


def _plan(raw: str) -> Artifact:
    return Artifact(path="plan.md", type=ArtifactType.PLAN, raw=raw, sections=[])


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# Should FIRE (scaling vocab present, no capacity number)
# ---------------------------------------------------------------------------

def test_fires_on_scales_horizontally_no_number():
    art = _plan("The service scales horizontally to handle peak load.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert len(findings) == 1
    assert "PLAN-MISSING-CAPACITY" in findings[0].pitfall_id


def test_fires_on_scales_vertically_no_number():
    art = _plan("We will scale vertically during the initial launch.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert len(findings) == 1


def test_fires_on_autoscaling_no_number():
    art = _plan("Autoscaling is configured to respond to CPU spikes.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert len(findings) == 1


def test_fires_on_replicas_mention_no_count():
    art = _plan("Deploy multiple replicas behind a load balancer.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert len(findings) == 1


def test_fires_on_instances_no_count():
    art = _plan("The application will run as multiple instances in production.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert len(findings) == 1


def test_fires_on_nodes_no_count():
    art = _plan("Kubernetes nodes will be used for deployment.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert len(findings) == 1


def test_fires_on_pods_no_count():
    art = _plan("Pods will be created per region.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert len(findings) == 1


def test_fires_on_scalable_no_number():
    art = _plan("The architecture is horizontally scalable.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# Should NOT fire (capacity number present)
# ---------------------------------------------------------------------------

def test_no_fire_with_replica_count():
    art = _plan("Deploy 3 replicas behind the load balancer.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings == []


def test_no_fire_with_instance_count():
    art = _plan("The application will run as 5 instances in production.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings == []


def test_no_fire_with_gb_ram():
    art = _plan("Each pod uses 4 GB RAM and scales horizontally.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings == []


def test_no_fire_with_vcpu():
    art = _plan("Provision 2 vcpu per node; autoscal up to 10 nodes.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings == []


def test_no_fire_with_memory():
    art = _plan("Configure autoscaling with 512 MB memory per container.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings == []


def test_no_fire_with_cores():
    art = _plan("Each instance gets 4 cores and scales up to 20 instances.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings == []


def test_no_fire_with_workers():
    art = _plan("Start with 8 workers; add more as load increases.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings == []


# ---------------------------------------------------------------------------
# Should NOT fire (no scaling vocabulary)
# ---------------------------------------------------------------------------

def test_no_fire_no_scaling_vocab():
    art = _plan("Refactor the authentication module for readability.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings == []


def test_no_fire_pure_refactoring_plan():
    art = _plan("Split UserService into AuthService and ProfileService. No deployment involved.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings == []


# ---------------------------------------------------------------------------
# Fires at most once per artifact
# ---------------------------------------------------------------------------

def test_fires_once_for_multiple_scaling_mentions():
    raw = "\n".join([
        "The service scales horizontally.",
        "Autoscaling is enabled.",
        "replicas will be added dynamically.",
    ])
    art = _plan(raw)
    findings = _plan_missing_capacity(art, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# Message content
# ---------------------------------------------------------------------------

def test_finding_message_mentions_capacity():
    art = _plan("The service autoscales to meet demand.")
    findings = _plan_missing_capacity(art, CATALOG)
    assert findings
    msg = findings[0].message.lower()
    assert "capacity" in msg or "replicas" in msg or "scaling" in msg
