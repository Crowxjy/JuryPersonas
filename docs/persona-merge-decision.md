# 画像合并决策包 · ad-buyer

本文件记录 `ad-buyer-expert` 与 `ad-buyer-senior` 的合并决策。

结论先行:已合并为统一画像 **`ad-buyer`**。旧文件保留为 legacy/source 资产,不再作为默认评审入口。

## 一、冲突来源

`tools/persona_dedupe.py --json` 原始扫描发现 1 个高风险重叠:

| 字段 | 值 |
|---|---|
| conflict type | `role_family_overlap` |
| key | `ad_buyer` |
| personas | `ad-buyer-expert`, `ad-buyer-senior` |
| tool recommendation | `coexist_or_merge` |
| final decision | merge into `ad-buyer` |

## 二、画像差异

| 维度 | `ad-buyer-expert` | `ad-buyer-senior` |
|---|---|---|
| 来源 | expert-roundtable legacy expert | JuryPersonas handcraft persona |
| 文件 | `personas/experts/ad-buyer-expert.md` | `personas/experts/ad-buyer-senior.md` |
| 状态 | `legacy` | `active` |
| 知识引用 | `knowledge/slices/shared.md`, `knowledge/slices/ad_buyer.md` | `knowledge/industry/ad-investment.md`, `knowledge/glossary/ad-terms.md` |
| 风格 | 专家 prompt,强调 3 合理 + 3 不合理、切片引用、红线 | 具名角色,有 L1-L5、行为细节、口头禅和 few-shot |
| 更适合 | 深度专家圆桌、Phase C 决策、需要切片引用的严肃评审 | 陪审团模拟、用户视角混合、需要自然角色反应的评审 |

## 三、最终决策

| 项 | 决策 |
|---|---|
| default role_id | `ad-buyer` |
| source role_ids | `ad-buyer-senior`, `ad-buyer-expert` |
| 是否改写 legacy 文件 | 否 |
| 是否保留兼容调用 | 是 |
| 合并配置 | `personas/_merge_decisions.json` |
| 统一画像文件 | `personas/experts/ad-buyer.md` |

## 四、合并原则

合并采用“新建统一入口 + 保留来源原件”的方式:

1. `ad-buyer` 继承 `ad-buyer-senior` 的具名角色、L1-L5 心智、口吻和 few-shot。
2. `ad-buyer` 引入 `ad-buyer-expert` 对应的 `knowledge/slices/shared.md` 与 `knowledge/slices/ad_buyer.md`。
3. `ad-buyer` 明确强化 expert-roundtable 的批判性立场:输入材料不是既定真理,必须独立质疑 ROI、起量、合规、操作成本。
4. `ad-buyer-expert.md` 不改写,继续作为 expert-roundtable 迁入审计原件。
5. `ad-buyer-senior.md` 不删除,用于历史结果复现和兼容旧命令。

## 五、执行规则

合并后默认规则:

- 新评审默认使用 `ad-buyer`。
- 旧命令中的 `ad-buyer-senior` 建议迁移到 `ad-buyer`。
- `ad-buyer-expert` 仅用于 expert-roundtable 原始资产复现、审计或对照。
- 同一场评审默认不再同时选择 `ad-buyer`、`ad-buyer-senior`、`ad-buyer-expert`。

## 六、验证标准

- `python3 modes/jury/compile_persona.py ad-buyer --json` 必须成功。
- `tools/persona_dedupe.py --json` 应把 ad_buyer 重叠归入 `resolved_conflicts`,不再作为未解决冲突。
- `tools/regression.py` 默认回归使用 `ad-buyer`。
