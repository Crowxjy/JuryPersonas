#!/usr/bin/env python3
"""
visual_extract_common.py - deterministic observation helpers for visual artifacts.

These helpers parse text/Markdown/JSON descriptions of screens, design drafts,
detail pages, and product cards. They do not inspect image pixels and do not make
quality judgements; image-only inputs should be handled by HCI observe modes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)]|[（(]?\d+[）)])\s+(.+?)\s*$")
KEY_VALUE_RE = re.compile(r"^\s*([^:：]{1,24})[:：]\s*(.+?)\s*$")

CTA_RE = re.compile(r"(购买|下单|预约|咨询|领取|提交|保存|发布|开通|立即|马上|点击|扫码|加购|去使用|开始)")
PRICE_RE = re.compile(r"(¥|￥|\d+\s*元|\d+\s*折|满\s*\d+|减\s*\d+|\d+\s*块|套餐|券|优惠)")
TRUST_RE = re.compile(r"(评价|评分|销量|认证|资质|实拍|案例|口碑|复购|老客户|保障|官方|正品|品牌)")
RULE_RE = re.compile(r"(规则|限制|有效期|库存|预约|核销|退款|不可用|节假日|到店|配送|范围|门槛)")
RISK_RE = re.compile(r"(不清楚|缺失|待补|疑问|冲突|误导|夸大|唯一|第一|保证|绝对|100%|百分百)")
LAYOUT_RE = re.compile(r"(首屏|顶部|底部|左侧|右侧|卡片|弹窗|按钮|导航|tab|表单|列表|筛选|主图|标题)")


def stringify_input(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"物料文件不存在: {path}")
    if path.suffix.lower() == ".json":
        return stringify_input(json.loads(path.read_text(encoding="utf-8")))
    return path.read_text(encoding="utf-8")


def non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_structure(lines: list[str], max_items: int) -> dict[str, Any]:
    headings = []
    bullets = []
    key_values = []
    for line_no, line in enumerate(lines, 1):
        heading = HEADING_RE.match(line)
        if heading and len(headings) < max_items:
            headings.append(
                {
                    "line": line_no,
                    "level": len(heading.group(1)),
                    "title": heading.group(2).strip(),
                }
            )
            continue

        bullet = BULLET_RE.match(line)
        if bullet and len(bullets) < max_items:
            bullets.append({"line": line_no, "text": bullet.group(1).strip()})

        key_value = KEY_VALUE_RE.match(line)
        if key_value and len(key_values) < max_items:
            key_values.append(
                {
                    "line": line_no,
                    "key": key_value.group(1).strip(),
                    "value": key_value.group(2).strip(),
                }
            )
    return {"headings": headings, "bullets": bullets, "key_values": key_values}


def find_matches(lines: list[str], pattern: re.Pattern[str], limit: int) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(lines, 1):
        matches = sorted(set(pattern.findall(line)))
        if matches:
            rows.append({"line": line_no, "text": line, "matches": matches})
            if len(rows) >= limit:
                break
    return rows


def count_present(signal_map: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {name: len(rows) for name, rows in signal_map.items()}


def missing_by_counts(required: dict[str, str], counts: dict[str, int]) -> list[str]:
    return [label for name, label in required.items() if counts.get(name, 0) == 0]


def build_observation(
    text: str,
    *,
    mode: str,
    source: str | None,
    required_signals: dict[str, str],
    max_items: int = 60,
) -> dict[str, Any]:
    normalized = text.strip()
    lines = non_empty_lines(normalized)
    structure = extract_structure(lines, max_items)
    signals = {
        "cta": find_matches(lines, CTA_RE, max_items),
        "price_or_offer": find_matches(lines, PRICE_RE, max_items),
        "trust": find_matches(lines, TRUST_RE, max_items),
        "rules": find_matches(lines, RULE_RE, max_items),
        "risk_words": find_matches(lines, RISK_RE, max_items),
        "layout": find_matches(lines, LAYOUT_RE, max_items),
    }
    signal_counts = count_present(signals)
    missing = missing_by_counts(required_signals, signal_counts)

    return {
        "mode": mode,
        "source": source,
        "stats": {
            "char_count": len(normalized),
            "line_count": len(lines),
            "heading_count": len(structure["headings"]),
            "bullet_count": len(structure["bullets"]),
            "key_value_count": len(structure["key_values"]),
        },
        "structure": structure,
        "signals": signals,
        "missing_critical_fields": missing,
        "summary": {
            **{f"n_{name}": count for name, count in signal_counts.items()},
            "n_missing_critical_fields": len(missing),
            "missing_critical_fields": missing,
        },
        "boundary": {
            "deterministic_extraction_only": True,
            "no_quality_judgement": True,
            "no_pixel_level_image_understanding": True,
            "use_hci_modes_for_image_metrics": True,
        },
    }


def write_or_print(data: dict[str, Any], out: str | None, *, pretty: bool) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)
    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)
