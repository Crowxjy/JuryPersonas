---
id: break_even
name: 盈亏平衡测算
artifact_types: [prd, design, screen, detail-page, product-card, marketing-copy, short-video]
tool:
  path: tools/methods/break_even_calc.py
  desc: 确定性盈亏平衡计算器。输入 JSON(房租/人工/水电/毛利率等),输出保本营业额、日/月差距与计算过程;缺毛利率会拒算。
  usage: "python3 tools/methods/break_even_calc.py --stdin --pretty  (或 --input case.json)"
  input_fields: rent_monthly, labor_monthly, utility_monthly, gross_margin_pct, daily_revenue?, days_per_month?, one_time_capex?, amortize_months?
---

# 盈亏平衡测算

## 适用场景

用于判断门店、活动、团购、开店方案或经营工具是否能覆盖基础成本。

## 必要输入

- 日营业额或预计订单量
- 毛利率
- 房租
- 人工
- 水电/燃气/损耗
- 额外投入:加盟费、装修、设备、投流、达人、平台佣金

## 操作步骤

1. 把月成本折算到每天。
2. 计算固定成本:房租 + 人工 + 水电/燃气/损耗。
3. 计算 `盈亏平衡营业额 = 固定成本 / 毛利率`。
4. 对比实际或预计日营业额。
5. 判断差距来自客流不足、毛利过低、房租过高、人效过低还是一次性投入过重。

## 输出格式

- 保本线:每天至少卖多少。
- 当前差距:每天差多少、每月亏多少。
- 主要杠杆:降成本、提客流、改品、提价、止损。
- 证据强度:高/中/低。

## 常见误用

- 没有毛利率就硬算。
- 只算平台订单,不算人工和房租。
- 把一次性投入当成不存在。
- 用"感觉客流会起来"替代真实营业额。

## 边界

盈亏平衡只能说明账面生死线,不能证明口味、品牌长期价值或经营者执行力。

