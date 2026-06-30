#!/usr/bin/env python3
"""
break_even_calc.py — deterministic break-even calculator for the
`break_even` method card (knowledge/methods/break_even.md).

它只做方法卡明确写出的计算,不做方法卡没规定的判断:
  - 核心公式(方法卡原文): 盈亏平衡营业额 = 固定成本 / 毛利率
  - 固定成本(方法卡原文): 房租 + 人工 + 水电/燃气/损耗
  - 月→日折算: 方法卡只说"折算到每天",未给天数 → days 为显式参数(默认 30,标注 assumption)
  - 一次性投入摊销: 方法卡列了加盟费/装修/设备但未给回本周期 → 仅当同时给出
    capex 与 amortize_months 才并入,否则不并入(不替用户假设回本周期)
  - 证据强度(高/中/低) 与 主要杠杆: 方法卡只列字段未给判定规则 → 不自动评级,
    输出留空并标注 needs_manual_judgement,交宿主 Agent/专家人工填

用法:
    python3 tools/methods/break_even_calc.py --input case.json --pretty
    echo '{"rent_monthly":12000,...}' | python3 tools/methods/break_even_calc.py --stdin

输入 JSON 字段:
    rent_monthly            房租/月(必填,数值,可为 0)
    labor_monthly           人工/月(必填)
    utility_monthly         水电/燃气/损耗/月(必填)
    gross_margin_pct        毛利率(%)(必填,>0,否则按方法卡红线拒算)
    daily_revenue           实际/预计日营业额(可选;给了才算差距)
    days_per_month          月折算天数(可选,默认 30,assumption)
    one_time_capex          一次性投入总额(可选)
    amortize_months         摊销月数(可选;仅当与 capex 同时给出才并入)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ["rent_monthly", "labor_monthly", "utility_monthly", "gross_margin_pct"]


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compute_break_even(payload: dict[str, Any]) -> dict[str, Any]:
    """Pure function. Returns a JSON-serializable result with full calc trace."""
    errors: list[str] = []
    warnings: list[str] = []

    rent = _num(payload.get("rent_monthly"))
    labor = _num(payload.get("labor_monthly"))
    utility = _num(payload.get("utility_monthly"))
    margin_pct = _num(payload.get("gross_margin_pct"))
    daily_revenue = _num(payload.get("daily_revenue"))
    capex = _num(payload.get("one_time_capex"))
    amortize_months = _num(payload.get("amortize_months"))

    days = _num(payload.get("days_per_month"))
    days_is_default = days is None
    if days is None:
        days = 30.0

    # 方法卡红线: 没有毛利率不得硬算
    if margin_pct is None or margin_pct <= 0:
        errors.append(
            "缺少有效毛利率(gross_margin_pct>0)。方法卡明确:『没有毛利率就硬算』属常见误用,拒绝计算。"
        )
    if days <= 0:
        errors.append("days_per_month 必须 > 0。")

    # 固定成本三项缺失视为 0 但提示(方法卡: 不能漏人工房租)
    for field, val in (("rent_monthly", rent), ("labor_monthly", labor), ("utility_monthly", utility)):
        if val is None:
            warnings.append(f"{field} 未提供,已按 0 计入;方法卡提醒不要漏算人工/房租。")

    if errors:
        return {
            "mode": "tool/break-even-calc",
            "status": "REFUSED",
            "errors": errors,
            "warnings": warnings,
            "boundary": _boundary(),
        }

    rent = rent or 0.0
    labor = labor or 0.0
    utility = utility or 0.0

    monthly_fixed = rent + labor + utility
    daily_fixed = monthly_fixed / days

    calc_trace = [
        f"月固定成本 = 房租 {rent:g} + 人工 {labor:g} + 水电燃气损耗 {utility:g} = {monthly_fixed:g}",
        f"日固定成本(不含一次性投入) = {monthly_fixed:g} ÷ {days:g} 天 = {daily_fixed:.2f}",
    ]

    # 一次性投入: 仅当 capex 与 amortize_months 同时有效才并入
    capex_included = False
    daily_capex = 0.0
    if capex and capex > 0:
        if amortize_months and amortize_months > 0:
            daily_capex = capex / amortize_months / days
            daily_fixed += daily_capex
            capex_included = True
            calc_trace.append(
                f"一次性投入摊入/天 = {capex:g} ÷ {amortize_months:g} 月 ÷ {days:g} 天 = {daily_capex:.2f}（assumption: 摊销月数由用户给定）"
            )
            calc_trace.append(f"日固定成本(含摊销) = {daily_fixed:.2f}")
        else:
            warnings.append(
                f"已填一次性投入 {capex:g} 元,但未填 amortize_months → 未并入日成本,避免擅自假设回本周期。"
            )

    margin = margin_pct / 100.0
    break_even_daily = daily_fixed / margin
    calc_trace.append(
        f"保本营业额/天 = {daily_fixed:.2f} ÷ {margin:.4g}(毛利率) = {break_even_daily:.2f}"
    )

    result: dict[str, Any] = {
        "mode": "tool/break-even-calc",
        "status": "OK",
        "inputs_normalized": {
            "rent_monthly": rent,
            "labor_monthly": labor,
            "utility_monthly": utility,
            "gross_margin_pct": margin_pct,
            "daily_revenue": daily_revenue,
            "days_per_month": days,
            "one_time_capex": capex,
            "amortize_months": amortize_months,
        },
        "assumptions": {
            "days_per_month": {
                "value": days,
                "is_default": days_is_default,
                "note": "方法卡只说『折算到每天』未给天数;此为可调假设,非方法卡规定。",
            },
            "capex_amortization": {
                "included": capex_included,
                "daily_capex": round(daily_capex, 2) if capex_included else None,
                "note": "方法卡未规定回本周期;仅在用户同时给出 capex 与 amortize_months 时并入。",
            },
        },
        "break_even_daily_revenue": round(break_even_daily, 2),
        "daily_fixed_cost": round(daily_fixed, 2),
        "monthly_fixed_cost": round(monthly_fixed, 2),
        "calc_trace": calc_trace,
        "gap": None,
        "needs_manual_judgement": {
            "evidence_strength": None,   # 方法卡: 高/中/低,无判定规则 → 留空待人工
            "main_levers": [],           # 候选: 降成本/提客流/改品/提价/止损,触发条件方法卡未给
            "note": "证据强度与主要杠杆方法卡未给判定阈值,工具不自动评级,由宿主 Agent/专家填写。",
        },
        "warnings": warnings,
        "boundary": _boundary(),
    }

    if daily_revenue is not None:
        gap_daily = daily_revenue - break_even_daily
        gap_monthly = gap_daily * days
        result["gap"] = {
            "daily_revenue": daily_revenue,
            "gap_daily": round(gap_daily, 2),
            "gap_monthly": round(gap_monthly, 2),
            "status": "盈余" if gap_daily >= 0 else "亏损",
        }
        result["calc_trace"].append(
            f"每日差距 = 日营业额 {daily_revenue:g} − 保本 {break_even_daily:.2f} = {gap_daily:+.2f}（{'盈余' if gap_daily>=0 else '亏损'}）"
        )
        result["calc_trace"].append(
            f"每月差距 = 每日差距 × {days:g} 天 = {gap_monthly:+.2f}"
        )
    else:
        result["warnings"].append("未提供 daily_revenue → 不计算差距,仅给保本线。")

    return result


def _boundary() -> dict[str, Any]:
    return {
        "source": "knowledge/methods/break_even.md",
        "deterministic_only": True,
        "method_card_note": "盈亏平衡只能说明账面生死线,不能证明口味、品牌长期价值或经营者执行力。",
        "common_misuse": [
            "没有毛利率就硬算",
            "只算平台订单,不算人工和房租",
            "把一次性投入当成不存在",
            "用『感觉客流会起来』替代真实营业额",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic break-even calculator (break_even method card)")
    parser.add_argument("--input", help="Input JSON file path")
    parser.add_argument("--stdin", action="store_true", help="Read input JSON from stdin")
    parser.add_argument("--out", help="Output JSON path; default stdout")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.stdin:
        raw = sys.stdin.read()
    elif args.input:
        raw = Path(args.input).read_text(encoding="utf-8")
    else:
        print("ERROR: 需要 --input <file> 或 --stdin", file=sys.stderr)
        return 2

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: 输入不是合法 JSON: {e}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("ERROR: 输入 JSON 顶层必须是对象", file=sys.stderr)
        return 2

    result = compute_break_even(payload)
    text = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)
    # REFUSED 也属正常退出(不是崩溃),用 0;调用方按 status 字段判断
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
