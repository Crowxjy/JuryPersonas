---
name: jury-personas
description: 陪审团画像 Skill。当用户需要对 PRD/设计稿/界面/短视频/详情页/营销文案做评审时使用本 Skill。先通过 Brief Workshop 收集需求(评估对象、目标受众、关心维度、是否有真实分布),再按场景推荐原子模式 DAG(客观度量/陪审反应/聚合/张力归纳/报告渲染),最后优先产出场景/Mode 自适应 HTML 报告,并保留 Markdown/DocxXML;飞书发布默认 dry-run,显式 --lark-execute 时用 DocxXML 走 lark-doc v2 创建。陪审团由专家画像 + 消费者画像 + BD/管理者画像组成,支持手写/切片自动构建/临时拟合/分布采样四种生成方式;专家经 method_lens 挂载方法卡与确定性工具。触发词:陪审、评审、Jury、流失评审、短视频评审、PRD 评审、设计评审、群体评审、用户视角评审。
---

# Jury Personas · 陪审团画像 Skill

> **隐喻**:陪审团 (Jury) 而非辩论赛。陪审员独立判断、不互相说服;主持人只汇总、不裁决;客观证据先行、主观反应后置。

## 一、五大组件

| 组件 | 目录 | 作用 |
|---|---|---|
| ① **需求 Brief** | `brief/` + `core/contracts/brief.schema.json` | 调用前先收集足够信息,防止幻觉编造 |
| ② **知识 Knowledge** | `knowledge/` | 行业知识 + 术语 + 切片标注库 + 方法卡(可挂确定性工具),跨画像共享 |
| ③ **画像 Persona** | `personas/` | 陪审员画像(专家/消费者/BD)+ 临时拟合;专家经 `method_lens` 挂方法 |
| ④ **场景 Scenario** | `scenarios/` | 评估对象的评审 SOP,声明可用模式列表 |
| ⑤ **模式 Mode** | `modes/` | 原子能力,按场景 DAG 组合调用 |

### 顶层目录速览

| 目录 | 作用 |
|---|---|
| `brief/` | 需求收集与充分性判定(组件①) |
| `knowledge/` | 行业知识 / 术语 / 切片库 / 方法卡(组件②) |
| `personas/` | 专家 / 消费者 / BD 陪审员画像(组件③) |
| `scenarios/` | 各评估对象的评审 SOP,单一事实源(组件④) |
| `modes/` | observe / jury / aggregate / synthesize / render 原子能力(组件⑤) |
| `orchestrator/` | 编排:Brief → 场景/DAG 规划 → 分阶段执行 |
| `reporting/` | 报告渲染:HTML 优先 + Markdown / DocxXML + 飞书发布 |
| `tools/` | 回归 / 校验 / handoff / 方法工具 / 真实视频证据流水线 |
| `core/` | JSON 契约与提示词(brief harness、Phase C) |
| `evals/` | 真实对照评测集骨架 |
| `assets/` | 可选模型权重(MSI-Net,按需下载) |
| `docs/` | 架构与维护文档 |

> 仅列顶层目录定位;文件级明细随代码演进,需要时用 `git ls-files` 现扫。

## 二、原子模式清单

| 模式 | 输入 | 输出 |
|---|---|---|
| `mode/heatmap` | 截图 | 注意力热力图 + HCI 指标 |
| `mode/cross-page` | 多张截图 | 跨页面动线 |
| `mode/annotate-issues` | 截图 + semantic.json + issues.json | 页面问题红框标注图 |
| `mode/keyframe-extract` | 关键帧 JSON / storyboard / `tools/video_evidence` 真实抽帧 artifact | 规范化关键帧 + 时序切片;排除 `observed:false` 推断帧 |
| `mode/prd-extract` | PRD Markdown/文本 | 结构化标题/需求/风险/指标/待确认 |
| `mode/copy-extract` | 营销文案 Markdown/文本 | 结构/利益点/证据/CTA/风险词/渠道线索 |
| `mode/design-extract` | 设计稿 Markdown/文本/JSON 描述 | 页面结构/CTA/信任证据/缺失字段 |
| `mode/screen-extract` | 单/多界面 Markdown/文本/JSON 描述 | 页面结构/流程规则/行动点/风险词 |
| `mode/detail-page-extract` | 详情页 Markdown/文本/JSON 描述 | 价格权益/规则/信任证据/CTA |
| `mode/product-card-extract` | 商品卡 Markdown/文本/JSON 描述 | 字段结构/价格优惠/证明/CTA |
| `mode/persona-fit` | 切片+标签 JSON | 临时画像 |
| `mode/persona-sample` | 联合分布 | N 个采样陪审员 |
| `mode/persona-pick` | 角色 ID 列表 | 指定陪审员 + system_prompt 包(含方法卡注入) |
| `mode/jury-react` | 陪审员清单 + 待评对象 | 各陪审员独立陈述 |
| `mode/aggregate-consensus` | reactions[] | 共识/分歧/流失点热力 |
| `mode/aggregate-distribution-gap` | reactions[] + 双分布 | 双分布 gap |
| `mode/synthesize-tension` | 分歧[] | 核心张力 + 决策偏好因子 |
| `mode/synthesize-paths` | 张力 + 偏好因子 | 🅰/🅑 双决策路径 |
| `mode/render-report` | 全部产物 | HTML 优先 + Markdown/DocxXML + lark-doc v2 发布预览/创建 |

