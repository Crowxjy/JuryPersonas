# JuryPersonas · 架构设计 v0.2

> 项目代号：**Jury Personas**（陪审团画像 Skill）
> 目标：把 `EAgents`（消费者群体流失评审）+ `expert-roundtable`（专家深度评审 + HCI 客观度量）合并为一个**面向 PM/设计/内容/运营的通用陪审团 Skill**。
> 路径：`/Users/bytedance/Documents/trae_projects/JuryPersonas`
> 形态：**单仓库 monorepo**

---

## 一、定位（一句话）

> Jury Personas 是一个**陪审团模拟 Skill**——面对任意"待评估对象"（PRD、设计稿、界面、短视频、详情页、商品卡、营销文案……），先帮用户**澄清需求场景 → 推荐合适的陪审团组合 → 跑客观度量底座 → 召开陪审 → 产出决策建议**。

**核心隐喻：陪审团 (Jury) 而非辩论赛。** 陪审员独立判断、不互相说服；主持人只汇总、不裁决；客观证据先行、主观反应后置。

---

## 二、五大核心组件（保持你强调的「知识 / 画像 / 场景 / 模式」+ 新增「需求」）

| 组件 | 是什么 | 对应目录 | 新增点 |
|---|---|---|---|
| ① **需求 (Brief)** | 用户调用 Skill 时的需求结构化抽取（评估什么、给谁看、关心什么、有没有约束） | `brief/` + `core/contracts/brief.schema.json` | ⭐ 全新组件，强制信息收集，防幻觉 |
| ② **知识 (Knowledge)** | 行业知识、术语、产品知识、切片标注库 | `knowledge/` | 双源（手写 + 切片自动构建） |
| ③ **画像 (Persona)** | 陪审员画像，覆盖专家/消费者/BD/管理者 + 临时拟合 | `personas/` | ⭐ 多种生成方式 + 画像合并机制 |
| ④ **场景 (Scenario)** | 评估对象的评审 SOP（PRD / 短视频 / 单界面 / 详情页 ……） | `scenarios/` | 每个场景显式声明"可用模式列表" |
| ⑤ **模式 (Mode)** | 原子可组合的执行能力：客观度量、采样、独立陈述、聚合、张力归纳…… | `modes/` | ⭐ **不再有 expert/crowd/mixed 三个固化模式**，改为原子能力 |

---

## 三、关键变更点（v0.1 → v0.2）

### 3.1 模式去固化：原子能力 + 场景 DAG（新设计）

v0.1 的「expert / crowd / mixed」三种模式被砍掉，改为 **19 个原子模式**，每个原子模式做且只做一件事：

| 原子模式 | 输入 | 输出 | 来源项目 |
|---|---|---|---|
| `mode/heatmap` | 截图 | 注意力热力图 + HCI 4 指标 | expert-roundtable |
| `mode/cross-page` | 多张截图 | 跨页面动线指标 | expert-roundtable |
| `mode/annotate-issues` | 截图 + semantic.json + issues.json | 单页问题红框标注图 | expert-roundtable |
| `mode/keyframe-extract` | 视频 | 关键帧 + 时序切片 | ⭐ 新（短视频专用） |
| `mode/prd-extract` | PRD 文档 | 结构化目标/差异点/红线 | ⭐ 新 |
| `mode/copy-extract` | 营销文案 | 结构/利益点/证据/CTA/风险词/渠道线索 | ⭐ 新 |
| `mode/design-extract` | 设计稿描述 | 页面结构/CTA/信任证据/缺失字段 | ⭐ 新 |
| `mode/screen-extract` | 单/多界面描述 | 页面结构/流程规则/行动点/风险词 | ⭐ 新 |
| `mode/detail-page-extract` | 详情页描述 | 价格权益/规则/信任证据/CTA | ⭐ 新 |
| `mode/product-card-extract` | 商品卡描述 | 字段结构/价格优惠/证明/CTA | ⭐ 新 |
| `mode/persona-fit` | 切片+标签 JSON | 临时画像 | EAgents |
| `mode/persona-sample` | 联合分布 | N 个采样陪审员 | EAgents |
| `mode/persona-pick` | 角色 ID 列表 | 指定陪审员 | 共有 |
| `mode/jury-react` | 陪审员清单 + 待评对象 + observation | 各陪审员独立陈述（5 字段流失表 OR reasonable/unreasonable） | 合并 |
| `mode/aggregate-consensus` | reactions[] | 共识/分歧/流失点热力 | 合并 |
| `mode/aggregate-distribution-gap` | reactions[] + 双分布 | F6 双分布 gap | EAgents |
| `mode/synthesize-tension` | 分歧[] | 核心张力 + 决策偏好因子 | expert-roundtable |
| `mode/synthesize-paths` | 张力 + 偏好因子 | 🅰/🅑 双决策路径 | expert-roundtable |
| `mode/render-report` | 上述全部 | 飞书 XML / Markdown 报告 | 合并 |

