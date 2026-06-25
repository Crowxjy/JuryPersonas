---
name: 商品卡评审
artifact_type: product-card
artifact_aliases:
  values:
    - 商品卡
default_personas:
  role_ids:
    - consumer-genz-female
    - ad-buyer
modes:
  required:
    - mode/product-card-extract
    - mode/jury-react
    - mode/aggregate-consensus
    - mode/render-report
  recommended:
    - mode/persona-pick
    - mode/heatmap
  optional:
    - mode/persona-sample
    - mode/persona-fit
    - mode/annotate-issues
    - mode/synthesize-tension
    - mode/synthesize-paths
    - mode/aggregate-distribution-gap
  forbidden:
    - mode/keyframe-extract
    - mode/prd-extract
    - mode/cross-page
    - mode/copy-extract
    - mode/design-extract
    - mode/screen-extract
    - mode/detail-page-extract
---

# 场景模板 · 商品卡评审

> 用于评审直播间小房子商品卡、信息流商品卡、列表页商品卡等短决策组件。v0.7 已接入 `mode/product-card-extract`,支持端到端执行。

---

## 一、输入

- 商品卡截图或结构化字段:标题、主图、价格、权益、销量/评价、CTA。
- 所在场景:直播间、搜索列表、推荐流、详情页内推荐等。
- 目标用户与转化目标。

商品卡必须提供至少一张截图或完整字段;只给商品名不足以评审。

---

## 二、默认评审重点

- **一眼识别**:是否看得懂卖什么。
- **差异利益点**:价格、权益、规格、限制是否清楚。
- **可信度**:评价、品牌、商家、销量等证据是否足够。
- **风险信息**:是否隐藏关键限制,是否容易误解。
- **行动诱因**:CTA 是否自然,是否显得套路或压迫。

---

## 三、输出要求

每位陪审员至少给出:

- 最先注意到的元素。
- 最可能卡住/误解的字段。
- 一条能直接改商品卡的建议。
- 一句边界声明:哪些信息因为截图/字段缺失不能判断。

---

## 四、边界

- 不根据商品卡单独判断完整交易体验。
- 不预测点击率/成交率绝对值。
- 不把商品卡之外的详情页信息脑补进来。
