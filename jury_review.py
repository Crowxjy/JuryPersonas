#!/usr/bin/env python3
"""
jury_review.py — Jury Personas 顶层入口(M3 MVP)

一条命令贯穿 brief → DAG → 模式 → 报告:

    python3 jury_review.py --brief tests/fixtures/short_video_demo/brief.json \\
        --artifact tests/fixtures/short_video_demo/artifact.json \\
        --personas consumer-bao-mom-tier2,consumer-silver-male,consumer-bluecollar-male

行为:
1. 调 orchestrator/pipeline.py --execute 跑全链
2. 默认 runtime-dir=/tmp/jp_m3 (沙箱友好,可改 .runtime)
3. 默认 lark 走 dry-run / 本地降级
4. 退出码:0=成功;1=brief 校验失败;2=参数错

设计理由(MVP):
- 这一层只做"参数转译 + 命令组装",真逻辑全在 orchestrator.pipeline.execute_dag
  - 正式使用时由宿主 Agent/模型回填 reactions,顶层入口保持稳定
"""
from __future__ import annotations

import argparse
import sys

from orchestrator import pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Jury Personas 顶层入口 — 一条命令跑通陪审团评审"
    )
    parser.add_argument("--brief", required=True, help="brief JSON 路径")
    parser.add_argument("--artifact", required=True, help="评审对象 JSON 路径")
    parser.add_argument(
        "--personas",
        help="陪审员 role_id 列表,逗号分隔;不传则使用场景默认组合",
    )
    parser.add_argument(
        "--runtime-dir",
        default="/tmp/jp_m3",
        help="运行产物目录(默认 /tmp/jp_m3)",
    )
    parser.add_argument(
        "--first-round",
        action="store_true",
        help="标记首次会话(boundary_ack 强制全 ack)",
    )
    parser.add_argument(
        "--context",
        help="用户原始上下文(可选,触发 evidence 回溯校验)",
    )
    parser.add_argument(
        "--no-mock-llm",
        action="store_true",
        help="不调 mock 桩,只产 jury-react bundle 让宿主 Agent/模型回填",
    )
    parser.add_argument(
        "--lark-execute",
        action="store_true",
        help="飞书发布关闭 dry-run(MVP 默认 dry-run / 本地降级)",
    )
    parser.add_argument("--pretty", action="store_true", default=True, help="美化 JSON")
    parser.add_argument(
        "--include", action="append", default=[], help="追加可选模式(可多次)"
    )
    parser.add_argument(
        "--exclude", action="append", default=[], help="排除非 required 模式(可多次)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # 把参数翻译为 pipeline.main() 期望的 CLI 形式,直接复用 argparse
    pipeline_argv = [
        "--brief-file", args.brief,
        "--artifact-file", args.artifact,
        "--runtime-dir", args.runtime_dir,
        "--execute",
    ]
    if args.personas:
        pipeline_argv += ["--personas", args.personas]
    if args.first_round:
        pipeline_argv.append("--first-round")
    if args.context:
        pipeline_argv += ["--context-file", args.context]
    if args.no_mock_llm:
        pipeline_argv.append("--no-mock-llm")
    if args.lark_execute:
        pipeline_argv.append("--lark-execute")
    if args.pretty:
        pipeline_argv.append("--pretty")
    for inc in args.include:
        pipeline_argv += ["--include", inc]
    for exc in args.exclude:
        pipeline_argv += ["--exclude", exc]

    return pipeline.main(pipeline_argv)


if __name__ == "__main__":
    sys.exit(main())
