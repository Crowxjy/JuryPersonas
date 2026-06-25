# 迁移指南

本指南记录 `EAgents` 与 `expert-roundtable` 合并到 `JuryPersonas` 后的资产映射和维护边界。

## 一、迁移原则

1. `JuryPersonas` 保持 Skill 形态:入口是 `SKILL.md`,运行时由宿主 Agent/模型负责理解 prompt 与回填 reaction。
2. legacy 资产尽量保留原件,特别是 expert-roundtable 的专家画像和知识切片,方便日后审计。
3. 脚本迁入不等于 execute 接入。状态必须区分:
   - 已复制/适配脚本
   - 已接入 `orchestrator --execute`
   - 已进入 `tools/regression.py`
4. 大模型不由脚本直接调用。`jury-react` 只生成 bundle;正式 reaction 由宿主 Agent/模型回填。

## 二、EAgents 映射

| 源仓能力 | JuryPersonas 位置 | 当前状态 |
|---|---|---|
| `SKILL.md` / 画像 Skill 说明 | `SKILL.md` + `docs/architecture-v0.2.md` | 已合并 |
| 手写画像 | `personas/{experts,consumers,bd}/` | 已迁入并 lint |
| 行业知识与术语 | `knowledge/industry/`, `knowledge/glossary/` | 已迁入 |
| 短视频评审场景 | `scenarios/review-short-video.md` | 已接入 e2e |
| `compile_persona.py` | `modes/jury/compile_persona.py` | 已适配 |
| `roundtable.py` / `roundtable_session.py` | `modes/jury/` | 独立可用,主链路使用 `jury-react` |
| `fit_persona.py` | `modes/jury/fit_persona.py` | 已接入 execute + regression |
| `sample_personas.py` | `modes/jury/sample_personas.py` | 已接入 execute + regression |
| 分布 fixtures | `tests/fixtures/distributions/` | 已迁入 |
| Phase 4 网页心智模拟 | 无默认实现 | 源仓 roadmap,不是当前迁漏 |

## 三、expert-roundtable 映射

| 源仓能力 | JuryPersonas 位置 | 当前状态 |
|---|---|---|
| 三专家画像 | `personas/experts/{product-expert,ad-buyer-expert,local-business-expert}.md` | 已迁入,关键文件 byte-identical |
| shared/ad/local/product 切片库 | `knowledge/slices/*.md` | 已迁入,关键文件 byte-identical |
| `references/` 流程文档 | `docs/references-from-expert-roundtable/` | 已镜像 |
| MSI-Net heatmap | `modes/observe/heatmap.py`, `assets/msinet_tf/README_model_weights.md` | A 档已接入 execute,B 档权重可选 |
| cross-page / annotate issues | `modes/observe/cross_page.py`, `modes/observe/annotate_issues.py` | 已接入 execute |
| Phase C 决策透镜 | `core/prompts/phase_c/`, `modes/synthesize/` | 已接入 bundle 生成 |
| 严格飞书 DocxXML 报告 | `reporting/docx_xml_renderer.py` | 已出草稿;真发布/图片入表待 lark-doc 环境 |
| `build_knowledge_base.py` | `tools/build_knowledge_base.py` | 已迁入 |

## 四、统一画像迁移

`ad-buyer-expert` 与 `ad-buyer-senior` 已合并为默认画像 `ad-buyer`:

- 默认使用: `personas/experts/ad-buyer.md`
- 合并决策: `personas/_merge_decisions.json`
- 决策说明: `docs/persona-merge-decision.md`

旧文件保留:

- `ad-buyer-expert.md`: expert-roundtable 审计原件
- `ad-buyer-senior.md`: JuryPersonas 历史复现原件

新命令和 fixture 应优先使用 `ad-buyer`。

## 五、迁移完成判定

一项能力只有同时满足以下条件,才可标为“端到端完成”:

1. 有稳定文件位置。
2. 可通过命令独立执行或由 orchestrator 调用。
3. 产物进入 `/tmp` runtime 或指定 runtime 目录。
4. 被 `tools/regression.py` 或专项 fixture 覆盖。
5. 文档说明边界和依赖。

只满足文件复制或脚本迁入时,状态写为“已迁入,待 execute 接入”。
