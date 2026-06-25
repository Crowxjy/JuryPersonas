#!/usr/bin/env python3
"""
markdown_renderer.py - small generic Markdown renderer for JuryPersonas reports.

Specialized renderers such as modes/render/report.py can keep their templates.
This module covers generic report assembly: title, summary table, sections, and
boundary notes. It is intentionally dependency-free and deterministic.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def escape_cell(value: Any) -> str:
    text = "—" if value is None else str(value)
    return text.replace("\n", "<br>").replace("|", "\\|")


def render_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    keys = list(rows[0].keys())
    out = [
        "| " + " | ".join(keys) + " |",
        "| " + " | ".join("---" for _ in keys) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(escape_cell(row.get(k)) for k in keys) + " |")
    return "\n".join(out)


def render_sections(sections: list[dict]) -> str:
    chunks = []
    for section in sections:
        title = section.get("title", "未命名章节")
        chunks.append(f"## {title}")
        if section.get("body"):
            chunks.append(str(section["body"]))
        if isinstance(section.get("table"), list):
            table = render_table(section["table"])
            if table:
                chunks.append(table)
        chunks.append("")
    return "\n".join(chunks).rstrip()


def render_report(data: dict) -> str:
    title = data.get("title", "JuryPersonas 评审报告")
    chunks = [f"# {title}", ""]

    if summary := data.get("summary"):
        if isinstance(summary, dict):
            chunks.append("## 摘要")
            for key, value in summary.items():
                chunks.append(f"- **{key}**:{escape_cell(value)}")
            chunks.append("")
        else:
            chunks.append(str(summary))
            chunks.append("")

    sections = data.get("sections", [])
    if isinstance(sections, list):
        body = render_sections(sections)
        if body:
            chunks.append(body)
            chunks.append("")

    boundaries = data.get("boundaries", [])
    if boundaries:
        chunks.append("## 边界声明")
        for item in boundaries:
            chunks.append(f"- {item}")
        chunks.append("")

    return "\n".join(chunks).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a generic JuryPersonas Markdown report")
    parser.add_argument("--input", required=True, help="Report JSON path")
    parser.add_argument("--output", required=True, help="Markdown output path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(data), encoding="utf-8")
    print(json.dumps({"status": "OK", "output": str(output_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
