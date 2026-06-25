#!/usr/bin/env python3
"""
reaction_handoff.py - prepare and validate host Agent/model reaction handoff.

This tool keeps JuryPersonas in Skill form: deterministic scripts prepare a
bundle, while the host Agent/model reads each participant prompt and writes
participants[*].reaction back into the bundle.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def log_event(event: str, **fields: Any) -> None:
    """Write human-readable diagnostics to stderr, keeping stdout JSON-clean."""
    parts = [f"[handoff] {datetime.now().isoformat(timespec='seconds')} {event}"]
    for key, value in fields.items():
        parts.append(f"{key}={value}")
    print(" ".join(parts), file=sys.stderr)


def load_bundle(path: Path) -> dict[str, Any]:
    log_event("load_bundle.start", path=path)
    if not path.exists():
        raise FileNotFoundError(f"bundle 不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("bundle 必须是 JSON object")
    if data.get("mode") != "mode/jury-react":
        raise ValueError(f"bundle.mode 非法: {data.get('mode')!r},期望 mode/jury-react")
    if not isinstance(data.get("participants"), list) or not data["participants"]:
        raise ValueError("bundle.participants 必须是非空数组")
    log_event(
        "load_bundle.ok",
        session_id=data.get("session_id"),
        scenario=data.get("scenario"),
        participants=len(data["participants"]),
    )
    return data


def safe_filename(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z._-]+", "_", value.strip())
    return value.strip("._") or "participant"


def validate_participants(bundle: dict[str, Any]) -> dict[str, Any]:
    participants = bundle.get("participants", [])
    log_event(
        "validate.start",
        session_id=bundle.get("session_id"),
        participants=len(participants),
    )
    rows = []
    missing_prompt = []
    missing_reaction = []
    for idx, participant in enumerate(participants):
        role_id = participant.get("role_id") or f"participant_{idx}"
        has_system = bool(str(participant.get("system_prompt") or "").strip())
        has_user = bool(str(participant.get("user_prompt") or "").strip())
        reaction = str(participant.get("reaction") or "").strip()
        if not (has_system and has_user):
            missing_prompt.append(role_id)
        if not reaction:
            missing_reaction.append(role_id)
        rows.append(
            {
                "role_id": role_id,
                "name": participant.get("name") or role_id,
                "has_system_prompt": has_system,
                "has_user_prompt": has_user,
                "has_reaction": bool(reaction),
                "reaction_chars": len(reaction),
            }
        )
    result = {
        "session_id": bundle.get("session_id"),
        "scenario": bundle.get("scenario"),
        "n_participants": len(participants),
        "participants": rows,
        "missing_prompt_role_ids": missing_prompt,
        "missing_reaction_role_ids": missing_reaction,
        "ready_for_host_agent": not missing_prompt,
        "ready_for_resume": not missing_prompt and not missing_reaction,
    }
    log_event(
        "validate.done",
        missing_prompts=len(missing_prompt),
        missing_reactions=len(missing_reaction),
        ready_for_host_agent=result["ready_for_host_agent"],
        ready_for_resume=result["ready_for_resume"],
    )
    return result


def render_prompt_file(bundle: dict[str, Any], participant: dict[str, Any]) -> str:
    role_id = participant.get("role_id", "unknown")
    header = {
        "session_id": bundle.get("session_id"),
        "scenario": bundle.get("scenario"),
        "role_id": role_id,
        "name": participant.get("name", role_id),
        "category": participant.get("category", ""),
        "sub_category": participant.get("sub_category", ""),
    }
    return "\n".join(
        [
            "# JuryPersonas Host Agent Reaction Task",
            "",
            "## Metadata",
            "",
            "```json",
            json.dumps(header, ensure_ascii=False, indent=2),
            "```",
            "",
            "## System Prompt",
            "",
            "```text",
            str(participant.get("system_prompt") or "").rstrip(),
            "```",
            "",
            "## User Prompt",
            "",
            "```text",
            str(participant.get("user_prompt") or "").rstrip(),
            "```",
            "",
            "## Fill Back Contract",
            "",
            "宿主 Agent/模型只需要把本次独立陈述写回原 bundle 的对应字段:",
            "",
            "```json",
            json.dumps(
                {
                    "role_id": role_id,
                    "reaction": "在这里写完整陪审员独立陈述,保持 user prompt 要求的结构",
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
            "边界:不要读取其他陪审员 prompt 或 reaction;每位陪审员必须独立判断。",
            "",
        ]
    )


def export_prompts(bundle: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    log_event(
        "export_prompts.start",
        out_dir=out_dir,
        participants=len(bundle.get("participants", [])),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "session_id": bundle.get("session_id"),
        "scenario": bundle.get("scenario"),
        "prompt_files": [],
    }
    for idx, participant in enumerate(bundle.get("participants", [])):
        role_id = participant.get("role_id") or f"participant_{idx}"
        prompt_path = out_dir / f"{idx + 1:02d}_{safe_filename(role_id)}.md"
        prompt_path.write_text(render_prompt_file(bundle, participant), encoding="utf-8")
        log_event("export_prompts.write_prompt", role_id=role_id, path=prompt_path)
        manifest["prompt_files"].append(
            {
                "role_id": role_id,
                "name": participant.get("name") or role_id,
                "path": str(prompt_path),
            }
        )
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log_event("export_prompts.write_manifest", path=manifest_path)
    return {**manifest, "manifest": str(manifest_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare/validate host Agent reaction handoff")
    parser.add_argument("--bundle-file", required=True, help="jury-react bundle JSON path")
    parser.add_argument("--export-prompts", help="Export one Markdown prompt file per participant")
    parser.add_argument("--check-filled", action="store_true", help="Validate participants[*].reaction")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    log_event(
        "main.start",
        bundle_file=args.bundle_file,
        export_prompts=bool(args.export_prompts),
        check_filled=args.check_filled,
    )
    try:
        bundle = load_bundle(Path(args.bundle_file))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        log_event("main.error", error=exc)
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2

    result: dict[str, Any] = {"status": "OK", "bundle": str(Path(args.bundle_file))}
    validation = validate_participants(bundle)
    result["validation"] = validation

    if args.export_prompts:
        result["export"] = export_prompts(bundle, Path(args.export_prompts))

    if args.check_filled and not validation["ready_for_resume"]:
        result["status"] = "REACTIONS_INCOMPLETE"
        log_event(
            "main.reactions_incomplete",
            missing_reactions=",".join(validation["missing_reaction_role_ids"]),
        )
    else:
        log_event("main.done", status=result["status"])

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
