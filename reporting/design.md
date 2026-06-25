# JuryPersonas HTML 报告设计约束

本文件是报告渲染器的内置约束说明。根目录 `DESIGN.md` 只作为视觉资产参考;HTML 报告必须优先服务评审阅读和决策,不得照搬营销页 hero、摄影素材或 CTA 风格。

## 设计目标

1. 场景适配:报告结构由 `scenario` 和实际组合的 `mode` 决定,不使用固定通用模板硬套所有评审。
2. HTML 优先:本地最终产物优先生成 `.html`,Markdown 作为飞书/纯文本 fallback。
3. 行动在前:第一屏先展示行动优先级和张力/双路径状态;observe / HCI / 分布差异作为证据区支撑判断。
4. 决策分层:共识、分歧、张力、双路径、待办分别呈现,不把主持人总结写成裁决。
5. 边界显性:没有真实反馈数据、没有 MSI-Net 权重、使用 mock reaction 等限制必须在报告中可见。

## 视觉风格

- 字体:正文与中文标题必须中文优先,使用 `PingFang SC` / `Hiragino Sans GB` / `Microsoft YaHei` / `Noto Sans CJK SC`;`D-DIN` 只用于 mode badge、数值、代码等拉丁/数字局部。
- 页面宽度:最大 1200px,居中;黑色画布,高对比白字。
- 背景:纯黑 `{colors.canvas-night}` + 近黑 `{colors.canvas-night-soft}` 区块,不使用浅灰卡片底。
- 强调方式:不引入品牌色;只使用黑、白、近白、hairline。状态色只在必要字段中小面积使用。
- 标题:避免营销页超大 hero。中文标题行高不低于 1.2,字号使用 `clamp(28px,5vw,48px)` 级别,不做全大写或过宽字距。
- 表格:优先使用表格表达结构化信息;表头大写、小字号、hairline 分隔。
- 标签:mode、scenario、boundary 以 ghost outlined pill badge 展示。
- 装饰:不使用阴影、重度渐变背景、左侧彩色边框卡片或 emoji;状态色只用于 score bar 和风险提示。
- 证据:禁止大段 JSON 直接常开铺满页面;长 JSON 使用可折叠区和最大高度。
- 图片:HCI 标注图、热力图等本地产物必须可在 HTML 中直接预览。

## 内容规则

1. 不出现“结论先行”“一句话总结”这类字面标题;直接把判断写在段落开头。
2. 不预测转化率、点击率、完播率等绝对值。
3. HCI 指标只陈述预测性客观观察,不替代真实眼动。
4. `mode/aggregate-distribution-gap` 没有真实反馈数据时,只说分布差异,不说真实效果。
5. 使用 mock reaction 时必须声明其为本地回归桩。

## 场景布局

| 场景 | HTML 布局 |
|---|---|
| 短视频 | 行动优先级 → 陪审结果 → 时间轴/关键帧观察 |
| PRD | 行动优先级 → 张力/双路径状态 → 需求结构与决策风险 |
| 设计稿/单界面 | 行动优先级 → HCI/结构观察 → 可理解性与体验断点 |
| 详情页/商品卡 | 行动优先级 → 价格/权益/规则 → 信任证据与转化阻力 |
| 营销文案 | 行动优先级 → 文案结构 → claim/evidence/CTA/risk |
| 含 distribution-gap | 增配/降配人群表必须进入证据区 |
| 含 heatmap/cross-page/annotate | HCI 观察区必须前置 |
