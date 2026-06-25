---
name: 营销文案评审
artifact_type: marketing-copy
modes:
  required:
    - mode/copy-extract
    - mode/jury-react
    - mode/aggregate-consensus
    - mode/render-report
  recommended:
    - mode/persona-pick
    - mode/synthesize-tension
    - mode/synthesize-paths
  optional:
    - mode/persona-sample
    - mode/persona-fit
    - mode/aggregate-distribution-gap
  forbidden:
    - mode/keyframe-extract
    - mode/prd-extract
    - mode/heatmap
    - mode/cross-page
    - mode/annotate-issues
---

# 场景模板 · 营销文案评审

> 用于评审朋友圈、小红书、短信、push、落地页文案、直播口播文案等以文字说服为主的素材。v0.6 已接入 `mode/copy-extract`,支持 `orchestrator --execute` 端到端执行。

---

## 一、输入

- 文案全文或文件路径。
- 发布渠道与触达时机。
- 目标人群。
- 希望用户采取的动作。

如果只给一句口号,必须追问渠道和目标动作;不同渠道的可接受语气差异很大。

---

## 二、默认评审重点

- **开头吸引力**:第一句是否让目标人群愿意继续读。
- **利益表达**:是否说清楚具体收益,而不是空泛形容。
- **信任与证据**:有没有证明、场景、限制条件。
- **语气匹配**:是否像目标人群愿意接受的表达。
- **行动引导**:CTA 是否明确、自然、低摩擦。
- **红线风险**:极限词、虚假承诺、诱导分享、医疗/金融等敏感表达。

---

## 三、输出要求

每位陪审员至少输出:

- 读完第一反应。
- 最劝退的一句话或缺失的信息。
- 最可保留的一句话。
- 三条改写建议,其中至少一条必须是具体改写示例。

---

## 四、边界

- 不预测转化率、打开率、点击率绝对值。
- 不脱离渠道评价语气。
- 不把目标人群没有确认的痛点强行写进建议。
