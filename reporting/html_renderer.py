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
DEFAULT_DESIGN = SCRIPT_DIR / "design.md"


def esc(value: Any) -> str:
    return html.escape("—" if value is None else str(value), quote=True)


def css() -> str:
    return """
:root { color-scheme:dark; --bg:#08090a; --bg-elev:#0e0f11; --panel:#141517; --panel-2:#191b1e; --line:#232629; --line-soft:#1c1e21; --text:#f7f8f8; --text-2:#b3b8bf; --text-3:#7c828a; --accent:#6e79d6; --accent-soft:rgba(110,121,214,.14); --red:#e5604d; --amber:#d6a24e; --green:#4eae6e; --radius:12px; --radius-sm:8px; --mono:"SF Mono",ui-monospace,"JetBrains Mono",Menlo,monospace; --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif; }
* { box-sizing:border-box; }
html { background:var(--bg); scroll-behavior:smooth; }
body { margin:0; background:var(--bg); color:var(--text); font-family:var(--sans); font-size:15px; line-height:1.62; -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility; }
::selection { background:var(--accent-soft); color:#fff; }
.wrap { max-width:920px; margin:0 auto; padding:0 24px; }
.topbar { position:sticky; top:0; z-index:20; border-bottom:1px solid var(--line); background:linear-gradient(180deg,rgba(12,13,15,.92),rgba(8,9,10,.88)); backdrop-filter:blur(8px); }
.topbar-inner { height:60px; display:flex; align-items:center; gap:12px; }
.topbar svg { width:24px; height:24px; color:var(--accent); flex:0 0 auto; }
.topbar-title { font-size:15px; font-weight:650; letter-spacing:-.01em; }
.topbar-sub { margin-left:auto; color:var(--text-3); font-family:var(--mono); font-size:12px; }
main.wrap { padding-bottom:64px; }
.hero { padding:56px 0 40px; border-bottom:1px solid var(--line-soft); }
.hero h1 { max-width:820px; margin:0 0 16px; font-size:clamp(30px,5vw,42px); font-weight:680; line-height:1.16; letter-spacing:-.025em; background:linear-gradient(180deg,#fff,#c5c9cf); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; overflow-wrap:anywhere; }
.hero p { max-width:660px; margin:0; color:var(--text-2); font-size:15px; line-height:1.75; }
.badges { display:flex; flex-wrap:wrap; gap:10px; margin-top:24px; }
.badge { display:inline-flex; align-items:center; min-height:30px; border-radius:999px; padding:6px 12px; color:var(--text-2); border:1px solid var(--line); background:var(--panel); font-family:var(--mono); font-size:12px; line-height:1; }
.badge.user { font-family:var(--sans); }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); padding:24px; margin-top:28px; }
.card.primary { position:relative; overflow:hidden; background:var(--panel); }
.card.primary::before { content:""; position:absolute; inset:0; pointer-events:none; background:radial-gradient(120% 100% at 0% 0%,var(--accent-soft),transparent 55%); }
.card.primary > * { position:relative; }
.card.soft { background:var(--bg-elev); }
.card h2 { margin:0 0 16px; font-size:21px; font-weight:640; line-height:1.28; letter-spacing:-.02em; }
.card h3 { margin:22px 0 10px; font-size:14px; font-weight:650; line-height:1.35; color:var(--text); }
.muted { color:var(--text-3); }
.boundary { background:var(--bg-elev); }
.ok { color:var(--green); font-weight:700; }
.danger { color:var(--red); font-weight:700; }
.table-wrap { width:100%; overflow-x:auto; border:1px solid var(--line); border-radius:var(--radius); }
table { width:100%; border-collapse:collapse; margin:0; font-size:13.5px; }
th,td { padding:12px 16px; vertical-align:top; text-align:left; line-height:1.6; border-bottom:1px solid var(--line-soft); }
tr:last-child td { border-bottom:none; }
th { background:var(--panel-2); color:var(--text-2); font-size:12.5px; font-weight:650; }
td { color:var(--text-2); }
pre { white-space:pre-wrap; background:var(--bg-elev); color:var(--text-2); padding:14px; border:1px solid var(--line); border-radius:var(--radius-sm); overflow:auto; max-height:340px; font-family:var(--mono); font-size:12.5px; line-height:1.55; }
details { border:1px solid var(--line); border-radius:var(--radius); padding:14px; background:var(--panel); }
summary { cursor:pointer; font-weight:650; color:var(--text); }
.scorebar { display:flex; align-items:center; gap:10px; min-width:150px; }
.scorebar span { font-family:var(--mono); font-variant-numeric:tabular-nums; }
.scorebar-track { height:6px; flex:1; background:var(--line-soft); border-radius:999px; overflow:hidden; }
.scorebar-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,var(--red),var(--amber),var(--green)); }
.media { margin-top:14px; }
.media img { width:100%; max-height:620px; object-fit:contain; border:1px solid var(--line); border-radius:var(--radius); background:var(--bg-elev); }
.frame-thumb { display:block; width:160px; max-height:220px; object-fit:contain; border:1px solid var(--line); border-radius:var(--radius-sm); background:var(--bg-elev); }
.small { font-size:12.5px; }
.score-note { margin:10px 0 16px; color:var(--text-3); font-size:13px; }
.method-note { margin:0 0 16px; color:var(--text-2); }
.quote { margin-top:14px; padding:14px 16px; border:1px solid var(--line); border-radius:var(--radius-sm); background:var(--bg-elev); color:var(--text-2); }
a { color:var(--text); text-decoration:underline; text-decoration-color:var(--accent); }
ul { padding-left:20px; color:var(--text-2); }
@media print { :root { color-scheme:light; } body,html { background:#fff; color:#111; } .topbar { position:static; } .card,.hero,details,pre,.table-wrap { background:#fff; color:#111; border-color:#bbb; } th { background:#f7f7f7; color:#111; } .badges { display:none; } }
@media (max-width:720px) { .wrap { padding:0 16px; } .hero { padding:40px 0 30px; } .card { padding:18px; } .topbar-sub { display:none; } }
"""


