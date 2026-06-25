#!/usr/bin/env python3
"""
prd_extract.py - lightweight deterministic PRD structure extractor.

This mode does not judge the PRD. It extracts headings, requirement-like lines,
risks, open questions, and decision keywords into an observation JSON that can be
fed to jury-react or synthesize modes.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)]|[（(]?\d+[）)])\s+(.+?)\s*$")
MUST_RE = re.compile(r"(必须|需要|需|should|must|required|不得|禁止|不允许)", re.I)
RISK_RE = re.compile(r"(风险|问题|限制|依赖|红线|合规|异常|失败|不可|不能|blocked?)", re.I)
METRIC_RE = re.compile(r"(指标|转化|点击|留存|完播|GMV|CTR|CVR|ROI|核销|成交|DAU|MAU)", re.I)
QUESTION_RE = re.compile(r"(待确认|Q[:：]|\?|？|TODO|待定|open question)", re.I)
DECISION_RE = re.compile(r"(方案|路径|取舍|决策|A/B|AB|优先级|trade.?off|张力)", re.I)


def read_input(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"PRD 文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def current_section(stack: list[dict]) -> str:
    return " > ".join(item["title"] for item in stack) if stack else "ROOT"


def append_limited(items: list[dict], item: dict, limit: int) -> None:
    if len(items) < limit:
        items.append(item)


def extract_prd(text: str, *, source: str | None = None, max_items: int = 80) -> dict[str, Any]:
    headings = []
    requirements = []
    risks = []
    metrics = []
    questions = []
    decisions = []
    stack: list[dict] = []

    lines = text.splitlines()
    for line_no, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            while stack and stack[-1]["level"] >= level:
                stack.pop()
            stack.append({"level": level, "title": title, "line": line_no})
            append_limited(headings, {"level": level, "title": title, "line": line_no}, max_items)
            continue

        bullet = LIST_RE.match(raw)
        content = bullet.group(1).strip() if bullet else line
        section = current_section(stack)
        item = {"line": line_no, "section": section, "text": content}

        if MUST_RE.search(content):
            append_limited(requirements, item, max_items)
        if RISK_RE.search(content):
            append_limited(risks, item, max_items)
        if METRIC_RE.search(content):
            append_limited(metrics, item, max_items)
        if QUESTION_RE.search(content):
            append_limited(questions, item, max_items)
        if DECISION_RE.search(content):
            append_limited(decisions, item, max_items)

    return {
        "mode": "mode/prd-extract",
        "source": source,
        "line_count": len(lines),
        "headings": headings,
        "requirements": requirements,
        "risks": risks,
        "metrics": metrics,
        "open_questions": questions,
        "decision_points": decisions,
        "summary": {
            "n_headings": len(headings),
            "n_requirements": len(requirements),
            "n_risks": len(risks),
            "n_metrics": len(metrics),
            "n_open_questions": len(questions),
            "n_decision_points": len(decisions),
        },
        "boundary": {
            "deterministic_extraction_only": True,
            "no_quality_judgement": True,
            "manual_review_required_for_pdf_docx": source is not None
            and Path(source).suffix.lower() in {".pdf", ".doc", ".docx"},
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract PRD structure into observation JSON")
    parser.add_argument("--input", required=True, help="PRD text/markdown file")
    parser.add_argument("--out", help="Output JSON path; default stdout")
    parser.add_argument("--max-items", type=int, default=80, help="Max items per bucket")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    data = extract_prd(read_input(input_path), source=str(input_path), max_items=args.max_items)
    text = json.dumps(data, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