## 三、当前真实入口

```bash
# Skill 正式使用:由宿主 Agent/模型按 core/prompts/brief_harness.md 收集 Brief,
# 信息充分后写入 brief.json,再调用本地脚本。

# 顶层本地执行入口;不传 --personas 时使用场景默认陪审团组合
python3 jury_review.py --brief <brief.json> --artifact <artifact> --personas <role_id,...>

# 只做 Brief → Scenario/DAG plan
python3 orchestrator/pipeline.py --brief-file <brief.json>

# 执行完整本地回归链路;--personas 可省略
python3 orchestrator/pipeline.py --brief-file <brief.json> --artifact-file <artifact> --personas <role_id,...> --execute

# 宿主 Agent/模型正式回填流
python3 tools/reaction_handoff.py --bundle-file <bundle.json> --export-prompts <dir>
python3 tools/reaction_handoff.py --bundle-file <filled_bundle.json> --check-filled
python3 orchestrator/pipeline.py --brief-file <brief.json> --filled-bundle-file <filled_bundle.json>

# 资产/健康检查
python3 tools/persona_dedupe.py --json
python3 tools/lint.py
```

### 真实短视频证据准备(可选)

```bash
VIDEO_URL=https://www.douyin.com/video/<aweme_id> \
WORK=$HOME/.session/<sid>/douyin_run \
bash tools/video_evidence/run_douyin_realframe_pipeline.sh
```

该流水线只负责取真实 `play_addr`、下载视频、抽帧、抽音和 ASR,并生成
`artifact.realframe.json`。抽帧图片为 `observed:true`;若画面描述为空,宿主
Agent/多模态模型必须先查看图片并补 `frame_descriptions.json`,否则 jury-react
会要求陪审员承认"画面看不清",不能脑补画面。

## 四、Brief 充分性判定 Harness

⚠️ **本 Skill 调用规则(对接入 Agent 的硬约束)**:

收到任何评审请求时,**必须先按 [core/prompts/brief_harness.md](core/prompts/brief_harness.md) 收集需求**,产出符合 [core/contracts/brief.schema.json](core/contracts/brief.schema.json) 的结构化判断。

充分性判断由调用本 Skill 的 Agent 大模型完成,本 Skill 提供:

1. **必备字段清单**(5 项,语义判据)
2. **一致性约束**(字段间逻辑自洽)
3. **边界共识**(4 条边界,首次会话强制声明)
4. **输出契约**(Agent 必须吐结构化 JSON,含 evidence/verdict/next_action)

orchestrator 会回查 evidence 是否在用户上下文可匹配,**杜绝伪造证据**。详见 [docs/architecture-v0.2.md §9.1](docs/architecture-v0.2.md)。

## 五、防幻觉硬约束(全 Skill 强制)

1. Brief Harness 未 SUFFICIENT,**不得**进入 observe/react 等下游阶段
2. 下游引用 brief 字段时**必须** `evidence: ["brief.field_x"]` 标注
3. 临时拟合画像 (`_fit_*`) 与 draft 画像在每次回答末尾**必须**加保真度声明
4. 评估视角"流失"模式下,**禁止**输出"会不会喜欢"类不可证伪结论
5. **禁止**预测完播率/转化率绝对值
6. 圆桌阶段每个陪审员**独立陈述**,不互相参考
7. 主持人**只汇总不裁决**,Phase C 给🅰/🅑 双路径不替选

## 六、Quickstart

```bash
# 一条命令贯穿 brief → DAG → 模式 → 报告
python3 jury_review.py \
  --brief tests/fixtures/short_video_demo/brief.json \
  --artifact tests/fixtures/short_video_demo/artifact.json \
  --personas consumer-bao-mom-tier2,consumer-silver-male,consumer-bluecollar-male \
  --runtime-dir /tmp/jp_m3
```

