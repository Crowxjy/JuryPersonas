"""Stage runners for the executable Jury Personas DAG."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from .artifacts import artifact_field_path, resolve_input_path
    from .bootstrap import SKILL_ROOT, ensure_skill_import_paths
    from .command_runner import log_event, run_json_command
except ImportError:
    from artifacts import artifact_field_path, resolve_input_path  # type: ignore
    from bootstrap import SKILL_ROOT, ensure_skill_import_paths  # type: ignore
    from command_runner import log_event, run_json_command  # type: ignore

ensure_skill_import_paths()


def build_fit_persona(fit_spec_path: Path, personas_dir: Path) -> dict:
    import fit_persona  # noqa: WPS433

    spec = json.loads(fit_spec_path.read_text(encoding="utf-8"))
    errors = fit_persona.validate(spec)
    if errors:
        return {"status": "ERROR", "errors": errors, "input": str(fit_spec_path)}
    built = fit_persona.build_persona(spec)
    role_id = built["role_id"]
    target = personas_dir / f"{role_id}.md"
    target.write_text(built["markdown"], encoding="utf-8")
    return {
        "mode": "mode/persona-fit",
        "status": "OK",
        "role_id": role_id,
        "path": str(target),
        "fit_fidelity": "临时拟合画像,保真度未验证",
        "source": str(fit_spec_path),
    }


def sample_personas_to_runtime(
    current_dist: Path,
    target_dist: Path | None,
    personas_dir: Path,
    *,
    count: int,
) -> dict:
    output = personas_dir / "persona_sample.json"
    cmd = [
        sys.executable,
        str(SKILL_ROOT / "modes" / "jury" / "sample_personas.py"),
        "--dist",
        str(current_dist),
        "--count",
        str(count),
        "--output",
        str(output),
    ]
    if target_dist:
        cmd.extend(["--target-dist", str(target_dist)])
    result = run_json_command(cmd, event="execute.persona_sample")
    if output.exists():
        return json.loads(output.read_text(encoding="utf-8"))
    return result


def run_heatmap_observe(
    image_path: Path | None,
    aoi_path: Path | None,
    observations_dir: Path,
    sid: str,
    *,
    engine: str,
) -> tuple[dict, dict[str, str]]:
    if not image_path:
        return {
            "mode": "mode/heatmap",
            "status": "SKIPPED",
            "reason": "缺少 image_path;文本评审继续执行",
        }, {}
    if engine == "A" and not aoi_path:
        return {
            "mode": "mode/heatmap",
            "status": "SKIPPED",
            "reason": "A 档 heatmap 需要 aoi_json;文本评审继续执行",
            "image": str(image_path),
        }, {}

    outdir = observations_dir / f"{sid}.heatmap"
    cmd = [
        sys.executable,
        str(SKILL_ROOT / "modes" / "observe" / "heatmap.py"),
        "--image",
        str(image_path),
        "--outdir",
        str(outdir),
        "--engine",
        engine,
    ]
    if aoi_path:
        cmd.extend(["--aoi-json", str(aoi_path)])
    result = run_json_command(cmd, event="execute.observe.heatmap")
    metrics_path = outdir / "metrics.json"
    heatmap_image = outdir / "heatmap.jpg"
    if metrics_path.exists():
        result = json.loads(metrics_path.read_text(encoding="utf-8"))
    obs = {
        "mode": "mode/heatmap",
        "status": "OK" if metrics_path.exists() else result.get("status", "ERROR"),
        "source_image": str(image_path),
        "metrics_path": str(metrics_path) if metrics_path.exists() else None,
        "heatmap_image": str(heatmap_image) if heatmap_image.exists() else None,
        "metrics_summary": {
            "engine": result.get("meta", {}).get("engine"),
            "needs_human_confirm": result.get("meta", {}).get("needs_human_confirm"),
            "hotspots": len(result.get("attention_distribution", {}).get("hotspots", [])),
            "cognitive_load": result.get("cognitive_load", {}),
            "coverage": result.get("coverage", {}),
        },
        "raw": result,
    }
    artifacts = {}
    if metrics_path.exists():
        artifacts["heatmap_metrics"] = str(metrics_path)
    if heatmap_image.exists():
        artifacts["heatmap_image"] = str(heatmap_image)
    return obs, artifacts


def run_cross_page_observe(
    metric_paths: list[Path],
    observations_dir: Path,
    sid: str,
    *,
    labels: list[str] | None = None,
) -> tuple[dict, dict[str, str]]:
    if len(metric_paths) < 2:
        return {
            "mode": "mode/cross-page",
            "status": "SKIPPED",
            "reason": "需要至少两个 metrics.json;单页/文本评审继续执行",
        }, {}
    out_path = observations_dir / f"{sid}.cross_page.json"
    cmd = [
        sys.executable,
        str(SKILL_ROOT / "modes" / "observe" / "cross_page.py"),
        "--metrics",
        *[str(p) for p in metric_paths],
        "--order-basis",
        "artifact.page_metrics order",
        "--out",
        str(out_path),
    ]
    if labels:
        cmd.extend(["--labels", *labels])
    result = run_json_command(cmd, event="execute.observe.cross_page")
    if out_path.exists():
        result = json.loads(out_path.read_text(encoding="utf-8"))
    return result, {"cross_page_observation": str(out_path)} if out_path.exists() else {}


def run_annotate_observe(
    image_path: Path | None,
    semantic_path: Path | None,
    issues_path: Path | None,
    observations_dir: Path,
    sid: str,
) -> tuple[dict, dict[str, str]]:
    if not image_path or not semantic_path or not issues_path:
        return {
            "mode": "mode/annotate-issues",
            "status": "SKIPPED",
            "reason": "需要 image_path + semantic_file + issues_file",
        }, {}
    out_path = observations_dir / f"{sid}.issues.png"
    cmd = [
        sys.executable,
        str(SKILL_ROOT / "modes" / "observe" / "annotate_issues.py"),
        "--image",
        str(image_path),
        "--semantic",
        str(semantic_path),
        "--issues",
        str(issues_path),
        "--out",
        str(out_path),
    ]
    result = run_json_command(cmd, event="execute.observe.annotate")
    obs = {
        "mode": "mode/annotate-issues",
        "status": "OK" if out_path.exists() else result.get("status", "ERROR"),
        "annotated_image": str(out_path) if out_path.exists() else None,
        "raw": result,
    }
    return obs, {"annotated_image": str(out_path)} if out_path.exists() else {}


def run_observe_stage(
    *,
    sid: str,
    scenario: str,
    dag_modes: list[str],
    artifact: dict,
    artifact_path: Path,
    observations_dir: Path,
    artifacts: dict[str, str],
    hci_engine: str,
    aoi_json: Path | None,
    semantic_file: Path | None,
    issues_file: Path | None,
) -> dict[str, dict]:
    import copy_extract  # noqa: WPS433
    import design_extract  # noqa: WPS433
    import detail_page_extract  # noqa: WPS433
    import keyframe_extract  # noqa: WPS433
    import product_card_extract  # noqa: WPS433
    import prd_extract  # noqa: WPS433
    import screen_extract  # noqa: WPS433

    observations: dict[str, dict] = {}

    if "mode/keyframe-extract" in dag_modes or scenario == "review-short-video":
        log_event("execute.observe.keyframe.start")
        keyframe_obs = keyframe_extract.build_keyframe_observation(
            artifact,
            source=str(artifact_path),
        )
        keyframe_path = observations_dir / f"{sid}.keyframe.json"
        keyframe_path.write_text(
            json.dumps(keyframe_obs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        observations["keyframe_extract"] = keyframe_obs
        artifacts["keyframe_observation"] = str(keyframe_path)
        log_event("execute.observe.keyframe.done", path=keyframe_path, status=keyframe_obs.get("status"))

    if "mode/prd-extract" in dag_modes or scenario == "review-prd":
        prd_text = artifact.get("content")
        if prd_text:
            log_event("execute.observe.prd.start", chars=len(prd_text))
            prd_obs = prd_extract.extract_prd(prd_text, source=str(artifact_path))
            prd_path = observations_dir / f"{sid}.prd.json"
            prd_path.write_text(json.dumps(prd_obs, ensure_ascii=False, indent=2), encoding="utf-8")
            observations["prd_extract"] = prd_obs
            artifacts["prd_observation"] = str(prd_path)
            log_event(
                "execute.observe.prd.done",
                path=prd_path,
                requirements=len(prd_obs.get("requirements", [])),
                risks=len(prd_obs.get("risks", [])),
            )
        else:
            log_event("execute.observe.prd.skip", reason="artifact_has_no_content")

    if "mode/copy-extract" in dag_modes or scenario == "review-marketing-copy":
        copy_text = artifact.get("content")
        if copy_text:
            log_event("execute.observe.copy.start", chars=len(copy_text))
            copy_obs = copy_extract.extract_copy(copy_text, source=str(artifact_path))
            copy_path = observations_dir / f"{sid}.copy.json"
            copy_path.write_text(json.dumps(copy_obs, ensure_ascii=False, indent=2), encoding="utf-8")
            observations["copy_extract"] = copy_obs
            artifacts["copy_observation"] = str(copy_path)
            log_event(
                "execute.observe.copy.done",
                path=copy_path,
                claims=copy_obs.get("summary", {}).get("n_claims"),
                cta=copy_obs.get("summary", {}).get("n_cta_candidates"),
                risks=copy_obs.get("summary", {}).get("n_risk_words"),
            )
        else:
            log_event("execute.observe.copy.skip", reason="artifact_has_no_content")

    if "mode/design-extract" in dag_modes or scenario == "review-design":
        design_text = artifact.get("content")
        if design_text:
            log_event("execute.observe.design.start", chars=len(design_text))
            design_obs = design_extract.extract_design(design_text, source=str(artifact_path))
            design_path = observations_dir / f"{sid}.design.json"
            design_path.write_text(json.dumps(design_obs, ensure_ascii=False, indent=2), encoding="utf-8")
            observations["design_extract"] = design_obs
            artifacts["design_observation"] = str(design_path)
            log_event(
                "execute.observe.design.done",
                path=design_path,
                missing=design_obs.get("summary", {}).get("n_missing_critical_fields"),
                cta=design_obs.get("summary", {}).get("n_cta"),
            )
        else:
            log_event("execute.observe.design.skip", reason="artifact_has_no_content")

    if "mode/screen-extract" in dag_modes or scenario == "review-screen":
        screen_text = artifact.get("content")
        if screen_text:
            log_event("execute.observe.screen.start", chars=len(screen_text))
            screen_obs = screen_extract.extract_screen(screen_text, source=str(artifact_path))
            screen_path = observations_dir / f"{sid}.screen.json"
            screen_path.write_text(json.dumps(screen_obs, ensure_ascii=False, indent=2), encoding="utf-8")
            observations["screen_extract"] = screen_obs
            artifacts["screen_observation"] = str(screen_path)
            log_event(
                "execute.observe.screen.done",
                path=screen_path,
                missing=screen_obs.get("summary", {}).get("n_missing_critical_fields"),
                cta=screen_obs.get("summary", {}).get("n_cta"),
            )
        else:
            log_event("execute.observe.screen.skip", reason="artifact_has_no_content")

    if "mode/detail-page-extract" in dag_modes or scenario == "review-detail-page":
        detail_text = artifact.get("content")
        if detail_text:
            log_event("execute.observe.detail_page.start", chars=len(detail_text))
            detail_obs = detail_page_extract.extract_detail_page(detail_text, source=str(artifact_path))
            detail_path = observations_dir / f"{sid}.detail_page.json"
            detail_path.write_text(json.dumps(detail_obs, ensure_ascii=False, indent=2), encoding="utf-8")
            observations["detail_page_extract"] = detail_obs
            artifacts["detail_page_observation"] = str(detail_path)
            log_event(
                "execute.observe.detail_page.done",
                path=detail_path,
                missing=detail_obs.get("summary", {}).get("n_missing_critical_fields"),
                cta=detail_obs.get("summary", {}).get("n_cta"),
                rules=detail_obs.get("summary", {}).get("n_rules"),
            )
        else:
            log_event("execute.observe.detail_page.skip", reason="artifact_has_no_content")

    if "mode/product-card-extract" in dag_modes or scenario == "review-product-card":
        card_text = artifact.get("content")
        if card_text:
            log_event("execute.observe.product_card.start", chars=len(card_text))
            card_obs = product_card_extract.extract_product_card(card_text, source=str(artifact_path))
            card_path = observations_dir / f"{sid}.product_card.json"
            card_path.write_text(json.dumps(card_obs, ensure_ascii=False, indent=2), encoding="utf-8")
            observations["product_card_extract"] = card_obs
            artifacts["product_card_observation"] = str(card_path)
            log_event(
                "execute.observe.product_card.done",
                path=card_path,
                missing=card_obs.get("summary", {}).get("n_missing_critical_fields"),
                cta=card_obs.get("summary", {}).get("n_cta"),
                offers=card_obs.get("summary", {}).get("n_price_or_offer"),
            )
        else:
            log_event("execute.observe.product_card.skip", reason="artifact_has_no_content")

    image_path = (
        resolve_input_path(str(artifact_path), artifact_path=artifact_path, artifact=artifact)
        if artifact_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".ppm"}
        else artifact_field_path(
            artifact,
            artifact_path,
            ("hci", "image_path"),
            ("image_path",),
            ("screenshot_path",),
        )
    )
    aoi_path = aoi_json or artifact_field_path(artifact, artifact_path, ("hci", "aoi_json"), ("aoi_json",))
    semantic_path = semantic_file or artifact_field_path(
        artifact, artifact_path, ("hci", "semantic_file"), ("semantic_file",)
    )
    issues_path = issues_file or artifact_field_path(
        artifact, artifact_path, ("hci", "issues_file"), ("issues_file",)
    )

    if "mode/heatmap" in dag_modes:
        log_event("execute.observe.heatmap.start", engine=hci_engine)
        heatmap_obs, heatmap_artifacts = run_heatmap_observe(
            image_path,
            aoi_path,
            observations_dir,
            sid,
            engine=hci_engine,
        )
        heatmap_path = observations_dir / f"{sid}.heatmap.json"
        heatmap_path.write_text(json.dumps(heatmap_obs, ensure_ascii=False, indent=2), encoding="utf-8")
        observations["heatmap"] = heatmap_obs
        artifacts["heatmap_observation"] = str(heatmap_path)
        artifacts.update(heatmap_artifacts)
        log_event("execute.observe.heatmap.done", status=heatmap_obs.get("status"))

    metric_paths = []
    if artifacts.get("heatmap_metrics"):
        metric_paths.append(Path(artifacts["heatmap_metrics"]))
    page_metrics = artifact.get("page_metrics") or artifact.get("hci", {}).get("page_metrics") or []
    for raw in page_metrics:
        path = resolve_input_path(str(raw), artifact_path=artifact_path, artifact=artifact)
        if path and path.exists():
            metric_paths.append(path)

    if "mode/cross-page" in dag_modes:
        log_event("execute.observe.cross_page.start", metrics=len(metric_paths))
        labels = artifact.get("page_labels") or artifact.get("hci", {}).get("page_labels")
        cross_obs, cross_artifacts = run_cross_page_observe(
            metric_paths,
            observations_dir,
            sid,
            labels=labels if isinstance(labels, list) else None,
        )
        observations["cross_page"] = cross_obs
        artifacts.update(cross_artifacts)
        log_event("execute.observe.cross_page.done", status=cross_obs.get("status"))

    if "mode/annotate-issues" in dag_modes:
        log_event("execute.observe.annotate.start")
        annotate_obs, annotate_artifacts = run_annotate_observe(
            image_path,
            semantic_path,
            issues_path,
            observations_dir,
            sid,
        )
        annotate_path = observations_dir / f"{sid}.annotate_issues.json"
        annotate_path.write_text(json.dumps(annotate_obs, ensure_ascii=False, indent=2), encoding="utf-8")
        observations["annotate_issues"] = annotate_obs
        artifacts["annotate_observation"] = str(annotate_path)
        artifacts.update(annotate_artifacts)
        log_event("execute.observe.annotate.done", status=annotate_obs.get("status"))

    return observations


def run_persona_stage(
    *,
    sid: str,
    dag_modes: list[str],
    artifact: dict,
    artifact_path: Path,
    persona_ids: list[str],
    personas_dir: Path,
    artifacts: dict[str, str],
    current_dist: Path | None,
    target_dist: Path | None,
    fit_spec_file: Path | None,
) -> tuple[list[str], dict | None]:
    import persona_pick  # noqa: WPS433

    if "mode/persona-fit" in dag_modes:
        fit_path = fit_spec_file or artifact_field_path(
            artifact, artifact_path, ("persona_fit", "spec_file"), ("fit_spec_file",)
        )
        if fit_path:
            log_event("execute.persona_fit.start", input=fit_path)
            fit_pack = build_fit_persona(fit_path, personas_dir)
            fit_pack_path = personas_dir / f"{sid}.persona_fit.json"
            fit_pack_path.write_text(json.dumps(fit_pack, ensure_ascii=False, indent=2), encoding="utf-8")
            artifacts["persona_fit"] = str(fit_pack_path)
            if fit_pack.get("status") == "OK" and fit_pack.get("role_id") not in persona_ids:
                persona_ids = [*persona_ids, str(fit_pack["role_id"])]
                os.environ["JURY_PERSONAS_EXTRA_PERSONA_DIRS"] = str(personas_dir)
            log_event("execute.persona_fit.done", status=fit_pack.get("status"))
        else:
            log_event("execute.persona_fit.skip", reason="missing_fit_spec_file")

    if "mode/persona-sample" in dag_modes:
        sample_current = current_dist or artifact_field_path(
            artifact, artifact_path, ("persona_sample", "current_dist"), ("current_dist",)
        )
        sample_target = target_dist or artifact_field_path(
            artifact, artifact_path, ("persona_sample", "target_dist"), ("target_dist",)
        )
        if sample_current:
            log_event("execute.persona_sample.start", current=sample_current, target=sample_target)
            sample_pack = sample_personas_to_runtime(
                sample_current,
                sample_target,
                personas_dir,
                count=max(1, len(persona_ids)),
            )
            sample_path = personas_dir / f"{sid}.persona_sample.json"
            sample_path.write_text(json.dumps(sample_pack, ensure_ascii=False, indent=2), encoding="utf-8")
            artifacts["persona_sample"] = str(sample_path)
            sampled_role_ids = [
                item.get("role_id")
                for item in sample_pack.get("selected", [])
                if item.get("role_id")
            ]
            if sampled_role_ids:
                persona_ids = [str(x) for x in sampled_role_ids]
            log_event("execute.persona_sample.done", selected=",".join(persona_ids))
        else:
            log_event("execute.persona_sample.skip", reason="missing_current_dist")

    if "mode/persona-pick" in dag_modes:
        log_event("execute.persona_pick.start", personas=",".join(persona_ids))
        persona_pack = persona_pick.pick_personas(persona_ids, compile_prompts=False)
        persona_pack_path = personas_dir / f"{sid}.persona_pick.json"
        persona_pack_path.write_text(json.dumps(persona_pack, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts["persona_pick"] = str(persona_pack_path)
        log_event(
            "execute.persona_pick.done",
            path=persona_pack_path,
            status=persona_pack.get("status"),
            errors=len(persona_pack.get("errors", [])),
        )
        if persona_pack["status"] == "ERROR":
            log_event("execute.persona_pick.failed")
            return persona_ids, {
                "status": "PERSONA_PICK_FAILED",
                "session_id": sid,
                "artifacts": artifacts,
                "errors": persona_pack["errors"],
            }

    return persona_ids, None


def run_jury_react_stage(
    *,
    sid: str,
    brief: dict,
    artifact: dict,
    persona_ids: list[str],
    scenario: str,
    observations: dict[str, dict],
    reactions_dir: Path,
    artifacts: dict[str, str],
    use_mock_llm: bool,
) -> tuple[dict, dict | None]:
    import jury_react  # noqa: WPS433
    import mock_llm_responder  # noqa: WPS433

    log_event("execute.jury_react.start", observations=",".join(observations.keys()) or "none")
    bundle = jury_react.build_jury_react_bundle(
        brief,
        artifact,
        persona_ids,
        scenario=scenario,
        observations=observations,
    )
    bundle_path = reactions_dir / f"{sid}.bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts["bundle"] = str(bundle_path)
    log_event(
        "execute.jury_react.done",
        path=bundle_path,
        participants=len(bundle.get("participants", [])),
        errors=len(bundle.get("errors", [])),
    )

    if bundle.get("errors"):
        log_event("execute.jury_react.failed")
        return bundle, {
            "status": "JURY_REACT_BUNDLE_FAILED",
            "session_id": sid,
            "artifacts": artifacts,
            "errors": bundle["errors"],
        }

    filled_path = reactions_dir / f"{sid}.filled.json"
    if use_mock_llm:
        log_event("execute.mock_reactions.start")
        mock_llm_responder.fill_bundle(bundle)
        filled_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts["filled_bundle"] = str(filled_path)
        log_event("execute.mock_reactions.done", path=filled_path)
        return bundle, None

    log_event("execute.waiting_for_reactions", bundle=bundle_path)
    return bundle, {
        "status": "WAITING_FOR_REACTIONS",
        "session_id": sid,
        "scenario": scenario,
        "artifacts": artifacts,
        "observations": list(observations.keys()),
        "next_step": (
            "宿主 Agent/模型需为 bundle.participants[*] 填 reaction,"
            "再喂给 modes/aggregate/consensus.py"
        ),
        "note": "已按 --no-mock-llm 停在 reactions bundle。",
    }


def run_aggregate_stage(
    *,
    sid: str,
    dag_modes: list[str],
    bundle: dict,
    consensus_dir: Path,
    artifacts: dict[str, str],
    observations: dict[str, dict],
    artifact: dict | None = None,
    artifact_path: Path | None = None,
    current_dist: Path | None = None,
    target_dist: Path | None = None,
) -> tuple[dict, Path]:
    import consensus as consensus_mod  # noqa: WPS433

    pack = consensus_mod.build_consensus_pack(bundle)
    consensus_path = consensus_dir / f"{sid}.json"
    consensus_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts["consensus"] = str(consensus_path)

    if "mode/aggregate-distribution-gap" in dag_modes:
        gap_current = current_dist
        gap_target = target_dist
        if artifact is not None and artifact_path is not None:
            gap_current = gap_current or artifact_field_path(
                artifact, artifact_path, ("persona_sample", "current_dist"), ("current_dist",)
            )
            gap_target = gap_target or artifact_field_path(
                artifact, artifact_path, ("persona_sample", "target_dist"), ("target_dist",)
            )
        if gap_current and gap_target:
            gap_path = consensus_dir / f"{sid}.distribution_gap.json"
            cmd = [
                sys.executable,
                str(SKILL_ROOT / "modes" / "aggregate" / "distribution_gap.py"),
                "--current-dist",
                str(gap_current),
                "--target-dist",
                str(gap_target),
                "--consensus-file",
                str(consensus_path),
                "--output",
                str(gap_path),
                "--pretty",
            ]
            gap_result = run_json_command(cmd, event="execute.aggregate.distribution_gap")
            if gap_path.exists():
                gap_result = json.loads(gap_path.read_text(encoding="utf-8"))
            observations["distribution_gap"] = gap_result
            artifacts["distribution_gap"] = str(gap_path)
            log_event(
                "execute.aggregate.distribution_gap.done",
                rows=gap_result.get("summary", {}).get("n_gap_rows"),
            )
        else:
            observations["distribution_gap"] = {
                "mode": "mode/aggregate-distribution-gap",
                "status": "SKIPPED",
                "reason": "需要 current_dist + target_dist",
            }
            log_event("execute.aggregate.distribution_gap.skip", reason="missing_dist")

    return pack, consensus_path


def run_synthesize_stage(
    *,
    sid: str,
    dag_modes: list[str],
    plan: dict,
    pack: dict,
    observations: dict[str, dict],
    consensus_path: Path,
    decisions_dir: Path,
    artifacts: dict[str, str],
) -> None:
    import paths as paths_mod  # noqa: WPS433
    import tension as tension_mod  # noqa: WPS433

    if "mode/synthesize-tension" in dag_modes:
        tension_bundle = tension_mod.build_tension_bundle(
            {
                "consensus_pack": pack,
                "observations": observations,
                "brief_summary": plan.get("brief_summary", {}),
            },
            source_path=consensus_path,
        )
        tension_path = decisions_dir / f"{sid}.tension.bundle.json"
        tension_path.write_text(json.dumps(tension_bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts["tension_bundle"] = str(tension_path)

    if "mode/synthesize-paths" in dag_modes:
        paths_bundle = paths_mod.build_paths_bundle(
            {
                "status": "WAITING_FOR_TENSION_RESULT",
                "note": "需要宿主 Agent/模型基于 tension_bundle 产出 dominant_tension 后再生成最终双路径。",
                "tension_bundle": artifacts.get("tension_bundle"),
                "consensus_summary": {
                    "complaints": len(pack.get("complaints", [])),
                    "consensus": len(pack.get("consensus", [])),
                    "divergence": len(pack.get("divergence", [])),
                },
            },
            source_path=Path(artifacts["tension_bundle"]) if artifacts.get("tension_bundle") else consensus_path,
        )
        paths_path = decisions_dir / f"{sid}.paths.bundle.json"
        paths_path.write_text(json.dumps(paths_bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts["paths_bundle"] = str(paths_path)
