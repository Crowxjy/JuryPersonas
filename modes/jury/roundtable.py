#!/usr/bin/env python3
"""
roundtable.py — 多角色圆桌:为多个角色生成独立的 System Prompt 包,供调用方并行调用模型

用法:
    python3 roundtable.py <role_id1,role_id2,...> [--question "你的问题"]
    python3 roundtable.py ad-buyer,consumer-genz-female --question "评价一下抖音购物车体验"
    python3 roundtable.py ad-buyer,consumer-genz-female --output bundle.json

设计原则:
- 本脚本不直接调用 LLM(避免硬编码 endpoint),只生成 prompt 包
- 调用方(Agent / 上层 Skill / 测试脚本)拿到 bundle 后,自行并行调用模型
- 每个角色独立 System Prompt,互不影响
"""
import argparse
import json
import sys

from compile_persona import compile_persona


def build_roundtable(role_ids, question=None):
    """构建圆桌 prompt 包"""
    bundle = {
        "mode": "roundtable",
        "question": question,
        "instructions_for_caller": (
            "对每个 participant 独立调用模型,system 用其 system_prompt,"
            "user 用 question 或调用方自定义。完成后将 responses 汇总,"
            "并由中立旁白(非角色)输出差异点对比表。"
        ),
        "participants": [],
        "summary_template": (
            "## 圆桌差异点对比(中立汇总)\n\n"
            "| 维度 | {roles_header} |\n"
            "|---|{sep}|\n"
            "| 直觉评分 | ... |\n"
            "| 最在意的问题 | ... |\n"
            "| 关键分歧 | ... |\n\n"
            "### 共识\n- ...\n\n"
            "### 分歧\n- ...\n\n"
            "### 建议优先采纳\n基于本次产物的目标人群,建议优先参考 [角色 X] 的反馈。"
        ),
    }

    errors = []
    for rid in role_ids:
        try:
            result = compile_persona(rid)
            bundle["participants"].append({
                "role_id": rid,
                "name": result["meta"].get("name", rid),
                "category": result["meta"].get("category", ""),
                "sub_category": result["meta"].get("sub_category", ""),
                "status": result["meta"].get("status", ""),
                "system_prompt": result["system_prompt"],
            })
        except FileNotFoundError as e:
            errors.append(str(e))

    if errors:
        bundle["errors"] = errors

    # 填充 summary_template 的角色列
    if bundle["participants"]:
        names = [p["name"] for p in bundle["participants"]]
        bundle["summary_template"] = bundle["summary_template"].format(
            roles_header=" | ".join(names),
            sep="|".join(["---"] * len(names)),
        )

    return bundle


def main():
    parser = argparse.ArgumentParser(description="多角色圆桌 prompt 包生成器")
    parser.add_argument("role_ids", help="角色 ID 列表,逗号分隔")
    parser.add_argument("--question", "-q", help="圆桌共同问题(可选)")
    parser.add_argument("--output", "-o", help="输出文件路径(默认 stdout)")
    args = parser.parse_args()

    role_ids = [r.strip() for r in args.role_ids.split(",") if r.strip()]
    if not role_ids:
        print("ERROR: 至少需要一个角色 ID", file=sys.stderr)
        sys.exit(1)

    bundle = build_roundtable(role_ids, args.question)
    output = json.dumps(bundle, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"OK: 圆桌包已生成 → {args.output}")
        print(f"   参与角色: {len(bundle['participants'])}")
        if "errors" in bundle:
            print(f"   失败角色: {len(bundle['errors'])}")
    else:
        print(output)


if __name__ == "__main__":
    main()