**场景 = 模式 DAG + 默认陪审团**：每个 [scenarios/*.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/scenarios) 在 frontmatter 声明自己**输入别名、默认角色、必跑/推荐/可选/禁止**的模式。`orchestrator/dag.py` 只负责读取这些声明并排序,执行层不再按 scenario 追加隐藏 mode。

```yaml
# scenarios/review-short-video.md (示例)
---
name: 短视频成片评审
artifact_type: short-video
artifact_aliases:
  values:
    - 短视频
default_personas:
  role_ids:
    - consumer-bao-mom-tier2
    - consumer-silver-male
    - consumer-bluecollar-male
modes:
  required:                  # 必跑(用户不可跳过)
    - mode/keyframe-extract
    - mode/jury-react
    - mode/aggregate-consensus
    - mode/render-report
  recommended:               # 默认跑(用户可关)
    - mode/persona-sample     # crowd 视角(对短视频天然适合)
    - mode/persona-fit
  optional:                  # 默认不跑(用户可开)
    - mode/persona-pick       # 想加几位专家旁听
    - mode/heatmap            # 对关键帧跑
    - mode/aggregate-distribution-gap
    - mode/synthesize-tension
  forbidden:                 # 禁用(避免误用)
    - mode/cross-page         # 不适用单条视频
---
```

**用户调用时**：Skill 先按 artifact_type/alias 选择场景,再按场景的 `required` + `recommended` 给出默认 DAG,让用户加减原子模式 → 形成**该次评审的执行计划** → 执行。

---

### 3.2 画像生成方式（多源 + 合并）

⭐ **画像支持 4 种生成方式**，用 frontmatter `source.kind` 明确标记：

| source.kind | 含义 | 维护成本 | 保真度 |
|---|---|---|---|
| `handcraft` | 手写画像（基于真实素材打磨） | 高 | 高 ✅ |
| `slice-built` | 由切片标注库自动构建（多维表格 → md） | 低 | 中-高 ✅ |
| `fit-synthesized` | 切片+标签即时合成（一次性） | 极低 | 低 ⚠️ |
| `pool-sampled` | 联合分布采样产物（一次性） | 极低 | 中 |

⭐ **画像合并机制（新）**：当多源画像描述同一类陪审员时，用 `merge_into` 字段声明合并目标：

```yaml
# personas/consumers/consumer-genz-female.md
---
id: consumer-genz-female
source:
  kind: handcraft
  origin: handwritten by 用研团队 2026-06
merge_with:           # ⭐ 此画像可吸收的同类切片源
  - knowledge/slices/consumer_genz.md       # slice-built 同源
fingerprint:           # ⭐ 用于去重检测
  category: 消费者
  age_band: 18-24
  gender: 女
  city_tier: 1-2
  signature_tags: [Z世代, 女, 一二线]
---
```

`tools/persona_dedupe.py` 扫描所有画像的 `fingerprint`，发现冲突时给出三种处理：
- **合并** → 把 slice-built 的切片块作为 imports 挂到 handcraft 主画像上
- **共存** → 显式声明区别（如同为 Z 世代但分一线/三线）
- **替换** → 较低保真度的让位（fit < pool < slice < handcraft）

---

### 3.3 需求收集流程（Brief Phase，⭐ 新增）

**Skill 接到任何评审请求时，必须先跑 Brief Phase，禁止直接进 Observe**。

`brief/brief_collector.md` 定义 **Workshop 三轮交互协议**（沿用 expert-roundtable 的"三问 + 编号选项"，但分轮）：

#### Round 1：评估对象 + 受众（必填）
```
我需要先和您确认 4 件事(请用编号回复或自由回答):

1. 这次评审的对象是什么?
   ① PRD 文档  ② 设计稿/界面截图  ③ 短视频成片
   ④ 详情页/商品卡  ⑤ 营销文案  ⑥ 其他(请描述)

2. 这份产物是给谁看的最终用户?
   ① 普通消费者(请说人群:_____)
   ② 商家/合作伙伴
   ③ 内部决策层(老板/总监)
   ④ 设计/产品同事
   ⑤ 其他

3. 您当前最关心什么?
   ① 用户会不会被劝退/流失
   ② 设计/逻辑是不是合理
   ③ 转化效果好不好
   ④ 决策怎么走(给我决策建议)
   ⑤ 综合评估

4. 有没有客观数据可以喂?
   ① 有真实分布(商家客群/品类) → 提供 JSON 路径
   ② 没有 → 用 mock 或纯主观
```

#### Round 2：场景 DAG 确认（必填）
基于 R1 答案推荐场景 + 默认 DAG，让用户增删原子模式。

#### Round 3：边界声明确认（必填）
显式告知用户：
- 本次评审**不会**预测转化率/完播率绝对值
- 本次评审**不会**裁决"该不该上线"，只给路径
- 临时拟合画像/draft 画像会带保真度声明
- 缺失关键素材时**会主动要求补齐**而非脑补

⚠️ **防幻觉硬约束**：Brief Phase 收集到的所有信息必须落到 `.runtime/briefs/<session_id>.json`，下游 Phase 引用 brief 字段时必须显式 `evidence: ["brief.field_x"]`，**禁止脑补未在 brief 中出现的信息**。

---

## 四、目录结构（v0.2 最终版）

```
JuryPersonas/
├── SKILL.md                          # 顶层 Skill 入口(命令清单 + 五大组件总览)
├── README.md                         # 维护者指南
├── requirements.txt
├── assets/                           # 模型权重(MSI-Net)
│   └── msinet_tf/
│
├── core/                             # 公共契约层
│   ├── contracts/
│   │   ├── brief.schema.json         # ⭐ 需求结构化
│   │   ├── observation.schema.json   # Phase A 输出
│   │   ├── reaction.schema.json      # 陪审员独立陈述
│   │   ├── decision.schema.json      # 决策建议
│   │   ├── persona.schema.json       # 画像 frontmatter
│   │   ├── scenario.schema.json      # 场景 frontmatter
│   │   ├── mode.schema.json          # ⭐ 原子模式接口
│   │   └── distribution.schema.json
│   └── prompts/                      # 公共 prompt 片段
│       ├── critical_stance.md        # 批判立场(专家用)
│       ├── churn_lens.md             # 流失视角(消费者用)
│       ├── fit_fidelity.md           # 拟合保真度声明
│       └── no_hallucination.md       # ⭐ 防幻觉硬约束
│
├── brief/                            # ⭐ 需求收集
│   ├── brief_collector.md            # Workshop 三轮交互协议
│   ├── brief_inferrer.py             # 从用户原始 query 半自动抽取 brief
│   └── brief_validator.py            # 校验 brief.schema.json 完整性
│
├── knowledge/                        # 知识库(双源)
│   ├── industry/                     # 手写行业知识
│   │   ├── ad-investment.md
│   │   ├── short-video-creation.md
│   │   └── ux-design-process.md
│   ├── glossary/                     # 术语词典
│   ├── product/
│   └── slices/                       # ⭐ 切片自动构建
│       ├── shared.md
│       ├── product_expert.md
│       ├── ad_buyer.md
│       ├── local_business.md
│       └── consumer_*.md
│
├── personas/                         # 画像库(按 kind + 角色类型分)
│   ├── _template.md                  # 通用模板
│   ├── _fingerprint_index.json       # ⭐ 自动维护的指纹索引(去重用)
│   ├── _merge_decisions.json         # ⭐ 已确认的画像合并决策
│   ├── experts/                      # 专家陪审员
│   │   ├── ad-buyer.md               # ⭐ 统一广告投手画像(默认入口)
│   │   ├── ad-buyer-expert.md        # legacy expert-roundtable source
│   │   ├── ad-buyer-senior.md        # legacy JuryPersonas source
│   │   ├── product-expert.md
│   │   ├── local-business-expert.md
│   │   └── ux-designer-senior.md
│   ├── consumers/                    # 消费者陪审员
│   │   ├── consumer-genz-female.md   # role_kind: user_persona
│   │   ├── consumer-bao-mom-tier2.md
│   │   ├── consumer-silver-male.md
│   │   └── consumer-bluecollar-male.md
│   ├── bd/                           # BD/管理者陪审员
│   │   ├── ka-bd-*.md
│   │   └── ...
│   └── _ephemeral/                   # ⭐ 临时画像(.gitignored)
│       ├── _fit_*.md                 # mode/persona-fit 产物
│       └── _sample_*.md              # mode/persona-sample 产物
│
├── scenarios/                        # 场景模板(按"评估对象"分)
│   ├── review-prd.md
│   ├── review-design.md
│   ├── review-screen.md              # 单/多界面
│   ├── review-short-video.md
│   ├── review-detail-page.md
│   ├── review-product-card.md
│   ├── review-marketing-copy.md
│   └── review-design-poc-protocol.md
│
├── modes/                            # ⭐ 原子模式实现
│   ├── observe/
│   │   ├── heatmap.py                # mode/heatmap
│   │   ├── cross_page.py             # mode/cross-page
│   │   ├── annotate_issues.py        # mode/annotate-issues
│   │   ├── keyframe_extract.py       # ⭐ mode/keyframe-extract
│   │   └── prd_extract.py            # ⭐ mode/prd-extract
│   ├── jury/
│   │   ├── compile_persona.py
│   │   ├── persona_fit.py            # mode/persona-fit
│   │   ├── persona_sample.py         # mode/persona-sample
│   │   ├── persona_pick.py           # mode/persona-pick
│   │   └── jury_react.py             # mode/jury-react
│   ├── aggregate/
│   │   ├── consensus.py              # mode/aggregate-consensus
│   │   └── distribution_gap.py       # mode/aggregate-distribution-gap
│   ├── synthesize/
│   │   ├── tension.py                # mode/synthesize-tension
│   │   ├── paths.py                  # mode/synthesize-paths
│   │   └── churn_vs_review.py        # F7 待做
│   └── render/
│       └── report.py                 # mode/render-report
│
├── orchestrator/                     # ⭐ 主调度器
│   ├── pipeline.py                   # 接 brief → 编排场景 DAG → 执行 / handoff 恢复
│   ├── dag.py                        # 从 scenario frontmatter + 用户调整 → 执行计划
│   ├── stage_runner.py               # 执行各 mode 并落运行产物
│   ├── reporting_stage.py            # 拼装 report_data 并渲染多格式报告
│   ├── artifacts.py                  # 评审对象加载 + 输入路径解析
│   ├── command_runner.py             # 子进程执行与日志
│   └── bootstrap.py                  # Skill 脚本路径初始化
│
├── reporting/                        # 报告渲染层
│   ├── templates/
│   │   └── report_video_xml.md       # 短视频 Markdown 报告模板
│   ├── lark_renderer.py
│   ├── html_renderer.py              # HTML 优先的本地报告
│   ├── docx_xml_renderer.py
│   └── markdown_renderer.py
│
├── data/                             # 预留本地数据目录;空目录不作为 Skill 必需文件
│   ├── distributions/
│   │   ├── _mock/
│   │   └── _real/
│   ├── slice_snapshots/
│   └── feedback/
│
├── tools/                            # 工程化脚本
│   ├── lint.py
│   ├── feedback_handler.py
│   ├── build_knowledge_base.py       # 切片库 → knowledge/slices/
│   ├── persona_dedupe.py             # ⭐ 画像指纹去重 + 合并提示
│   └── sync_skill.sh
│
├── tests/
│   └── fixtures/                     # regression/evaluation 使用的稳定 fixture
│
├── docs/                             # ⭐ 设计文档
│   ├── architecture-v0.2.md          # 本文件
│   ├── migration-guide.md            # 从 EAgents/expert-roundtable 迁移
│   └── mode-cookbook.md              # 各场景常用 DAG 配方
│
└── .runtime/                         # .gitignored
    ├── briefs/                       # ⭐ Brief Phase 产物
    ├── observations/
    ├── reactions/
    ├── decisions/
    └── reports/
```

---

## 五、统一调用入口（当前真实入口）

```bash
# Skill 正式使用:宿主 Agent/模型先按 core/prompts/brief_harness.md 收集 Brief。

# 顶层本地执行入口
python3 jury_review.py --brief <brief.json> --artifact <artifact> --personas <role_id,...>

# 底层编排入口
python3 orchestrator/pipeline.py --brief-file <brief.json> --artifact-file <artifact> --personas <role_id,...> --execute

# 资产/健康检查
python3 tools/persona_dedupe.py --json
find scenarios -maxdepth 1 -name 'review-*.md' | sort
find modes -maxdepth 3 -name '*.py' | sort
python3 tools/lint.py
```

**核心调用流程**：

```
宿主 Agent/模型触发 Skill
  ↓
core/prompts/brief_harness.md (语义充分性判断)
  ↓ 写 .runtime/briefs/<sid>.json
orchestrator/pipeline.py
  ↓ 推荐场景 + DAG → 用户调整 → 锁定执行计划
orchestrator/pipeline.py
  ↓ 顺序/并行调用 modes/*
mode/heatmap → mode/keyframe-extract → ... → mode/jury-react → ...
  ↓ 各阶段产物落 .runtime/
mode/render-report
  ↓
飞书 wiki / Markdown 报告 (用户拿走)
```

---

## 六、关键设计原则（汇总）

1. **五大组件分离**（知识 / 画像 / 场景 / 模式 / 需求），每个组件独立演进
2. **模式原子化、场景组合化**：场景 = 原子模式的 DAG，不固化套餐
3. **画像多源共存**：handcraft / slice-built / fit / pool 四种 kind，用 fingerprint 去重合并
4. **需求先行、防止幻觉**：所有评审必须先 Brief，下游引用必须 evidence 标注
5. **客观先行、主观后置**：Phase B 陪审员开口前必须吃到 Phase A observation
6. **只评不裁、只给路径**：Phase B 角色不互相说服，Phase C 给🅰/🅑 不替选
7. **保真度自带声明**：fit/draft 画像在每次回答末尾必标
8. **契约驱动**：跨阶段全 JSON Schema，模式可单测、可替换、可并行

---

## 七、迁移路线（六步走，1 周内）

| 步 | 工作量 | 依赖 | 内容 |
|---|---|---|---|
| **S1**·骨架 | 0.5 天 | - | 在 `JuryPersonas/` 建空目录 + `core/contracts/*.schema.json` + 顶层 SKILL.md 草稿 |
| **S2**·EAgents 迁入 | 0.5 天 | S1 | `personas/consumer-*` → `personas/consumers/`；`personas/*-bd-*` `am-*` `ka-*` → `personas/bd/`；`scripts/sample_personas.py` 拆 → `modes/jury/persona_sample.py` 等 |
| **S3**·expert-roundtable 迁入 | 1 天 | S1 | 三专家 → `personas/experts/`；`scripts/generate_heatmap.py` → `modes/observe/heatmap.py`；Phase C 文档 → `modes/synthesize/` + `core/prompts/` |
| **S4**·Brief + Orchestrator | 1.5 天 | S1-3 | 写 `brief/brief_collector.md`、`orchestrator/dag.py`、`orchestrator/pipeline.py` |
| **S5**·画像去重 + 切片融合 | 1 天 | S2-3 | `tools/persona_dedupe.py` + `_fingerprint_index.json` 自动维护；`tools/build_knowledge_base.py` 接入 |
| **S6**·端到端 case + 文档 | 1 天 | S1-5 | 3 个 case：①短视频 crowd ②单界面 expert ③详情页混合；写 `docs/migration-guide.md` + `docs/mode-cookbook.md` |

---

## 八、给原作者的协作提议（合并谈判要点）

如果要拉 expert-roundtable 作者一起做：

1. **保留双方仓库现状**：JuryPersonas 是新仓库，原仓库不动，按 git subtree / submodule 引入历史
2. **代码归属**：`modes/observe/*` 大头来自 expert-roundtable，`modes/jury/persona_*` 大头来自 EAgents，commit 历史保留
3. **PRD 对齐**：双方各保留各自原 PRD，新仓库写一份合并 PRD（明确什么场景走 crowd、什么走 expert）
4. **维护边界**：知识库（手写 + 切片）由原 expert-roundtable 团队主导；画像谱系（消费者 + BD）由原 EAgents 团队主导；场景/模式/orchestrator 共建

---

## 九、关键决策（已锁定 → 进入 MVP）

| # | 决策 | 设计落地 |
|---|---|---|
| 1 | **Brief 跳过条件**：只有宿主 Agent/模型判断上下文已收集到足够信息才能跳过 | ⭐ 不再用已有 brief 文件或分数阈值这种"形式跳过";改为按 [core/prompts/brief_harness.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/core/prompts/brief_harness.md) 逐项给出 evidence/verdict/next_action,由 orchestrator 做结构与证据回查（详见 9.1） |
| 2 | **画像合并冲突**：让用户决定 | `tools/persona_dedupe.py` 仅输出冲突报告 + 推荐策略，**不自动合并**；用户拍板后通过 `jury persona merge --left A --right B --strategy ...` 显式执行 |
| 3 | **MVP 先做最简方案** | ⭐ MVP 范围收紧到 5 个原子模式（详见 9.2），其余暂停 |
| 4 | **MVP 报告通道**：先飞书报告 | `reporting/lark_renderer.py` 优先实现，Markdown renderer 进 v0.3 |

### 9.1 Brief 充分性判定 Harness（决策 1 落地）

**核心原则**：充分性判断是**语义理解问题**，不是**算分问题**。我们不写打分公式，而是把判断权交给调用本 Skill 的 Agent 大模型，由我们提供一份强约束的 Harness 让它**逐项检视、结构化输出**，并在缺信息时强制澄清。

#### Harness = 三类约束的合集

##### ① 必备字段清单（Required Fields Checklist）
Agent 必须逐项确认以下信息是否在上下文中明确出现（不允许"差不多/可能是"）：

| 字段 | 充分的标准（Agent 检视判据） | 不充分的反例 |
|---|---|---|
| `artifact_type` | 用户**明确说出**评估对象类别（短视频成片/PRD/单界面/详情页/商品卡/营销文案/其他），或**给出可识别的文件后缀**（.mp4 / .md / .png 等） | "帮我看看这个东西"、"评一下我的方案" |
| `artifact_locator` | 上下文中存在**可定位的素材**：本地绝对路径 / URL / 已粘贴的内容片段 / 已确认稍后会提供 | "我有一个视频"但没给路径 |
| `target_audience` | **明确指明产物的目标受众人群**（消费者细分/商家/内部决策层/同事），或用户已确认走"通用人群" | "用户"这种泛指 |
| `key_concern` | **明确说出最关心的问题**（流失/转化/合理性/决策建议/综合评估），或用户已确认走"综合" | 默认或推测 |
| `distribution_intent` | **明确表态**：① 提供真实分布 JSON；② 用 mock 分布；③ 不需要采样（走指定专家） | 没问没说 |

⚠️ **判据写得越严格，Agent 越不容易"温柔通过"**。每条标准都用"明确"两字防止 Agent 用宽松解读绕过。

##### ② 一致性约束（Consistency Constraints）
即便上面 5 个字段都填了，Agent 还要确认它们之间逻辑自洽：

- 如果 `artifact_type=短视频`，`artifact_locator` 必须是视频文件 / 视频链接 / 关键帧 + 文案，**不能是纯文字描述**
- 如果 `key_concern=流失`，`target_audience` 不能是"内部决策层"（流失视角对内部无意义）
- 如果 `distribution_intent=真实分布`，必须有可访问的 JSON 路径或可识别的商家 ID
- 如果 `target_audience` 与 `personas/` 现有谱系无任何匹配（如要评 to B SaaS 给 IT 经理看），Agent 必须额外确认是否需要 `mode/persona-fit` 临时合成

不一致时 Agent 必须挑出冲突点向用户澄清，**不允许默默调和**。

##### ③ 边界共识（Boundary Acknowledgement）
Agent 在宣布"信息已足"前，必须确认用户已知悉以下边界（首次会话至少出现一次）：

- 本 Skill **不会预测**完播率/转化率绝对值
- 本 Skill **不会裁决**"该不该上线"，只给路径
- 临时拟合画像 / draft 画像在每次发言末尾会有保真度声明
- 缺关键素材时**会主动要求补齐**，不脑补

如果用户首次调用且这三条都没明示讨论过，Agent 必须显式声明这些边界并等用户确认。

#### Agent 判定输出契约

Agent 在每一轮收集后必须输出以下结构化判断（落 [.runtime/briefs/<sid>.json](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/.runtime/briefs)），交给 orchestrator 决定下一步：

```json
{
  "session_id": "...",
  "round": 1,
  "fields": {
    "artifact_type":       {"value": "短视频", "evidence": "用户原话: ...", "sufficient": true},
    "artifact_locator":    {"value": null,    "evidence": null,           "sufficient": false},
    "target_audience":     {"value": "三线小龙虾店消费者", "evidence": "用户原话: ...", "sufficient": true},
    "key_concern":         {"value": "流失",  "evidence": "用户原话: ...", "sufficient": true},
    "distribution_intent": {"value": "mock",  "evidence": "用户原话: ...", "sufficient": true}
  },
  "consistency_check": {
    "passed": true,
    "conflicts": []
  },
  "boundary_ack": {
    "no_absolute_metrics_predicted": true,
    "no_go_no_go_decision": true,
    "fit_fidelity_disclaimer": true,
    "ask_dont_hallucinate": true
  },
  "verdict": "INSUFFICIENT",
  "verdict_reason": "artifact_locator 字段缺失,无法定位评审素材",
  "next_action": {
    "kind": "ASK_USER",
    "questions": [
      "请提供评审素材路径(本地视频文件绝对路径 / 视频 URL / 或粘贴关键帧+文案)"
    ]
  }
}
```

#### orchestrator 的硬约束（防 Agent 偷懒）

`orchestrator/pipeline.py` 在进入下一阶段前必须强制校验：

| 校验项 | 失败行为 |
|---|---|
| `verdict` ∈ `{SUFFICIENT, INSUFFICIENT}` | 抛错，不允许其他值 |
| 所有 `fields[*].sufficient=true` 才允许 `verdict=SUFFICIENT` | 强制返回 ASK_USER |
| `consistency_check.passed=true` 才允许 `verdict=SUFFICIENT` | 强制返回 ASK_USER |
| `boundary_ack` 全 true 才允许首次会话 `verdict=SUFFICIENT` | 强制让 Agent 补充边界声明 |
| `fields[*].evidence` 必须是用户上下文中可回溯的原话或路径 | 触发"伪造证据"告警 |

⚠️ **核心思路**：Agent 拥有判断的"语义能力"，Harness 拥有"形式约束"。Agent 不能跳过任何字段、不能拍脑袋，**也不能伪造 evidence**——orchestrator 拿到 JSON 后会回查 evidence 是否真的能在上下文中匹配到。

#### 跳过 Workshop 的唯一路径

只有当 Agent 输出的 JSON 满足 **全部 5 字段 sufficient=true + consistency_check.passed + boundary_ack 全 true** 时，orchestrator 才允许跳过 Workshop 直接进 DAG 推荐，但**必须先输出"已自动判定的 brief 摘要"让用户一键确认/修改**（避免 Agent 误判）。


### 9.2 MVP 范围（决策 3 落地）

**MVP 目标**：跑通"短视频成片评审"这一条最有差异化的端到端链路。

#### MVP 包含
| 组件 | 内容 |
|---|---|
| Brief | brief_collector + brief_inferrer（基础版） |
| 知识 | 沿用 EAgents 现有 `knowledge/`，**不引入切片自动构建** |
| 画像 | 沿用 EAgents 现有 `personas/`（消费者 4 + BD 9 + UX 1），**仅迁不重构**；专家画像迁入 1 个（product-expert）做混合 demo |
| 场景 | **只做 `review-short-video.md`**，其余 v0.3 |
| 模式 | **5 个原子模式** |
| 报告 | 飞书 wiki 渲染（沿用 EAgents 第一轮飞书文档生成路径） |

#### MVP 5 个原子模式
1. `mode/persona-fit`（迁自 EAgents `fit_persona.py`）
2. `mode/persona-sample`（迁自 EAgents `sample_personas.py`）
3. `mode/jury-react`（用 LLM 跑陪审反应，先按 review-short-video 的 5 字段输出）
4. `mode/aggregate-consensus`（流失点热力 + 反应矩阵）
5. `mode/render-report`（→ 飞书 wiki，沿用本会话第一轮的 lark-cli docs +create 路径）

#### MVP 不包含（推迟到 v0.3+）
- ❌ `mode/heatmap`、`mode/cross-page`、`mode/annotate-issues`（HCI 客观度量层）
- ❌ `mode/keyframe-extract`、`mode/prd-extract`
- ❌ `mode/synthesize-tension`、`mode/synthesize-paths`（Phase C 决策透镜）
- ❌ 切片自动构建 `tools/build_knowledge_base.py`
- ❌ 画像合并 `tools/persona_dedupe.py`（只做基础 lint 校验，冲突检测留 v0.3）
- ❌ Markdown renderer
- ❌ Phase A 完整客观底座（短视频评审 MVP 阶段先纯主观跑）

### 9.3 MVP 迁移路线（重排，从 6 步压到 3 步 · 2-3 天）

| 步 | 工作量 | 状态 | 内容 |
|---|---|---|---|
| **M1**·骨架 + 迁移 | 1 天 | ✅ 完成 | 建 JuryPersonas 目录骨架，把 EAgents 全量迁入（personas/ knowledge/ scenarios/review-short-video.md / scripts → modes/jury+tools）；脚本路径推导改为 `parent.parent.parent`，画像查找改 `rglob` 适配 `personas/{experts,consumers,bd}/` 子目录 |
| **M1.5**·expert-roundtable 迁入（局部） | 0.5 天 | ✅ 部分完成（仅画像） | 已迁：`personas/experts/product-expert.md`（314 行）+ `knowledge/slices/product_expert.md`（443 行，与上游 byte-identical）；lint 17 画像 0 error。剩余资产（HCI 度量层 / Phase C 决策透镜 / references 文档 / MSI-Net 权重）**v0.3 必须迁入**，详见 9.3.1 |
| **M2**·Brief + Orchestrator | 1 天 | ✅ 完成 | 已落 [brief/brief_collector.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/brief/brief_collector.md)（Workshop 三轮协议）+ [brief/brief_inferrer.py](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/brief/brief_inferrer.py)（5 字段半自动抽取）+ [brief/brief_validator.py](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/brief/brief_validator.py)（五重校验）+ [orchestrator/pipeline.py](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/orchestrator/pipeline.py)（按场景 frontmatter modes 字段构建 DAG，含 stage_priority 排序 + include/exclude override） |
| **M3**·飞书报告 + 端到端验证 | 0.5-1 天 | ✅ 完成 | 已落 [tools/mock_llm_responder.py](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/tools/mock_llm_responder.py)（M3 桩,3 角色差异化假 reaction）+ [modes/aggregate/consensus.py](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/modes/aggregate/consensus.py)（共识/分歧/5 维矩阵抽取）+ [modes/render/report.py](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/modes/render/report.py) + [reporting/templates/report_video_xml.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/reporting/templates/report_video_xml.md) + [reporting/lark_renderer.py](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/reporting/lark_renderer.py)（默认 dry-run 预览;`--lark-execute` 用 DocxXML 走 lark-doc v2 真创建,失败不伪降级）+ orchestrator [pipeline.py --execute](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/orchestrator/pipeline.py) 升级为执行器 + 顶层入口 [jury_review.py](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/jury_review.py)。短视频端到端冒烟通过:9 complaints / 3 consensus / 3 divergence / 5 维矩阵 / 8.5KB 报告 |

### 9.3.1 expert-roundtable 迁入清单（M1.5 已迁 + v0.3 必迁）

合并目标的另一半项目（[github.com/wuhaadesign/expert-roundtable](https://github.com/wuhaadesign/expert-roundtable)）资产分两批迁入：

| 资产 | 来源 | 落地位置 | 状态 | 阻塞 MVP |
|---|---|---|---|---|
| 专家画像 `product-expert.md` | `references/phase_b_roundtable/experts/product-expert/SKILL.md` | [personas/experts/product-expert.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/personas/experts/product-expert.md) | ✅ M1.5 已迁 | 否 |
| 切片库 `product_expert/knowledge_base.md` | `references/phase_b_roundtable/experts/product-expert/knowledge_base.md` | [knowledge/slices/product_expert.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/knowledge/slices/product_expert.md) | ✅ M1.5 已迁（byte-identical） | 否 |
| 专家画像 `ad-buyer-expert.md` + 切片库 | `references/phase_b_roundtable/experts/ad-buyer-expert/*` | [personas/experts/ad-buyer-expert.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/personas/experts/ad-buyer-expert.md) + [knowledge/slices/ad_buyer.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/knowledge/slices/ad_buyer.md) | ✅ v0.3 已迁（byte-identical） | 否 |
| 专家画像 `local-business-expert.md` + 切片库 | `references/phase_b_roundtable/experts/local-business-expert/*` | [personas/experts/local-business-expert.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/personas/experts/local-business-expert.md) + [knowledge/slices/local_business.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/knowledge/slices/local_business.md) | ✅ v0.3 已迁（byte-identical） | 否 |
| HCI 度量脚本 `generate_heatmap.py`（MSI-Net） | `scripts/generate_heatmap.py` | `modes/observe/heatmap.py` | ✅ v0.3 已迁,默认模型路径改为 `assets/msinet_tf/` | 否（9.2 明确 MVP 不含 HCI） |
| MSI-Net 模型权重说明 | `assets/README_model_weights.md` | `assets/msinet_tf/README_model_weights.md` + `.gitkeep` | ✅ v0.3 已迁（权重本体仍 gitignored） | 否 |
| 跨页/问题标注脚本 | `scripts/cross_page_summary.py` `scripts/annotate_issues.py` | `modes/observe/cross_page.py` `modes/observe/annotate_issues.py` | ✅ v0.3 已迁 | 否 |
| Phase C 决策透镜协议（张力归纳/双路径） | `references/phase_c_decision/*.md` | `core/prompts/phase_c/` + `modes/synthesize/{tension.py,paths.py}` | ✅ v0.3 已迁 | 否（MVP 报告先纯主观陪审） |
| `references/` 系列流程文档（PoC 协议、专家 system prompt、integration 同步） | `references/{integration,phase_a_hci,phase_b_roundtable,phase_c_decision}/` | `docs/references-from-expert-roundtable/` | ✅ v0.3 已迁（`diff -qr` 0 差异） | 否 |
| 共享切片层 `shared/knowledge_base.md` | `references/phase_b_roundtable/experts/shared/knowledge_base.md` | `knowledge/slices/shared.md` | ✅ v0.3 已迁（688 行 / 390090 bytes / byte-identical） | 否 |
| 切片自动构建脚本 `build_knowledge_base.py` | `scripts/build_knowledge_base.py` | `tools/build_knowledge_base.py` | ✅ v0.3 已迁,输出适配 `knowledge/slices/*.md` | 否 |

**M1.5 决策**（用户表态："A，但后续该迁还是要迁"）：
- ✅ M1.5 仅迁 `product-expert.md` + 配套切片库（让专家陪审谱系 ad-buyer / ux-designer / product-expert 三足成形），避免 MVP 范围回扩
- ✅ v0.3 已把表格中硬承诺资产迁入；剩余工作是端到端回归、lint 与安装说明同步

### 9.4 v0.3+ 路线（MVP 之后）

- **v0.3（合并硬承诺）：迁入 expert-roundtable 剩余全部资产**——HCI 客观度量层（`mode/heatmap` + `mode/cross-page` + `mode/annotate-issues`） + Phase C 决策透镜（`mode/synthesize-tension` + `mode/synthesize-paths`） + 共享切片层 + references/ 文档 + MSI-Net 权重说明 + 切片自动构建脚本。当前已完成迁入,进入回归验证
- v0.4：切片自动构建上线 + 画像 fingerprint 去重 + 单界面/多界面/PRD 三个新场景（已起步: `tools/persona_dedupe.py` 只报告、不自动合并;`review-prd.md`/`review-design.md`/`review-screen.md` 已支持 DAG plan）
- v0.5：Markdown renderer + 详情页/商品卡/营销文案场景（已起步:`reporting/markdown_renderer.py` + 3 个场景 DAG plan）
- v0.6：把 DAG 中已出现但缺实现的原子模式补齐（已起步:`mode/persona-pick` / `mode/prd-extract` / `mode/keyframe-extract`;已补营销文案 `mode/copy-extract` 并纳入 e2e 回归）
- v0.7：补齐设计稿/单界面/详情页/商品卡 observe + e2e,并把宿主 Agent/模型回填整理成正式 Skill 使用流
- v0.8：真实评测集工程骨架 + 画像合并决策包（已起步:`evals/` + `tools/evaluation_runner.py` + `docs/persona-merge-decision.md`）
- v0.9：合并 `ad-buyer-expert` 与 `ad-buyer-senior` 为统一画像 `ad-buyer`,并补运行依赖说明
- v0.10：源仓审计收口:补迁移/模式文档,把脚本迁入、execute 接入、可选资产三类状态分开追踪
- v0.11：最后三块工程收尾 + HTML 优先动态报告:persona-fit/sample、distribution-gap、HCI observe 接入 execute;报告按场景/Mode 自适应
- v1.0：F7 AI vs 真实差评对照评测集 + 真实分布接入

---

### 9.5 阶段命名关系与剩余工作

当前没有更换路线,只是进入了不同粒度的记录:

| 命名 | 含义 | 当前状态 |
|---|---|---|
| S1/S2 | 最早的迁移路线切分,用于确认两个源项目怎么合并 | 已被 M 路线吸收,不再单独推进 |
| M1/M2/M3 | MVP 交付里程碑,用于回答"最小可用 Skill 是否跑通" | 已完成:M1 迁入、M2 Brief/Orchestrator、M3 短视频闭环 |
| v0.n | MVP 之后的本地连续迭代版本,用于记录每次能力增量 | 当前进入 v0.11,最后三块工程收尾已落地 |

源仓审计后的收口状态:

1. **工程收口**:
   - ✅ `persona-fit` / `persona-sample` 已串入 `orchestrator --execute`,临时画像落 runtime 并通过 `JURY_PERSONAS_EXTRA_PERSONA_DIRS` 进入 `jury-react`。
   - ✅ `mode/aggregate-distribution-gap` 已串入 aggregate stage,可读取 current/target 双分布和 consensus。
   - ✅ `heatmap` / `cross-page` / `annotate-issues` 已成为 execute observe 产物分支;缺输入时返回 `SKIPPED`,不阻断文本评审。
   - ✅ 报告层已改为 HTML 优先,同时输出 Markdown fallback 与 expert-roundtable 兼容 DocxXML 草稿。
   - ⏳ 严格飞书 DocxXML 的图片上传、block_replace、图片入表仍需 lark-doc 运行环境执行,当前本地只生成草稿产物。
2. **外部输入**:
   - 导入真实反馈数据:当前已有评测集 schema、seed cases 和 runner;正式效果结论需要真实差评/人工标注/业务复盘数据。
3. **可选资产**:
   - 按需恢复 heatmap 深度模型权重:MSI-Net 权重不是主链路依赖,但需要 heatmap B 档时要恢复 `assets/msinet_tf/`。
   - EAgents 源仓 Phase 4 的网页心智模拟 / `mira-remote-browser` 属于源仓 roadmap 能力,不是当前 Skill 主链路迁漏;需要真实浏览器自动化评审时再立项。

### 9.6 源仓审计结论（2026-06-24）

本轮对 `EAgents`、`/tmp/expert-roundtable-mirror` 与当前 `JuryPersonas` 做只读对照:

| 类别 | 结论 | 后续动作 |
|---|---|---|
| EAgents 画像/知识/场景/脚本 | 已有对应迁入物;核心回归通过 | 继续维护兼容,不再按文件搬迁 |
| expert-roundtable references/专家画像/切片库 | 已迁入且关键资产 byte-identical | 保留 legacy 原件用于审计 |
| 文档断链 | `docs/migration-guide.md`、`docs/mode-cookbook.md` 被引用但缺文件 | v0.10 补齐 |
| persona fit/sample | 已进入 orchestrator execute | 继续扩大真实分布输入 |
| distribution gap | 已进入 orchestrator aggregate stage | 等真实反馈数据后做效果对照 |
| HCI observe | 已进入 execute 产物链,A 档 fixture 回归通过 | MSI-Net B 档权重继续可选 |
| 报告 | HTML 优先 + Markdown fallback + DocxXML 草稿 | 真飞书图片入表需 lark-doc 环境 |
| 真实评测 | seed eval 可跑 | 等真实差评/人工标注导入 |

---

## 十、版本与变更记录

- **v0.1（2026-06-22）**：初版，三模式（expert/crowd/mixed）固化
- **v0.2（2026-06-22）**：模式去固化 → 14 原子模式 + Brief Phase + 画像四源 + 五大组件
- **v0.2.1（2026-06-22）**：
  - 锁定 4 个关键决策，进入 MVP 阶段
  - Brief 跳过条件改为宿主 Agent/模型语义判定（废弃分数阈值口径）
  - 画像合并明确"让用户决定"，去掉自动合并
  - MVP 范围收紧：1 个场景（短视频）+ 5 个原子模式 + 飞书报告
  - 迁移路线从 6 步压到 3 步（M1/M2/M3，2-3 天）
  - v0.3+ 路线分阶段补齐其余能力
- **v0.2.2（2026-06-22）**：
  - ⭐ Brief 充分性判定**改为 Agent 大模型判断 + Harness 约束**（不再用打分公式）
  - ⭐ Harness 由三类约束组成：必备字段清单（语义判据）+ 一致性约束 + 边界共识
  - ⭐ Agent 必须输出结构化 JSON（含 evidence/verdict/next_action），由 orchestrator 校验
  - ⭐ 防 Agent 偷懒：evidence 可回溯校验、verdict 二值化、boundary_ack 首次会话强制
- **v0.2.3（2026-06-24）**：M1.5 + 9.3.1 + 9.4
  - ✅ M1.5 局部完成：迁入 product-expert 画像（314 行）+ 切片库（443 行 byte-identical），lint 17 画像 0 error
  - ⭐ §9.3.1 改名为"M1.5 已迁 + v0.3 必迁"，扩展为 9 行清单（原 5 行）
  - ⭐ §9.4 v0.3 加粗为"合并硬承诺"——expert-roundtable 剩余资产 v0.3 必迁，不再是可选项
- **v0.2.4（2026-06-24）**：M3 完成,MVP 闭环
  - ✅ §9.3 M3 行打勾,9 子任务全部交付:fixture(#18) + jury-react(#19) + mock_llm_responder(#20) + aggregate-consensus(#21) + render-report(#22) + lark_renderer(#23) + orchestrator --execute(#24) + jury_review.py(#25) + e2e 冒烟(#26)
  - ✅ 短视频 case 端到端跑通:`python3 jury_review.py --brief ... --artifact ... --personas a,b,c` → /tmp/jp_m3_top/{reactions,consensus,reports}/<sid>.* 全产物齐
  - ⚠️ 沙箱限制约束:`.runtime/` 通过 Write 工具可写,但 Shell 进程不能写,因此 MVP 默认 runtime-dir=/tmp/jp_m3,后续接真 LLM 时可在生产环境改 .runtime
  - ⚠️ MVP 模型反应走 mock_llm_responder 桩,宿主 Agent/模型回填接入是 v0.3+ 范围(只需替换 orchestrator.execute_dag 中 mock 调用或走 `--filled-bundle-file`)
- **v0.2.5（2026-06-24）**：v0.3 合并硬承诺资产迁入
  - ✅ expert-roundtable 镜像锁定 commit `7921f97c8911809078946e4e2c928db60907b46f`
  - ✅ shared/ad-buyer/local-business/product-expert 切片库与专家画像 byte-identical 迁入
  - ✅ `references/` 全量镜像到 `docs/references-from-expert-roundtable/`,`diff -qr` 0 差异
  - ✅ HCI 脚本迁入:`heatmap.py` / `cross_page.py` / `annotate_issues.py`,并修正不存在的 `semantic_collect.py` 记录
  - ✅ Phase C prompt 迁入 `core/prompts/phase_c/`,新增 `modes/synthesize/{tension.py,paths.py}` prompt bundle 生成器
  - ✅ MSI-Net 权重说明迁入 `assets/msinet_tf/README_model_weights.md`,权重本体继续 gitignored
- **v0.2.6（2026-06-24）**：v0.4 起步:画像 fingerprint 去重报告
  - ✅ 新增 `tools/persona_dedupe.py`,扫描 `personas/` 生成 fingerprint / role_family / source_kind / fidelity_rank
  - ✅ 默认只输出冲突报告,不自动改画像;`--write-index` 才刷新 `personas/_fingerprint_index.json`
  - ✅ 兼容 expert-roundtable legacy 专家格式,按 `metadata.role` 推断隐式知识引用
  - ✅ 原始报告发现 1 个高风险重叠:`ad-buyer-expert` vs `ad-buyer-senior`;v0.9 已合并到统一画像 `ad-buyer`
- **v0.2.7（2026-06-24）**：v0.4 起步:PRD/设计稿/单界面场景 DAG plan
  - ✅ `scenarios/review-prd.md` 补齐 frontmatter,可被 orchestrator 解析为 PRD DAG
  - ✅ 新增 `scenarios/review-design.md` 与 `scenarios/review-screen.md`,覆盖设计稿与单/多界面截图
  - ✅ `orchestrator/pipeline.py` 增加 `界面截图`/`多界面` → `review-screen` 映射
  - ✅ 非短视频 `--execute` 显式返回 `EXECUTE_UNSUPPORTED`,避免误导为已端到端执行
  - ✅ 新增 `tests/fixtures/{prd_demo,design_demo,screen_demo}/brief.json`,3 类新场景 plan 冒烟通过
- **v0.2.8（2026-06-24）**：v0.5 起步:详情页/商品卡/营销文案场景 + Markdown renderer
  - ✅ 新增 `scenarios/review-detail-page.md` / `review-product-card.md` / `review-marketing-copy.md`,补齐 pipeline 已映射但缺文件的 3 类场景
  - ✅ 新增 `tests/fixtures/{detail_page_demo,product_card_demo,marketing_copy_demo}/brief.json`,3 类场景 plan 冒烟通过
  - ✅ 新增 `reporting/markdown_renderer.py`,支持通用 JSON → Markdown 报告渲染
- **v0.2.9（2026-06-24）**：v0.6 起步:补齐 3 个 DAG 原子模式脚本
  - ✅ 新增 `modes/jury/persona_pick.py`,校验显式 role_id 列表并编译 system_prompt 包
  - ✅ 新增 `modes/observe/prd_extract.py`,从 PRD Markdown/文本规则化抽取标题、需求、风险、指标、待确认问题与决策点
  - ✅ 新增 `modes/observe/keyframe_extract.py`,把已提供关键帧/storyboard 规范化为时序 observation;只有裸视频路径时返回 `NEEDS_KEYFRAMES`,不脑补画面
  - ✅ 新增 `tests/fixtures/prd_demo/prd.md`,覆盖 `prd-extract` 冒烟
- **v0.2.10（2026-06-24）**：v0.6 起步:observe/persona/synthesize 串入 orchestrator --execute
  - ✅ `orchestrator/pipeline.py --execute` 支持按 DAG 落 `observations/`、`personas/`、`reactions/`、`consensus/`、`decisions/`、`reports/`
  - ✅ `jury_react.py` 增加通用场景 prompt,可注入 observe 阶段 JSON 证据
  - ✅ `mock_llm_responder.py` 增加非短视频 generic mock,用于本地端到端冒烟;`--no-mock-llm` 仍可停在 `WAITING_FOR_REACTIONS`
  - ✅ PRD e2e 跑通:`prd_extract` → `persona_pick` → `jury-react bundle` → mock reactions → consensus → tension/paths bundle → Markdown report
  - ✅ 短视频旧链路保持通过,并额外落 `keyframe_observation`
- **v0.2.11（2026-06-24）**：v0.6 起步:宿主 Agent/模型 reaction 回填恢复执行
  - ✅ 新增 `--filled-bundle-file`,支持从已回填 `participants[*].reaction` 的 bundle 恢复执行
  - ✅ 恢复阶段会继续跑 `aggregate-consensus`、`synthesize-tension`、`synthesize-paths`、`render-report` 与 lark fallback
  - ✅ 若 bundle 仍有 participant 缺 reaction,返回 `REACTIONS_INCOMPLETE` 并列出缺失 role_id
  - ✅ PRD handoff 流程验证通过:`--no-mock-llm` 生成 bundle → 宿主 Agent/模型回填 → `--filled-bundle-file` 恢复生成报告
- **v0.2.12（2026-06-24）**：v0.6 起步:宿主 Agent/模型 handoff 工具化
  - ✅ 统一文档与代码术语为"宿主 Agent/模型",保持 Skill 形态边界清晰
  - ✅ 新增 `tools/reaction_handoff.py`,支持把 jury-react bundle 拆成每位陪审员独立 Markdown prompt
  - ✅ `reaction_handoff.py --check-filled` 可校验 `participants[*].reaction` 是否已全部回填,用于恢复执行前置检查
  - ✅ Quickstart 增加宿主 Agent/模型回填、prompt 导出与 filled bundle 校验流程
- **v0.2.13（2026-06-24）**：v0.6 起步:回填链路关键节点诊断日志
  - ✅ `tools/reaction_handoff.py` 在 bundle 加载、participant 校验、prompt 导出、filled 检查失败等节点向 stderr 打印 `[handoff]` 日志
  - ✅ `orchestrator/pipeline.py --filled-bundle-file` 在恢复执行的加载、缺失 reaction、aggregate、Phase C、report、publish 等节点向 stderr 打印 `[pipeline]` 日志
  - ✅ `orchestrator/pipeline.py --execute --no-mock-llm` 在 observe/persona/jury-react bundle 生成与等待回填节点打印日志
  - ✅ 日志不污染 stdout JSON,便于上层继续解析执行结果
- **v0.2.14（2026-06-24）**：v0.6 起步:本地全链路回归 runner
  - ✅ 新增 `tools/regression.py`,一条命令执行本地完整回归,产物默认只落 `/tmp`
  - ✅ 覆盖 Python 语法、画像 lint、6 类场景 DAG plan、短视频 e2e、PRD e2e
  - ✅ 覆盖宿主 Agent/模型 handoff:bundle 导出 prompt、未回填检查、mock 回填、filled 校验、恢复执行
  - ✅ 覆盖 incomplete reaction 防护与 `__pycache__`/`.pyc` 残留检查
- **v0.2.15（2026-06-24）**：v0.6:营销文案 observe 节点端到端
  - ✅ 新增 `modes/observe/copy_extract.py`,对营销文案做确定性结构抽取,不评价好坏
  - ✅ `review-marketing-copy.md` 必跑 `mode/copy-extract`,并接入 `orchestrator/pipeline.py --execute`
  - ✅ 新增 `tests/fixtures/marketing_copy_demo/copy.md`,营销文案 e2e 输出 `copy_observation`、consensus、Phase C bundle 与 Markdown report
  - ✅ `tools/regression.py` 扩展到 18 步,新增 `marketing_copy_e2e`
- **v0.2.16（2026-06-24）**：v0.7:主线 1/2 完成
  - ✅ 新增 `mode/design-extract` / `mode/screen-extract` / `mode/detail-page-extract` / `mode/product-card-extract`
  - ✅ 四类场景 frontmatter 改为必跑各自 observe mode,支持 `orchestrator/pipeline.py --execute`
  - ✅ 新增设计稿、单界面、详情页、商品卡四类 demo 物料,并纳入 `tools/regression.py`
  - ✅ 新增 [docs/host-agent-workflow.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/docs/host-agent-workflow.md),把宿主 Agent/模型 reaction 回填整理成正式 Skill 使用流
  - ✅ 本地完整回归扩展到 22 步:语法、lint、6 类 plan、7 类 e2e、handoff 与 incomplete 防护全通过
- **v0.2.17（2026-06-24）**：v0.8 起步:评测集与画像决策包
  - ✅ 新增 `evals/schema/evaluation_case.schema.json` 与 `evals/cases/seed_cases.jsonl`,定义 F7 对照评测 case 契约
  - ✅ 新增 `tools/evaluation_runner.py`,运行 pipeline 并计算 gold label coverage,当前 seed cases 2/2 通过
  - ✅ `tools/regression.py` 纳入 `evaluation_seed` 与 `persona_dedupe_report`,防止评测/画像决策链路回退
  - ✅ 新增 [docs/persona-merge-decision.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/docs/persona-merge-decision.md),整理 `ad-buyer-expert` vs `ad-buyer-senior` 的合并选项;v0.9 已执行合并
- **v0.2.18（2026-06-24）**：v0.9:ad-buyer 统一画像与运行依赖说明
  - ✅ 新增 `personas/experts/ad-buyer.md`,合并 `ad-buyer-senior` 的具名行为细节与 `ad-buyer-expert` 的切片知识/红线立场
  - ✅ 新增 `personas/_merge_decisions.json`,去重扫描把 ad_buyer 重叠归入 `resolved_conflicts`
  - ✅ 默认示例、seed eval 与 regression 改用统一画像 `ad-buyer`
  - ✅ 新增 [docs/runtime-assets.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/docs/runtime-assets.md),明确真实差评/标注数据不是运行依赖,heatmap MSI-Net 权重是可选增强资产
- **v0.2.19（2026-06-24）**：v0.10 起步:源仓审计计划收口
  - ✅ 对 `EAgents`、`/tmp/expert-roundtable-mirror` 与当前仓库做只读审计,确认主链路回归通过
  - ✅ 新增 §9.6 源仓审计结论,把文件迁入、execute 接入、可选资产、源仓 roadmap 分开追踪
  - ✅ 新增 [docs/migration-guide.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/docs/migration-guide.md),补齐 EAgents/expert-roundtable 资产映射和完成判定
  - ✅ 新增 [docs/mode-cookbook.md](file:///Users/bytedance/Documents/trae_projects/JuryPersonas/docs/mode-cookbook.md),明确各场景 DAG 配方与当前 `e2e/script/planned` 状态
  - ✅ `SKILL.md` 状态表修正: HCI、persona-fit/persona-sample、distribution-gap 不再标成已全量 execute
- **v0.2.20（2026-06-24）**：v0.10:distribution gap 收口
  - ✅ 新增 `modes/aggregate/distribution_gap.py`,比较 current/target 联合分布并输出 F6 gap rows
  - ✅ 明确边界:`no_real_effect_claim_without_feedback_data=true`,没有真实反馈时只做确定性分布差异,不宣称效果
  - ✅ `tools/regression.py` 增加 `distribution_gap` 步骤,覆盖 demo 双分布 12 个 gap rows
- **v0.2.21（2026-06-24）**：v0.11:最后三块工程收尾 + 动态报告
  - ✅ `persona-fit` / `persona-sample` 接入 `orchestrator --execute`;fit 画像落 runtime,通过 extra persona dir 编译进入 `jury-react`
  - ✅ `mode/aggregate-distribution-gap` 接入 aggregate stage,有 current/target 双分布时生成 `distribution_gap` 产物
  - ✅ `mode/heatmap` / `mode/cross-page` / `mode/annotate-issues` 接入 observe stage;新增 HCI fixture 覆盖 A 档 heatmap 与红框图
  - ✅ 新增 `reporting/html_renderer.py` 与 `reporting/design.md`,报告按场景和实际 Mode 组合选择 HTML 布局,HTML 为优先产物
  - ✅ 新增 `reporting/docx_xml_renderer.py`,输出 expert-roundtable/飞书兼容 DocxXML 草稿,为后续 lark-doc 图片入表留接口
  - ✅ `tools/regression.py` 扩展到 29 步,覆盖 HCI、persona-fit、persona-sample + distribution-gap、HTML/DocxXML 产物
  - **v0.2.22（2026-06-25）**：v0.12:Skill runtime 结构对齐
    - ✅ `scenarios/review-*.md` frontmatter 增加 `artifact_aliases` 与 `default_personas`,场景选择和默认陪审团不再硬编码在 `dag.py`
    - ✅ PRD/短视频等场景把实际必跑 observe mode 写入 `required`,执行层只按 `dag_modes` 运行,不再按 scenario 隐式追加
    - ✅ `tools/regression.py` 扩展到 38 步,新增各场景 plan 必须显式包含 observe mode 的断言
  - **v0.2.23（2026-06-25）**：v0.13:DocxXML 飞书发布链路
    - ✅ `reporting/lark_renderer.py` 改为 lark-doc v2 创建语义:`docs +create --api-version v2 --doc-format xml|markdown --content ...`
    - ✅ `orchestrator/pipeline.py` 发布源从 Markdown 改为 `report_docx_xml`;默认仍 dry-run
    - ✅ `--lark-execute` 下发布失败提升为顶层 `PUBLISH_FAILED`,退出码非 0,不再 local fallback 或 fake URL
  - **v0.2.24（2026-06-25）**：v0.14:契约修复 + Linear HTML 报告风格
    - ✅ `jury-react` prompt 与 `aggregate-consensus` 解析契约对齐;聚合器同时兼容宿主 Agent 回填的 Markdown 字段表
    - ✅ `copy-extract` 改为泛化识别价格、CTA、功效/稀缺风险表达,不把单条测试文案写入运行规则
    - ✅ `ad-buyer` 大知识库仅在已知 artifact 类型下做保守预算压缩,避免 400KB+ system prompt 稀释判断
    - ✅ HTML 报告风格切换为 Linear 深色信息面板风格
    - ✅ `tools/regression.py` 扩展到 43 步,覆盖表格解析、copy 抽取、prompt 体积和非 mock 边界声明
  - **v0.2.25（2026-06-26）**：v0.15:真实短视频证据流水线
    - ✅ 新增 `tools/video_evidence/`,支持抖音 URL → real `play_addr` → mp4 → 等距抽帧 → 抽音 → ASR → `artifact.realframe.json`
    - ✅ `keyframe_extract` 保留真实抽帧图片路径和 `needs_visual_description`,并清空 `observed:false` 推断帧的画面/台词
    - ✅ `jury-react` 短视频 prompt 只引用 `observed:true`/未标推断的帧;缺画面描述时要求先看图,否则必须承认看不清
    - ✅ HTML 报告预览真实抽帧,并提示排除的 `observed:false` 推断帧
    - ✅ `tools/regression.py` 扩展到 47 步,覆盖真实抽帧 artifact builder 与推断帧防泄漏
