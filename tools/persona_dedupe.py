#!/usr/bin/env python3
"""
persona_dedupe.py - persona fingerprint scanner and conflict reporter.

Default behavior is read-only: scan personas, infer stable fingerprints, and
print merge/coexist/replace recommendations. It never edits persona files.

Use --write-index only when you want to refresh personas/_fingerprint_index.json.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TOOLS_DIR.parent
PERSONAS_DIR = SKILL_ROOT / "personas"
INDEX_PATH = PERSONAS_DIR / "_fingerprint_index.json"
MERGE_DECISIONS_PATH = PERSONAS_DIR / "_merge_decisions.json"


def load_bootstrap():
    spec = importlib.util.spec_from_file_location(
        "jury_personas_bootstrap",
        SKILL_ROOT / "orchestrator" / "bootstrap.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 orchestrator/bootstrap.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


load_bootstrap().ensure_skill_import_paths()

from compile_persona import infer_legacy_expert_imports, parse_frontmatter  # noqa: E402

FIDELITY_RANK = {
    "pool-sampled": 1,
    "fit-synthesized": 2,
    "slice-built": 3,
    "handcraft": 4,
    "legacy-expert-roundtable": 4,
    "merged": 5,
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", "", text)
    return text


def normalize_tags(tags: Any) -> list[str]:
    if not isinstance(tags, list):
        return []
    return sorted({normalize_text(t) for t in tags if normalize_text(t)})


def age_band(age: Any) -> str:
    if age is None:
        return ""
    match = re.search(r"\d+", str(age))
    if not match:
        return ""
    n = int(match.group(0))
    if n < 18:
        return "<18"
    low = (n // 5) * 5
    high = low + 4
    return f"{low}-{high}"


def city_tier(city: Any) -> str:
    text = str(city or "")
    if any(x in text for x in ("北京", "上海", "广州", "深圳", "杭州")):
        return "1"
    if any(x in text for x in ("成都", "重庆", "武汉", "南京", "苏州", "南昌", "西安")):
        return "2"
    if any(x in text for x in ("三线", "四线", "县城", "下沉")):
        return "3-4"
    return ""


def get_source_kind(meta: dict, persona_path: Path) -> str:
    source = meta.get("source")
    if isinstance(source, dict) and source.get("kind"):
        return str(source["kind"])
    metadata = meta.get("metadata") or {}
    if persona_path.parent.name == "experts" and isinstance(metadata, dict) and metadata.get("role"):
        return "legacy-expert-roundtable"
    if persona_path.parts and "_ephemeral" in persona_path.parts:
        return "fit-synthesized"
    return "handcraft"


def infer_role_family(meta: dict, persona_path: Path) -> str:
    metadata = meta.get("metadata") or {}
    if isinstance(metadata, dict) and metadata.get("role"):
        return normalize_text(metadata["role"])

    haystack = " ".join(
        str(x)
        for x in [
            meta.get("id"),
            meta.get("name"),
            meta.get("category"),
            meta.get("sub_category"),
            " ".join(str(t) for t in meta.get("tags", []) or []),
            persona_path.stem,
        ]
        if x
    ).lower()
    rules = [
        ("am_area_manager", ["am-area-manager", "区域经理", "area-manager"]),
        ("cm_city_manager", ["cm-city-manager", "城市经理", "city-manager"]),
        ("bdm_sales_team_lead", ["bdm-sales-team-lead", "销售团队管理", "bdm"]),
        ("ka_bd", ["ka-bd", "ka bd", "ka_bd", "头部客户"]),
        ("offline_bd", ["offline-bd", "offline_bd", "线下bd", "网格"]),
        ("self_serve_bd", ["self-serve-bd", "self_serve_bd", "自助"]),
        ("regional_director", ["regional-director", "大区", "区域总监"]),
        ("ad_buyer", ["ad-buyer", "ad_buyer", "广告投手", "投手", "千川", "巨量引擎"]),
        ("product_expert", ["product", "产品专家", "产品经理", "pm"]),
        ("local_business", ["local-business", "local_business", "本地服务", "商家"]),
        ("ux_designer", ["ux", "designer", "设计师", "设计"]),
        ("consumer_bao_mom", ["宝妈", "妈妈"]),
        ("consumer_silver", ["银发", "老年"]),
        ("consumer_bluecollar", ["蓝领", "工友"]),
        ("consumer_genz", ["genz", "z世代", "年轻女性"]),
        ("bd", ["bd", "客户经营", "ka", "区域", "商服"]),
    ]
    for family, needles in rules:
        if any(n.lower() in haystack for n in needles):
            return family
    return normalize_text(meta.get("category") or persona_path.parent.name)


def explicit_or_inferred_fingerprint(meta: dict, persona_path: Path) -> dict:
    explicit = meta.get("fingerprint")
    if isinstance(explicit, dict):
        fp = dict(explicit)
    else:
        basic = meta.get("basic") if isinstance(meta.get("basic"), dict) else {}
        fp = {
            "category": meta.get("category") or persona_path.parent.name,
            "sub_category": meta.get("sub_category") or "",
            "age_band": age_band(basic.get("age")),
            "gender": basic.get("gender") or "",
            "city_tier": city_tier(basic.get("city")),
            "role_family": infer_role_family(meta, persona_path),
            "signature_tags": normalize_tags(meta.get("tags")),
        }

    fp["role_family"] = normalize_text(fp.get("role_family") or infer_role_family(meta, persona_path))
    fp["category"] = normalize_text(fp.get("category"))
    fp["sub_category"] = normalize_text(fp.get("sub_category"))
    fp["age_band"] = normalize_text(fp.get("age_band"))
    fp["gender"] = normalize_text(fp.get("gender"))
    fp["city_tier"] = normalize_text(fp.get("city_tier"))
    fp["signature_tags"] = normalize_tags(fp.get("signature_tags"))
    return fp


def fingerprint_key(fp: dict) -> str:
    fields = [
        fp.get("category", ""),
        fp.get("sub_category", ""),
        fp.get("age_band", ""),
        fp.get("gender", ""),
        fp.get("city_tier", ""),
        fp.get("role_family", ""),
        ",".join(fp.get("signature_tags", [])),
    ]
    return "|".join(fields)


def load_personas() -> list[dict]:
    records = []
    for path in sorted(PERSONAS_DIR.rglob("*.md")):
        if path.name.startswith("_") or "_ephemeral" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        role_id = meta.get("id") or path.stem
        source_kind = get_source_kind(meta, path)
        fp = explicit_or_inferred_fingerprint(meta, path)
        imports = meta.get("imports", []) or infer_legacy_expert_imports(meta)
        records.append(
            {
                "id": role_id,
                "path": str(path.relative_to(SKILL_ROOT)),
                "name": meta.get("name") or "",
                "status": meta.get("status") or "legacy",
                "source_kind": source_kind,
                "fidelity_rank": FIDELITY_RANK.get(source_kind, 0),
                "role_family": fp["role_family"],
                "fingerprint": fp,
                "fingerprint_key": fingerprint_key(fp),
                "imports": imports,
                "body_chars": len(body),
            }
        )
    return records


def load_merge_decisions() -> list[dict]:
    if not MERGE_DECISIONS_PATH.exists():
        return []
    data = json.loads(MERGE_DECISIONS_PATH.read_text(encoding="utf-8"))
    decisions = data.get("decisions", [])
    return [d for d in decisions if d.get("status") == "merged"]


def resolved_by_decision(conflict: dict, decisions: list[dict]) -> dict | None:
    persona_ids = {r["id"] for r in conflict["personas"]}
    for decision in decisions:
        resolved_ids = set(decision.get("source_role_ids", []))
        merged_role_id = decision.get("merged_role_id")
        if merged_role_id:
            resolved_ids.add(merged_role_id)
        if persona_ids and persona_ids.issubset(resolved_ids):
            return {
                "decision_id": decision.get("decision_id"),
                "merged_role_id": merged_role_id,
                "source_role_ids": decision.get("source_role_ids", []),
                "default_role_id": decision.get("default_role_id") or merged_role_id,
                "preserve_legacy_files": bool(decision.get("preserve_legacy_files")),
                "reason": decision.get("reason") or "",
            }
    return None


def apply_merge_decisions(conflicts: list[dict], decisions: list[dict]) -> tuple[list[dict], list[dict]]:
    unresolved = []
    resolved = []
    for conflict in conflicts:
        decision = resolved_by_decision(conflict, decisions)
        if decision:
            resolved.append(
                {
                    "type": conflict["type"],
                    "key": conflict["key"],
                    "personas": conflict["personas"],
                    "resolution": decision,
                }
            )
        else:
            unresolved.append(conflict)
    return unresolved, resolved


def choose_primary(records: list[dict]) -> dict:
    return sorted(
        records,
        key=lambda r: (
            r["fidelity_rank"],
            r["status"] == "active",
            r["body_chars"],
            r["id"],
        ),
        reverse=True,
    )[0]


def recommendation(records: list[dict], conflict_type: str) -> dict:
    primary = choose_primary(records)
    others = [r for r in records if r["id"] != primary["id"]]
    if conflict_type == "exact_fingerprint":
        strategy = "merge_or_replace"
        reason = "fingerprint 完全一致,默认保留保真度更高/信息量更大的画像"
    else:
        strategy = "coexist_or_merge"
        reason = "role_family 相同但 fingerprint 不完全一致,需要人工判断是细分共存还是合并"
    return {
        "strategy": strategy,
        "primary_candidate": primary["id"],
        "secondary_candidates": [r["id"] for r in others],
        "reason": reason,
    }


def find_conflicts(records: list[dict]) -> list[dict]:
    conflicts = []

    by_key: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_key[record["fingerprint_key"]].append(record)
    for key, group in by_key.items():
        if len(group) > 1:
            conflicts.append(
                {
                    "type": "exact_fingerprint",
                    "key": key,
                    "personas": group,
                    "recommendation": recommendation(group, "exact_fingerprint"),
                }
            )

    by_family: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_family[record["role_family"]].append(record)
    exact_ids = {r["id"] for c in conflicts for r in c["personas"]}
    for family, group in by_family.items():
        source_kinds = {r["source_kind"] for r in group}
        has_committed_persona = any(
            r["status"] == "active" or r["source_kind"] == "legacy-expert-roundtable"
            for r in group
        )
        high_risk_overlap = len(source_kinds) > 1 or has_committed_persona
        if len(group) > 1 and high_risk_overlap and not all(r["id"] in exact_ids for r in group):
            conflicts.append(
                {
                    "type": "role_family_overlap",
                    "key": family,
                    "personas": group,
                    "recommendation": recommendation(group, "role_family_overlap"),
                }
            )

    return conflicts


def build_index(records: list[dict], conflicts: list[dict], resolved_conflicts: list[dict]) -> dict:
    return {
        "schema_version": "1.0",
        "generated_by": "tools/persona_dedupe.py",
        "personas": records,
        "conflicts": [
            {
                "type": c["type"],
                "key": c["key"],
                "persona_ids": [r["id"] for r in c["personas"]],
                "recommendation": c["recommendation"],
            }
            for c in conflicts
        ],
        "resolved_conflicts": [
            {
                "type": c["type"],
                "key": c["key"],
                "persona_ids": [r["id"] for r in c["personas"]],
                "resolution": c["resolution"],
            }
            for c in resolved_conflicts
        ],
    }


def print_markdown(records: list[dict], conflicts: list[dict], resolved_conflicts: list[dict]) -> None:
    print("# Persona Dedupe Report")
    print("")
    print(f"- personas: {len(records)}")
    print(f"- conflicts: {len(conflicts)}")
    print(f"- resolved_conflicts: {len(resolved_conflicts)}")
    print("")
    if not conflicts and not resolved_conflicts:
        print("No fingerprint conflicts found.")
        return
    if resolved_conflicts:
        print("## Resolved")
        print("")
        for conflict in resolved_conflicts:
            ids = ", ".join(f"`{r['id']}`" for r in conflict["personas"])
            resolution = conflict["resolution"]
            print(
                f"- {conflict['type']} `{conflict['key']}`: {ids} -> "
                f"`{resolution['default_role_id']}` "
                f"({resolution['decision_id']})"
            )
        print("")
    if not conflicts:
        print("No unresolved fingerprint conflicts found.")
        return
    for idx, conflict in enumerate(conflicts, 1):
        print(f"## {idx}. {conflict['type']} `{conflict['key']}`")
        print("")
        for record in conflict["personas"]:
            print(
                f"- `{record['id']}` ({record['source_kind']}, {record['status']}) "
                f"- `{record['path']}`"
            )
        rec = conflict["recommendation"]
        print("")
        print(f"recommendation: `{rec['strategy']}`")
        print(f"primary_candidate: `{rec['primary_candidate']}`")
        print(f"reason: {rec['reason']}")
        print("")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan persona fingerprints and report conflicts")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument(
        "--write-index",
        action="store_true",
        help="Write personas/_fingerprint_index.json",
    )
    parser.add_argument(
        "--fail-on-conflict",
        action="store_true",
        help="Exit 1 when any conflict is found (for CI/gates)",
    )
    args = parser.parse_args()

    records = load_personas()
    raw_conflicts = find_conflicts(records)
    merge_decisions = load_merge_decisions()
    conflicts, resolved_conflicts = apply_merge_decisions(raw_conflicts, merge_decisions)
    index = build_index(records, conflicts, resolved_conflicts)

    if args.write_index:
        INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(index, ensure_ascii=False, indent=2))
    else:
        print_markdown(records, conflicts, resolved_conflicts)

    return 1 if args.fail_on_conflict and conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
