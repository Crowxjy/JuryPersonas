#!/usr/bin/env python3
"""
modes/aggregate/consensus.py — mode/aggregate-consensus 实现

职责:
1. 读 jury-react filled bundle JSON(participants[*].reaction 已回填)
2. 从每位陪审员的 5 字段卡点中抽取结构化条目
3. 按 (关注点 + 场景化卡点位置规约) 聚类,统计提及频次和提及人群
4. 抽出共识(>= 2 人提到同一卡点)和分歧(单人或评分差距大的维度)
5. 生成场景化评分矩阵(5 维 × N 角色)
6. 输出 consensus_pack JSON 给 mode/render-report 消费

⚠️ 抽取策略(M3 MVP):
- 解析 reaction Markdown 里 "#### 问题 N" 块下的 5 字段(所属人群/关注点/卡点位置/可能流失原因/改进建议)
- 同时抽 "0-10 量化" 段下 5 个维度的分数
- 卡点位置归一化(0-3 秒封面 / 32 秒 CTA / 中段 / 整体 / 成品装盘 等)用关键词映射,
  避免"0-3 秒封面"和"封面前 3 秒"被算成不同卡点

使用模式:

    python3 modes/aggregate/consensus.py \\
        --bundle-file /tmp/jp_m3/reactions/m3-demo.filled.json \\
        --output /tmp/jp_m3/consensus/m3-demo.json --pretty

输出 consensus_pack 结构:
{
  "mode": "mode/aggregate-consensus",
  "session_id": "...",
  "scenario": "review-short-video",
  "n_participants": 3,
  "complaints": [   # 5 字段卡点扁平表
    {"role_id": "...", "category": "...", "sub_category": "...",
     "concern": "...", "position": "...", "position_canonical": "...",
     "reason": "...", "fix": "..."}
  ],
  "consensus": [    # 提及频次 >= 2 的卡点
    {"position_canonical": "...", "concerns": [...], "mentioned_by": [...],
     "frequency": 2, "best_fix": "..."}
  ],
  "divergence": [   # 单人卡点 + 角色间打分差异 > 3 的维度
    {"kind": "unique_complaint", "role_id": "...", "...": "..."},
    {"kind": "score_gap", "metric": "完播倾向", "scores": {...}, "gap": 4}
  ],
    "score_matrix": {
      "scenario": "review-prd",
      "metrics": ["必要性", "可行性", "完整性", "风险可控性", "推荐推进度"],
    "rows": [{"role_id":"...", "name":"...", "scores":{...}, "average": 2.6}],
    "averages": {"完播倾向": 5.0, ...}
  }
}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict


# 卡点位置归一化(关键词命中即归类)。短视频规则只用于 review-short-video;
# 其他场景使用自己的章节/区域体系,避免把 PRD/设计稿归到时间轴位置。
POSITION_RULESETS: dict[str, list[tuple[str, list[str]]]] = {
    "review-short-video": [
    ("0-3 秒封面/钩子", ["0-3", "0~3", "封面", "前 3 秒", "前3秒", "钩子"]),
    ("3-15 秒中段", ["3-15", "中段", "煮的过程", "中间"]),
    ("22 秒成品装盘", ["22", "成品", "装盘"]),
    ("32 秒处 CTA", ["32", "cta", "小黄车", "购物车"]),
    ("整体定位", ["整体", "定位", "无关", "和我无关", "跟我没关系"]),
    ("信任/分量", ["分量", "几只", "几两", "值不值", "信任"]),
    ],
    "review-prd": [
        ("目标/背景", ["目标", "背景", "问题", "机会", "为什么"]),
        ("用户场景", ["用户", "人群", "场景", "触发", "路径"]),
        ("方案设计", ["方案", "功能", "流程", "策略", "规则"]),
        ("指标/证据", ["指标", "证据", "数据", "口径", "验收"]),
        ("风险/边界", ["风险", "边界", "依赖", "反例", "不能"]),
        ("资源/排期", ["排期", "资源", "成本", "里程碑", "owner"]),
        ("整体定位", ["整体", "定位", "主线", "范围"]),
    ],
    "review-design": [
        ("首屏/主视觉", ["首屏", "主视觉", "hero", "顶部", "第一屏"]),
        ("信息架构", ["信息架构", "结构", "分组", "层级", "模块"]),
        ("CTA/行动入口", ["cta", "按钮", "行动", "入口", "下一步"]),
        ("交互反馈", ["交互", "反馈", "状态", "动效", "点击"]),
        ("视觉层级", ["视觉", "层级", "字号", "颜色", "对比"]),
        ("信任/说明", ["信任", "说明", "证据", "背书", "提示"]),
        ("整体体验", ["整体", "风格", "一致", "体验"]),
    ],
    "review-screen": [
        ("首屏/主视觉", ["首屏", "主视觉", "顶部", "第一屏"]),
        ("信息架构", ["信息架构", "结构", "分组", "层级", "模块"]),
        ("CTA/行动入口", ["cta", "按钮", "行动", "入口", "下一步"]),
        ("交互反馈", ["交互", "反馈", "状态", "点击", "表单"]),
        ("视觉层级", ["视觉", "层级", "字号", "颜色", "对比"]),
        ("信任/说明", ["信任", "说明", "证据", "背书", "提示"]),
        ("整体体验", ["整体", "风格", "一致", "体验"]),
    ],
    "review-detail-page": [
        ("标题/卖点", ["标题", "卖点", "利益点", "首屏", "主图"]),
        ("价格/权益", ["价格", "优惠", "权益", "券", "套餐"]),
        ("图片/示例", ["图片", "视频", "示例", "样张", "场景图"]),
        ("规格/配送", ["规格", "库存", "配送", "时效", "售后"]),
        ("评价/信任", ["评价", "口碑", "信任", "证据", "背书"]),
        ("CTA/购买入口", ["cta", "按钮", "购买", "下单", "加购"]),
        ("页面整体", ["整体", "页面", "转化", "路径"]),
    ],
    "review-product-card": [
        ("标题/卖点", ["标题", "卖点", "利益点", "卡片", "主图"]),
        ("价格/权益", ["价格", "优惠", "权益", "券", "补贴"]),
        ("图片/示例", ["图片", "示例", "样张", "视觉"]),
        ("规格/配送", ["规格", "库存", "配送", "时效"]),
        ("评价/信任", ["评价", "口碑", "信任", "证据", "背书"]),
        ("CTA/购买入口", ["cta", "按钮", "购买", "下单", "加购"]),
        ("卡片整体", ["整体", "卡片", "转化", "路径"]),
    ],
    "review-marketing-copy": [
        ("标题/钩子", ["标题", "钩子", "开头", "第一句", "首句"]),
        ("核心卖点", ["卖点", "利益", "价值", "痛点", "收益"]),
        ("证据/背书", ["证据", "背书", "案例", "数据", "口碑"]),
        ("CTA/行动", ["cta", "行动", "按钮", "下单", "咨询"]),
        ("语气/品牌", ["语气", "品牌", "调性", "人设", "措辞"]),
        ("长度/结构", ["长度", "结构", "段落", "节奏", "信息密度"]),
        ("文案整体", ["整体", "转化", "传播", "理解"]),
    ],
}

DEFAULT_POSITION_RULES: list[tuple[str, list[str]]] = [
    ("目标/背景", ["目标", "背景", "问题", "机会"]),
    ("用户场景", ["用户", "人群", "场景", "触发"]),
    ("方案/内容主体", ["方案", "内容", "主体", "流程"]),
    ("证据/信任", ["证据", "信任", "数据", "背书"]),
    ("CTA/下一步", ["cta", "按钮", "行动", "下一步"]),
    ("整体", ["整体", "定位", "体验", "结构"]),
]


SCORE_METRICSETS: dict[str, list[str]] = {
    "review-short-video": ["完播倾向", "互动倾向", "转化倾向", "信任度", "推荐倾向"],
    "review-prd": ["必要性", "可行性", "完整性", "风险可控性", "推荐推进度"],
    "review-design": ["可用性", "一致性", "视觉层级", "信息密度", "行动清晰度"],
    "review-screen": ["可用性", "一致性", "视觉层级", "信息密度", "行动清晰度"],
    "review-detail-page": ["理解效率", "信任证据", "购买意愿", "价格清晰度", "行动清晰度"],
    "review-product-card": ["理解效率", "信任证据", "购买意愿", "价格清晰度", "行动清晰度"],
    "review-marketing-copy": ["读完意愿", "利益清晰度", "信任感", "转化意愿", "传播意愿"],
}

DEFAULT_SCORE_METRICS = ["理解意愿", "参与意愿", "行动意愿", "信任度", "推荐意愿"]

SCORE_ALIASES: dict[str, list[str]] = {
    "必要性": ["必要性", "价值必要性"],
    "可行性": ["可行性", "落地可行性"],
    "完整性": ["完整性", "方案完整性"],
    "风险可控性": ["风险可控性", "风险"],
    "推荐推进度": ["推荐推进度", "推荐倾向"],
    "可用性": ["可用性", "易用性"],
    "一致性": ["一致性", "视觉一致性"],
    "视觉层级": ["视觉层级", "层级清晰度"],
    "信息密度": ["信息密度", "信息清晰度"],
    "行动清晰度": ["行动清晰度", "互动倾向"],
    "理解效率": ["理解效率", "理解清晰度"],
    "信任证据": ["信任证据", "信任度"],
    "购买意愿": ["购买意愿", "转化倾向"],
    "价格清晰度": ["价格清晰度", "价格理解"],
    "读完意愿": ["读完意愿", "完播倾向"],
    "利益清晰度": ["利益清晰度", "卖点清晰度"],
    "信任感": ["信任感", "信任度"],
    "转化意愿": ["转化意愿", "转化倾向"],
    "传播意愿": ["传播意愿", "推荐倾向"],
    "理解意愿": ["理解意愿", "完播倾向"],
    "参与意愿": ["参与意愿", "互动倾向"],
    "行动意愿": ["行动意愿", "转化倾向"],
    "推荐意愿": ["推荐意愿", "推荐倾向"],
}


def get_position_rules(scenario: str | None) -> list[tuple[str, list[str]]]:
    return POSITION_RULESETS.get(scenario or "", DEFAULT_POSITION_RULES)


def get_score_metrics(scenario: str | None) -> list[str]:
    return SCORE_METRICSETS.get(scenario or "", DEFAULT_SCORE_METRICS)


def normalize_position(raw: str, scenario: str | None = None) -> str:
    if not raw:
        return "未知位置"
    rl = raw.lower()
    for canonical, kws in get_position_rules(scenario):
        for kw in kws:
            if kw.lower() in rl:
                return canonical
    return raw.strip()


def parse_complaints(reaction_text: str, participant: dict, scenario: str | None = None) -> list[dict]:
    """从 Markdown reaction 中抽取 5 字段卡点条目。"""
    out: list[dict] = []
    if not reaction_text:
        return out
    # 切问题块: #### 问题 N
    blocks = re.split(r"####\s*问题\s*\d+", reaction_text)
    for blk in blocks[1:]:  # 第 0 段是问题表头之前的内容
        # 字段抽取: "- 关注点: xxx"
        def grab(label: str) -> str:
            m = re.search(rf"-\s*{re.escape(label)}\s*[::]\s*(.+)", blk)
            return m.group(1).strip() if m else ""

        item = {
            "role_id": participant["role_id"],
            "name": participant.get("name", participant["role_id"]),
            "category": participant.get("category", ""),
            "sub_category": participant.get("sub_category", ""),
            "concern": grab("关注点"),
            "position": grab("卡点位置"),
            "reason": grab("可能流失原因"),
            "fix": grab("改进建议"),
        }
        item["position_canonical"] = normalize_position(item["position"], scenario)
        # 至少要有 concern 和 position 才算有效条目
        if item["concern"] and item["position"]:
            out.append(item)
    return out


def parse_scores(reaction_text: str, scenario: str | None = None) -> dict[str, int]:
    """从 reaction 抽 5 维 0-10 评分,缺失补 None。"""
    scores: dict[str, int] = {}
    for metric in get_score_metrics(scenario):
        labels = SCORE_ALIASES.get(metric, [metric])
        m = None
        for label in labels:
            m = re.search(rf"{re.escape(label)}\s*[::]\s*(\d+)\s*/\s*10", reaction_text)
            if m:
                break
        if m:
            scores[metric] = int(m.group(1))
        else:
            scores[metric] = None  # type: ignore[assignment]
    return scores


def aggregate_consensus(complaints: list[dict]) -> list[dict]:
    """按 position_canonical 聚类,频次 >= 2 视作共识。"""
    by_pos: dict[str, list[dict]] = defaultdict(list)
    for c in complaints:
        by_pos[c["position_canonical"]].append(c)

    consensus = []
    for pos, items in by_pos.items():
        if len(items) >= 2:
            # 选最长的 fix 作为 best_fix(粗启发式:更具体)
            best_fix = max((i["fix"] for i in items if i.get("fix")), key=len, default="")
            consensus.append(
                {
                    "position_canonical": pos,
                    "concerns": sorted({i["concern"] for i in items}),
                    "mentioned_by": [
                        {"role_id": i["role_id"], "name": i["name"], "sub_category": i["sub_category"]}
                        for i in items
                    ],
                    "frequency": len(items),
                    "best_fix": best_fix,
                }
            )
    consensus.sort(key=lambda x: (-x["frequency"], x["position_canonical"]))
    return consensus


def find_divergence(
    complaints: list[dict],
    score_rows: list[dict],
    scenario: str | None = None,
) -> list[dict]:
    """两类分歧:
    1. 单人 unique_complaint:某 position_canonical 仅 1 人提
    2. score_gap:同一指标上最大-最小分差 > 3
    """
    div: list[dict] = []

    by_pos: dict[str, list[dict]] = defaultdict(list)
    for c in complaints:
        by_pos[c["position_canonical"]].append(c)
    for pos, items in by_pos.items():
        if len(items) == 1:
            i = items[0]
            div.append(
                {
                    "kind": "unique_complaint",
                    "position_canonical": pos,
                    "role_id": i["role_id"],
                    "name": i["name"],
                    "concern": i["concern"],
                    "reason": i["reason"],
                    "fix": i["fix"],
                }
            )

    for metric in get_score_metrics(scenario):
        vals = [(r["role_id"], r["scores"].get(metric)) for r in score_rows]
        vals_known = [(rid, v) for rid, v in vals if isinstance(v, int)]
        if len(vals_known) < 2:
            continue
        max_rid, max_v = max(vals_known, key=lambda x: x[1])
        min_rid, min_v = min(vals_known, key=lambda x: x[1])
        gap = max_v - min_v
        if gap > 3:
            div.append(
                {
                    "kind": "score_gap",
                    "metric": metric,
                    "max": {"role_id": max_rid, "score": max_v},
                    "min": {"role_id": min_rid, "score": min_v},
                    "gap": gap,
                }
            )
    return div


def build_score_matrix(score_rows: list[dict], scenario: str | None = None) -> dict:
    """构建 5 维评分矩阵 + 每行均分 + 每列均分。"""
    averages: dict[str, float] = {}
    metrics = get_score_metrics(scenario)
    for metric in metrics:
        vals = [r["scores"][metric] for r in score_rows if isinstance(r["scores"].get(metric), int)]
        averages[metric] = round(sum(vals) / len(vals), 2) if vals else None  # type: ignore[assignment]
    for r in score_rows:
        knowns = [v for v in r["scores"].values() if isinstance(v, int)]
        r["average"] = round(sum(knowns) / len(knowns), 2) if knowns else None
    return {
        "scenario": scenario,
        "metrics": metrics,
        "rows": score_rows,
        "averages": averages,
    }


def build_consensus_pack(bundle: dict) -> dict:
    participants = bundle.get("participants", [])
    scenario = bundle.get("scenario")
    all_complaints: list[dict] = []
    score_rows: list[dict] = []

    for p in participants:
        reaction = p.get("reaction") or ""
        complaints = parse_complaints(reaction, p, scenario)
        all_complaints.extend(complaints)
        score_rows.append(
            {
                "role_id": p["role_id"],
                "name": p.get("name", p["role_id"]),
                "sub_category": p.get("sub_category", ""),
                "scores": parse_scores(reaction, scenario),
            }
        )

    consensus = aggregate_consensus(all_complaints)
    score_matrix = build_score_matrix(score_rows, scenario)
    divergence = find_divergence(all_complaints, score_rows, scenario)

    return {
        "mode": "mode/aggregate-consensus",
        "session_id": bundle.get("session_id"),
          "scenario": scenario,
        "n_participants": len(participants),
        "complaints": all_complaints,
        "consensus": consensus,
        "divergence": divergence,
        "score_matrix": score_matrix,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="mode/aggregate-consensus 实现")
    parser.add_argument(
        "--bundle-file",
        required=True,
        help="jury-react filled bundle JSON 路径(reaction 已回填)",
    )
    parser.add_argument("--output", "-o", help="输出 consensus_pack 路径(默认 stdout)")
    parser.add_argument("--pretty", action="store_true", help="美化 JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    path = Path(args.bundle_file)
    if not path.exists():
        sys.stderr.write(f"[error] bundle 文件不存在: {path}\n")
        return 2

    bundle = json.loads(path.read_text(encoding="utf-8"))
    pack = build_consensus_pack(bundle)
    out = json.dumps(pack, ensure_ascii=False, indent=2 if args.pretty else None)

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        sys.stdout.write(
            f"[OK] consensus pack → {args.output} "
            f"(complaints={len(pack['complaints'])}, "
            f"consensus={len(pack['consensus'])}, "
            f"divergence={len(pack['divergence'])})\n"
        )
    else:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
