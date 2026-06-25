---
name: 设计稿评审
artifact_type: design
modes:
  required:
    - mode/design-extract
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
    - mode/screen-extract
    - mode/detail-page-extract
    - mode/product-card-extract
---

# 场景模板 · 设计稿评审

> 用于评审 Figma/Sketch/PNG/JPG 等设计稿。v0.7 已接入 `mode/design-extract`,支持 Markdown/文本/JSON 设计描述的端到端执行;图片像素级指标仍交给 HCI observe 模式。

---

## 一、输入

- 评审对象:设计稿链接、导出的界面截图,或多张页面截图。
- 目标用户/业务场景:必须明确,不能只说"用户"。
- 关注维度:体验合理性、转化、信息架构、可理解性、决策建议等。

> 若只有设计稿但没有目标用户或任务场景,Brief Harness 必须回到 ASK_USER,不得直接评审。

---

## 二、推荐 DAG 说明

1. `mode/heatmap`:对单张或关键截图生成 HCI 客观观察。
2. `mode/jury-react`:专家/用户/BD 陪审员独立判断。
3. `mode/aggregate-consensus`:聚合共识、分歧与风险点。
4. `mode/synthesize-tension` + `mode/synthesize-paths`:当分歧足够明确时产出两条决策路径。
5. `mode/render-report`:输出报告。

多页设计稿可显式 include `mode/cross-page`;已有 semantic.json 与问题清单时可 include `mode/annotate-issues`。

---

## 三、评审输出约束

每位陪审员应输出:

- 直觉反应:第一眼是否理解页面目标。
- 任务路径:用户从进入页面到完成核心动作是否顺畅。
- 信息层级:主信息、次信息、行动点是否清晰。
- 风险点:误解、劝退、遗漏、信任损耗。
- 改进建议:必须可执行,不能只说"优化体验"。

---

## 四、边界

- 不预测转化率/点击率绝对值。
- 不把设计稿自带文案当作事实成立,设计稿本身就是被评估对象。
- HCI 热力图是预测性客观观察,不是眼动实测。
- 主持人只汇总,不裁决是否上线。
