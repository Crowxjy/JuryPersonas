#!/usr/bin/env python3
"""
docx_xml_renderer.py - expert-roundtable compatible DocxXML draft renderer.

This renderer does not call Lark by itself. It emits a conservative
DocxXML-like draft. reporting/lark_renderer.py can create the Feishu doc from
this XML; image placeholders still need a later lark-doc media/block_replace
pass when strict in-table image embedding is required.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def esc(value: Any) -> str:
    return html.escape("—" if value is None else str(value), quote=True)


def p(text: Any) -> str:
    return f"<p>{esc(text)}</p>"


def rows(items: list[dict[str, Any]], columns: list[str]) -> str:
    head = "<tr>" + "".join(f"<th><p>{esc(col)}</p></th>" for col in columns) + "</tr>"
    body = []
    for item in items:
        body.append(
            "<tr>"
            + "".join(f"<td><p>{esc(item.get(col))}</p></td>" for col in columns)
            + "</tr>"
        )
    return f"<table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table>"


def extract_section(data: dict[str, Any], title: str) -> list[dict[str, Any]]:
    for section in data.get("sections", []):
        if section.get("title") == title:
            return section.get("table", [])
    return []


def render_docx_xml(data: dict[str, Any]) -> str:
    summary = data.get("summary", {})
    observations = data.get("observations", {})
    consensus = extract_section(data, "共识卡点")
    complaints = extract_section(data, "具体问题样例")
    scores = extract_section(data, "评分均值")

    hci_rows = []
    for name in ("heatmap", "cross_page", "annotate_issues"):
        if name in observations:
            obs = observations[name]
            hci_rows.append(
                {
                    "页面/产物": name,
                    "客观读数": json.dumps(
                        obs.get("summary") or obs.get("metrics_summary") or obs.get("status"),
                        ensure_ascii=False,
                    ),
                    "图片占位": obs.get("heatmap_image") or obs.get("annotated_image") or "—",
                }
            )

    xml = [
        f"<title>【圆桌评审】{esc(data.get('title', 'JuryPersonas 评审报告'))}</title>",
        '<callout emoji="📌" background-color="light-blue" border-color="blue">',
        p(f"评审对象:{summary.get('artifact_type')}"),
        p(f"评审场景:{summary.get('scenario')}"),
        p(f"参与人数:{summary.get('participants')}"),
        "</callout>",
        "<h1>一、需求背景</h1>",
        p(f"目标受众:{summary.get('target_audience')}"),
        p(f"关键关注:{summary.get('key_concern')}"),
        "<h1>二、页面测评</h1>",
        "<h3>客观数据速览</h3>",
        rows(hci_rows, ["页面/产物", "客观读数", "图片占位"]) if hci_rows else p("本次没有 HCI 图片产物。"),
        "<h1>三、圆桌纪要</h1>",
        "<h3>共识要改的</h3>",
        rows(consensus, list(consensus[0].keys())) if consensus else p("暂无频次 >= 2 的共识卡点。"),
        "<h3>有分歧的</h3>",
        rows(complaints, list(complaints[0].keys())) if complaints else p("暂无问题样例。"),
        "<h3>待办总结</h3>",
        rows(scores, list(scores[0].keys())) if scores else p("暂无评分均值。"),
        "<blockquote>",
        p("本 DocxXML 可由 lark_renderer 直接创建飞书文档。图片入表与 block_replace 仍需后续 lark-doc media 流程完成。"),
        "</blockquote>",
    ]
    return "\n".join(xml) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render expert-roundtable compatible DocxXML draft")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_docx_xml(data), encoding="utf-8")
    print(json.dumps({"status": "OK", "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
