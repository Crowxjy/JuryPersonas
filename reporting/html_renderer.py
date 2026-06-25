#!/usr/bin/env python3
"""
html_renderer.py - dynamic HTML reports for JuryPersonas.

The renderer chooses report sections from scenario + executed modes. It keeps
Markdown output as fallback, but HTML is the preferred local report artifact.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_DESIGN = PROJECT_ROOT / "DESIGN.md"


def esc(value: Any) -> str:
    return html.escape("—" if value is None else str(value), quote=True)


def css() -> str:
    return """
:root { color-scheme: dark; --bg:#000000; --panel:#0a0a0a; --panel-soft:#111114; --ink:#ffffff; --muted:#c8c8d2; --line:#3a3a3f; --hairline:#242428; --cool:#f0f0fa; --warn:#f7c948; --ok:#8ff0b2; --danger:#ff8a80; --font-cjk:"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC","Source Han Sans SC",sans-serif; --font-latin:D-DIN,"Arial Narrow",Arial,Verdana,sans-serif; }
* { box-sizing: border-box; }
html { background:var(--bg); }
body { margin:0; background:var(--bg); color:var(--ink); font-family:var(--font-cjk); line-height:1.68; letter-spacing:.02em; -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility; }
body::before { content:""; position:fixed; inset:0; pointer-events:none; border:1px solid var(--hairline); }
main { max-width:1180px; margin:0 auto; padding:24px 20px 64px; }
.hero { min-height:auto; display:flex; flex-direction:column; justify-content:flex-end; background:linear-gradient(180deg,#050505,#000); color:var(--ink); border:1px solid var(--line); border-radius:8px; padding:28px 28px; }
.hero h1 { max-width:940px; margin:0 0 14px; font-family:var(--font-cjk); font-size:clamp(28px,5vw,48px); font-weight:700; line-height:1.22; letter-spacing:.02em; overflow-wrap:anywhere; }
.hero p { margin:0; color:var(--muted); font-size:13px; line-height:1.8; letter-spacing:.03em; }
.badges { display:flex; flex-wrap:wrap; gap:10px; margin-top:20px; }
.badge { display:inline-flex; align-items:center; min-height:32px; border-radius:32px; padding:7px 12px; color:var(--ink); border:1px solid var(--ink); background:transparent; font-family:var(--font-latin); font-size:12px; font-weight:700; line-height:1; letter-spacing:.08em; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(310px,1fr)); gap:18px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:24px; margin-top:22px; }
.card.primary { background:#f7f7f2; color:#080808; border-color:#f7f7f2; }
.card.primary .muted { color:#505050; }
.card.soft { background:var(--panel-soft); }
.card h2 { margin:0 0 16px; font-family:var(--font-cjk); font-size:clamp(24px,3.5vw,38px); font-weight:700; line-height:1.24; letter-spacing:.02em; }
.card h3 { margin:22px 0 10px; font-size:14px; font-weight:700; line-height:1.35; letter-spacing:.03em; }
.muted { color:var(--muted); }
.boundary { background:var(--bg); }
.ok { color:var(--ok); font-weight:700; }
.danger { color:var(--danger); font-weight:700; }
.table-wrap { width:100%; overflow-x:auto; }
table { width:100%; border-collapse:collapse; margin:12px 0; font-size:14px; }
th,td { border:1px solid var(--line); padding:10px 12px; vertical-align:top; text-align:left; line-height:1.6; }
th { background:var(--bg); color:var(--muted); font-size:12px; font-weight:700; letter-spacing:.04em; }
td { color:var(--ink); }
pre { white-space:pre-wrap; background:var(--bg); color:var(--muted); padding:14px; border:1px solid var(--line); border-radius:6px; overflow:auto; max-height:340px; font-family:var(--font-latin); font-size:13px; line-height:1.55; letter-spacing:0; }
details { border:1px solid var(--line); border-radius:8px; padding:14px; background:var(--panel-soft); }
summary { cursor:pointer; font-weight:700; }
.scorebar { display:flex; align-items:center; gap:10px; min-width:150px; }
.scorebar span { font-family:var(--font-latin); font-variant-numeric:tabular-nums; }
.scorebar-track { height:8px; flex:1; background:#242428; border-radius:999px; overflow:hidden; }
.scorebar-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,var(--danger),var(--warn),var(--ok)); }
.media { margin-top:14px; }
.media img { width:100%; max-height:620px; object-fit:contain; border:1px solid var(--line); border-radius:8px; background:#050505; }
.pill-row { display:flex; flex-wrap:wrap; gap:10px; }
.small { font-size:13px; }
a { color:var(--ink); text-decoration:underline; }
@media print { :root { color-scheme: light; } body,html { background:#fff; color:#111; } .hero,.card { background:#fff; color:#111; border-color:#bbb; } pre,th { background:#f7f7f7; color:#111; } .badges { display:none; } }
@media (max-width: 700px) { main { padding:16px 12px 44px; } .hero { padding:24px 18px; } .card { padding:16px; } }
"""


def list_modes(data: dict[str, Any]) -> list[str]:
    return [item.get("mode", "") for item in data.get("plan", {}).get("dag", [])]


def infer_layout(data: dict[str, Any]) -> str:
    scenario = data.get("summary", {}).get("scenario") or data.get("scenario")
    modes = set(list_modes(data))
    if {"mode/heatmap", "mode/cross-page", "mode/annotate-issues"} & modes:
        return "hci_first"
    if scenario in {"review-design", "review-screen"}:
        return "design_review"
    if scenario in {"review-detail-page", "review-product-card"}:
        return "conversion_review"
    if scenario == "review-marketing-copy":
        return "copy_review"
    if scenario == "review-prd":
        return "decision_review"
    if scenario == "review-short-video":
        return "video_review"
    return "generic_review"


def render_table(rows: list[dict[str, Any]], *, limit: int | None = None) -> str:
    if not rows:
        return '<p class="muted">暂无结构化行。</p>'
    rows = rows[:limit] if limit else rows
    keys = list(rows[0].keys())
    head = "".join(f"<th>{esc(k)}</th>" for k in keys)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{esc(row.get(k))}</td>" for k in keys) + "</tr>")
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def score_cell(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return esc(value)
    width = max(0, min(100, float(value) * 10))
    return (
        '<div class="scorebar">'
        f'<span>{esc(value)}</span>'
        '<span class="scorebar-track">'
        f'<span class="scorebar-fill" style="width:{width:.0f}%"></span>'
        "</span></div>"
    )


def render_score_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="muted">暂无评分均值。</p>'
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{esc(row.get('指标'))}</td>"
            f"<td>{score_cell(row.get('均值'))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr><th>指标</th><th>均值</th></tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def render_summary(data: dict[str, Any]) -> str:
    summary = data.get("summary", {})
    rows = [{"字段": key, "值": value} for key, value in summary.items()]
    return f'<section class="card"><h2>评审概览</h2>{render_table(rows)}</section>'


def render_action_priorities(data: dict[str, Any]) -> str:
    consensus = data.get("aggregate", {}).get("consensus", [])
    complaints = data.get("aggregate", {}).get("complaints", [])
    rows = []
    for item in consensus[:3]:
        rows.append(
            {
                "优先级": f"P{len(rows) + 1}",
                "卡点": item.get("position_canonical"),
                "为什么先改": f"{item.get('frequency')} 位陪审员提到: {' / '.join(item.get('concerns', []))}",
                "建议动作": item.get("best_fix"),
            }
        )
    if not rows:
        for item in complaints[:3]:
            rows.append(
                {
                    "优先级": f"P{len(rows) + 1}",
                    "卡点": item.get("position_canonical") or item.get("position"),
                    "为什么先改": item.get("reason"),
                    "建议动作": item.get("fix"),
                }
            )
    return (
        '<section class="card primary" id="actions"><h2>行动优先级</h2>'
        '<p class="muted">按共识频次和具体建议自动排序,用于先决定改什么。</p>'
        f"{render_table(rows)}"
        "</section>"
    )


def render_modes(data: dict[str, Any]) -> str:
    rows = [
        {"mode": item.get("mode"), "reason": item.get("reason")}
        for item in data.get("plan", {}).get("dag", [])
    ]
    return f'<section class="card"><h2>DAG 与 Mode 组合</h2>{render_table(rows)}</section>'


def compact_observation(obs: dict[str, Any]) -> Any:
    return (
        obs.get("summary")
        or obs.get("timeline_summary")
        or obs.get("cross_page_metrics")
        or obs.get("metrics_summary")
        or obs.get("status")
        or obs
    )


def render_media_artifacts(data: dict[str, Any]) -> str:
    artifacts = data.get("artifacts", {})
    image_keys = ("annotated_image", "heatmap_image", "source_image")
    chunks = []
    for key in image_keys:
        path = artifacts.get(key)
        if path:
            chunks.append(
                '<div class="media">'
                f"<h3>{esc(key)}</h3>"
                f'<img src="{esc(Path(path).as_uri() if Path(path).is_absolute() else path)}" alt="{esc(key)}"/>'
                f'<p class="small muted">{esc(path)}</p>'
                "</div>"
            )
    return "".join(chunks)


def render_observations(data: dict[str, Any], layout: str) -> str:
    observations = data.get("observations", {})
    if not observations:
        return '<section class="card"><h2>Observe 证据</h2><p class="muted">本次没有 observe 产物。</p></section>'

    priority = []
    if layout in {"hci_first", "design_review"}:
        priority = ["heatmap", "cross_page", "annotate_issues"]
    elif layout == "copy_review":
        priority = ["copy_extract"]
    elif layout == "conversion_review":
        priority = ["detail_page_extract", "product_card_extract", "heatmap"]
    elif layout == "decision_review":
        priority = ["prd_extract", "distribution_gap"]
    elif layout == "video_review":
        priority = ["keyframe_extract", "distribution_gap"]

    names = []
    for name in priority + sorted(observations):
        if name in observations and name not in names:
            names.append(name)

    chunks = ['<section class="card soft"><h2>Observe 证据</h2>']
    media = render_media_artifacts(data)
    if media:
        chunks.append(media)
    chunks.append('<div class="grid">')
    for name in names:
        chunks.append(
            "<details open>"
            f"<summary>{esc(name)}</summary>"
            f"<pre>{esc(json.dumps(compact_observation(observations[name]), ensure_ascii=False, indent=2))}</pre>"
            "</details>"
        )
    chunks.append("</div></section>")
    return "".join(chunks)


def render_decision_lens(data: dict[str, Any]) -> str:
    artifacts = data.get("artifacts", {})
    rows = []
    if artifacts.get("tension_bundle"):
        rows.append(
            {
                "产物": "核心张力 bundle",
                "状态": "等待宿主 Agent/模型提炼 dominant_tension",
                "路径": artifacts.get("tension_bundle"),
            }
        )
    if artifacts.get("paths_bundle"):
        rows.append(
            {
                "产物": "双路径 bundle",
                "状态": "等待宿主 Agent/模型生成 A/B 决策路径",
                "路径": artifacts.get("paths_bundle"),
            }
        )
    if not rows:
        return ""
    return (
        '<section class="card" id="decision-lens"><h2>决策透镜</h2>'
        '<p class="muted">本区展示 Phase C 张力/双路径产物的当前状态;最终路径仍由宿主 Agent/模型基于 bundle 生成。</p>'
        f"{render_table(rows)}"
        "</section>"
    )


def render_consensus(data: dict[str, Any]) -> str:
    sections = data.get("sections", [])
    consensus_rows = []
    complaint_rows = []
    score_rows = []
    for section in sections:
        if section.get("title") == "共识卡点":
            consensus_rows = section.get("table", [])
        elif section.get("title") == "具体问题样例":
            complaint_rows = section.get("table", [])
        elif section.get("title") == "评分均值":
            score_rows = section.get("table", [])

    return (
        '<section class="card"><h2>陪审结果</h2>'
        "<h3>共识卡点</h3>"
        f"{render_table(consensus_rows)}"
        "<h3>具体问题样例</h3>"
        f"{render_table(complaint_rows, limit=12)}"
        "<h3>评分均值</h3>"
          f"{render_score_rows(score_rows)}"
        "</section>"
    )


def render_boundary(data: dict[str, Any], design_constraints: str) -> str:
    boundaries = data.get("boundaries", [])
    items = "".join(f"<li>{esc(item)}</li>" for item in boundaries)
    constraint_note = summarize_design_constraints(design_constraints)
    return (
        '<section class="card boundary"><h2>边界声明</h2>'
        f"<ul>{items}</ul>"
        f'<p class="small muted">已应用内置报告风格约束: {esc(constraint_note.lstrip("# ").strip())}</p>'
        "</section>"
    )


def summarize_design_constraints(design_constraints: str) -> str:
    if not design_constraints:
        return "JuryPersonas HTML 报告设计约束"
    for line in design_constraints.splitlines():
        stripped = line.strip()
        if stripped.startswith("name:"):
            return stripped.partition(":")[2].strip()
    for line in design_constraints.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("# ").strip()
    return "Spacex-Inspired-design-analysis"


def render_report(data: dict[str, Any], *, design_path: Path = DEFAULT_DESIGN) -> str:
    design_constraints = design_path.read_text(encoding="utf-8") if design_path.exists() else ""
    layout = infer_layout(data)
    title = data.get("title", "JuryPersonas 评审报告")
    scenario = data.get("summary", {}).get("scenario") or "unknown"
    modes = list_modes(data)
    badges = "".join(f'<span class="badge">{esc(mode)}</span>' for mode in modes)
    html_body = [
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"/>",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>",
        f"<title>{esc(title)}</title><style>{css()}</style></head><body><main>",
        '<section class="hero">',
        f"<h1>{esc(title)}</h1>",
        f"<p>场景: {esc(scenario)} · 布局: {esc(layout)}</p>",
        '<div class="badges">',
        badges,
        "</div></section>",
          render_action_priorities(data),
          render_decision_lens(data),
          render_consensus(data),
          render_observations(data, layout),
        render_summary(data),
        render_modes(data),
        render_boundary(data, design_constraints),
        "</main></body></html>",
    ]
    return "".join(html_body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render dynamic JuryPersonas HTML report")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--design", default=str(DEFAULT_DESIGN))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(data, design_path=Path(args.design)), encoding="utf-8")
    print(json.dumps({"status": "OK", "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
