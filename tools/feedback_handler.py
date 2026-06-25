#!/usr/bin/env python3
"""
feedback_handler.py — 用户反馈收集与提交

设计目标:
1. 优先引导用户走飞书表单提交,降低参与门槛
2. 表单不可用时,中间模型(LLM)在对话中收集结构化反馈,再由本脚本写入 Base
3. 不直接调用 LLM API,符合"脚本严禁直接调用 LLM"约束

依赖:
- lark-cli (https://github.com/larksuite/cli) 必须已安装,并已 `auth login --as user`

使用模式:

    # 模式 A: 输出表单链接(供中间模型推送给用户填表)
    python3 feedback_handler.py form-url

    # 模式 B: 输出表单引导文案(供中间模型直接复述给用户)
    python3 feedback_handler.py form-prompt

    # 模式 C: 中间模型从对话中收集到结构化反馈,本脚本兜底落库
    python3 feedback_handler.py submit \
        --type "知识缺失" \
        --description "回答里提到 awsl=阿伟死了,但当前年轻人很少这样用。应改为更中性的含义" \
        --reporter "xxx@xxx.com"

    # 模式 D: dry-run 预览,不真正写入
    python3 feedback_handler.py submit --description "..." --dry-run
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# 飞书多维表格反馈库的固定信息(已在 lark-base 中创建)
BASE_TOKEN = "HGLTbRGqdagunpsf5r9cPjobnDd"
TABLE_ID = "tblEoCPkWbIc3rKk"
FORM_ID = "vewriYNmAf"
BASE_URL = f"https://bytedance.larkoffice.com/base/{BASE_TOKEN}"
FORM_URL = f"{BASE_URL}?table={TABLE_ID}&view={FORM_ID}"

# 字段白名单与可选值校验,避免脏数据
ALLOWED_TYPES = {
    "角色拟合错误",
    "角色信息缺失",
    "知识错误或过时",
    "知识缺失",
    "圆桌讨论效果差",
    "功能建议",
    "其他",
}
ALLOWED_SOURCE = {"飞书表单", "对话兜底", "内部录入"}

DEFAULT_TYPE = "其他"
DEFAULT_SOURCE = "对话兜底"


def output_form_url() -> int:
    print(FORM_URL)
    return 0


def output_form_prompt() -> int:
    """输出可直接复述给用户的引导文案(中间模型可作为表单引导话术使用)。"""
    prompt = (
        "我们提供了一份极简飞书反馈表,请帮我们记录下你遇到的问题:\n"
        f"  {FORM_URL}\n\n"
        "提交后我们会持续优化角色画像与共享知识库。\n"
        "如果暂时不方便填表,可以直接在对话里告诉我以下信息,我会帮你登记:\n"
        "  1. 问题类型(角色拟合错误/角色信息缺失/知识错误或过时/知识缺失/圆桌讨论效果差/功能建议/其他)\n"
        "  2. 问题描述(详细描述遇到的问题、现象及期望结果)\n"
    )
    print(prompt)
    return 0


def normalize_choice(value, allowed: set, default: str, label: str) -> str:
    """容错处理选项值:支持包含、不区分大小写匹配,失败则降级到 default。"""
    if not value:
        return default
    value = value.strip()
    if value in allowed:
        return value
    lowered = value.lower()
    for option in allowed:
        if option.lower() == lowered or option.lower() in lowered or lowered in option.lower():
            return option
    sys.stderr.write(
        f"[warn] {label} '{value}' 不在白名单 {sorted(allowed)},降级为 '{default}'\n"
    )
    return default


def build_payload(args) -> dict:
    payload = {
        "问题描述": (args.description or "").strip(),
        "问题类型": normalize_choice(args.type, ALLOWED_TYPES, DEFAULT_TYPE, "问题类型"),
        "反馈来源": normalize_choice(args.source, ALLOWED_SOURCE, DEFAULT_SOURCE, "反馈来源"),
        "处理状态": "Todo",
    }
    if args.reporter and args.reporter.strip():
        payload["提交人"] = args.reporter.strip()
    return payload


def ensure_lark_cli() -> str:
    binary = shutil.which("lark-cli")
    if not binary:
        sys.stderr.write(
            "[error] 未检测到 lark-cli,请先安装并执行 `lark-cli auth login --domain base`\n"
        )
        sys.exit(2)
    return binary


def submit(args) -> int:
    if not args.description or not args.description.strip():
        sys.stderr.write("[error] --description 必填,请先确认问题描述\n")
        return 2
    payload = build_payload(args)
    cmd = [
        ensure_lark_cli(),
        "base",
        "+record-upsert",
        "--base-token",
        BASE_TOKEN,
        "--table-id",
        TABLE_ID,
        "--json",
        json.dumps(payload, ensure_ascii=False),
        "--as",
        "user",
    ]
    if args.dry_run:
        print(json.dumps({"dry_run": True, "command": cmd, "payload": payload}, ensure_ascii=False, indent=2))
        return 0
    result = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode != 0:
        sys.stderr.write("[error] 反馈写入失败,请重试或改用飞书表单提交\n")
        return result.returncode
    print(f"\n[ok] 反馈已记录到飞书多维表格: {BASE_URL}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EAgents 用户反馈处理器")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("form-url", help="输出飞书反馈表单 URL")
    sub.add_parser("form-prompt", help="输出表单引导文案(供中间模型复述)")

    submit_parser = sub.add_parser("submit", help="对话兜底:把结构化反馈写入飞书 Base")
    submit_parser.add_argument("--description", required=True, help="问题描述(必填)")
    submit_parser.add_argument("--type", help="问题类型,见白名单")
    submit_parser.add_argument("--source", help="反馈来源(默认 对话兜底)")
    submit_parser.add_argument("--reporter", help="提交人,姓名或邮箱")
    submit_parser.add_argument("--dry-run", action="store_true", help="只打印拼好的命令,不真正写入")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "form-url":
        return output_form_url()
    if args.command == "form-prompt":
        return output_form_prompt()
    if args.command == "submit":
        return submit(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
