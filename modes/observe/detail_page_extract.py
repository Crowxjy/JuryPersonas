#!/usr/bin/env python3
"""detail_page_extract.py - deterministic detail page observation extractor."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from visual_extract_common import build_observation, read_text, write_or_print


REQUIRED_SIGNALS = {
    "price_or_offer": "价格/权益/套餐",
    "trust": "评价/销量/品牌等信任证据",
    "rules": "核销/退款/有效期等规则",
    "cta": "下单/预约/咨询等行动点",
}


def extract_detail_page(text: str, *, source: str | None = None, max_items: int = 60) -> dict[str, Any]:
    return build_observation(
        text,
        mode="mode/detail-page-extract",
        source=source,
        required_signals=REQUIRED_SIGNALS,
        max_items=max_items,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract detail page observation JSON")
    parser.add_argument("--input", required=True, help="Detail page description Markdown/text/JSON")
    parser.add_argument("--out", help="Output JSON path; default stdout")
    parser.add_argument("--max-items", type=int, default=60, help="Max items per bucket")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    data = extract_detail_page(read_text(input_path), source=str(input_path), max_items=args.max_items)
    write_or_print(data, args.out, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
