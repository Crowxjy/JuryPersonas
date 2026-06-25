# 宿主 Agent/模型正式使用流

本文档定义 JuryPersonas 作为 Skill 安装后的正式执行边界。脚本只负责确定性编排、prompt bundle、校验、聚合和报告;陪审员反应由宿主 Agent/模型读取 prompt 后回填。

## 一、执行边界

| 阶段 | 执行方 | 产物 |
|---|---|---|
| Brief Harness | 宿主 Agent/模型 + `brief_validator.py` | `brief.json` |
| DAG 与 observe/persona | JuryPersonas 脚本 | `observations/*.json`、`personas/*.json` |
| jury-react prompt bundle | JuryPersonas 脚本 | `reactions/<sid>.bundle.json` |
| 陪审员独立反应 | 宿主 Agent/模型 | `participants[*].reaction` |
| 校验与恢复执行 | JuryPersonas 脚本 | `consensus/*.json`、`decisions/*.json`、`reports/*.md` |

关键约束:

- 宿主 Agent/模型不得把一个陪审员的 prompt 或 reaction 泄露给另一个陪审员。
- `participants[*].reaction` 必须保持该场景 user prompt 要求的结构。
- 如果任一 participant 缺 reaction,恢复执行必须停在 `REACTIONS_INCOMPLETE`。
- 日志写 stderr,stdout 保持 JSON,方便上层 Agent 解析。

## 二、标准命令流

### 1. 生成 bundle 并停在回填点

```bash
python3 orchestrator/pipeline.py \
  --brief-file tests/fixtures/prd_demo/brief.json \
  --artifact-file tests/fixtures/prd_demo/prd.md \
  --personas product-expert,ad-buyer \
  --execute \
  --no-mock-llm \
  --runtime-dir /tmp/jp_host_agent
```

期望状态:`WAITING_FOR_REACTIONS`。

关键产物:

- `/tmp/jp_host_agent/reactions/<sid>.bundle.json`
- `/tmp/jp_host_agent/observations/<sid>.*.json`
- `/tmp/jp_host_agent/personas/<sid>.persona_pick.json`

### 2. 拆出每位陪审员独立 prompt

```bash
python3 tools/reaction_handoff.py \
  --bundle-file /tmp/jp_host_agent/reactions/<sid>.bundle.json \
  --export-prompts /tmp/jp_host_agent/prompts \
  --pretty
```

宿主 Agent/模型逐个读取 `/tmp/jp_host_agent/prompts/*.md`,按文件内 `Fill Back Contract` 把反应写回原 bundle 的对应 `participants[*].reaction` 字段。

### 3. 恢复前校验

```bash
python3 tools/reaction_handoff.py \
  --bundle-file /tmp/jp_host_agent/reactions/<sid>.filled.json \
  --check-filled \
  --pretty
```

期望:

- `status=OK`
- `validation.ready_for_resume=true`
- `validation.missing_reaction_role_ids=[]`

### 4. 从 filled bundle 恢复执行

```bash
python3 orchestrator/pipeline.py \
  --brief-file tests/fixtures/prd_demo/brief.json \
  --execute \
  --filled-bundle-file /tmp/jp_host_agent/reactions/<sid>.filled.json \
  --runtime-dir /tmp/jp_host_agent_final
```

恢复阶段会继续执行:

- `mode/aggregate-consensus`
- `mode/synthesize-tension` 和 `mode/synthesize-paths`(如 DAG 包含)
- `mode/render-report`
- 飞书发布默认 dry-run;传 `--lark-execute` 时用 DocxXML 真创建飞书文档,失败显式返回 ERROR

## 三、错误处理

| 状态 | 含义 | 处理 |
|---|---|---|
| `WAITING_FOR_REACTIONS` | bundle 已生成,等待宿主 Agent/模型回填 | 进入 prompt 导出和回填 |
| `REACTIONS_INCOMPLETE` | 有 participant 缺 reaction | 补齐列出的 role_id 后重跑校验 |
| `JURY_REACT_BUNDLE_FAILED` | persona 或 prompt bundle 构建失败 | 查看 `errors` 与 `[pipeline]` stderr 日志 |
| `PERSONA_PICK_FAILED` | 指定画像不存在或编译失败 | 修正 `--personas` 或画像文件 |

## 四、Skill 调用口径

宿主 Agent 安装本 Skill 后,用户只需要提出评审需求;Agent 应按以下顺序执行:

1. 先用 Brief Harness 判断信息是否充分。
2. 充分后生成 DAG,必要时向用户确认场景与陪审员。
3. 执行 `pipeline.py --execute --no-mock-llm`。
4. 为每位陪审员独立完成 reaction 回填。
5. 用 `reaction_handoff.py --check-filled` 校验。
6. 用 `pipeline.py --filled-bundle-file` 恢复聚合和报告。

本流程不引入第三方模型服务概念;“模型”始终指当前安装 Skill 的宿主 Agent/模型。
