---
name: 详情页评审
artifact_type: detail-page
artifact_aliases:
  values:
    - 详情页
default_personas:
  role_ids:
    - consumer-bao-mom-tier2
    - local-business-expert
modes:
  required:
    - mode/detail-page-extract
    - mode/jury-react
    - mode/aggregate-consensus
    - mode/render-report
  recommended:
    - mode/persona-pick
    - mode/heatmap
    - mode/synthesize-tension
    - mode/synthesize-paths
  optional:
    - mode/persona-sample
    - mode/persona-fit
    - mode/cross-page
    - mode/annotate-issues
    - mode/aggregate-distribution-gap
  forbidden:
    - mode/keyframe-extract
    - mode/prd-extract
    - mode/copy-extract
    - mode/design-extract
    - mode/screen-extract
    - mode/product-card-extract
---

# 场景模板 · 详情页评审

> 用于评审商品详情页、POI 详情页、活动详情页、商家落地页等承载转化决策的页面。v0.7 已接入 `mode/detail-page-extract`,支持端到端执行。

---

## 一、输入

- 详情页截图或 URL。
- 商品/门店/服务的基本信息。
- 目标用户:消费者、商家、BD、内部决策层等。
- 当前最关心的问题:理解成本、信任、权益表达、转化、合规红线。

如果页面截图缺少价格、权益、核销规则、评价或 CTA 等关键区域,必须要求补充完整截图或页面链接。

---

## 二、默认评审重点

- **首屏判断**:用户是否能快速知道卖什么、适合谁、为什么可信。
- **权益与规则**:价格、优惠、套餐、核销、限制条件是否清楚且一致。
- **信任证据**:评价、案例、门店/品牌信息是否足够支撑行动。
- **CTA 路径**:按钮、咨询、收藏、下单等行动是否顺。
- **合规红线**:夸大宣传、挂 A 卖 B、价格/库存/规则不一致。

---

## 三、推荐 DAG

- 默认:`mode/heatmap` → `mode/jury-react` → `mode/aggregate-consensus` → `mode/synthesize-*` → `mode/render-report`
- 如果详情页属于多页漏斗,include `mode/cross-page`。
- 如果已有 semantic.json 与 issues.json,include `mode/annotate-issues`。

---

## 四、边界

- 不预测转化率绝对值。
- 不替用户裁决是否上线。
- 对页面没有展示的信息必须标成"缺失",不能按行业常识补齐。
