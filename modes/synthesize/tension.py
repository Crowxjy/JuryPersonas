#!/usr/bin/env python3
"""
tension.py - build the Phase C tension-synthesis prompt bundle.

This mode does not call an LLM. It packages the consensus/reaction evidence with
the Phase C decision-lens references so an Agent or external model can extract
claim vectors and identify the dominant decision tension.
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


def build_tension_bundle(input_data: Any, *, source_path: Path | None = None) -> dict:
    """Return a model-ready prompt bundle for mode/synthesize-tension."""
    return {
        "mode": "mode/synthesize-tension",
        "llm_required": True,
        "source": str(source_path) if source_path else None,
        "task": {
            "objective": (
                "Extract claim vectors from jury reactions/consensus, group same-axis "
                "positions, and identify the dominant decision tension."
            ),
            "output_contract": {
                "claim_vectors": "array following claim_vector_schema.md",
                "consensus_points": "array of same-axis or non-conflicting claims",
                "candidate_tensions": "array of same-axis opposite-pole conflicts",
                "dominant_tension": "single selected tension with axis, poles, evidence",
                "needs_clarification": "boolean",
                "clarifying_questions": "array, max 3",
            },
        },
        "references": {
            "claim_vector_schema": read_text(PHASE_C_PROMPTS / "claim_vector_schema.md"),
            "tension_axis_library": read_text(PHASE_C_PROMPTS / "tension_axis_library.md"),
            "preference_factors": read_text(PHASE_C_PROMPTS / "preference_factors.md"),
            "facilitator_prompt": read_text(PHASE_C_PROMPTS / "facilitator_prompt.md"),
        },
        "input": input_data,
        "boundary": {
            "do_not_decide_for_user": True,
            "use_only_observed_claims": True,
            "tension_must_be_same_axis_opposite_poles": True,
            "ask_when_constraints_are_missing": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Phase C tension prompt bundle")
    parser.add_argument(
        "--input",
        required=True,
        help="Consensus/reactions JSON produced by aggregate-consensus or jury-react",
    )
    parser.add_argument("--out", required=True, help="Output bundle JSON path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    out_path = Path(args.out)
    bundle = build_tension_bundle(load_json(input_path), source_path=input_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2 if args.pretty else None),
        encoding="utf-8",
    )
    print(json.dumps({"status": "OK", "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
