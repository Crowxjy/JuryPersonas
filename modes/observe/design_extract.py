#!/usr/bin/env python3
"""design_extract.py - deterministic design draft observation extractor."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from visual_extract_common import build_observation, read_text, write_or_print


REQUIRED_SIGNALS = {
    "layout": "页面结构/关键区域",
    "cta": "核心行动点",
    "trust": "信任或证明信息",
}


def extract_design(text: str, *, source: str | None = None, max_items: int = 60) -> dict[str, Any]:
    return build_observation(
        text,
        mode="mode/design-extract",
        source=source,
        required_signals=REQUIRED_SIGNALS,
        max_items=max_items,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract design draft observation JSON")
    parser.add_argument("--input", required=True, help="Design description Markdown/text/JSON")
    parser.add_argument("--out", help="Output JSON path; default stdout")
    parser.add_argument("--max-items", type=int, default=60, help="Max items per bucket")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    data = extract_design(read_text(input_path), source=str(input_path), max_items=args.max_items)
    write_or_print(data, args.out, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
