#!/usr/bin/env python3
"""
pipeline.py — Brief → scenario DAG 调度 + Skill 执行器

职责:
1. 读 brief.json
2. 跑 brief_validator 五重校验,不过则输出 next_action 让 Agent 重收
3. 过了则按 brief.fields.artifact_type 选 scenario,解析 frontmatter modes 字段
4. 按 brief.fields.distribution_intent 决定走 persona-sample / persona-fit / persona-pick
5. 输出 DAG 执行计划 JSON,或按 DAG 执行 observe/react/aggregate/synthesize/report

执行边界:
   - 场景 DAG、默认陪审团和 artifact alias 以 scenarios/review-*.md frontmatter 为事实源
   - 本地回归可用 tools/mock_llm_responder.py 回填 reactions
   - 正式使用时由宿主 Agent/模型回填 reactions;脚本层保持 Skill 形态
   - 报告优先产出 HTML,同时生成 Markdown/DocxXML;--lark-execute 使用 DocxXML 走 lark-doc v2 真发布

使用模式:

    # 仅出 plan
    python3 pipeline.py --brief-file <path>

    # 本地执行端到端
    python3 pipeline.py --brief-file <path> \\
        --artifact-file <artifact.json> \\
        --personas consumer-bao-mom-tier2,consumer-silver-male,consumer-bluecollar-male \\
        --execute \\
        --runtime-dir /tmp/jp_runtime

    # 不要 mock(等待宿主 Agent/模型回填 reactions),只跑到 jury-react bundle
    python3 pipeline.py --brief-file <path> --artifact-file <a> \\
        --personas a,b,c --execute --no-mock-llm
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:  # package import path
    from .artifacts import load_artifact, resolve_input_path
    from .bootstrap import SKILL_ROOT, ensure_skill_import_paths
    from .command_runner import log_event
    from .dag import build_plan, default_persona_ids_for_scenario
    from .reporting_stage import render_all_reports
    from .stage_runner import (
        run_aggregate_stage,
        run_jury_react_stage,
        run_observe_stage,
        run_persona_stage,
        run_synthesize_stage,
    )
except ImportError:  # direct script execution: python orchestrator/pipeline.py
    from artifacts import load_artifact, resolve_input_path  # type: ignore
    from bootstrap import SKILL_ROOT, ensure_skill_import_paths  # type: ignore
    from command_runner import log_event  # type: ignore
    from dag import build_plan, default_persona_ids_for_scenario  # type: ignore
    from reporting_stage import render_all_reports  # type: ignore
    from stage_runner import (  # type: ignore
        run_aggregate_stage,
        run_jury_react_stage,
        run_observe_stage,
        run_persona_stage,
        run_synthesize_stage,
    )

ensure_skill_import_paths()

import brief_validator  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Brief → scenario DAG 调度 + Skill 执行器")
    parser.add_argument("--brief-file", required=True, help="Agent 吐出的 brief JSON 路径")
    parser.add_argument("--context-file", help="用户原始上下文文件,触发 evidence 回溯")
    parser.add_argument("--first-round", action="store_true", help="首次会话标记")
    parser.add_argument(
        "--include", action="append", default=[], help="用户增加的可选模式(可多次)"
    )
    parser.add_argument(
        "--exclude", action="append", default=[], help="用户排除的非 required 模式(可多次)"
    )
    parser.add_argument("--pretty", action="store_true", help="美化 JSON 输出")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="按 DAG 执行,否则只输出计划",
    )
    parser.add_argument(
        "--artifact-file",
        help="评审对象 JSON 路径(--execute 必需)",
    )
    parser.add_argument(
        "--personas",
        help="陪审员 role_id 列表,逗号分隔;不传则使用场景默认组合",
    )
    parser.add_argument(
        "--runtime-dir",
        default="/tmp/jp_m3",
        help="执行产物目录(默认 /tmp/jp_m3,可改为 .runtime)",
    )
    parser.add_argument(
        "--no-mock-llm",
        action="store_true",
        help="不调 mock_llm_responder,只产出 jury-react bundle 让宿主 Agent/模型回填",
    )
    parser.add_argument(
        "--filled-bundle-file",
        help="已回填 participants[*].reaction 的 bundle;从 aggregate 阶段恢复执行",
    )
    parser.add_argument(
        "--lark-execute",
        action="store_true",
        help="飞书发布关闭 dry-run;需要 lark-cli + docs v2 权限,失败不会本地伪降级",
    )
    parser.add_argument("--current-dist", help="persona-sample / distribution-gap 当前分布 JSON")
    parser.add_argument("--target-dist", help="persona-sample / distribution-gap 目标分布 JSON")
    parser.add_argument("--fit-spec-file", help="persona-fit 临时画像输入 JSON")
    parser.add_argument("--hci-engine", default="A", choices=["auto", "A", "B"], help="heatmap 引擎")
    parser.add_argument("--aoi-json", help="heatmap A 档 AOI JSON")
    parser.add_argument("--semantic-file", help="annotate-issues semantic.json")
    parser.add_argument("--issues-file", help="annotate-issues issues.json")
    return parser


def finalize_filled_bundle(
    brief: dict,
    plan: dict,
    filled_bundle_path: Path,
    runtime_dir: Path,
    *,
    lark_execute: bool,
) -> dict:
    """从已回填 reaction 的 bundle 恢复执行 aggregate/synthesize/report。"""
    log_event(
        "resume.start",
        filled_bundle=filled_bundle_path,
        runtime_dir=runtime_dir,
        lark_execute=lark_execute,
    )
    import lark_renderer  # noqa: WPS433

    log_event("resume.load_bundle.start", path=filled_bundle_path)
    bundle = json.loads(filled_bundle_path.read_text(encoding="utf-8"))
    sid = brief["session_id"]
    scenario = bundle.get("scenario") or plan["scenario"]["slug"]
    dag_modes = [item["mode"] for item in plan.get("dag", [])]
    observations = bundle.get("observations") or {}
    participants = bundle.get("participants", [])
    log_event(
        "resume.load_bundle.ok",
        session_id=sid,
        scenario=scenario,
        participants=len(participants),
        observations=",".join(observations.keys()) or "none",
        dag_modes=",".join(dag_modes),
    )

    missing = [
        p.get("role_id", f"participant_{idx}")
        for idx, p in enumerate(participants)
        if not p.get("reaction")
    ]
    if missing:
        log_event("resume.reactions_incomplete", missing_role_ids=",".join(missing))
        return {
            "status": "REACTIONS_INCOMPLETE",
            "session_id": sid,
            "filled_bundle": str(filled_bundle_path),
            "missing_role_ids": missing,
            "next_step": "请补齐 bundle.participants[*].reaction 后再用 --filled-bundle-file 恢复执行。",
        }

    reactions_dir = runtime_dir / "reactions"
    consensus_dir = runtime_dir / "consensus"
    decisions_dir = runtime_dir / "decisions"
    reports_dir = runtime_dir / "reports"
    for d in (reactions_dir, consensus_dir, decisions_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)
        log_event("resume.ensure_dir", path=d)

    canonical_filled_path = reactions_dir / f"{sid}.filled.json"
    if filled_bundle_path.resolve() != canonical_filled_path.resolve():
        log_event(
            "resume.copy_filled_bundle.start",
            source=filled_bundle_path,
            target=canonical_filled_path,
        )
        canonical_filled_path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log_event("resume.copy_filled_bundle.done", target=canonical_filled_path)
    else:
        log_event("resume.copy_filled_bundle.skip", target=canonical_filled_path)

    artifacts: dict[str, str] = {"filled_bundle": str(canonical_filled_path)}
    log_event("resume.aggregate.start")
    pack, consensus_path = run_aggregate_stage(
        sid=sid,
        dag_modes=dag_modes,
        bundle=bundle,
        consensus_dir=consensus_dir,
        artifacts=artifacts,
        observations=observations,
    )
    log_event(
        "resume.aggregate.done",
        path=consensus_path,
        complaints=len(pack.get("complaints", [])),
        consensus=len(pack.get("consensus", [])),
        divergence=len(pack.get("divergence", [])),
    )

    log_event("resume.synthesize.start")
    run_synthesize_stage(
        sid=sid,
        dag_modes=dag_modes,
        plan=plan,
        pack=pack,
        observations=observations,
        consensus_path=consensus_path,
        decisions_dir=decisions_dir,
        artifacts=artifacts,
    )
    log_event(
        "resume.synthesize.done",
        tension=artifacts.get("tension_bundle"),
        paths=artifacts.get("paths_bundle"),
    )

    log_event("resume.render_report.start", scenario=scenario)
    report_artifacts = render_all_reports(
        brief,
        plan,
        bundle,
        pack,
        observations,
        reports_dir,
        scenario=scenario,
        artifacts=artifacts,
    )
    artifacts.update(report_artifacts)
    publish_report_path = Path(report_artifacts["report_docx_xml"])
    log_event(
        "resume.render_report.done",
        md=report_artifacts["report_md"],
        html=report_artifacts["report_html"],
        docx_xml=report_artifacts["report_docx_xml"],
    )

    log_event("resume.publish.start", dry_run=not lark_execute, source=publish_report_path)
    publish_result = lark_renderer.publish(
        publish_report_path,
        title=f"陪审团评审报告 · {sid}",
        session_id=sid,
        local_only=False,
        dry_run=not lark_execute,
        output_dir=reports_dir,
        execute=lark_execute,
        doc_format="xml",
    )
    log_event(
        "resume.publish.done",
        status=publish_result.get("status"),
        saved_to=publish_result.get("saved_to"),
    )
    status = (
        "PUBLISH_FAILED"
        if lark_execute and publish_result.get("status") != "OK"
        else "OK"
    )

    result = {
        "status": status,
        "session_id": sid,
        "n_participants": pack["n_participants"],
        "artifacts": artifacts,
        "summary": {
            "complaints": len(pack["complaints"]),
            "consensus": len(pack["consensus"]),
            "divergence": len(pack["divergence"]),
            "score_averages": pack["score_matrix"]["averages"],
        },
        "publish": publish_result,
    }
    log_event("resume.done", status=result["status"], artifacts=len(artifacts))
    return result


def execute_dag(
    brief: dict,
    plan: dict,
    artifact_path: Path,
    persona_ids: list[str],
    runtime_dir: Path,
    *,
    use_mock_llm: bool,
    lark_execute: bool,
    current_dist: Path | None = None,
    target_dist: Path | None = None,
    fit_spec_file: Path | None = None,
    hci_engine: str = "A",
    aoi_json: Path | None = None,
    semantic_file: Path | None = None,
    issues_file: Path | None = None,
) -> dict:
    """按 DAG 执行当前已落地的模式,产物落 runtime_dir。

    默认用 mock_llm_responder 完成端到端冒烟;传 --no-mock-llm 时会停在
    WAITING_FOR_REACTIONS,等待宿主 Agent/模型回填。
    """
    import lark_renderer  # noqa: WPS433

    sid = brief["session_id"]
    scenario = plan["scenario"]["slug"]
    dag_modes = [item["mode"] for item in plan.get("dag", [])]
    log_event(
        "execute.start",
        session_id=sid,
        scenario=scenario,
        artifact=artifact_path,
        personas=",".join(persona_ids),
        use_mock_llm=use_mock_llm,
    )
    observations_dir = runtime_dir / "observations"
    personas_dir = runtime_dir / "personas"
    reactions_dir = runtime_dir / "reactions"
    consensus_dir = runtime_dir / "consensus"
    decisions_dir = runtime_dir / "decisions"
    reports_dir = runtime_dir / "reports"
    for d in (observations_dir, personas_dir, reactions_dir, consensus_dir, decisions_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)
        log_event("execute.ensure_dir", path=d)

    log_event("execute.load_artifact.start", path=artifact_path)
    artifact = load_artifact(artifact_path, brief, scenario)
    artifact["base_dir"] = str(artifact_path.parent)
    log_event(
        "execute.load_artifact.done",
        title=artifact.get("title"),
        has_content=bool(artifact.get("content")),
    )
    artifacts: dict[str, str] = {}
    observations = run_observe_stage(
        sid=sid,
        dag_modes=dag_modes,
        artifact=artifact,
        artifact_path=artifact_path,
        observations_dir=observations_dir,
        artifacts=artifacts,
        hci_engine=hci_engine,
        aoi_json=aoi_json,
        semantic_file=semantic_file,
        issues_file=issues_file,
    )

    persona_ids, persona_error = run_persona_stage(
        sid=sid,
        dag_modes=dag_modes,
        artifact=artifact,
        artifact_path=artifact_path,
        persona_ids=persona_ids,
        personas_dir=personas_dir,
        artifacts=artifacts,
        current_dist=current_dist,
        target_dist=target_dist,
        fit_spec_file=fit_spec_file,
    )
    if persona_error:
        return persona_error

    bundle, jury_error = run_jury_react_stage(
        sid=sid,
        brief=brief,
        artifact=artifact,
        persona_ids=persona_ids,
        scenario=scenario,
        observations=observations,
        reactions_dir=reactions_dir,
        artifacts=artifacts,
        use_mock_llm=use_mock_llm,
    )
    if jury_error:
        return jury_error

    pack, consensus_path = run_aggregate_stage(
        sid=sid,
        dag_modes=dag_modes,
        bundle=bundle,
        consensus_dir=consensus_dir,
        artifacts=artifacts,
        observations=observations,
        artifact=artifact,
        artifact_path=artifact_path,
        current_dist=current_dist,
        target_dist=target_dist,
    )

    run_synthesize_stage(
        sid=sid,
        dag_modes=dag_modes,
        plan=plan,
        pack=pack,
        observations=observations,
        consensus_path=consensus_path,
        decisions_dir=decisions_dir,
        artifacts=artifacts,
    )

    # Step 4: render-report
    report_artifacts = render_all_reports(
        brief,
        plan,
        bundle,
        pack,
        observations,
        reports_dir,
        scenario=scenario,
        artifacts=artifacts,
    )
    artifacts.update(report_artifacts)
    publish_report_path = Path(report_artifacts["report_docx_xml"])

    # Step 5: lark publish(默认 dry-run; --lark-execute 真发布,失败即 ERROR)
    publish_result = lark_renderer.publish(
        publish_report_path,
        title=f"陪审团评审报告 · {sid}",
        session_id=sid,
        local_only=False,
        dry_run=not lark_execute,
        output_dir=reports_dir,
        execute=lark_execute,
        doc_format="xml",
    )
    status = (
        "PUBLISH_FAILED"
        if lark_execute and publish_result.get("status") != "OK"
        else "OK"
    )

    return {
        "status": status,
        "session_id": sid,
        "n_participants": pack["n_participants"],
        "artifacts": artifacts,
        "summary": {
            "complaints": len(pack["complaints"]),
            "consensus": len(pack["consensus"]),
            "divergence": len(pack["divergence"]),
            "score_averages": pack["score_matrix"]["averages"],
        },
        "publish": publish_result,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    brief_path = Path(args.brief_file)
    if not brief_path.exists():
        sys.stderr.write(f"[error] brief 文件不存在: {brief_path}\n")
        return 2
    brief = json.loads(brief_path.read_text(encoding="utf-8"))

    context = None
    if args.context_file:
        ctx_path = Path(args.context_file)
        if ctx_path.exists():
            context = ctx_path.read_text(encoding="utf-8")

    schema_path = SKILL_ROOT / "core" / "contracts" / "brief.schema.json"
    errors = brief_validator.validate(
        brief,
        first_round=args.first_round,
        context=context,
        schema_path=schema_path,
    )
    if errors:
        out = {
            "status": "BRIEF_INVALID",
            "errors": errors,
            "session_id": brief.get("session_id"),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
        return 1

    if brief.get("verdict") != "SUFFICIENT":
        out = {
            "status": "BRIEF_INSUFFICIENT",
            "session_id": brief.get("session_id"),
            "next_action": brief.get("next_action"),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0

    try:
        plan = build_plan(brief, args.include, args.exclude)
    except RuntimeError as e:
        out = {"status": "ERROR", "message": str(e)}
        print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
        return 1

    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0

    runtime_dir = Path(args.runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    if args.filled_bundle_file:
        filled_bundle_path = Path(args.filled_bundle_file)
        if not filled_bundle_path.exists():
            out = {
                "status": "ERROR",
                "message": f"filled bundle 不存在: {filled_bundle_path}",
                "plan": plan,
            }
            print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
            return 2
        exec_result = finalize_filled_bundle(
            brief,
            plan,
            filled_bundle_path,
            runtime_dir,
            lark_execute=args.lark_execute,
        )
        out = {
            "status": exec_result["status"],
            "plan": plan,
            "execution": exec_result,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0 if exec_result["status"] == "OK" else 1

    if not args.artifact_file:
        out = {
            "status": "ERROR",
            "message": "--execute 需要提供 --artifact-file;或提供 --filled-bundle-file 恢复执行",
            "plan": plan,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
        return 2

    artifact_path = Path(args.artifact_file)
    if not artifact_path.exists():
        out = {
            "status": "ERROR",
            "message": f"artifact 不存在: {artifact_path}",
        }
        print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
        return 2

    if args.personas:
        persona_ids = [r.strip() for r in args.personas.split(",") if r.strip()]
        persona_source = "user"
    else:
        persona_ids = default_persona_ids_for_scenario(plan["scenario"]["slug"])
        persona_source = "scenario_default"
    if not persona_ids:
        out = {
            "status": "ERROR",
            "message": f"场景 {plan['scenario']['slug']} 没有默认陪审团,请显式提供 --personas",
            "plan": plan,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
        return 2
    plan["persona_selection"] = {"source": persona_source, "role_ids": persona_ids}

    exec_result = execute_dag(
        brief,
        plan,
        artifact_path,
        persona_ids,
        runtime_dir,
        use_mock_llm=not args.no_mock_llm,
        lark_execute=args.lark_execute,
        current_dist=resolve_input_path(args.current_dist, artifact_path=artifact_path),
        target_dist=resolve_input_path(args.target_dist, artifact_path=artifact_path),
        fit_spec_file=resolve_input_path(args.fit_spec_file, artifact_path=artifact_path),
        hci_engine=args.hci_engine,
        aoi_json=resolve_input_path(args.aoi_json, artifact_path=artifact_path),
        semantic_file=resolve_input_path(args.semantic_file, artifact_path=artifact_path),
        issues_file=resolve_input_path(args.issues_file, artifact_path=artifact_path),
    )
    out = {
        "status": exec_result["status"],
        "plan": plan,
        "execution": exec_result,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if exec_result["status"] in {"OK", "WAITING_FOR_REACTIONS"} else 1


if __name__ == "__main__":
    sys.exit(main())
