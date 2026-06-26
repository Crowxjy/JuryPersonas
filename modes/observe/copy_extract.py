#!/usr/bin/env python3
"""
copy_extract.py - deterministic marketing copy observation extractor.

It does not judge whether the copy is good. It extracts structure, claims,
evidence markers, CTA, risk words, and channel clues for jury-react.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CTA_RE = re.compile(
    r"(点(?:我|击|进|开)?[^。！？!?\n]{0,8}(?:主页|链接|按钮|小黄车|购物车|下方|左下角|右下角)"
    r"|(?:主页|私信|评论区|链接|小黄车|购物车)[^。！？!?\n]{0,8}(?:领|领取|咨询|下单|购买|预约|报名)"
    r"|扫码|私信|咨询|下单|购买|领取|报名|预约|进群|加微信|回复|立即|马上)"
)
CLAIM_RE = re.compile(r"(免费|限时|立减|返现|优惠|福利|爆款|第一|最好|必买|保证|承诺|官方|正品|同城|包邮)")
EVIDENCE_RE = re.compile(r"(真实|案例|数据|截图|评价|口碑|认证|资质|销量|复购|老客户|实拍|到店)")
RISK_RE = re.compile(
    r"(最高级|第一|唯一|保证|稳赚|无效退款|包治|根治|绝对|100%|百分百|诱导|转发"
    r"|瘦(?:身|脸|腿|腰|下来|下去|了)|减(?:肥|脂|重)|掉秤|塑形|燃脂"
    r"|错过[^。！？!?\n]{0,8}(?:就|再|没有|没了|亏|等)"
    r"|(?:仅剩|只剩|限量|限时|最后|倒计时)[^。！？!?\n]{0,8}(?:个|名|天|小时|分钟|席|份|库存|机会|名额)?)"
)
PRICE_RE = re.compile(
    r"(¥\s*\d+(?:\.\d+)?|￥\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*元|\d+(?:\.\d+)?\s*折|满\s*\d+(?:\.\d+)?|减\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*块"
    r"|(?:首月|只要|仅需|新人价|新客价|体验价|活动价|特惠价|券后价|到手价|低至)[^。！？!?\n]{0,12}\d+(?:\.\d+)?)"
)
CHANNEL_RE = re.compile(r"(朋友圈|小红书|短信|push|直播|口播|落地页|详情页|社群|私域|公众号)")


def read_input(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"文案文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；;])\s*|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def find_matches(sentences: list[str], pattern: re.Pattern[str], limit: int) -> list[dict[str, Any]]:
    rows = []
    for idx, sentence in enumerate(sentences, 1):
        found = sorted(set(pattern.findall(sentence)))
        if found:
            rows.append({"sentence_index": idx, "text": sentence, "matches": found})
            if len(rows) >= limit:
                break
    return rows


def extract_copy(text: str, *, source: str | None = None, max_items: int = 40) -> dict[str, Any]:
    normalized = text.strip()
    sentences = split_sentences(normalized)
    non_empty_lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    opening = sentences[0] if sentences else ""
    closing = sentences[-1] if sentences else ""

    cta = find_matches(sentences, CTA_RE, max_items)
    claims = find_matches(sentences, CLAIM_RE, max_items)
    evidence = find_matches(sentences, EVIDENCE_RE, max_items)
    risks = find_matches(sentences, RISK_RE, max_items)
    prices = find_matches(sentences, PRICE_RE, max_items)
    channels = sorted(set(CHANNEL_RE.findall(normalized)))

    return {
        "mode": "mode/copy-extract",
        "source": source,
        "stats": {
            "char_count": len(normalized),
            "line_count": len(non_empty_lines),
            "sentence_count": len(sentences),
        },
        "structure": {
            "opening": opening,
            "closing": closing,
            "first_three_sentences": sentences[:3],
        },
        "claims": claims,
        "evidence_markers": evidence,
        "cta_candidates": cta,
        "price_or_offer_mentions": prices,
        "risk_words": risks,
        "channel_clues": channels,
        "summary": {
            "n_claims": len(claims),
            "n_evidence_markers": len(evidence),
            "n_cta_candidates": len(cta),
            "n_risk_words": len(risks),
            "n_price_mentions": len(prices),
            "channels": channels,
            "opening_chars": len(opening),
        },
        "boundary": {
            "deterministic_extraction_only": True,
            "no_quality_judgement": True,
            "manual_review_required_for_compliance": bool(risks),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract marketing copy observation JSON")
    parser.add_argument("--input", required=True, help="Marketing copy text/markdown file")
    parser.add_argument("--out", help="Output JSON path; default stdout")
    parser.add_argument("--max-items", type=int, default=40, help="Max items per bucket")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    data = extract_copy(read_input(input_path), source=str(input_path), max_items=args.max_items)
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
