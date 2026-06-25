---
name: 单/多界面评审
artifact_type: screen
modes:
  required:
    - mode/screen-extract
    - mode/jury-react
    - mode/aggregate-consensus
    - mode/render-report
  recommended:
    - mode/persona-pick
    - mode/heatmap
  optional:
    - mode/cross-page
    - mode/annotate-issues
    - mode/synthesize-tension
    - mode/synthesize-paths
    - mode/persona-sample
    - mode/persona-fit
    - mode/aggregate-distribution-gap
  forbidden:
    - mode/keyframe-extract
    - mode/prd-extract
    - mode/copy-extract
    - mode/design-extract
    - mode/detail-page-extract
    - mode/product-card-extract
---

# 场景模板 · 单/多界面评审

> 用于评审单张截图、页面截图组、关键流程截图。与 `review-design.md` 的区别:本场景更偏"已成型界面/流程"走查,设计稿场景更偏"设计方案"评审。v0.7 已接入 `mode/screen-extract`,支持端到端执行。

---

## 一、输入

- 单界面:一张截图 + 页面目标 + 目标用户。
- 多界面:按用户动线排序的多张截图 + 每张页面标签。
- 可选:semantic.json、HCI metrics.json、业务目标、已有问题清单。

如果多界面截图没有顺序,必须询问用户确认顺序;不得自行脑补完整动线。

---

## 二、默认评审问题

### 单界面

- 第一眼是否知道页面在做什么。
- 核心行动点是否在首屏或合理位置。
- 信息层级是否支持目标用户快速判断。
- 是否存在误导、暗黑模式、信任损耗或空态劝退。

### 多界面

- 页面间承接是否清楚。
- 上一页形成的预期是否被下一页兑现。
- 关键状态、对象、价格、权益是否跨页一致。
- 流程中哪一步最可能让用户停下或返回。

---

## 三、推荐 DAG

- 单界面默认: `mode/heatmap` → `mode/jury-react` → `mode/aggregate-consensus` → `mode/render-report`
- 多界面建议 include: `mode/cross-page`
- 如已有 semantic.json 和 issues.json,可 include: `mode/annotate-issues`
- 存在决策分歧时 include: `mode/synthesize-tension` + `mode/synthesize-paths`

---

## 四、边界

- 不预测点击率、转化率、留存率绝对值。
- 不把页面宣称的价值当作事实。
- 视觉观察与角色判断要分开:客观热区归 Observe,合理/不合理归 Jury。
