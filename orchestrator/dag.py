"""Scenario selection and DAG planning.

Kept separate from ``pipeline.py`` so the pipeline can focus on execution and
resume behavior instead of carrying scenario metadata, frontmatter parsing, and
mode ordering.
"""
from __future__ import annotations

import re
from pathlib import Path

try:  # package import: python -m orchestrator.pipeline / jury_review.py
    from .bootstrap import SCENARIOS_DIR
except ImportError:  # script import: python orchestrator/pipeline.py
    from bootstrap import SCENARIOS_DIR  # type: ignore


DISTRIBUTION_TO_MODE = {
    "real": "mode/persona-sample",
    "mock": "mode/persona-sample",
    "specified_personas": "mode/persona-pick",
}

STAGE_PRIORITY = {
    "mode/keyframe-extract": 1,
    "mode/prd-extract": 1,
    "mode/copy-extract": 1,
    "mode/design-extract": 1,
    "mode/screen-extract": 1,
    "mode/detail-page-extract": 1,
    "mode/product-card-extract": 1,
    "mode/heatmap": 1,
    "mode/cross-page": 1,
    "mode/annotate-issues": 1,
    "mode/persona-pick": 2,
    "mode/persona-fit": 2,
    "mode/persona-sample": 2,
    "mode/jury-react": 3,
    "mode/aggregate-consensus": 4,
    "mode/aggregate-distribution-gap": 4,
    "mode/synthesize-tension": 5,
    "mode/synthesize-paths": 5,
    "mode/render-report": 6,
}


def parse_frontmatter(scenario_path: Path) -> dict:
    """Parse the subset of YAML frontmatter used by scenario files."""
    text = scenario_path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise RuntimeError(f"scenario 缺 frontmatter: {scenario_path}")

    raw = match.group(1)
    data: dict = {}
    current_top: str | None = None
    current_nested: str | None = None

    for line in raw.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not line.startswith(" "):
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = value
                current_top = None
                current_nested = None
            else:
                data[key] = {}
                current_top = key
                current_nested = None
        elif line.startswith("  ") and not line.startswith("    "):
            if current_top is None:
                continue
            stripped = line.strip()
            if ":" not in stripped:
                continue
            nested_key, _, value = stripped.partition(":")
            nested_key = nested_key.strip()
            value = value.strip()
            if value:
                data[current_top][nested_key] = value
                current_nested = None
            else:
                data[current_top][nested_key] = []
                current_nested = nested_key
        elif line.startswith("    -"):
            if current_top is None or current_nested is None:
                continue
            item = line.strip()[1:].strip()
            data[current_top][current_nested].append(item)
    return data


def normalize_alias(value: object) -> str:
    return str(value or "").strip().lower()


def scenario_paths() -> list[Path]:
    return sorted(SCENARIOS_DIR.glob("review-*.md"))


def scenario_aliases(frontmatter: dict) -> list[str]:
    raw_aliases = frontmatter.get("artifact_aliases", {}).get("values", [])
    aliases = [frontmatter.get("artifact_type"), frontmatter.get("name"), *raw_aliases]
    return [normalize_alias(alias) for alias in aliases if normalize_alias(alias)]


def select_scenario(artifact_type: str) -> tuple[str, Path]:
    requested = normalize_alias(artifact_type)
    for path in scenario_paths():
        front = parse_frontmatter(path)
        if requested in scenario_aliases(front):
            return path.stem, path
    raise RuntimeError(f"暂未实现 artifact_type='{artifact_type}' 的 scenario")


def default_persona_ids_for_scenario(scenario_slug: str) -> list[str]:
    """Return conservative default jury members declared by a scenario."""
    path = SCENARIOS_DIR / f"{scenario_slug}.md"
    if not path.exists():
        return []
    front = parse_frontmatter(path)
    defaults = front.get("default_personas", {}).get("role_ids", [])
    return list(defaults)


def build_dag(
    scenario_modes: dict,
    distribution_intent: str,
    include: list[str],
    exclude: list[str],
) -> list[dict]:
    """Build the final ordered mode list with inclusion reasons."""
    required = scenario_modes.get("required", [])
    recommended = scenario_modes.get("recommended", [])
    optional = scenario_modes.get("optional", [])
    forbidden = set(scenario_modes.get("forbidden", []))

    dag: list[dict] = []
    seen: set[str] = set()
    persona_picked = False
    persona_mode_for_intent = DISTRIBUTION_TO_MODE.get(distribution_intent)

    def add(mode: str, reason: str) -> None:
        nonlocal persona_picked
        if mode in seen or mode in forbidden:
            return
        if mode in exclude and reason != "required":
            return
        if mode.startswith("mode/persona-"):
            if persona_picked and reason != "include":
                return
            persona_picked = True
        seen.add(mode)
        dag.append({"mode": mode, "reason": reason})

    for mode in required:
        add(mode, "required")

    if persona_mode_for_intent and persona_mode_for_intent not in forbidden:
        add(persona_mode_for_intent, f"distribution_intent={distribution_intent}")

    for mode in recommended:
        if mode.startswith("mode/persona-") and persona_picked:
            continue
        add(mode, "recommended_default")

    for mode in include:
        if mode in forbidden or mode in seen:
            continue
        if mode in optional or mode in recommended:
            add(mode, "include")
        else:
            add(mode, "include_unsanctioned")

    return reorder_dag(dag)


def reorder_dag(dag: list[dict]) -> list[dict]:
    """Order modes by the standard observe → jury → aggregate → synthesize → render flow."""
    return sorted(dag, key=lambda item: STAGE_PRIORITY.get(item["mode"], 99))


def build_plan(brief: dict, include: list[str], exclude: list[str]) -> dict:
    artifact_type = brief["fields"]["artifact_type"].get("value")
    distribution_intent = brief["fields"]["distribution_intent"].get("value", "mock")

    slug, scenario_path = select_scenario(artifact_type)
    front = parse_frontmatter(scenario_path)
    modes = front.get("modes", {})

    dag = build_dag(modes, distribution_intent, include, exclude)
    return {
        "status": "OK",
        "session_id": brief["session_id"],
        "scenario": {
            "slug": slug,
            "name": front.get("name"),
            "artifact_type_slug": front.get("artifact_type"),
            "path": str(scenario_path),
        },
        "brief_summary": {
            "artifact_type": artifact_type,
            "artifact_locator": brief["fields"]["artifact_locator"].get("value"),
            "target_audience": brief["fields"]["target_audience"].get("value"),
            "key_concern": brief["fields"]["key_concern"].get("value"),
            "distribution_intent": distribution_intent,
        },
        "dag": dag,
        "user_overrides": {"include": include, "exclude": exclude},
    }