### 宿主 Agent/模型回填流程

```bash
# 1) 先跑 observe/persona/jury-react,停在 bundle
python3 orchestrator/pipeline.py \
  --brief-file tests/fixtures/prd_demo/brief.json \
  --artifact-file tests/fixtures/prd_demo/prd.md \
  --personas product-expert,ad-buyer \
  --execute --no-mock-llm \
  --runtime-dir /tmp/jp_host_agent

# 可选:拆出每位陪审员的独立 prompt,方便宿主 Agent/模型逐个读取
python3 tools/reaction_handoff.py \
  --bundle-file /tmp/jp_host_agent/reactions/<sid>.bundle.json \
  --export-prompts /tmp/jp_host_agent/prompts \
  --pretty

# 2) 宿主 Agent/模型回填 /tmp/jp_host_agent/reactions/<sid>.bundle.json
#    中的 participants[*].reaction

# 可选:校验 filled bundle 是否已经可恢复执行
python3 tools/reaction_handoff.py \
  --bundle-file /path/to/<sid>.filled.json \
  --check-filled \
  --pretty

# 3) 从 filled bundle 恢复 aggregate → synthesize → report
python3 orchestrator/pipeline.py \
  --brief-file tests/fixtures/prd_demo/brief.json \
  --execute \
  --filled-bundle-file /path/to/<sid>.filled.json \
  --runtime-dir /tmp/jp_host_agent_final
```

### 本地回归

```bash
python3 tools/regression.py \
  --runtime-root /tmp/jp_regression \
  --pretty
```

覆盖:Python 语法、画像 lint、seed 评测集、画像重叠扫描、7 类场景 DAG plan、短视频 e2e、PRD e2e、设计稿/单界面/详情页/商品卡 e2e、营销文案 e2e、HCI heatmap/annotate e2e、persona-fit/persona-sample/distribution-gap execute、宿主 Agent/模型 handoff 导出/校验/恢复、reaction 缺失防护。

### 正式 Skill 使用流

宿主 Agent/模型正式执行时按 [docs/host-agent-workflow.md](docs/host-agent-workflow.md) 走:

1. Brief Harness 判定信息充分。
2. `pipeline.py --execute --no-mock-llm` 生成 observe/persona 产物和 jury-react bundle。
3. `reaction_handoff.py --export-prompts` 拆出每位陪审员独立 prompt。
4. 宿主 Agent/模型逐个回填 `participants[*].reaction`。
5. `reaction_handoff.py --check-filled` 校验完整性。
6. `pipeline.py --filled-bundle-file` 恢复 aggregate/synthesize/report。

产物落 `<runtime-dir>/{reactions,consensus,reports}/<session_id>.*`:
- `reactions/<sid>.bundle.json` — jury-react 多人 prompt 包
- `reactions/<sid>.filled.json` — mock responder 或宿主 Agent/模型回填后的 reactions
- `consensus/<sid>.json` — 共识/分歧/5 维矩阵
- `reports/<sid>.html` — 场景/Mode 自适应 HTML 报告(优先阅读)
- `reports/<sid>.md` — Markdown fallback 报告
- `reports/<sid>.docx.xml` — 飞书 DocxXML;`--lark-execute` 时用于 lark-doc v2 创建
- `publish` JSON 字段 — 默认 `DRY_RUN`;真发布失败时为 `PUBLISH_FAILED`

⚠️ 本地回归默认走 `mock_llm_responder` 测试桩;正式使用时由宿主 Agent/模型回填 reaction。

## 七、对齐设计文档

- 完整架构: [docs/architecture-v0.2.md](docs/architecture-v0.2.md)
- 宿主 Agent/模型使用流: [docs/host-agent-workflow.md](docs/host-agent-workflow.md)
- 专家方法/工具维度(method_lens + 方法卡 + 确定性工具): [docs/expert-method-tool-dimension.md](docs/expert-method-tool-dimension.md)
- 真实评测集: [evals/README.md](evals/README.md)
- 画像合并决策包: [docs/persona-merge-decision.md](docs/persona-merge-decision.md)
- 运行依赖与可选资产: [docs/runtime-assets.md](docs/runtime-assets.md)
- 迁移指南: [docs/migration-guide.md](docs/migration-guide.md)
- 模式 cookbook: [docs/mode-cookbook.md](docs/mode-cookbook.md)