def list_modes(data: dict[str, Any]) -> list[str]:
    return [item.get("mode", "") for item in data.get("plan", {}).get("dag", [])]


SCENARIO_LABELS = {
    "review-short-video": "短视频成片评审",
    "review-marketing-copy": "营销文案评审",
    "review-prd": "PRD 评审",
    "review-design": "设计稿评审",
    "review-screen": "界面评审",
    "review-detail-page": "详情页评审",
    "review-product-card": "商品卡评审",
}

OBSERVATION_LABELS = {
    "keyframe_extract": "关键帧与口播摘要",
    "copy_extract": "文案结构抽取",
    "prd_extract": "PRD 结构抽取",
    "design_extract": "设计信息抽取",
    "screen_extract": "界面信息抽取",
    "detail_page_extract": "详情页信息抽取",
    "product_card_extract": "商品卡信息抽取",
    "heatmap": "HCI 视觉观察",
    "distribution_gap": "人群分布差异",
}

SCORE_MEANINGS = {
    "完播倾向": "这个角色主观上愿不愿意把内容看完。",
    "互动倾向": "这个角色是否可能点赞、评论、收藏或停留互动。",
    "转化倾向": "这个角色是否可能点击购买、咨询、报名或进入下一步。",
    "信任度": "这个角色对内容承诺、证据和表达方式的信任程度。",
    "推荐倾向": "这个角色是否愿意转发给别人或口头推荐。",
    "读完意愿": "这个角色是否愿意把文案读完。",
    "利益清晰度": "角色是否能快速理解这件事对自己有什么好处。",
    "转化意愿": "角色是否愿意采取文案希望的下一步行动。",
    "传播意愿": "角色是否愿意转发、分享或推荐。",
    "必要性": "角色是否认为这件事值得做、值得推进。",
    "可行性": "角色是否相信方案在资源、流程和执行上可落地。",
    "完整性": "信息、路径、边界和反例是否足够完整。",
    "风险可控性": "潜在风险是否被识别并有可执行的兜底。",
    "推荐推进度": "角色是否建议继续推进。",
    "可用性": "用户能不能顺利理解并完成主要任务。",
    "一致性": "页面、文案、交互和预期是否前后一致。",
    "视觉层级": "用户是否能分清主次、先看什么后看什么。",
    "信息密度": "信息是否过载或过少,是否影响理解。",
    "行动清晰度": "用户是否知道下一步该做什么、点哪里、会发生什么。",
    "理解效率": "用户是否能在短时间内看懂卖点、规则或任务。",
    "信任证据": "证据、评价、资质、规则是否足够支撑行动。",
    "购买意愿": "用户是否愿意下单或进入购买链路。",
    "价格清晰度": "价格、优惠、限制和后续费用是否清楚。",
}


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


def scenario_label(data: dict[str, Any]) -> str:
    scenario = data.get("summary", {}).get("scenario") or data.get("scenario") or ""
    return SCENARIO_LABELS.get(str(scenario), str(scenario) or "评审")


def observation_label(name: str) -> str:
    return OBSERVATION_LABELS.get(name, name)


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


