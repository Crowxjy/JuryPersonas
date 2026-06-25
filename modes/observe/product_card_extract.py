#!/usr/bin/env python3
"""product_card_extract.py - deterministic product card observation extractor."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from visual_extract_common import build_observation, read_text, write_or_print


REQUIRED_SIGNALS = {
    "layout": "商品卡结构/字段位置",
    "price_or_offer": "价格/优惠/规格",
    "trust": "销量/评价/品牌等证明",
    "cta": "商品卡行动点",
}


def extract_product_card(text: str, *, source: str | None = None, max_items: int = 60) -> dict[str, Any]:
    return build_observation(
        text,
        mode="mode/product-card-extract",
        source=source,
        required_signals=REQUIRED_SIGNALS,
        max_items=max_items,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract product card observation JSON")
    parser.add_argument("--input", required=True, help="Product card description Markdown/text/JSON")
    parser.add_argument("--out", help="Output JSON path; default stdout")
    parser.add_argument("--max-items", type=int, default=60, help="Max items per bucket")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    data = extract_product_card(read_text(input_path), source=str(input_path), max_items=args.max_items)
    write_or_print(data, args.out, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
