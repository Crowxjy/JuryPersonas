#!/usr/bin/env python3
"""
reporting/lark_renderer.py — 把 DocxXML/Markdown 报告发布到飞书文档

设计原则:
- 真发布走 lark-cli docs +create --api-version v2;本脚本不持飞书 token
- 默认 --dry-run:打印 lark-cli 命令,不真执行
- 显式 --local 时降级到本地保存;--execute 真发布时不做伪 URL 降级,失败即返回 ERROR

使用模式:

    # 默认 dry-run:打印命令但不发
    python3 reporting/lark_renderer.py --report /tmp/jp_m3/reports/m3-demo.md --title "短视频评审报告"

    # 显式本地落盘(降级)
    python3 reporting/lark_renderer.py --report <md> --local --output-dir .runtime/reports

    # 真发布(需要 lark-cli + lark-doc v2 权限):
    python3 reporting/lark_renderer.py --report <docx.xml> --format xml --execute
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_LOCAL_DIR = SKILL_ROOT / ".runtime" / "reports"


def find_lark_cli() -> str | None:
    return shutil.which("lark-cli") or shutil.which("lark")


def infer_doc_format(report_path: Path) -> str:
    """Infer the lark-doc content format from the report filename."""
    if report_path.name.endswith(".docx.xml") or report_path.suffix == ".xml":
        return "xml"
    return "markdown"


def build_lark_command(report_path: Path, title: str, doc_format: str, cli_bin: str = "lark-cli") -> list[str]:
    """组装 lark-cli docs +create 命令(对齐 lark-doc v2 协议)。"""
    content = report_path.read_text(encoding="utf-8")
    if doc_format == "markdown" and not content.lstrip().startswith("#"):
        content = f"# {title}\n\n{content}"
    return [
        cli_bin,
        "docs",
        "+create",
        "--api-version", "v2",
        "--doc-format", doc_format,
        "--content", content,
    ]


def publish_local(report_path: Path, output_dir: Path, session_id: str) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".lark.docx.xml" if infer_doc_format(report_path) == "xml" else ".lark.md"
    target = output_dir / f"{session_id}{suffix}"
    target.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
    return {
        "status": "LOCAL_FALLBACK",
        "mode": "local",
        "saved_to": str(target),
        "note": "显式选择 local;报告已落盘,可手工上传飞书。",
    }


def extract_document_url(stdout: str) -> str | None:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    document = payload.get("data", {}).get("document", {})
    return document.get("url")


def public_command_preview(cmd: list[str]) -> list[str]:
    if "--content" not in cmd:
        return cmd
    idx = cmd.index("--content") + 1
    preview = list(cmd)
    preview[idx] = f"<content chars={len(cmd[idx])}>"
    return preview


def publish_via_lark(
    report_path: Path,
    title: str,
    dry_run: bool,
    doc_format: str,
    cli_bin: str = "lark-cli",
) -> dict:
    cmd = build_lark_command(report_path, title, doc_format, cli_bin=cli_bin)
    if dry_run:
        return {
            "status": "DRY_RUN",
            "mode": "lark",
            "doc_format": doc_format,
            "source": str(report_path),
            "command": public_command_preview(cmd),
            "note": "dry-run 打印 lark-doc v2 创建命令,未真发布。传 --execute 才会执行。",
        }
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return {"status": "ERROR", "mode": "lark", "error": "lark-cli 未安装"}
    except subprocess.TimeoutExpired:
        return {"status": "ERROR", "mode": "lark", "error": "lark-cli 60 秒超时"}

    if result.returncode != 0:
        return {
            "status": "ERROR",
            "mode": "lark",
            "doc_format": doc_format,
            "source": str(report_path),
            "command": public_command_preview(cmd),
            "returncode": result.returncode,
            "stderr": result.stderr.strip(),
        }
    return {
        "status": "OK",
        "mode": "lark",
        "doc_format": doc_format,
        "source": str(report_path),
        "command": public_command_preview(cmd),
        "url": extract_document_url(result.stdout.strip()),
        "stdout": result.stdout.strip(),
    }


def publish(
    report_path: Path,
    title: str,
    session_id: str,
    *,
    local_only: bool,
    dry_run: bool,
    output_dir: Path,
    execute: bool,
    doc_format: str | None = None,
) -> dict:
    resolved_format = doc_format or infer_doc_format(report_path)
    if local_only:
        return publish_local(report_path, output_dir, session_id)
    cli_bin = find_lark_cli()
    if cli_bin is None:
        if execute:
            return {
                "status": "ERROR",
                "mode": "lark",
                "doc_format": resolved_format,
                "source": str(report_path),
                "error": "lark-cli 未安装,无法执行真实飞书发布。",
            }
        return publish_via_lark(report_path, title, dry_run=True, doc_format=resolved_format)
    # 找到 lark-cli:默认 dry-run,只有 --execute 才真跑
    return publish_via_lark(
        report_path,
        title,
        dry_run=not execute or dry_run,
        doc_format=resolved_format,
        cli_bin=cli_bin,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把 DocxXML/Markdown 报告发布到飞书")
    parser.add_argument("--report", required=True, help="报告路径(.docx.xml 或 .md)")
    parser.add_argument("--title", default="陪审团评审报告", help="飞书文档标题")
    parser.add_argument("--session-id", default="unknown", help="会话 ID(用作本地降级文件名)")
    parser.add_argument(
        "--local",
        action="store_true",
        help="强制走本地降级,不调 lark-cli",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="启用真发布(去掉 dry-run)。需要 lark-cli 与飞书文档权限。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="dry-run 打印 lark-doc v2 命令,不真发(默认行为,显式开关用于自文档)",
    )
    parser.add_argument(
        "--format",
        choices=["xml", "markdown"],
        help="报告格式;默认按文件名推断(.docx.xml/.xml 为 xml,其余为 markdown)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_LOCAL_DIR),
        help=f"本地降级目录(默认 {DEFAULT_LOCAL_DIR})",
    )
    parser.add_argument("--pretty", action="store_true", help="美化 JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report_path = Path(args.report)
    if not report_path.exists():
        sys.stderr.write(f"[error] 报告不存在: {report_path}\n")
        return 2

    result = publish(
        report_path,
        args.title,
        args.session_id,
        local_only=args.local,
        dry_run=args.dry_run,
        output_dir=Path(args.output_dir),
        execute=args.execute,
        doc_format=args.format,
    )
    out = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    print(out)
    return 0 if result["status"] in {"OK", "DRY_RUN", "LOCAL_FALLBACK"} else 1


if __name__ == "__main__":
    sys.exit(main())
