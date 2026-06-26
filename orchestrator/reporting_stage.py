"""Report data assembly and multi-format rendering."""
from __future__ import annotations

import json
from pathlib import Path

try:
    from .bootstrap import ensure_skill_import_paths
except ImportError:
    from bootstrap import ensure_skill_import_paths  # type: ignore

ensure_skill_import_paths()


def build_generic_report_data(
    brief: dict,
    plan: dict,
    bundle: dict,
    pack: dict,
    observations: dict,
) -> dict:
    fields = brief.get("fields", {})
    score_averages = pack.get("score_matrix", {}).get("averages", {})
    consensus_rows = [
        {
            "频次": item.get("frequency"),
            "位置": item.get("position_canonical"),
            "关注点": " / ".join(item.get("concerns", [])),
            "建议": item.get("best_fix"),
        }
        for item in pack.get("consensus", [])
    ]
    complaint_rows = [
        {
            "陪审员": item.get("name"),
            "关注点": item.get("concern"),
            "卡点位置": item.get("position_canonical") or item.get("position"),
            "原因": item.get("reason"),
            "建议": item.get("fix"),
        }
        for item in pack.get("complaints", [])[:12]
    ]
    responder = str(bundle.get("responder") or "")
    if responder.startswith("mock_llm_responder"):
        reaction_boundary = "本报告由 mock_llm_responder 生成模拟陪审反应,用于验证 orchestrator e2e 链路。"
    else:
        reaction_boundary = "陪审反应由宿主 Agent/模型回填;本报告未使用 mock_llm_responder 模拟反应。"

    return {
        "title": f"陪审团评审报告 · {plan['scenario']['name']}",
        "summary": {
            "session_id": brief.get("session_id"),
            "scenario": plan["scenario"]["slug"],
            "artifact_type": fields.get("artifact_type", {}).get("value"),
            "target_audience": fields.get("target_audience", {}).get("value"),
            "key_concern": fields.get("key_concern", {}).get("value"),
            "participants": pack.get("n_participants"),
            "observations": ", ".join(observations.keys()) or "无",
        },
        "sections": [
            {
                "title": "DAG 执行概览",
                "table": [
                    {"mode": item["mode"], "reason": item["reason"]}
                    for item in plan.get("dag", [])
                ],
            },
            {
                "title": "Observe 摘要",
                "body": json.dumps(
                    {
                        name: obs.get("summary")
                        or obs.get("timeline_summary")
                        or obs.get("status")
                        for name, obs in observations.items()
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            },
            {
                "title": "共识卡点",
                "table": consensus_rows,
                "body": "暂无频次 >= 2 的共识卡点。" if not consensus_rows else "",
            },
            {
                "title": "具体问题样例",
                "table": complaint_rows,
            },
            {
                "title": "评分均值",
                "table": [
                    {"指标": metric, "均值": value}
                    for metric, value in score_averages.items()
                ],
            },
        ],
        "aggregate": {
            "complaints": pack.get("complaints", []),
            "consensus": pack.get("consensus", []),
            "divergence": pack.get("divergence", []),
            "score_matrix": pack.get("score_matrix", {}),
        },
        "boundaries": [
            reaction_boundary,
            "正式评审链路以 bundle.participants[*].reaction 的实际回填内容为准。",
            "不预测转化率/点击率/完播率等绝对值,只输出风险、共识、分歧和路径建议。",
        ],
    }


def render_all_reports(
    brief: dict,
    plan: dict,
    bundle: dict,
    pack: dict,
    observations: dict,
    reports_dir: Path,
    *,
    scenario: str,
    artifacts: dict[str, str] | None = None,
) -> dict[str, str]:
    import report as report_mod  # noqa: WPS433
    import markdown_renderer  # noqa: WPS433
    import html_renderer  # noqa: WPS433
    import docx_xml_renderer  # noqa: WPS433

    sid = brief["session_id"]
    report_data = build_generic_report_data(brief, plan, bundle, pack, observations)
    report_data["observations"] = observations
    report_data["plan"] = plan
    report_data["artifacts"] = artifacts or {}

    report_data_path = reports_dir / f"{sid}.report_data.json"
    report_data_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if scenario == "review-short-video":
        report_md = report_mod.render_report(brief, bundle, pack)
    else:
        report_md = markdown_renderer.render_report(report_data)
    report_path = reports_dir / f"{sid}.md"
    report_path.write_text(report_md, encoding="utf-8")

    report_html = html_renderer.render_report(report_data)
    report_html_path = reports_dir / f"{sid}.html"
    report_html_path.write_text(report_html, encoding="utf-8")

    report_docx_xml = docx_xml_renderer.render_docx_xml(report_data)
    report_docx_xml_path = reports_dir / f"{sid}.docx.xml"
    report_docx_xml_path.write_text(report_docx_xml, encoding="utf-8")

    return {
        "report_data": str(report_data_path),
        "report_md": str(report_path),
        "report_html": str(report_html_path),
        "report_docx_xml": str(report_docx_xml_path),
    }
