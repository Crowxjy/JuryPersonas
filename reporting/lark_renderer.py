#!/usr/bin/env python3
"""
reporting/lark_renderer.py — 把 Markdown 报告发布到飞书 wiki

设计原则:
- 真发布走 lark-cli docs +create(wiki 渲染);本脚本不持飞书 token,只组装命令
- 默认 --dry-run:打印 lark-cli 命令,不真执行,**MVP 阶段必须保留这一项保护**
- lark-cli 不可用或显式 --local 时,**降级到本地保存**,把 Markdown 拷贝到 .runtime/reports/<session>.lark.md 并返回伪 URL,流水线不被打断
- 未来加 token / 真发布时,只改 publish_via_lark 一处即可

使用模式:

    # 默认 dry-run(MVP 必须):打印命令但不发
    python3 reporting/lark_renderer.py --report /tmp/jp_m3/reports/m3-demo.md --title "短视频评审报告"

    # 显式本地落盘(降级)
    python3 reporting/lark_renderer.py --report <md> --local --output-dir .runtime/reports

    # 真发布(需要 lark-cli + token,MVP 不会走到):
    python3 reporting/lark_renderer.py --report <md> --execute
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


def build_lark_command(report_path: Path, title: str) -> list[str]:
    """组装 lark-cli docs +create 命令(对齐 lark-doc skill 默认协议)。"""
    return [
        "lark-cli",
        "docs",
        "+create",
        "--api-version", "v2",
        "--title", title,
        "--from-markdown",
        str(report_path),
    ]


def publish_local(report_path: Path, output_dir: Path, session_id: str) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{session_id}.lark.md"
    target.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
    return {
        "status": "LOCAL_FALLBACK",
        "mode": "local",
        "saved_to": str(target),
        "fake_url": f"file://{target}",
        "note": "lark-cli 不可用或显式选 local;报告已落盘,可手工上传飞书。",
    }


def publish_via_lark(report_path: Path, title: str, dry_run: bool) -> dict:
    cmd = build_lark_command(report_path, title)
    if dry_run:
        return {
            "status": "DRY_RUN",
            "mode": "lark",
            "command": cmd,
            "note": "dry-run 打印命令,未真发布。去掉 --dry-run 才会执行。",
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
            "command": cmd,
            "returncode": result.returncode,
            "stderr": result.stderr.strip(),
        }
    return {
        "status": "OK",
        "mode": "lark",
        "command": cmd,
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
) -> dict:
    if local_only or find_lark_cli() is None:
        return publish_local(report_path, output_dir, session_id)
    # 找到 lark-cli:默认 dry-run,只有 --execute 才真跑
    return publish_via_lark(report_path, title, dry_run=not execute or dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把 Markdown 报告发布到飞书(MVP)")
    parser.add_argument("--report", required=True, help="Markdown 报告路径")
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
        help="启用真发布(去掉 dry-run)。MVP 默认禁用。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="dry-run 打印 lark-cli 命令,不真发(默认行为,显式开关用于自文档)",
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
    )
    out = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    print(out)
    return 0 if result["status"] in {"OK", "DRY_RUN", "LOCAL_FALLBACK"} else 1


if __name__ == "__main__":
    sys.exit(main())
