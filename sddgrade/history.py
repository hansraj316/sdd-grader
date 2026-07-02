"""Local, per-repo review history — a JSONL trail under ``.sddgrade/``.

One line per run, append-only. The dashboard reads this back for trends and
top-pitfall metrics. No DB, no server.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .model import ReviewResult

HISTORY_DIR = ".sddgrade"
HISTORY_FILE = "history.jsonl"


def history_path(root: Path) -> Path:
    return root / HISTORY_DIR / HISTORY_FILE


def record(root: Path, result: ReviewResult) -> Path:
    """Append a compact summary of ``result`` to the repo's history."""
    path = history_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)

    pitfalls = Counter(f.pitfall_id for f in result.all_findings if f.pitfall_id)
    entry = {
        "timestamp": result.timestamp,
        "tool": result.tool,
        "engine": result.engine,
        "overall": round(result.overall, 1),
        "artifact_count": len(result.artifacts),
        "finding_count": len(result.all_findings),
        "pitfalls": dict(pitfalls),
        "artifacts": [
            {
                "path": a.path,
                "type": a.type.value,
                "overall": round(a.overall, 1),
                "findings": len(a.findings),
            }
            for a in result.artifacts
        ],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return path


def load(root: Path) -> list[dict]:
    """Read all recorded runs (oldest first); empty list if none."""
    path = history_path(root)
    if not path.is_file():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