def score_band(value: Any) -> tuple[str, str]:
    if not isinstance(value, (int, float)):
        return "无法判断", "样本不足或未给出有效评分。"
    if value < 3:
        return "明显偏低", "需要优先处理,否则大概率卡在这一环。"
    if value < 5:
        return "偏弱", "有明确阻力,需要靠信息补充或表达调整拉回。"
    if value < 7:
        return "中等", "不是硬伤,但还不足以形成稳定正向判断。"
    if value < 8.5:
        return "较好", "多数角色能接受,可继续局部优化。"
    return "强", "这一项对目标角色基本成立。"


def render_score_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="muted">暂无评分均值。</p>'
    body = []
    for row in rows:
        band, meaning = score_band(row.get("均值"))
        metric = row.get("指标")
        body.append(
            "<tr>"
            f"<td>{esc(metric)}</td>"
            f"<td>{score_cell(row.get('均值'))}</td>"
            f"<td>{esc(band)}</td>"
            f"<td>{esc(SCORE_MEANINGS.get(str(metric), meaning))}</td>"
            "</tr>"
        )
    return (
        '<p class="score-note">评分是 0-10 的角色主观判断:'
        "0-3 明显偏低,3-5 偏弱,5-7 中等,7-8.5 较好,8.5 以上强。"
        "它不预测真实转化率,只表示这组陪审员的理解、信任和行动阻力。</p>"
        '<div class="table-wrap"><table><thead><tr><th>指标</th><th>均值</th><th>判断</th><th>代表什么</th></tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def render_summary(data: dict[str, Any]) -> str:
    summary = data.get("summary", {})
    rows = [
        {"字段": "评审对象", "值": summary.get("artifact_type")},
        {"字段": "目标人群", "值": summary.get("target_audience")},
        {"字段": "关注问题", "值": summary.get("key_concern")},
        {"字段": "参与角色数", "值": summary.get("participants")},
    ]
    return f'<section class="card"><h2>本次评审范围</h2>{render_table(rows)}</section>'


def render_user_chips(data: dict[str, Any]) -> str:
    summary = data.get("summary", {})
    observations = data.get("observations", {})
    chips = [
        scenario_label(data),
        f"{summary.get('participants', '—')} 位陪审员",
    ]
    artifact_type = summary.get("artifact_type")
    target = summary.get("target_audience")
    if artifact_type:
        chips.append(str(artifact_type))
    if target:
        chips.append(str(target))
    keyframe = observations.get("keyframe_extract") or {}
    if keyframe.get("duration_sec"):
        chips.append(f"{keyframe.get('duration_sec')} 秒")
    if keyframe.get("platform"):
        chips.append(str(keyframe.get("platform")))
    return "".join(f'<span class="badge user">{esc(chip)}</span>' for chip in chips)


def hero_description(data: dict[str, Any]) -> str:
    summary = data.get("summary", {})
    concern = summary.get("key_concern")
    target = summary.get("target_audience")
    parts = []
    if target:
        parts.append(f"面向 {target}")
    if concern:
        parts.append(f"重点看 {concern}")
    if parts:
        return "。".join(parts) + "。报告先给可执行修改顺序,再展开用户反馈、分析依据和评分解释。"
    return "报告先给可执行修改顺序,再展开用户反馈、分析依据和评分解释。"


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
        {"内部步骤": item.get("mode"), "触发原因": item.get("reason")}
        for item in data.get("plan", {}).get("dag", [])
    ]
    if not rows:
        return ""
    return (
        '<details class="card"><summary>技术附录:执行步骤</summary>'
        '<p class="small muted">以下内容用于审计本次 Skill 的执行过程,业务阅读可跳过。</p>'
        f"{render_table(rows)}"
        "</details>"
    )


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


def local_image_src(path_value: Any) -> str:
    if not path_value:
        return ""
    raw = str(path_value)
    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path.as_uri()
    return raw


