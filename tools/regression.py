#!/usr/bin/env python3
"""
regression.py - local end-to-end regression runner for JuryPersonas.

It only writes runtime artifacts under /tmp by default. Source files are never
modified by this runner.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TOOLS_DIR.parent
DEFAULT_RUNTIME_ROOT = Path("/tmp") / f"jp_regression_{int(time.time())}"

SCENARIO_BRIEFS = [
    "tests/fixtures/prd_demo/brief.json",
    "tests/fixtures/design_demo/brief.json",
    "tests/fixtures/screen_demo/brief.json",
    "tests/fixtures/detail_page_demo/brief.json",
    "tests/fixtures/product_card_demo/brief.json",
    "tests/fixtures/marketing_copy_demo/brief.json",
    "tests/fixtures/hci_demo/brief.json",
]


class StepFailed(RuntimeError):
    pass


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(SKILL_ROOT))
    except ValueError:
        return str(path)


def run_cmd(
    name: str,
    cmd: list[str],
    *,
    runtime_root: Path,
    expect_code: int = 0,
    check_stdout_contains: list[str] | None = None,
    check_stderr_contains: list[str] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    log_dir = runtime_root / "_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{name}.stdout.log"
    stderr_path = log_dir / f"{name}.stderr.log"

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        cmd,
        cwd=SKILL_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")

    if proc.returncode != expect_code:
        raise StepFailed(
            f"{name}: exit={proc.returncode}, expected={expect_code}, "
            f"stdout={stdout_path}, stderr={stderr_path}"
        )

    for needle in check_stdout_contains or []:
        if needle not in proc.stdout:
            raise StepFailed(
                f"{name}: stdout missing {needle!r}, "
                f"stdout={stdout_path}, stderr={stderr_path}"
            )

    for needle in check_stderr_contains or []:
        if needle not in proc.stderr:
            raise StepFailed(
                f"{name}: stderr missing {needle!r}, "
                f"stdout={stdout_path}, stderr={stderr_path}"
            )

    return {
        "name": name,
        "status": "OK",
        "exit_code": proc.returncode,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def parse_json_stdout(step: dict[str, Any]) -> dict[str, Any]:
    text = Path(step["stdout"]).read_text(encoding="utf-8")
    return json.loads(text)


def check_no_python_cache() -> list[str]:
    matches = []
    for pattern in ("__pycache__", "*.pyc", ".pytest_cache", "test_write_perm.tmp"):
        for path in SKILL_ROOT.rglob(pattern):
            matches.append(rel(path))
    return sorted(matches)


def run_regression(runtime_root: Path, *, keep_runtime: bool) -> dict[str, Any]:
    if runtime_root.exists() and not keep_runtime:
        shutil.rmtree(runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)

    steps: list[dict[str, Any]] = []
    py_files = [
        str(path.relative_to(SKILL_ROOT))
        for base in ("brief", "modes", "orchestrator", "reporting", "tools")
        for path in (SKILL_ROOT / base).rglob("*.py")
    ]
    py_files.append("jury_review.py")

    steps.append(
        run_cmd(
            "py_compile",
            [sys.executable, "-B", "-m", "py_compile", *py_files],
            runtime_root=runtime_root,
        )
    )
    steps.append(
        run_cmd(
            "lint",
            [sys.executable, "tools/lint.py"],
            runtime_root=runtime_root,
            check_stdout_contains=["errors=0"],
        )
    )
    steps.append(
        run_cmd(
            "evaluation_seed",
            [
                sys.executable,
                "tools/evaluation_runner.py",
                "--cases",
                "evals/cases/seed_cases.jsonl",
                "--runtime-root",
                str(runtime_root / "evaluation_seed"),
                "--pretty",
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                '"cases": 2',
                '"avg_gold_coverage": 1.0',
            ],
        )
    )
    steps.append(
        run_cmd(
            "persona_dedupe_report",
            [sys.executable, "tools/persona_dedupe.py", "--json"],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"conflicts"',
                '"ad-buyer-expert"',
                '"ad-buyer-senior"',
                '"ad-buyer"',
                '"resolved_conflicts"',
            ],
        )
    )
    steps.append(
        run_cmd(
            "brief_evidence_traceback_positive",
            [
                sys.executable,
                "brief/brief_validator.py",
                "--brief-file",
                "tests/fixtures/brief_sufficient.json",
                "--context-file",
                "tests/fixtures/brief_context_full.txt",
                "--quiet",
            ],
            runtime_root=runtime_root,
        )
    )
    steps.append(
        run_cmd(
            "negative_bad_evidence_traceback",
            [
                sys.executable,
                "brief/brief_validator.py",
                "--brief-file",
                "tests/fixtures/brief_sufficient.json",
                "--context-file",
                "tests/fixtures/prd_demo/prd.md",
            ],
            runtime_root=runtime_root,
            expect_code=1,
            check_stderr_contains=["无法回溯"],
        )
    )
    steps.append(
        run_cmd(
            "distribution_gap",
            [
                sys.executable,
                "modes/aggregate/distribution_gap.py",
                "--current-dist",
                "tests/fixtures/distributions/merchant_current.json",
                "--target-dist",
                "tests/fixtures/distributions/category_target.json",
                "--pretty",
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"mode": "mode/aggregate-distribution-gap"',
                '"n_gap_rows": 12',
                '"top_increase"',
                '"no_real_effect_claim_without_feedback_data": true',
            ],
        )
    )

    for idx, brief in enumerate(SCENARIO_BRIEFS, start=1):
        steps.append(
            run_cmd(
                f"scenario_plan_{idx:02d}_{Path(brief).parent.name}",
                [sys.executable, "orchestrator/pipeline.py", "--brief-file", brief],
                runtime_root=runtime_root,
                check_stdout_contains=['"status": "OK"'],
            )
        )

    short_runtime = runtime_root / "short_video"
    steps.append(
        run_cmd(
            "short_video_e2e",
            [
                sys.executable,
                "jury_review.py",
                "--brief",
                "tests/fixtures/short_video_demo/brief.json",
                "--artifact",
                "tests/fixtures/short_video_demo/artifact.json",
                "--personas",
                "consumer-bao-mom-tier2,consumer-silver-male,consumer-bluecollar-male",
                "--runtime-dir",
                str(short_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                  '"complaints"',
                  '"consensus"',
                  '"divergence"',
            ],
        )
    )

    prd_runtime = runtime_root / "prd_direct"
    steps.append(
        run_cmd(
            "prd_direct_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/prd_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/prd_demo/prd.md",
                "--personas",
                "product-expert,ad-buyer",
                "--execute",
                "--runtime-dir",
                str(prd_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                  '"complaints"',
                  '"consensus"',
                  '"divergence"',
                "tension_bundle",
                "paths_bundle",
                "report_md",
                "report_html",
            ],
        )
    )
    steps.append(
        run_cmd(
            "default_personas_prd_handoff",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/prd_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/prd_demo/prd.md",
                "--execute",
                "--no-mock-llm",
                "--runtime-dir",
                str(runtime_root / "default_personas_prd_handoff"),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                "WAITING_FOR_REACTIONS",
                '"source": "scenario_default"',
                "product-expert",
                "ad-buyer",
            ],
        )
    )

    dag_stage_observe_runtime = runtime_root / "dag_stage_observe"
    steps.append(
        run_cmd(
            "dag_stage_observe_handoff",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/dag_stage_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/dag_stage_demo/copy.md",
                "--personas",
                "consumer-genz-female,ad-buyer",
                "--execute",
                "--no-mock-llm",
                "--runtime-dir",
                str(dag_stage_observe_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                "WAITING_FOR_REACTIONS",
                "copy_observation",
                "bundle",
            ],
        )
    )

    dag_stage_runtime = runtime_root / "dag_stage_full"
    steps.append(
        run_cmd(
            "dag_stage_full_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/dag_stage_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/dag_stage_demo/copy.md",
                "--personas",
                "consumer-genz-female,ad-buyer",
                "--execute",
                "--runtime-dir",
                str(dag_stage_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                "copy_observation",
                "consensus",
                "tension_bundle",
                "paths_bundle",
                "report_html",
            ],
        )
    )
    steps.append(
        run_cmd(
            "dag_stage_aggregate_standalone",
            [
                sys.executable,
                "modes/aggregate/consensus.py",
                "--bundle-file",
                str(dag_stage_runtime / "reactions" / "20260625-dag-stage-demo.filled.json"),
                "--output",
                str(dag_stage_runtime / "consensus" / "standalone-consensus.json"),
                "--pretty",
            ],
            runtime_root=runtime_root,
            check_stdout_contains=["consensus pack"],
        )
    )

    design_runtime = runtime_root / "design"
    steps.append(
        run_cmd(
            "design_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/design_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/design_demo/design.md",
                "--personas",
                "ux-designer-senior,product-expert",
                "--execute",
                "--runtime-dir",
                str(design_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                "design_observation",
                  '"complaints"',
                  '"consensus"',
                "report_md",
                "report_html",
            ],
        )
    )

    screen_runtime = runtime_root / "screen"
    steps.append(
        run_cmd(
            "screen_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/screen_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/screen_demo/screen.md",
                "--personas",
                "local-business-expert,ad-buyer",
                "--execute",
                "--runtime-dir",
                str(screen_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                "screen_observation",
                  '"complaints"',
                  '"consensus"',
                "report_md",
                "report_html",
            ],
        )
    )

    detail_runtime = runtime_root / "detail_page"
    steps.append(
        run_cmd(
            "detail_page_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/detail_page_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/detail_page_demo/detail.md",
                "--personas",
                "consumer-bao-mom-tier2,local-business-expert",
                "--execute",
                "--runtime-dir",
                str(detail_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                "detail_page_observation",
                  '"complaints"',
                  '"consensus"',
                "report_md",
                "report_html",
            ],
        )
    )

    card_runtime = runtime_root / "product_card"
    steps.append(
        run_cmd(
            "product_card_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/product_card_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/product_card_demo/card.md",
                "--personas",
                "consumer-bao-mom-tier2,ad-buyer",
                "--execute",
                "--runtime-dir",
                str(card_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                "product_card_observation",
                  '"complaints"',
                  '"consensus"',
                "report_md",
                "report_html",
            ],
        )
    )

    marketing_runtime = runtime_root / "marketing_copy"
    steps.append(
        run_cmd(
            "marketing_copy_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/marketing_copy_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/marketing_copy_demo/copy.md",
                "--personas",
                "consumer-bao-mom-tier2,ad-buyer",
                "--execute",
                "--runtime-dir",
                str(marketing_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                "copy_observation",
                  '"complaints"',
                  '"consensus"',
                "report_md",
                "report_html",
            ],
        )
    )

    hci_runtime = runtime_root / "hci"
    steps.append(
        run_cmd(
            "hci_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/hci_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/hci_demo/artifact.json",
                "--personas",
                "ux-designer-senior,ad-buyer",
                "--execute",
                "--include",
                "mode/annotate-issues",
                "--runtime-dir",
                str(hci_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                "heatmap_metrics",
                "annotated_image",
                "report_html",
                "report_docx_xml",
            ],
        )
    )

    fit_runtime = runtime_root / "persona_fit"
    steps.append(
        run_cmd(
            "persona_fit_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/short_video_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/short_video_demo/artifact.json",
                "--personas",
                "consumer-bao-mom-tier2",
                "--execute",
                "--include",
                "mode/persona-fit",
                "--fit-spec-file",
                "tests/fixtures/fit_demo.json",
                "--runtime-dir",
                str(fit_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                "persona_fit",
                "report_html",
            ],
        )
    )

    sample_runtime = runtime_root / "persona_sample_gap"
    steps.append(
        run_cmd(
            "persona_sample_distribution_gap_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/short_video_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/short_video_demo/artifact.json",
                "--personas",
                "consumer-bao-mom-tier2,consumer-silver-male",
                "--execute",
                "--include",
                "mode/persona-sample",
                "--include",
                "mode/aggregate-distribution-gap",
                "--current-dist",
                "tests/fixtures/distributions/merchant_current.json",
                "--target-dist",
                "tests/fixtures/distributions/category_target.json",
                "--runtime-dir",
                str(sample_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                "persona_sample",
                "distribution_gap",
                "report_html",
            ],
        )
    )

    handoff_runtime = runtime_root / "handoff_seed"
    steps.append(
        run_cmd(
            "handoff_seed_waiting",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/prd_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/prd_demo/prd.md",
                "--personas",
                "product-expert,ad-buyer",
                "--execute",
                "--no-mock-llm",
                "--runtime-dir",
                str(handoff_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "WAITING_FOR_REACTIONS"',
                "prd_observation",
                "persona_pick",
                "bundle",
            ],
        )
    )

    bundle_path = handoff_runtime / "reactions" / "20260624-v04-prd-demo.bundle.json"
    prompts_dir = runtime_root / "handoff_prompts"
    steps.append(
        run_cmd(
            "handoff_export_prompts",
            [
                sys.executable,
                "tools/reaction_handoff.py",
                "--bundle-file",
                str(bundle_path),
                "--export-prompts",
                str(prompts_dir),
                "--pretty",
            ],
            runtime_root=runtime_root,
            check_stdout_contains=["ready_for_host_agent", "prompt_files"],
        )
    )

    steps.append(
        run_cmd(
            "handoff_incomplete_check",
            [
                sys.executable,
                "tools/reaction_handoff.py",
                "--bundle-file",
                str(bundle_path),
                "--check-filled",
            ],
            runtime_root=runtime_root,
            expect_code=1,
            check_stdout_contains=[
                "REACTIONS_INCOMPLETE",
                "product-expert",
                "ad-buyer",
            ],
        )
    )

    filled_path = handoff_runtime / "reactions" / "20260624-v04-prd-demo.filled.json"
    steps.append(
        run_cmd(
            "handoff_mock_fill",
            [
                sys.executable,
                "tools/mock_llm_responder.py",
                "--bundle-file",
                str(bundle_path),
                "--output",
                str(filled_path),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=["mock reactions 回填"],
        )
    )

    steps.append(
        run_cmd(
            "handoff_filled_check",
            [
                sys.executable,
                "tools/reaction_handoff.py",
                "--bundle-file",
                str(filled_path),
                "--check-filled",
                "--pretty",
            ],
            runtime_root=runtime_root,
            check_stdout_contains=['"status": "OK"', '"ready_for_resume": true'],
        )
    )

    resume_runtime = runtime_root / "handoff_resume"
    steps.append(
        run_cmd(
            "handoff_resume_e2e",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/prd_demo/brief.json",
                "--execute",
                "--filled-bundle-file",
                str(filled_path),
                "--runtime-dir",
                str(resume_runtime),
            ],
            runtime_root=runtime_root,
            check_stdout_contains=[
                '"status": "OK"',
                  '"complaints"',
                  '"consensus"',
                "report_md",
            ],
        )
    )

    steps.append(
        run_cmd(
            "pipeline_incomplete_resume",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/prd_demo/brief.json",
                "--execute",
                "--filled-bundle-file",
                str(bundle_path),
                "--runtime-dir",
                str(runtime_root / "incomplete_resume"),
            ],
            runtime_root=runtime_root,
            expect_code=1,
            check_stdout_contains=[
                "REACTIONS_INCOMPLETE",
                "product-expert",
                "ad-buyer",
            ],
        )
    )

    steps.append(
        run_cmd(
            "negative_missing_artifact",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/prd_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/prd_demo/not-exists.md",
                "--personas",
                "product-expert,ad-buyer",
                "--execute",
                "--runtime-dir",
                str(runtime_root / "negative_missing_artifact"),
            ],
            runtime_root=runtime_root,
            expect_code=2,
            check_stdout_contains=["artifact 不存在"],
        )
    )

    steps.append(
        run_cmd(
            "negative_missing_persona",
            [
                sys.executable,
                "orchestrator/pipeline.py",
                "--brief-file",
                "tests/fixtures/prd_demo/brief.json",
                "--artifact-file",
                "tests/fixtures/prd_demo/prd.md",
                "--personas",
                "persona-not-exists",
                "--execute",
                "--runtime-dir",
                str(runtime_root / "negative_missing_persona"),
            ],
            runtime_root=runtime_root,
            expect_code=1,
            check_stdout_contains=["角色不存在"],
        )
    )

    cache_matches = check_no_python_cache()
    if cache_matches:
        raise StepFailed(f"unexpected generated cache files: {cache_matches}")

    return {
        "status": "OK",
        "runtime_root": str(runtime_root),
        "steps": steps,
        "summary": {
            "steps": len(steps),
              "short_video": "structural e2e passed",
              "prd": "scenario-aware score/position e2e passed",
            "visual_artifacts": "design/screen/detail_page/product_card e2e passed",
            "hci": "heatmap A + annotate issues e2e passed",
            "marketing_copy": "copy_extract + 6 complaints / 3 consensus",
              "dag_stage": "observe handoff / full e2e / standalone aggregate passed",
            "persona_fit_sample": "fit/sample execute wiring passed",
            "evaluation": "2 seed cases / avg_gold_coverage=1.0",
            "persona_dedupe": "ad_buyer overlap resolved by ad-buyer unified persona",
            "distribution_gap": "12 deterministic current-vs-target gap rows",
              "handoff": "export/check/resume/incomplete all passed",
              "negative_paths": "bad evidence / missing artifact / missing persona fail fast",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run JuryPersonas local regression checks")
    parser.add_argument(
        "--runtime-root",
        default=str(DEFAULT_RUNTIME_ROOT),
        help="Where runtime artifacts and command logs are written",
    )
    parser.add_argument(
        "--keep-runtime",
        action="store_true",
        help="Do not remove an existing runtime root before running",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run_regression(Path(args.runtime_root), keep_runtime=args.keep_runtime)
    except StepFailed as exc:
        result = {"status": "FAILED", "error": str(exc), "runtime_root": args.runtime_root}
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
