#!/usr/bin/env python3
"""
evaluation_runner.py - run JuryPersonas evaluation cases.

The runner reads JSONL cases, runs the local pipeline for each case, and compares
aggregated complaints/consensus against gold feedback labels. It writes only
runtime artifacts under the requested runtime root.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TOOLS_DIR.parent
DEFAULT_CASES = SKILL_ROOT / "evals" / "cases" / "seed_cases.jsonl"
DEFAULT_RUNTIME_ROOT = Path("/tmp") / f"jp_eval_{int(time.time())}"


class EvaluationError(RuntimeError):
    pass


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvaluationError(f"{path}:{line_no} JSON 解析失败: {exc}") from exc
        validate_case(case, path, line_no)
        cases.append(case)
    if not cases:
        raise EvaluationError(f"评测集为空: {path}")
    return cases


def validate_case(case: dict[str, Any], path: Path, line_no: int) -> None:
    required = ["case_id", "scenario", "brief_file", "artifact_file", "personas", "gold_feedback", "expected"]
    missing = [field for field in required if field not in case]
    if missing:
        raise EvaluationError(f"{path}:{line_no} 缺字段: {missing}")
    if not isinstance(case["personas"], list) or not case["personas"]:
        raise EvaluationError(f"{path}:{line_no} personas 必须是非空数组")
    if not isinstance(case["gold_feedback"], list) or not case["gold_feedback"]:
        raise EvaluationError(f"{path}:{line_no} gold_feedback 必须是非空数组")


def run_pipeline(case: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    case_runtime = runtime_root / case["case_id"]
    case_runtime.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "orchestrator/pipeline.py",
        "--brief-file",
        case["brief_file"],
        "--artifact-file",
        case["artifact_file"],
        "--personas",
        ",".join(case["personas"]),
        "--execute",
        "--runtime-dir",
        str(case_runtime),
    ]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        cmd,
        cwd=SKILL_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    logs_dir = runtime_root / "_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = logs_dir / f"{case['case_id']}.stdout.log"
    stderr_path = logs_dir / f"{case['case_id']}.stderr.log"
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise EvaluationError(
            f"{case['case_id']} pipeline exit={proc.returncode}, stdout={stdout_path}, stderr={stderr_path}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise EvaluationError(f"{case['case_id']} pipeline stdout 非 JSON: {stdout_path}") from exc


def load_consensus(execution: dict[str, Any]) -> dict[str, Any]:
    consensus_path = execution.get("artifacts", {}).get("consensus")
    if not consensus_path:
        raise EvaluationError("execution.artifacts.consensus 缺失")
    return json.loads(Path(consensus_path).read_text(encoding="utf-8"))


def normalize_tokens(text: str) -> list[str]:
    text = str(text or "").lower()
    chunks = re.split(r"[\s,，。；;:/|()（）【】\[\]\"'“”]+", text)
    return [chunk for chunk in chunks if len(chunk) >= 2]


def row_text(row: dict[str, Any]) -> str:
    return " ".join(str(value) for value in row.values() if value is not None)


def gold_matches_row(gold: dict[str, Any], row: dict[str, Any]) -> bool:
    haystack = row_text(row)
    position = str(gold.get("position") or "")
    concern = str(gold.get("concern") or "")
    if position and position in haystack:
        return True
    if concern and concern in haystack:
        return True
    evidence_tokens = normalize_tokens(str(gold.get("evidence") or ""))
    if evidence_tokens:
        hits = sum(1 for token in evidence_tokens if token in haystack)
        return hits >= min(2, len(evidence_tokens))
    return False


def score_case(case: dict[str, Any], consensus: dict[str, Any], pipeline_result: dict[str, Any]) -> dict[str, Any]:
    rows = list(consensus.get("complaints", [])) + list(consensus.get("consensus", []))
    matched = []
    missing = []
    for gold in case["gold_feedback"]:
        if any(gold_matches_row(gold, row) for row in rows):
            matched.append(gold)
        else:
            missing.append(gold)

    gold_coverage = len(matched) / len(case["gold_feedback"]) if case["gold_feedback"] else 0.0
    complaints = len(consensus.get("complaints", []))
    consensus_count = len(consensus.get("consensus", []))
    expected = case.get("expected", {})
    failures = []
    if complaints < int(expected.get("min_complaints", 0)):
        failures.append(f"complaints {complaints} < {expected.get('min_complaints')}")
    if consensus_count < int(expected.get("min_consensus", 0)):
        failures.append(f"consensus {consensus_count} < {expected.get('min_consensus')}")
    if gold_coverage < float(expected.get("min_gold_coverage", 0)):
        failures.append(f"gold_coverage {gold_coverage:.2f} < {expected.get('min_gold_coverage')}")

    return {
        "case_id": case["case_id"],
        "scenario": case["scenario"],
        "status": "OK" if not failures else "FAILED",
        "gold_coverage": round(gold_coverage, 4),
        "matched_gold": matched,
        "missing_gold": missing,
        "complaints": complaints,
        "consensus": consensus_count,
        "artifacts": pipeline_result.get("execution", {}).get("artifacts", {}),
        "failures": failures,
    }


def run_evaluation(cases_path: Path, runtime_root: Path) -> dict[str, Any]:
    runtime_root.mkdir(parents=True, exist_ok=True)
    cases = load_cases(cases_path)
    results = []
    for case in cases:
        pipeline_result = run_pipeline(case, runtime_root)
        consensus = load_consensus(pipeline_result["execution"])
        results.append(score_case(case, consensus, pipeline_result))

    failed = [result for result in results if result["status"] != "OK"]
    avg_coverage = sum(result["gold_coverage"] for result in results) / len(results)
    return {
        "status": "OK" if not failed else "FAILED",
        "cases_path": str(cases_path),
        "runtime_root": str(runtime_root),
        "summary": {
            "cases": len(results),
            "failed": len(failed),
            "avg_gold_coverage": round(avg_coverage, 4),
        },
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run JuryPersonas evaluation cases")
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Evaluation JSONL path")
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT), help="Runtime output dir")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run_evaluation(Path(args.cases), Path(args.runtime_root))
    except EvaluationError as exc:
        result = {"status": "FAILED", "error": str(exc), "runtime_root": args.runtime_root}
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
