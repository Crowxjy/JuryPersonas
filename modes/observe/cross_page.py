#!/usr/bin/env python3
"""
cross_page.py — Cross-page (multi-interface) OBJECTIVE summary engine.

只测不判 (measure-only, no judgement): given the per-page metrics.json produced by
generate_heatmap.py for >=2 RELATED pages (in flow order), compute the four
cross-page objective metrics defined in
  references/phase_a_hci/cross_page_metrics.md
and emit cross_page.json. It states facts (numbers/curves) ONLY; it never says
good/bad/should — coherence & business-goal judgement is left to Phase B/C roles.

Usage:
  python3 modes/observe/cross_page.py \
      --metrics hci_1/metrics.json hci_2/metrics.json hci_3/metrics.json \
      --labels  "列表页" "详情页" "下单页" \
      --order-basis "filename:step1<step2<step3" \
      --business-goal "提升下单转化率" --goal-source prd \
      --out cross_page.json

Notes:
  * --metrics order = the (technique-inferred) page flow order. Caller must also
    pass --order-basis describing HOW the order was inferred, which is echoed into
    the output flagged as an inference (技能推测), per the red line.
  * --business-goal optional; --goal-source one of prd|user|inferred.
"""
import argparse
import json
import math
import os
import sys


def load_pages(paths):
    pages = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            m = json.load(f)
        pages.append({"path": p, "m": m})
    return pages


def top_hotspot(m):
    """Main heat peak (proxy for the page's dominant attention / main CTA landing)."""
    spots = m.get("attention_distribution", {}).get("hotspots", []) or []
    if not spots:
        return None
    return max(spots, key=lambda s: s.get("peak", 0))


def norm_dist(p1, p2, W, H):
    """Pixel distance between two points, normalized by the diagonal (0..1)."""
    diag = math.hypot(W, H) or 1.0
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1]) / diag


def variance(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return 0.0
    mean = sum(xs) / len(xs)
    return sum((x - mean) ** 2 for x in xs) / len(xs)


def metric_handoff_consistency(pages):
    """① 动线接力一致性: 上一页主热区落点 vs 下一页主热区落点的归一化距离。
    只给距离数值,不判好坏。"""
    steps = []
    for i in range(len(pages) - 1):
        a, b = pages[i]["m"], pages[i + 1]["m"]
        Wa, Ha = a.get("meta", {}).get("image_size", [0, 0])
        ha, hb = top_hotspot(a), top_hotspot(b)
        if not ha or not hb:
            steps.append({"from": i + 1, "to": i + 2, "handoff_distance_norm": None,
                          "note": "缺主热区,无法计算"})
            continue
        # 用上一页画布尺寸归一化(承接关系以离开页为参照)
        d = norm_dist((ha["cx"], ha["cy"]), (hb["cx"], hb["cy"]), Wa or 1, Ha or 1)
        steps.append({"from": i + 1, "to": i + 2,
                      "from_peak_xy": [ha["cx"], ha["cy"]],
                      "to_peak_xy": [hb["cx"], hb["cy"]],
                      "handoff_distance_norm": round(d, 3)})
    return steps


def metric_attention_decay(pages):
    """② 注意力衰减曲线: 逐页"核心入口可见性"序列。
    用 coverage.above_fold_attention_ratio 作为入口可见性代理。"""
    curve = []
    for i, pg in enumerate(pages):
        cov = pg["m"].get("coverage", {})
        v = cov.get("above_fold_attention_ratio")
        curve.append({"step": i + 1, "entry_visibility": v})
    deltas = []
    for i in range(1, len(curve)):
        a, b = curve[i - 1]["entry_visibility"], curve[i]["entry_visibility"]
        deltas.append(round(b - a, 3) if (a is not None and b is not None) else None)
    return {"curve": curve, "step_deltas": deltas}


def metric_style_coherence(pages):
    """③ 视觉风格连贯度: 跨页 信息密度/认知负荷/层级集中度 的波动(方差+极差)。
    波动数值本身是事实,不判'乱不乱'。"""
    loads = [pg["m"].get("cognitive_load", {}).get("composite_score") for pg in pages]
    ginis = [pg["m"].get("coverage", {}).get("attention_gini") for pg in pages]
    def rng(xs):
        xs2 = [x for x in xs if x is not None]
        return round(max(xs2) - min(xs2), 3) if len(xs2) >= 2 else 0.0
    return {
        "cognitive_load_series": loads,
        "cognitive_load_variance": round(variance(loads), 3),
        "cognitive_load_range": rng(loads),
        "attention_gini_series": ginis,
        "attention_gini_variance": round(variance(ginis), 4),
        "attention_gini_range": rng(ginis),
    }


def metric_path_depth(pages):
    """④ 路径深度与负荷累加: 步数 + 各页认知负荷累加。"""
    loads = [pg["m"].get("cognitive_load", {}).get("composite_score") or 0 for pg in pages]
    return {"path_steps": len(pages),
            "cognitive_load_sum": round(sum(loads), 1),
            "cognitive_load_avg": round(sum(loads) / len(pages), 1) if pages else 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", nargs="+", required=True,
                    help="per-page metrics.json paths, IN inferred flow order")
    ap.add_argument("--labels", nargs="*", default=[],
                    help="optional page labels, same order as --metrics")
    ap.add_argument("--order-basis", default="unknown",
                    help="how the page order was inferred (echoed as 技能推测)")
    ap.add_argument("--business-goal", default="")
    ap.add_argument("--goal-source", default="inferred",
                    choices=["prd", "user", "inferred"])
    ap.add_argument("--out", default="cross_page.json")
    args = ap.parse_args()

    if len(args.metrics) < 2:
        raise SystemExit("cross-page summary needs >=2 metrics.json (multi-interface only).")

    pages = load_pages(args.metrics)
    labels = args.labels + [f"页面{i+1}" for i in range(len(pages))]
    labels = labels[:len(pages)]

    out = {
        "kind": "cross_page_objective_summary",
        "measure_only": True,
        "judgement_note": ("此为跨页面客观度量,只测不判;'体验连贯/能否达成业务目标'"
                           "的判断归 Phase B 三角色 + Phase C 主持人。"),
        "page_count": len(pages),
        "page_labels": labels,
        "page_order": {
            "sequence": labels,
            "inferred": True,
            "inference_basis": args.order_basis,
            "warning": "⚠️ 页面顺序为技能推测,如有误请指正",
        },
        "business_goal": {
            "goal": args.business_goal or None,
            "source": args.goal_source,
            "warning": ("⚠️ 业务目标为推测" if args.goal_source == "inferred" and args.business_goal
                        else None),
        },
        "cross_page_metrics": {
            "handoff_consistency": metric_handoff_consistency(pages),
            "attention_decay": metric_attention_decay(pages),
            "style_coherence": metric_style_coherence(pages),
            "path_depth": metric_path_depth(pages),
        },
        # 业务目标对齐表: Phase A 只填客观列,judgement 列留空给角色
        "goal_alignment_table": [
            {"step": i + 1, "label": labels[i],
             "entry_visibility": pages[i]["m"].get("coverage", {}).get("above_fold_attention_ratio"),
             "cognitive_load": pages[i]["m"].get("cognitive_load", {}).get("composite_score"),
             "judgement": None}  # ← Phase B/C 角色在圆桌正文里填
            for i in range(len(pages))
        ],
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n[OK] cross-page summary -> {args.out} ({len(pages)} pages)", file=sys.stderr)


if __name__ == "__main__":
    main()
