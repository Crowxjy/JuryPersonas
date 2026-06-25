#!/usr/bin/env python3
"""
modes/render/report.py — mode/render-report 实现

职责:
1. 读 brief + filled jury-react bundle + consensus_pack
2. 渲染 reporting/templates/report_video_xml.md 为 Markdown 报告
3. 输出到本地文件(默认 .runtime/reports/<session_id>.md);
4. 后续 reporting/lark_renderer.py 接力做飞书发布

使用模式:

    python3 modes/render/report.py \\
        --brief-file tests/fixtures/short_video_demo/brief.json \\
        --bundle-file /tmp/jp_m3/reactions/m3-demo.filled.json \\
        --consensus-file /tmp/jp_m3/consensus/m3-demo.json \\
        --output /tmp/jp_m3/reports/m3-demo.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent.parent
TEMPLATE_PATH = SKILL_ROOT / "reporting" / "templates" / "report_video_xml.md"


def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def render_score_matrix_rows(matrix: dict) -> str:
    rows = []
    metrics = matrix["metrics"]
    for r in matrix["rows"]:
        scores = r["scores"]
        cells = [fmt(scores.get(m)) for m in metrics]
        rows.append(
            f"| {r['name']} | {r['sub_category']} | "
            f"{cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} | "
            f"{fmt(r.get('average'))} |"
        )
    return "\n".join(rows)


def render_consensus_rows(consensus: list[dict]) -> str:
    if not consensus:
        return "| — | (无频次≥2 的共识卡点) | — | — | — |"
    rows = []
    for c in consensus:
        names = ", ".join(m["name"] for m in c["mentioned_by"])
        concerns = " / ".join(c["concerns"])
        rows.append(
            f"| {c['frequency']} | {c['position_canonical']} | {concerns} | {names} | {c['best_fix']} |"
        )
    return "\n".join(rows)


def render_divergence_block(divergence: list[dict]) -> str:
    if not divergence:
        return "_(无显著分歧)_"
    chunks = []
    uniques = [d for d in divergence if d["kind"] == "unique_complaint"]
    if uniques:
        chunks.append("### 单人卡点(仅 1 位陪审员提到)")
        for u in uniques:
            chunks.append(
                f"- **{u['position_canonical']}** · {u['name']}({u['concern']}) — "
                f"{u['reason']} → 建议:{u['fix']}"
            )
    gaps = [d for d in divergence if d["kind"] == "score_gap"]
    if gaps:
        chunks.append("\n### 评分断层(同一指标分差 > 3)")
        for g in gaps:
            chunks.append(
                f"- **{g['metric']}**:最高 {g['max']['role_id']}={g['max']['score']} / "
                f"最低 {g['min']['role_id']}={g['min']['score']} (差 {g['gap']} 分)"
            )
    return "\n".join(chunks)


def render_participants_block(participants: list[dict]) -> str:
    chunks = []
    for p in participants:
        if not p.get("reaction"):
            continue
        chunks.append(f"### {p['name']} · {p.get('sub_category', p['role_id'])}")
        chunks.append(p["reaction"])
        chunks.append("")
    return "\n".join(chunks).rstrip()


def render_brief_summary_block(brief: dict) -> str:
    fields = brief.get("fields", {})
    rows = []
    for key in [
        "artifact_type",
        "artifact_locator",
        "target_audience",
        "key_concern",
        "distribution_intent",
    ]:
        f = fields.get(key, {})
        rows.append(f"- **{key}**:{f.get('value', '—')}")
    next_action = brief.get("next_action", {}) or {}
    if summary := next_action.get("summary_for_user"):
        rows.append(f"- **brief 摘要**:{summary}")
    return "\n".join(rows)


def replace_template(template: str, ctx: dict) -> str:
    out = template
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def render_report(brief: dict, bundle: dict, pack: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    artifact = bundle.get("artifact", {})
    matrix = pack["score_matrix"]
    avgs = matrix["averages"]

    ctx = {
        "title": "短视频陪审团评审报告",
        "session_id": brief.get("session_id", "—"),
        "scenario_name": "短视频成片评审",
        "artifact_title": artifact.get("title", "—"),
        "artifact_platform": artifact.get("platform", "—"),
        "artifact_duration": str(artifact.get("duration_sec", "—")),
        "target_audience": brief["fields"]["target_audience"].get("value", "—"),
        "key_concern": brief["fields"]["key_concern"].get("value", "—"),
        "n_participants": str(pack["n_participants"]),
        "brief_summary_block": render_brief_summary_block(brief),
        "score_matrix_rows": render_score_matrix_rows(matrix),
        "avg_wan_bo": fmt(avgs.get("完播倾向")),
        "avg_hu_dong": fmt(avgs.get("互动倾向")),
        "avg_zhuan_hua": fmt(avgs.get("转化倾向")),
        "avg_xin_ren": fmt(avgs.get("信任度")),
        "avg_tui_jian": fmt(avgs.get("推荐倾向")),
        "consensus_rows": render_consensus_rows(pack.get("consensus", [])),
        "divergence_block": render_divergence_block(pack.get("divergence", [])),
        "participants_block": render_participants_block(bundle.get("participants", [])),
    }
    return replace_template(template, ctx)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="mode/render-report 实现")
    parser.add_argument("--brief-file", required=True)
    parser.add_argument("--bundle-file", required=True, help="filled jury-react bundle")
    parser.add_argument("--consensus-file", required=True, help="aggregate-consensus 输出")
    parser.add_argument("--output", "-o", required=True, help="Markdown 报告输出路径")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    brief = json.loads(Path(args.brief_file).read_text(encoding="utf-8"))
    bundle = json.loads(Path(args.bundle_file).read_text(encoding="utf-8"))
    pack = json.loads(Path(args.consensus_file).read_text(encoding="utf-8"))

    report = render_report(brief, bundle, pack)
    Path(args.output).write_text(report, encoding="utf-8")
    sys.stdout.write(f"[OK] 报告已生成 → {args.output} ({len(report)} chars)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
