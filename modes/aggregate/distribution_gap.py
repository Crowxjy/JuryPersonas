#!/usr/bin/env python3
"""
distribution_gap.py - mode/aggregate-distribution-gap.

Compare a merchant/current joint distribution with a target/category joint
distribution and produce F6-style gap rows. This mode does not invent user
feedback; optional consensus/evaluation inputs are only used as evidence links.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_distribution(path: Path) -> dict[str, Any]:
    data = load_json(path)
    required = {"axes", "joint_distribution"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"{path} 缺字段: {sorted(missing)}")
    total = sum(float(bucket.get("weight", 0)) for bucket in data["joint_distribution"])
    data["_weight_sum"] = round(total, 6)
    data["_weight_warning"] = abs(total - 1.0) > 0.05
    return data


def bucket_key(bucket: dict[str, Any], axes: list[str]) -> tuple[tuple[str, str], ...]:
    return tuple((axis, str(bucket.get(axis, ""))) for axis in axes)


def label_from_key(key: tuple[tuple[str, str], ...]) -> str:
    return "/".join(value for _, value in key if value) or "未命名桶"


def infer_direction(delta: float) -> str:
    if delta > 0.05:
        return "目标增配"
    if delta < -0.05:
        return "目标降配"
    return "轻微变化"


def infer_action(delta: float) -> str:
    if delta > 0.05:
        return "补充该桶画像或提高该桶在采样陪审团中的权重"
    if delta < -0.05:
        return "保留现有基础盘,但避免让该桶声音过度代表目标增长人群"
    return "维持观察,不建议单独调整陪审团权重"


def normalize_tokens(values: list[Any]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = str(value or "")
        for token in text.replace("，", ",").replace("、", ",").split(","):
            token = token.strip()
            if token:
                tokens.add(token)
    return tokens


def find_related_complaints(row: dict[str, Any], consensus: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not consensus:
        return []
    tags = normalize_tokens(row.get("tags_hint", []))
    axis_tokens = normalize_tokens([row.get("bucket")])
    needles = tags | axis_tokens
    if not needles:
        return []
    related = []
    for complaint in consensus.get("complaints", []):
        text = json.dumps(complaint, ensure_ascii=False)
        if any(token and token in text for token in needles):
            related.append(
                {
                    "role_id": complaint.get("role_id"),
                    "concern": complaint.get("concern"),
                    "position": complaint.get("position_canonical") or complaint.get("position"),
                }
            )
    return related[:5]


def build_gap_rows(
    current: dict[str, Any],
    target: dict[str, Any],
    *,
    min_abs_delta: float,
    consensus: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    common_axes = [axis for axis in current.get("axes", []) if axis in target.get("axes", [])]
    current_map = {
        bucket_key(bucket, common_axes): bucket
        for bucket in current.get("joint_distribution", [])
    }
    target_map = {
        bucket_key(bucket, common_axes): bucket
        for bucket in target.get("joint_distribution", [])
    }

    rows = []
    for key in sorted(set(current_map) | set(target_map), key=label_from_key):
        current_bucket = current_map.get(key, {})
        target_bucket = target_map.get(key, {})
        current_weight = float(current_bucket.get("weight", 0))
        target_weight = float(target_bucket.get("weight", 0))
        delta = target_weight - current_weight
        if abs(delta) < min_abs_delta:
            continue
        tags_hint = target_bucket.get("tags_hint") or current_bucket.get("tags_hint") or []
        row = {
            "bucket": label_from_key(key),
            "axes": {axis: value for axis, value in key},
            "current_weight": round(current_weight, 4),
            "target_weight": round(target_weight, 4),
            "delta": round(delta, 4),
            "abs_delta": round(abs(delta), 4),
            "direction": infer_direction(delta),
            "recommended_action": infer_action(delta),
            "tags_hint": tags_hint,
        }
        row["related_complaints"] = find_related_complaints(row, consensus)
        rows.append(row)

    rows.sort(key=lambda item: (-item["abs_delta"], item["bucket"]))
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    target_increase = [row for row in rows if row["delta"] > 0]
    target_decrease = [row for row in rows if row["delta"] < 0]
    return {
        "n_gap_rows": len(rows),
        "n_target_increase": len(target_increase),
        "n_target_decrease": len(target_decrease),
        "top_increase": target_increase[0] if target_increase else None,
        "top_decrease": target_decrease[0] if target_decrease else None,
    }


def build_pack(
    current: dict[str, Any],
    target: dict[str, Any],
    *,
    current_path: Path,
    target_path: Path,
    consensus: dict[str, Any] | None,
    consensus_path: Path | None,
    min_abs_delta: float,
) -> dict[str, Any]:
    rows = build_gap_rows(
        current,
        target,
        min_abs_delta=min_abs_delta,
        consensus=consensus,
    )
    return {
        "mode": "mode/aggregate-distribution-gap",
        "inputs": {
            "current_distribution": str(current_path),
            "target_distribution": str(target_path),
            "consensus": str(consensus_path) if consensus_path else None,
            "min_abs_delta": min_abs_delta,
        },
        "current": {
            "id": current.get("merchant_id") or current.get("category_id"),
            "name": current.get("merchant_name") or current.get("category_name"),
            "axes": current.get("axes", []),
            "weight_sum": current.get("_weight_sum"),
            "weight_warning": current.get("_weight_warning"),
        },
        "target": {
            "id": target.get("category_id") or target.get("merchant_id"),
            "name": target.get("category_name") or target.get("merchant_name"),
            "axes": target.get("axes", []),
            "weight_sum": target.get("_weight_sum"),
            "weight_warning": target.get("_weight_warning"),
        },
        "gap_rows": rows,
        "summary": summarize(rows),
        "boundary": {
            "deterministic_distribution_compare_only": True,
            "no_real_effect_claim_without_feedback_data": True,
            "consensus_links_are_evidence_only": consensus is not None,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="mode/aggregate-distribution-gap")
    parser.add_argument("--current-dist", required=True, help="Current/merchant distribution JSON")
    parser.add_argument("--target-dist", required=True, help="Target/category distribution JSON")
    parser.add_argument("--consensus-file", help="Optional consensus pack JSON")
    parser.add_argument("--min-abs-delta", type=float, default=0.02)
    parser.add_argument("--output", "-o", help="Output JSON path; stdout when omitted")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    current_path = Path(args.current_dist)
    target_path = Path(args.target_dist)
    consensus_path = Path(args.consensus_file) if args.consensus_file else None

    current = load_distribution(current_path)
    target = load_distribution(target_path)
    consensus = load_json(consensus_path) if consensus_path else None
    pack = build_pack(
        current,
        target,
        current_path=current_path,
        target_path=target_path,
        consensus=consensus,
        consensus_path=consensus_path,
        min_abs_delta=args.min_abs_delta,
    )
    output = json.dumps(pack, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