def render_video_keyframe_table(frames: list[dict[str, Any]]) -> str:
    if not frames:
        return ""
    rows = []
    for frame in frames:
        image = frame.get("image") or frame.get("image_path")
        if image:
            image_cell = (
                f'<img class="frame-thumb" src="{esc(local_image_src(image))}" alt="frame {esc(frame.get("ts_sec"))}"/>'
                f'<p class="small muted">{esc(image)}</p>'
            )
        else:
            image_cell = '<span class="muted">未提供</span>'
        desc = frame.get("description") or (
            "真实抽帧,但画面描述未填写;未查看图片时不能评价画面。"
            if frame.get("needs_visual_description")
            else "未填写"
        )
        rows.append(
            "<tr>"
            f"<td>{esc(frame.get('ts_sec'))}s</td>"
            f"<td>{image_cell}</td>"
            f"<td>{esc(desc)}</td>"
            f"<td>{esc(frame.get('voiceover') or '无')}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        '<th>时间点</th><th>真实抽帧</th><th>画面/元素</th><th>口播</th>'
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def render_observations(data: dict[str, Any], layout: str) -> str:
    observations = data.get("observations", {})
    if not observations:
        return '<section class="card"><h2>分析依据</h2><p class="muted">本次没有结构化分析依据。</p></section>'

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

    chunks = ['<section class="card soft"><h2>分析依据</h2>']
    if layout == "video_review" and observations.get("keyframe_extract"):
        keyframe = observations.get("keyframe_extract") or {}
        all_frames = keyframe.get("key_frames", [])
        observed_frames = [frame for frame in all_frames if frame.get("observed", True) is not False]
        inferred_frames = [frame for frame in all_frames if frame.get("observed", True) is False]
        boundary = keyframe.get("boundary", {})
        chunks.append(
            '<p class="method-note">短视频评审基于提供的关键帧、口播和结构化素材理解内容。'
            "本次没有解码完整视频文件,因此不会声称看到了未提供的画面。</p>"
        )
        if observed_frames:
            chunks.append(render_video_keyframe_table(observed_frames))
        else:
            chunks.append('<p class="danger">未提供可验证关键帧;本次不能声称已理解完整视频画面。</p>')
        if inferred_frames:
            inferred_ts = ", ".join(str(frame.get("ts_sec", "?")) for frame in inferred_frames)
            chunks.append(
                f'<p class="small muted">已排除 {len(inferred_frames)} 个 observed:false 推断帧'
                f"({esc(inferred_ts)} 秒);这些帧没有作为视频事实进入报告。</p>"
            )
        if boundary:
            chunks.append(
                '<p class="small muted">边界:仅使用已提供关键帧/口播;缺失画面不会被脑补。</p>'
            )
        chunks.append("</section>")
        return "".join(chunks)

    media = render_media_artifacts(data)
    if media:
        chunks.append(media)
    chunks.append('<div class="grid">')
    for name in names:
        label = observation_label(name)
        chunks.append(
            "<details>"
            f"<summary>{esc(label)}</summary>"
            f"<pre>{esc(json.dumps(compact_observation(observations[name]), ensure_ascii=False, indent=2))}</pre>"
            "</details>"
        )
    chunks.append("</div></section>")
    return "".join(chunks)


def render_decision_lens(data: dict[str, Any]) -> str:
    return ""


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
        '<section class="card"><h2>用户反馈汇总</h2>'
        "<h3>多人都卡住的地方</h3>"
        f"{render_table(consensus_rows)}"
        "<h3>逐人反馈样例</h3>"
        f"{render_table(complaint_rows, limit=12)}"
        "<h3>评分怎么读</h3>"
        f"{render_score_rows(score_rows)}"
        "</section>"
    )


def visible_boundary_text(item: str) -> str:
    if "mock_llm_responder" in item:
        return "本页是本地回归样例,陪审反馈由测试桩生成;正式使用时应由宿主 Agent/模型逐位回填。"
    if "未使用 mock_llm_responder" in item:
        return "陪审反馈来自宿主 Agent/模型回填,报告按这些独立反馈做聚合。"
    if "bundle.participants" in item:
        return "聚合结果以每位陪审员的独立反馈为准。"
    return item


def render_boundary(data: dict[str, Any], design_constraints: str) -> str:
    boundaries = data.get("boundaries", [])
    items = "".join(f"<li>{esc(visible_boundary_text(item))}</li>" for item in boundaries)
    return (
        '<section class="card boundary"><h2>方法与边界</h2>'
        f"<ul>{items}</ul>"
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
    return "JuryPersonas HTML 报告设计约束"


def render_report(data: dict[str, Any], *, design_path: Path = DEFAULT_DESIGN) -> str:
    design_constraints = design_path.read_text(encoding="utf-8") if design_path.exists() else ""
    layout = infer_layout(data)
    title = data.get("title", "JuryPersonas 评审报告")
    label = scenario_label(data)
    badges = render_user_chips(data)
    html_body = [
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"/>",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>",
        f"<title>{esc(title)}</title><style>{css()}</style></head><body>",
        '<header class="topbar"><div class="wrap topbar-inner">',
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 6.5 12 3l9 3.5"/><path d="M3 6.5v11L12 21l9-3.5v-11"/>'
        '<path d="M12 12v9"/><path d="m3 6.5 9 5.5 9-5.5"/></svg>',
        '<span class="topbar-title">JuryPersonas</span>',
        f'<span class="topbar-sub">{esc(label)}</span>',
        "</div></header>",
        '<main class="wrap">',
        '<section class="hero">',
        f"<h1>{esc(title)}</h1>",
        f"<p>{esc(hero_description(data))}</p>",
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
