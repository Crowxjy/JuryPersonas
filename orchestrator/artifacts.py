"""Artifact loading and path resolution helpers."""
from __future__ import annotations

import json
from pathlib import Path

try:
    from .bootstrap import SKILL_ROOT
except ImportError:
    from bootstrap import SKILL_ROOT  # type: ignore


def load_artifact(artifact_path: Path, brief: dict, scenario: str) -> dict:
    """Load review artifacts into a normalized dictionary."""
    suffix = artifact_path.suffix.lower()
    fields = brief.get("fields", {})
    artifact_type = fields.get("artifact_type", {}).get("value")
    base = {
        "artifact_type": artifact_type,
        "scenario": scenario,
        "locator": str(artifact_path),
        "title": artifact_path.stem,
    }
    if suffix == ".json":
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {**base, **data}
        return {**base, "content": data}
    if suffix in {".md", ".txt"}:
        return {**base, "content": artifact_path.read_text(encoding="utf-8")}
    return base


def resolve_input_path(
    raw: str | None,
    *,
    artifact_path: Path | None = None,
    artifact: dict | None = None,
) -> Path | None:
    """Resolve optional user/artifact paths against cwd, skill root, and artifact dir."""
    if not raw:
        return None
    candidate = Path(raw)
    candidates = [candidate]
    if not candidate.is_absolute():
        candidates.append(SKILL_ROOT / candidate)
        if artifact_path is not None:
            candidates.append(artifact_path.parent / candidate)
        if artifact and artifact.get("base_dir"):
            candidates.append(Path(str(artifact["base_dir"])) / candidate)
    for path in candidates:
        if path.exists():
            return path
    return candidate


def nested_get(data: dict, *keys: str) -> str | None:
    cur: object = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return str(cur) if cur else None


def artifact_field_path(
    artifact: dict,
    artifact_path: Path,
    *field_paths: tuple[str, ...],
) -> Path | None:
    for keys in field_paths:
        raw = nested_get(artifact, *keys)
        path = resolve_input_path(raw, artifact_path=artifact_path, artifact=artifact)
        if path and path.exists():
            return path
    return None
