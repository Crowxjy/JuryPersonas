#!/usr/bin/env python3
"""
persona_pick.py - deterministic implementation of mode/persona-pick.

It validates an explicit role_id list, compiles each persona into a system prompt,
and returns a pick pack for downstream jury-react. No LLM calls are made here.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parents[1]

from compile_persona import compile_persona, find_persona_path


def parse_role_ids(raw: str | None, role_file: str | None) -> list[str]:
    role_ids: list[str] = []
    if raw:
        role_ids.extend(x.strip() for x in raw.split(",") if x.strip())
    if role_file:
        data = json.loads(Path(role_file).read_text(encoding="utf-8"))
        if isinstance(data, list):
            role_ids.extend(str(x).strip() for x in data if str(x).strip())
        elif isinstance(data, dict) and isinstance(data.get("role_ids"), list):
            role_ids.extend(str(x).strip() for x in data["role_ids"] if str(x).strip())
        else:
            raise ValueError("--role-file 必须是 role_id 数组或包含 role_ids 数组的对象")

    seen = set()
    deduped = []
    for role_id in role_ids:
        if role_id in seen:
            continue
        seen.add(role_id)
        deduped.append(role_id)
    return deduped


def pick_personas(role_ids: list[str], *, compile_prompts: bool = True) -> dict[str, Any]:
    pack: dict[str, Any] = {
        "mode": "mode/persona-pick",
        "status": "OK",
        "requested_role_ids": role_ids,
        "selected": [],
        "errors": [],
    }

    for role_id in role_ids:
        try:
            path = find_persona_path(role_id)
            try:
                display_path = str(path.relative_to(SKILL_ROOT))
            except ValueError:
                display_path = str(path)
            item: dict[str, Any] = {
                "role_id": role_id,
                "path": display_path,
            }
            if compile_prompts:
                compiled = compile_persona(role_id)
                meta = compiled["meta"]
                item.update(
                    {
                        "name": meta.get("name", role_id),
                        "category": meta.get("category", ""),
                        "sub_category": meta.get("sub_category", ""),
                        "status": meta.get("status", ""),
                        "knowledge_files": compiled["knowledge_files"],
                        "system_prompt": compiled["system_prompt"],
                    }
                )
            pack["selected"].append(item)
        except (FileNotFoundError, RuntimeError) as exc:
            pack["errors"].append({"role_id": role_id, "error": str(exc)})

    if pack["errors"]:
        pack["status"] = "PARTIAL" if pack["selected"] else "ERROR"
    return pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pick and compile explicit personas")
    parser.add_argument("--role-ids", help="Comma-separated role_id list")
    parser.add_argument("--role-file", help="JSON list or object with role_ids")
    parser.add_argument("--out", help="Output JSON path; default stdout")
    parser.add_argument(
        "--no-compile",
        action="store_true",
        help="Only validate role ids and paths; do not emit system_prompt",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        role_ids = parse_role_ids(args.role_ids, args.role_file)
    except ValueError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2

    if not role_ids:
        print(json.dumps({"status": "ERROR", "error": "未提供 role_id"}, ensure_ascii=False))
        return 2

    pack = pick_personas(role_ids, compile_prompts=not args.no_compile)
    text = json.dumps(pack, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0 if pack["status"] in {"OK", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
