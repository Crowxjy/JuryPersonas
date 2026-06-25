# 真实评测集

`evals/` 用于沉淀 F7 方向的评测数据:把 JuryPersonas 产出的陪审问题与真实差评、人工标注或业务复盘反馈做对照。

当前状态是工程骨架 + seed cases。seed cases 用于验证评测 runner、字段契约和回归链路;正式结论必须等真实反馈数据进入后再看。

## 目录

| 路径 | 作用 |
|---|---|
| `schema/evaluation_case.schema.json` | 单条评测 case 的字段契约 |
| `cases/seed_cases.jsonl` | 本地可跑的 seed cases |
| `tools/evaluation_runner.py` | 读取 cases,运行 pipeline,对照 gold labels |

## Case 粒度

一条 case 对应一次评审对象:

- `brief_file`: 已通过 Brief Harness 的 `brief.json`
- `artifact_file`: 被评审对象
- `personas`: 陪审员 role_id 列表
- `gold_feedback`: 真实差评/人工标注/业务复盘中的问题点
- `expected`: 对本次评测的最低结构要求

## 评分口径

runner 当前输出:

- `gold_coverage`: gold label 中有多少被 complaints/consensus 覆盖
- `matched_gold`: 被命中的 gold label
- `missing_gold`: 未被命中的 gold label
- `complaints` / `consensus`: pipeline 聚合输出规模

这不是线上效果绝对分,只用于回答:

1. 真实问题有没有被陪审团提到。
2. 哪类问题经常漏掉。
3. 哪些 persona 或 observe mode 对真实问题更敏感。

## 后续接入真实数据

追加真实 case 时,不要改 runner,只新增 JSONL 行:

```json
{"case_id":"real_xxx","scenario":"review-detail-page","brief_file":"...","artifact_file":"...","personas":["..."],"gold_feedback":[{"position":"...","concern":"...","evidence":"...","source":"real_complaint"}],"expected":{"min_gold_coverage":0.5}}
```

真实用户评论、差评、人工标注如含隐私信息,必须先脱敏再入库。
