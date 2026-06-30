---
version: 1.0
name: Linear-Inspired-report-design
description: JuryPersonas 报告与展示页的视觉参考资产。以 Linear 的深色信息面板语言为基准——近黑画布、克制的中性灰阶面板、单一靛蓝强调色、等宽数字、细线分隔、低饱和语义色。区别于营销页:不做大屏 hero、不堆撞色、不用 emoji,服务的是决策者快速扫读结构化结论。本文件是视觉参考;可执行的报告约束以 reporting/design.md 为准,当两者冲突时以 design.md 为事实源。

colors:
  bg: "#08090a"
  bg-elev: "#0e0f11"
  panel: "#141517"
  panel-2: "#191b1e"
  line: "#232629"
  line-soft: "#1c1e21"
  text: "#f7f8f8"
  text-2: "#b3b8bf"
  text-3: "#7c828a"
  accent: "#6e79d6"
  accent-soft: "rgba(110,121,214,0.12)"
  risk: "#e5484d"
  warning: "#f5a623"
  positive: "#46a758"

typography:
  sans: "-apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, Hiragino Sans GB, Microsoft YaHei, Noto Sans CJK SC, sans-serif"
  mono: "SF Mono, ui-monospace, JetBrains Mono, Menlo, monospace"
  hero:
    fontSize: 30-42px
    fontWeight: 680
    lineHeight: 1.2
    letterSpacing: -0.02em
  section:
    fontSize: 21px
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: -0.01em
  body:
    fontSize: 14-15px
    fontWeight: 400
    lineHeight: 1.6
  small:
    fontSize: 12-13px
    fontWeight: 400
    lineHeight: 1.5
    color: text-3
  mono-num:
    fontFamily: mono
    use: 数字、评分、mode/scenario badge、代码与日志

radius:
  sm: 8px
  md: 12px
  lg: 16px
  pill: 999px

spacing:
  base: 8px
  tokens: [4, 8, 12, 16, 24, 32, 48]
  page-max-width: 920px
  page-gutter: 24px
---

# JuryPersonas 报告视觉参考(Linear 风格)

本文件是视觉参考资产。可执行的报告渲染约束以 [reporting/design.md](design.md) 为准;当二者冲突时,以 design.md 为事实源。报告样式当前写死在 [html_renderer.py](html_renderer.py),本文件用于人读对照与后续迭代基线。

## 总览

Linear 风格是一种"信息面板"语言:近黑画布上用克制的中性灰阶面板分层,单一靛蓝色 `{colors.accent}` 只用于焦点与关键数字,语义色只对应风险/警告/正向状态。它不依赖图片堆砌或大字号 hero,信息密度服务决策阅读。

**关键特征:**
- 单一近黑画布 `{colors.bg}`(`#08090a`),面板用 `{colors.panel}` / `{colors.panel-2}` 分层。
- 唯一品牌强调色 `{colors.accent}`(`#6e79d6`),只用于焦点、关键数字、当前状态;不大面积铺。
- 细线分层:`{colors.line}` / `{colors.line-soft}`,靠闭合细线和面板嵌套表达层级,不用重投影、不单侧描边。
- 等宽数字:评分、占比、badge、代码与日志统一用 `{typography.mono}`,便于扫读对齐。
- 禁用 emoji;需要图标时用 inline SVG。
- 不做营销页大屏 hero;页面最大宽 `{spacing.page-max-width}` 居中。

## 颜色

### 画布与面板
- **Bg** (`{colors.bg}` — `#08090a`):页面基底,近黑。
- **Bg Elev** (`{colors.bg-elev}` — `#0e0f11`):顶栏/微抬升区。
- **Panel** (`{colors.panel}` — `#141517`):主信息面板。
- **Panel 2** (`{colors.panel-2}` — `#191b1e`):面板内的次级分区。
- **Line** (`{colors.line}` — `#232629`):面板与分区的主要细线。
- **Line Soft** (`{colors.line-soft}` — `#1c1e21`):更弱的内部分隔线。

### 文本
- **Text** (`{colors.text}` — `#f7f8f8`):主文本/标题。
- **Text 2** (`{colors.text-2}` — `#b3b8bf`):次级文本、表头。
- **Text 3** (`{colors.text-3}` — `#7c828a`):描述、编号、路径、辅助说明。

### 强调与语义
- **Accent** (`{colors.accent}` — `#6e79d6`):唯一品牌强调色,只用于焦点、关键数字、当前状态、强调边框。
- **Accent Soft** (`{colors.accent-soft}`):强调底色,用于 tag / 高亮面板边框。
- **Risk / Warning / Positive** (`#e5484d` / `#f5a623` / `#46a758`):只对应风险、警告、正向状态,不当装饰色用。

## 字体

- **无衬线栈** `{typography.sans}`:正文与标题,中文优先。
- **等宽栈** `{typography.mono}`:数字、评分、mode/scenario badge、代码、日志、路径。
- **层级**:Hero 30–42px / 区块标题 21px / 正文 14–15px / 辅助 12–13px。
- **中文行高不得低于 1.15**;标题用轻微负字距(`-0.01em ~ -0.02em`)。
- 不使用 D-DIN、Arial Narrow 等条窄工业体或全大写 display(那是已废弃的 SpaceX 风格,会与本风格冲突)。

## 形状与间距

- **圆角**:`{radius.sm}` 8px(chip/小卡)· `{radius.md}` 12px(主面板)· `{radius.lg}` 16px(舞台容器)· `{radius.pill}` 胶囊(chip/tag)。
- **间距基数** 8px,常用 token `{spacing.tokens}`。
- **页面**:最大宽 `{spacing.page-max-width}` 居中,左右留白 `{spacing.page-gutter}` 24px。

## 层级与深度

- 用面板嵌套 + 闭合细线 + 极弱 radial-gradient 表达层级。
- 禁止:重投影、外发光、大面积撞色块、单侧描边。
- 表格优先表达结构化信息;表头用深色面板和小字号,数据值保持易扫读。

## Do / Don't

### Do
- 近黑画布 + 中性灰阶面板分层;强调色只点在焦点和关键数字上。
- 评分、占比、badge 一律等宽数字,并解释分值区间与含义,不只给均值。
- 业务可读标签前置(评审类型、目标人群、参与角色数、视频时长、平台);mode/scenario 等技术标签只进折叠附录。
- 长 JSON / 日志用可折叠区 + 最大高度,不常开铺满页面。

### Don't
- 不引入第二个品牌强调色;不大面积铺 accent。
- 不用 emoji;不用重投影/渐变叠层装饰。
- 不用全大写 display、不用条窄工业体(SpaceX/D-DIN 风格已废弃)。
- 不做营销页大屏 hero,不堆装饰图。
- 不把 DAG、mode、bundle、mock_llm_responder、raw JSON 作为主内容裸露。

## 迭代指引

1. 颜色/字体/间距 token 以本文件 frontmatter 为人读基准,代码实现在 [html_renderer.py](html_renderer.py)。
2. 修改视觉时,先改 design.md 的执行约束,再同步 token 到本文件与渲染器,避免三处漂移。
3. 新增组件按"面板 + 细线 + 等宽数字"的语言扩展,保持单一强调色规则。
