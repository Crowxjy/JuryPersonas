#!/usr/bin/env python3
"""
brief_validator.py — Agent 输出的 Brief JSON 五重校验器

设计目标:
1. orchestrator 拿到 Agent 吐的 brief JSON 后,跑本脚本做五重校验
2. 校验失败时返回非 0 退出码 + stderr 错误清单,orchestrator 把控制权交还 Agent 重出 JSON
3. stdlib 自足,无外部依赖(jsonschema 软依赖,装了就跑结构校验,没装跳过)

五重校验(对齐 brief_harness.md §四 + architecture-v0.2.md §9.1):

  1) JSON 结构合法 + 顶层必填字段齐全
  2) verdict ∈ {SUFFICIENT, INSUFFICIENT}
  3) verdict=SUFFICIENT 时,所有 fields[*].sufficient=true
  4) verdict=SUFFICIENT 时,consistency_check.passed=true
  5) verdict=SUFFICIENT 时,boundary_ack 全 true(首次会话)
  6) [可选] evidence 回溯:fields[*].evidence 必须能在用户上下文中匹配
     仅当 --context-file 提供时执行;否则跳过(由 orchestrator 决定何时执行)

使用模式:

    # 基础校验(不查 evidence)
    python3 brief_validator.py --brief-file .runtime/briefs/<sid>.json

    # 完整校验(含 evidence 回溯)
    python3 brief_validator.py \\
        --brief-file .runtime/briefs/<sid>.json \\
        --context-file .runtime/contexts/<sid>.txt \\
        --first-round            # 首次会话,boundary_ack 强制全 true

    # 指定 schema 文件(默认走 ../core/contracts/brief.schema.json)
    python3 brief_validator.py --brief-file <path> --schema-file <path>

退出码:
  0 = 全部通过
  1 = 一项及以上失败
  2 = 参数错或文件不存在
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_SCHEMA = SKILL_ROOT / "core" / "contracts" / "brief.schema.json"

REQUIRED_TOP_FIELDS = [
    "session_id",
    "round",
    "fields",
    "consistency_check",
    "boundary_ack",
    "verdict",
    "next_action",
]

REQUIRED_FIELD_KEYS = [
    "artifact_type",
    "artifact_locator",
    "target_audience",
    "key_concern",
    "distribution_intent",
]

REQUIRED_BOUNDARY_KEYS = [
    "no_absolute_metrics_predicted",
    "no_go_no_go_decision",
    "fit_fidelity_disclaimer",
    "ask_dont_hallucinate",
]

ALLOWED_VERDICTS = {"SUFFICIENT", "INSUFFICIENT"}
ALLOWED_NEXT_ACTION_KINDS = {"ASK_USER", "PROCEED_TO_DAG"}
EVIDENCE_PREFIXES = ("用户原话:", "用户原话：", "用户说:", "用户说：", "原话:", "原话：")
STRUCTURED_REPLY_RE = re.compile(r"(用户回复|用户选了|用户选择|编号\s*\d|[①②③④⑤⑥])")
URL_OR_PATH_RE = re.compile(r"(https?://[^\s，。；;\"'）)]+|/[^\s，。；;\"'）)]+)")


class ValidationError(Exception):
    pass


def load_json(path: Path, label: str) -> Any:
    if not path.exists():
        raise ValidationError(f"[{label}] 文件不存在: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValidationError(f"[{label}] JSON 解析失败: {e}")


def check_structure(brief: dict, errors: list) -> None:
    """① 顶层必填字段齐全 + 子字段结构。"""
    for key in REQUIRED_TOP_FIELDS:
        if key not in brief:
            errors.append(f"① 顶层必填字段缺失: {key}")

    fields = brief.get("fields", {})
    if not isinstance(fields, dict):
        errors.append("① fields 必须是 object")
    else:
        for key in REQUIRED_FIELD_KEYS:
            if key not in fields:
                errors.append(f"① fields 缺失字段: {key}")
                continue
            field = fields[key]
            if not isinstance(field, dict):
                errors.append(f"① fields.{key} 必须是 object")
                continue
            for fk in ("value", "evidence", "sufficient"):
                if fk not in field:
                    errors.append(f"① fields.{key} 缺子字段: {fk}")
            if "sufficient" in field and not isinstance(field["sufficient"], bool):
                errors.append(f"① fields.{key}.sufficient 必须是 bool")

    boundary = brief.get("boundary_ack", {})
    if not isinstance(boundary, dict):
        errors.append("① boundary_ack 必须是 object")
    else:
        for key in REQUIRED_BOUNDARY_KEYS:
            if key not in boundary:
                errors.append(f"① boundary_ack 缺字段: {key}")
            elif not isinstance(boundary[key], bool):
                errors.append(f"① boundary_ack.{key} 必须是 bool")

    consistency = brief.get("consistency_check", {})
    if not isinstance(consistency, dict):
        errors.append("① consistency_check 必须是 object")
    else:
        if "passed" not in consistency:
            errors.append("① consistency_check.passed 缺失")
        elif not isinstance(consistency["passed"], bool):
            errors.append("① consistency_check.passed 必须是 bool")
        if "conflicts" not in consistency:
            errors.append("① consistency_check.conflicts 缺失")
        elif not isinstance(consistency["conflicts"], list):
            errors.append("① consistency_check.conflicts 必须是 array")


def check_verdict_value(brief: dict, errors: list) -> None:
    """② verdict 取值合法。"""
    verdict = brief.get("verdict")
    if verdict not in ALLOWED_VERDICTS:
        errors.append(
            f"② verdict 取值非法: {verdict!r}, 必须是 {sorted(ALLOWED_VERDICTS)}"
        )


def check_sufficient_consistency(brief: dict, errors: list) -> None:
    """③④ verdict=SUFFICIENT 时,所有 fields[*].sufficient + consistency_check.passed 必须 true。"""
    if brief.get("verdict") != "SUFFICIENT":
        return

    fields = brief.get("fields", {})
    for key in REQUIRED_FIELD_KEYS:
        field = fields.get(key, {})
        if not field.get("sufficient", False):
            errors.append(
                f"③ verdict=SUFFICIENT 但 fields.{key}.sufficient=false,逻辑矛盾"
            )

    consistency = brief.get("consistency_check", {})
    if not consistency.get("passed", False):
        errors.append("④ verdict=SUFFICIENT 但 consistency_check.passed=false,逻辑矛盾")


def check_boundary_ack(brief: dict, errors: list, first_round: bool) -> None:
    """⑤ 首次会话时,verdict=SUFFICIENT 必须 boundary_ack 全 true。"""
    if not first_round:
        return
    if brief.get("verdict") != "SUFFICIENT":
        return
    boundary = brief.get("boundary_ack", {})
    not_acked = [k for k in REQUIRED_BOUNDARY_KEYS if not boundary.get(k, False)]
    if not_acked:
        errors.append(
            f"⑤ 首次会话 verdict=SUFFICIENT 但 boundary_ack 未全 ack: {not_acked}"
        )


def check_next_action(brief: dict, errors: list) -> None:
    """next_action 与 verdict 联动校验。"""
    next_action = brief.get("next_action", {})
    if not isinstance(next_action, dict):
        errors.append("next_action 必须是 object")
        return
    kind = next_action.get("kind")
    if kind not in ALLOWED_NEXT_ACTION_KINDS:
        errors.append(
            f"next_action.kind 非法: {kind!r},必须是 {sorted(ALLOWED_NEXT_ACTION_KINDS)}"
        )
        return

    verdict = brief.get("verdict")
    if verdict == "SUFFICIENT" and kind != "PROCEED_TO_DAG":
        errors.append("verdict=SUFFICIENT 但 next_action.kind != PROCEED_TO_DAG")
    if verdict == "INSUFFICIENT" and kind != "ASK_USER":
        errors.append("verdict=INSUFFICIENT 但 next_action.kind != ASK_USER")

    if kind == "ASK_USER":
        questions = next_action.get("questions")
        if not isinstance(questions, list) or not questions:
            errors.append("next_action.kind=ASK_USER 但 questions 为空")
        elif len(questions) > 4:
            errors.append(f"next_action.questions 超过 4 条({len(questions)} 条)")
    elif kind == "PROCEED_TO_DAG":
        summary = next_action.get("summary_for_user")
        if not summary or not isinstance(summary, str):
            errors.append("next_action.kind=PROCEED_TO_DAG 但 summary_for_user 缺失")


def normalize_trace_text(text: str) -> str:
    """Normalize user text for evidence traceback.

    This intentionally keeps only letters, digits, CJK characters and path-ish
    separators. It allows Chinese/English punctuation and whitespace variance
    without turning a tiny generic word into valid evidence.
    """
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff/_\-.]+", "", text.casefold())


def strip_wrapping_quotes(text: str) -> str:
    return text.strip().strip(" \t\r\n\"'`“”‘’「」『』《》")


def extract_evidence_snippets(evidence: str) -> list[str]:
    """Extract concrete source snippets from an evidence string.

    Supported forms:
    - /path/to/file or http(s)://...
    - 用户原话: <snippet>
    - quoted snippets such as "..." or 「...」
    - otherwise the whole evidence string as a last resort
    """
    snippets: list[str] = []

    for match in URL_OR_PATH_RE.finditer(evidence):
        snippets.append(match.group(1))

    for prefix in EVIDENCE_PREFIXES:
        if prefix in evidence:
            snippets.append(strip_wrapping_quotes(evidence.split(prefix, 1)[1]))
            break

    for quoted in re.findall(r"[\"“「『](.+?)[\"”」』]", evidence):
        snippets.append(strip_wrapping_quotes(quoted))

    snippets.append(strip_wrapping_quotes(evidence))

    deduped: list[str] = []
    seen: set[str] = set()
    for snippet in snippets:
        snippet = strip_wrapping_quotes(snippet)
        if not snippet:
            continue
        key = normalize_trace_text(snippet)
        if key and key not in seen:
            seen.add(key)
            deduped.append(snippet)
    return deduped


def evidence_matches_context(evidence: str, context: str) -> tuple[bool, str]:
    """Return whether evidence can be traced back to user context.

    The old validator used a whitespace-free substring match against the whole
    evidence string. That caused both false positives (very short/generic
    fragments) and false negatives (quote/path wrappers). This version first
    extracts concrete snippets, then requires exact path/URL matches or a
    sufficiently specific normalized natural-language match.
    """
    if STRUCTURED_REPLY_RE.search(evidence):
        return True, "structured reply marker"

    context_norm = normalize_trace_text(context)
    candidates = extract_evidence_snippets(evidence)
    checked: list[str] = []

    for snippet in candidates:
        if URL_OR_PATH_RE.fullmatch(snippet):
            if snippet in context:
                return True, f"path/url matched: {snippet[:60]}"
            checked.append(snippet)
            continue

        if snippet in context:
            return True, f"exact matched: {snippet[:60]}"

        snippet_norm = normalize_trace_text(snippet)
        checked.append(snippet)
        if len(snippet_norm) < 6:
            continue
        if snippet_norm in context_norm:
            return True, f"normalized matched: {snippet[:60]}"

    checked_preview = " | ".join(item[:40] for item in checked[:3])
    return False, checked_preview or "<empty>"


def check_evidence_traceback(brief: dict, errors: list, context: str) -> None:
    """⑥ evidence 回溯:fields[*].evidence 必须能在用户上下文中匹配。

    匹配规则:
      - 路径/URL 必须原样在 context 中出现
      - "用户原话: <X>" / 引号内片段必须能回溯到 context
      - 中文/英文标点和空白差异可容错,但过短泛化片段不算证据
      - 明确的结构化选项回复(如"用户回复 ①")允许跳过全文匹配
    """
    fields = brief.get("fields", {})

    for key in REQUIRED_FIELD_KEYS:
        field = fields.get(key, {})
        if not field.get("sufficient", False):
            continue  # 不充分时不校验 evidence
        evidence = field.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"⑥ fields.{key}.sufficient=true 但 evidence 为空")
            continue
        matched, reason = evidence_matches_context(evidence.strip(), context)
        if not matched:
            errors.append(
                f"⑥ fields.{key}.evidence 在用户上下文中无法回溯: '{evidence[:60]}' "
                f"(checked: {reason})"
            )


def maybe_jsonschema_validate(brief: dict, schema_path: Path, errors: list) -> None:
    """软依赖:如果 jsonschema 已装,跑一次 schema 校验。"""
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return  # 软跳过
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"⓪ schema 文件不存在: {schema_path}")
        return
    try:
        jsonschema.validate(brief, schema)  # type: ignore
    except jsonschema.ValidationError as e:  # type: ignore
        errors.append(f"⓪ jsonschema 校验失败: {e.message} (path: {list(e.absolute_path)})")


def validate(
    brief: dict,
    *,
    first_round: bool,
    context: str | None,
    schema_path: Path,
) -> list[str]:
    errors: list[str] = []
    maybe_jsonschema_validate(brief, schema_path, errors)
    check_structure(brief, errors)
    check_verdict_value(brief, errors)
    check_sufficient_consistency(brief, errors)
    check_boundary_ack(brief, errors, first_round)
    check_next_action(brief, errors)
    if context is not None:
        check_evidence_traceback(brief, errors, context)
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Brief JSON 五重校验器")
    parser.add_argument("--brief-file", required=True, help="Agent 吐出的 brief JSON 路径")
    parser.add_argument("--context-file", help="用户原始上下文文件,提供则触发 evidence 回溯校验")
    parser.add_argument(
        "--first-round",
        action="store_true",
        help="标记为首次会话,boundary_ack 强制全 true 才允许 SUFFICIENT",
    )
    parser.add_argument(
        "--schema-file",
        default=str(DEFAULT_SCHEMA),
        help=f"schema 路径(默认: {DEFAULT_SCHEMA})",
    )
    parser.add_argument("--quiet", action="store_true", help="只输出错误,不输出 OK 信息")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    brief_path = Path(args.brief_file)
    schema_path = Path(args.schema_file)

    try:
        brief = load_json(brief_path, "brief")
    except ValidationError as e:
        sys.stderr.write(f"{e}\n")
        return 2

    context: str | None = None
    if args.context_file:
        ctx_path = Path(args.context_file)
        if not ctx_path.exists():
            sys.stderr.write(f"[error] context 文件不存在: {ctx_path}\n")
            return 2
        context = ctx_path.read_text(encoding="utf-8")

    errors = validate(
        brief,
        first_round=args.first_round,
        context=context,
        schema_path=schema_path,
    )
    if errors:
        sys.stderr.write(f"[FAIL] brief {brief_path} 校验未通过,共 {len(errors)} 项:\n")
        for i, err in enumerate(errors, 1):
            sys.stderr.write(f"  {i}. {err}\n")
        return 1

    if not args.quiet:
        sys.stdout.write(f"[OK] brief {brief_path} 全部 {6 if context else 5} 重校验通过\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
