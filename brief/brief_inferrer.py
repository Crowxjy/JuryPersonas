#!/usr/bin/env python3
"""
brief_inferrer.py — Brief 字段半自动抽取脚手架

设计目标:
1. 从用户原始 query 中抽取 5 个必备字段的"候选值"(hints),供上层 Agent 参考
2. 严禁直接拍板 → Agent 拿到 hints 后,仍需按 brief_harness.md 自行判断 sufficient
3. 严禁直接调用 LLM API → 仅做规则化抽取(关键词 / 正则 / 后缀识别)
4. 不做 Markdown 包裹 → 输出纯 JSON,便于 Agent 直接解析

抽取策略:
- artifact_type:    后缀名 + 关键词(短视频/PRD/设计稿等)
- artifact_locator: 绝对路径正则 + URL 正则
- target_audience:  人群关键词(消费者/商家/Z 世代/银发/宝妈/蓝领等)
- key_concern:      关心点关键词(流失/转化/合理/决策/综合)
- distribution_intent: 分布关键词(真实分布/mock/指定专家)

⚠️ 抽取置信度低时,字段返回 null,留给 Agent 自己问用户。

使用模式:

    # 模式 A: 从 stdin 读 query
    echo "评一下 /Users/me/video.mp4 这个短视频" | python3 brief_inferrer.py

    # 模式 B: 命令行参数
    python3 brief_inferrer.py --query "评一下 /Users/me/video.mp4 这个短视频"

    # 模式 C: 从文件读 query
    python3 brief_inferrer.py --query-file user_input.txt

输出:

    {
      "hints": {
        "artifact_type":       {"value": "短视频", "evidence": "包含 .mp4 后缀", "confidence": 0.9},
        "artifact_locator":    {"value": "/Users/me/video.mp4", "evidence": "匹配绝对路径正则", "confidence": 0.95},
        "target_audience":     {"value": null, "evidence": null, "confidence": 0.0},
        "key_concern":         {"value": null, "evidence": null, "confidence": 0.0},
        "distribution_intent": {"value": null, "evidence": null, "confidence": 0.0}
      },
      "raw_query": "..."
    }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Optional

ARTIFACT_TYPE_KEYWORDS = {
    "短视频": ["短视频", "成片", "视频成片", "抖音", "视频号", "B 站", "tiktok"],
    "PRD": ["prd", "需求文档", "需求稿", "产品文档"],
    "设计稿": ["设计稿", "ui 稿", "界面稿", "figma", "sketch"],
    "单界面": ["截图", "界面截图", "单页面", "单界面"],
    "详情页": ["详情页", "商详", "商品详情"],
    "商品卡": ["商品卡", "card", "卡片"],
    "营销文案": ["营销文案", "朋友圈文案", "小红书文案", "落地页文案", "种草文案"],
}

ARTIFACT_TYPE_SUFFIX = {
    ".mp4": "短视频", ".mov": "短视频", ".avi": "短视频", ".webm": "短视频",
    ".md": "PRD", ".docx": "PRD", ".doc": "PRD", ".pdf": "PRD",
    ".png": "设计稿", ".jpg": "设计稿", ".jpeg": "设计稿", ".webp": "设计稿",
    ".fig": "设计稿", ".sketch": "设计稿",
}

TARGET_AUDIENCE_KEYWORDS = {
    "Z 世代女性": ["z 世代女", "z世代女", "00 后女", "00后女"],
    "Z 世代男性": ["z 世代男", "z世代男", "00 后男", "00后男"],
    "宝妈": ["宝妈", "妈妈群体", "母婴人群"],
    "银发男性": ["银发男", "退休男", "中老年男"],
    "银发女性": ["银发女", "退休女", "中老年女"],
    "蓝领男性": ["蓝领", "工友", "工地", "外卖员", "快递员", "司机"],
    "三线消费者": ["三线", "县城", "下沉市场"],
    "一二线消费者": ["一二线", "一线", "北上广深"],
    "中小商家": ["中小商家", "小 b", "小B", "商家"],
    "KA 商家": ["ka 商家", "ka商家", "大客户", "头部商家"],
    "内部决策层": ["老板", "总监", "vp", "决策层", "高管"],
    "设计/产品同事": ["同事", "设计师", "产品经理", "pm 同事", "ue 同事"],
    "通用人群": ["通用人群", "all users", "通用"],
}

KEY_CONCERN_KEYWORDS = {
    "流失": ["流失", "劝退", "划走", "跳出", "看不下去"],
    "转化": ["转化", "成单", "下单", "购买", "点击"],
    "合理性": ["合理", "逻辑", "设计原则", "信息架构"],
    "决策建议": ["决策建议", "🅰", "🅑", "决策怎么走", "给路径"],
    "综合评估": ["综合评估", "都看看", "综合", "整体"],
}

DISTRIBUTION_INTENT_KEYWORDS = {
    "mock": ["用mock", "用 mock", "走mock", "走 mock", "mock分布", "mock 分布", "假数据", "默认mock"],
    "specified_personas": ["指定专家", "指定画像", "我点名", "只用[a-zA-Z0-9_-]+", "走 [a-zA-Z0-9_-]+"],
    "real": ["有真实分布", "提供真实分布", "客群分布json", "真实数据路径", "我有真实"],
}

ABS_PATH_RE = re.compile(r"(/(?:[A-Za-z0-9._\-\u4e00-\u9fa5]+/?)+)")
URL_RE = re.compile(r"(https?://[^\s'\"]+)")


def lower_normalize(text: str) -> str:
    return text.lower().replace(" ", "").replace("　", "")


def match_keywords(text_lower: str, keyword_map: dict) -> tuple[Optional[str], Optional[str]]:
    """命中第一组关键词返回 (label, matched_keyword);否则返回 (None, None)。"""
    for label, keywords in keyword_map.items():
        for kw in keywords:
            if lower_normalize(kw) in text_lower:
                return label, kw
    return None, None


def extract_artifact_type(query: str) -> dict:
    text_lower = lower_normalize(query)

    # 优先看后缀(更可靠)
    for suffix, label in ARTIFACT_TYPE_SUFFIX.items():
        if suffix in text_lower:
            return {
                "value": label,
                "evidence": f"包含 {suffix} 后缀",
                "confidence": 0.9,
            }

    # 关键词
    label, kw = match_keywords(text_lower, ARTIFACT_TYPE_KEYWORDS)
    if label:
        return {
            "value": label,
            "evidence": f"包含关键词 '{kw}'",
            "confidence": 0.7,
        }

    return {"value": None, "evidence": None, "confidence": 0.0}


def extract_artifact_locator(query: str) -> dict:
    # 优先 URL
    url_match = URL_RE.search(query)
    if url_match:
        return {
            "value": url_match.group(1),
            "evidence": "匹配 URL 正则",
            "confidence": 0.95,
        }

    # 绝对路径(/ 开头)
    path_matches = ABS_PATH_RE.findall(query)
    for path in path_matches:
        if "/" in path[1:] and len(path) > 3:
            return {
                "value": path,
                "evidence": "匹配绝对路径正则",
                "confidence": 0.9,
            }

    return {"value": None, "evidence": None, "confidence": 0.0}


def extract_target_audience(query: str) -> dict:
    text_lower = lower_normalize(query)
    label, kw = match_keywords(text_lower, TARGET_AUDIENCE_KEYWORDS)
    if label:
        return {
            "value": label,
            "evidence": f"包含关键词 '{kw}'",
            "confidence": 0.7,
        }
    return {"value": None, "evidence": None, "confidence": 0.0}


def extract_key_concern(query: str) -> dict:
    text_lower = lower_normalize(query)
    label, kw = match_keywords(text_lower, KEY_CONCERN_KEYWORDS)
    if label:
        return {
            "value": label,
            "evidence": f"包含关键词 '{kw}'",
            "confidence": 0.75,
        }
    return {"value": None, "evidence": None, "confidence": 0.0}


def extract_distribution_intent(query: str) -> dict:
    text_lower = lower_normalize(query)
    for label, keywords in DISTRIBUTION_INTENT_KEYWORDS.items():
        for kw in keywords:
            if re.search(kw, text_lower):
                return {
                    "value": label,
                    "evidence": f"匹配模式 '{kw}'",
                    "confidence": 0.7,
                }
    return {"value": None, "evidence": None, "confidence": 0.0}


def infer(query: str) -> dict:
    return {
        "hints": {
            "artifact_type": extract_artifact_type(query),
            "artifact_locator": extract_artifact_locator(query),
            "target_audience": extract_target_audience(query),
            "key_concern": extract_key_concern(query),
            "distribution_intent": extract_distribution_intent(query),
        },
        "raw_query": query,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Brief 字段半自动抽取(候选值,非最终判断)")
    parser.add_argument("--query", help="用户原始 query 文本")
    parser.add_argument("--query-file", help="从文件读取用户 query")
    parser.add_argument("--pretty", action="store_true", help="美化 JSON 输出")
    return parser


def read_query(args) -> str:
    if args.query:
        return args.query
    if args.query_file:
        with open(args.query_file, "r", encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    sys.stderr.write("[error] 必须提供 --query / --query-file / 或从 stdin 读\n")
    sys.exit(2)


def main() -> int:
    args = build_parser().parse_args()
    query = read_query(args).strip()
    if not query:
        sys.stderr.write("[error] query 为空\n")
        return 2
    result = infer(query)
    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
