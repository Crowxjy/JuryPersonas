#!/usr/bin/env python3
"""
paths.py - build the Phase C dual decision-path prompt bundle.

This mode starts after mode/synthesize-tension. It packages the dominant tension
with the facilitator prompt and preference-factor library so an Agent or external
model can produce two same-axis decision paths without making the final decision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parents[1]
PHASE_C_PROMPTS = SKILL_ROOT / "core" / "prompts" / "phase_c"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_paths_bundle(tension_pack: Any, *, source_path: Path | None = None) -> dict:
    """Return a model-ready prompt bundle for mode/synthesize-paths."""
    return {
        "mode": "mode/synthesize-paths",
        "llm_required": True,
        "source": str(source_path) if source_path else None,
        "task": {
            "objective": (
                "Generate two comparable decision paths from the dominant tension. "
                "Each path must map to one pole of the same tension axis."
            ),
            "output_contract": {
                "tension_summary": "plain-language sentence",
                "path_a": {
                    "name": "short label",
                    "core_action": "what to do",
                    "validation": "how to verify",
                    "applies_when": "required conditions",
                    "preference_factors": "factor names only, no factor IDs",
                },
                "path_b": {
                    "name": "short label",
                    "core_action": "what to do",
                    "validation": "how to verify",
                    "applies_when": "required conditions",
                    "preference_factors": "factor names only, no factor IDs",
                },
                "inclination_hint": "conditional hint only; never a final ruling",
                "boundary_statement": "final decision belongs to the human user",
            },
        },
        "references": {
            "facilitator_prompt": read_text(PHASE_C_PROMPTS / "facilitator_prompt.md"),
            "tension_axis_library": read_text(PHASE_C_PROMPTS / "tension_axis_library.md"),
            "preference_factors": read_text(PHASE_C_PROMPTS / "preference_factors.md"),
            "claim_vector_schema": read_text(PHASE_C_PROMPTS / "claim_vector_schema.md"),
        },
        "input": tension_pack,
        "boundary": {
            "do_not_decide_for_user": True,
            "paths_must_share_one_axis": True,
            "paths_must_use_opposite_poles": True,
            "factor_names_only_in_user_output": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Phase C decision-path prompt bundle")
    parser.add_argument(
        "--tension",
        required=True,
        help="JSON produced by host Agent/model from mode/synthesize-tension bundle",
    )
    parser.add_argument("--out", required=True, help="Output bundle JSON path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tension_path = Path(args.tension)
    out_path = Path(args.out)
    bundle = build_paths_bundle(load_json(tension_path), source_path=tension_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2 if args.pretty else None),
        encoding="utf-8",
    )
    print(json.dumps({"status": "OK", "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
