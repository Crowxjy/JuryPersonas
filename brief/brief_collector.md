# Brief Collector · Workshop 三轮交互协议

> **作用**：本文件是 Jury Personas Skill 的 **Workshop 协议**——给调用 Skill 的 Agent 一份"和用户对话怎么走"的剧本。Agent 拿到用户首次请求后，按本协议分轮交互，每轮收完都按 [core/prompts/brief_harness.md](../core/prompts/brief_harness.md) 出一份 JSON 落 `.runtime/briefs/<sid>.json`。
> **形式契约**：本文件管"对话流程"；[brief.schema.json](../core/contracts/brief.schema.json) 管"输出长什么样"；[brief_harness.md](../core/prompts/brief_harness.md) 管"什么叫信息够"。三份文件配合使用。

---

## 总原则

1. **不允许跳过 Workshop 直接进 DAG**——除非 [brief_inferrer.py](brief_inferrer.py) 抽取后 Agent 判定 5 字段全 sufficient + 一致性 + 边界共识全过，并把 brief 摘要发给用户做"一键确认"
2. **每轮收完先出 JSON**——按 schema 落 `.runtime/briefs/<sid>.json`，再由 orchestrator 决定要不要进下一轮
3. **不给开放性问题**——每条问题必须能让用户用 1-2 句话或一个路径回答；不要让用户写小作文
4. **不脑补字段值**——用户没说的，`value` 就是 null，不要替用户填合理默认
5. **冲突必须挑出来澄清**——5 字段间逻辑不自洽时（详见 harness §② 一致性约束），不能默默调和

---

## Round 1：评估对象 + 受众 + 关心点 + 分布意图（必填 4 问 + 边界声明）

### Step 1.0：先甩 4 条边界声明（首次会话强制）

> 在问任何问题之前，先告知用户本 Skill 的 4 条边界，让用户知道自己买的是什么：

```
在我开始评审前，先和您对齐 4 条边界（这是 Jury Personas 的硬约束）：

1. ✋ 我不会预测完播率/转化率/CTR 这类绝对数值——这是不可证伪的
2. ✋ 我不会替您裁决"该不该上线"，只会给出🅰/🅑双路径供您拍板
3. ⚠️ 临时拟合的画像（_fit_*）会在每段发言末尾标注保真度声明，请按此判断可信度
4. ⚠️ 缺关键素材时我会主动要求您补齐，不会脑补——所以请准备好评审对象的完整资料

如果以上 4 条您接受，我们就开始；如果有疑问请提出。
```

→ 用户确认后，`boundary_ack` 4 项可全标 true。

### Step 1.1：4 个必填问题（编号选项 + 自由回答兜底）

```
我需要先和您确认 4 件事（请用编号回复，或直接说明）：

1. **这次评审的对象是什么？**
   ① PRD 文档（.md / .pdf / .docx）
   ② 设计稿/单界面截图（.png / .fig / .sketch）
   ③ 短视频成片（.mp4 / 视频链接 / 关键帧+文案）
   ④ 详情页/商品卡（截图 + 文案）
   ⑤ 营销文案（朋友圈/小红书/落地页文案）
   ⑥ 其他（请描述）
   → 请同时提供素材路径（本地绝对路径 / URL / 或粘贴内容）

2. **这份产物是给谁看的最终用户？**（是您**真实的目标受众**，不是"任何用户"）
   ① 普通消费者（请明确细分人群：年龄段/性别/城市层级/职业等）
   ② 商家/合作伙伴
   ③ 内部决策层（老板/总监）
   ④ 设计/产品同事
   ⑤ 其他（请描述）

3. **您当前最关心什么？**
   ① 用户会不会被劝退/流失（看流失点定位）
   ② 设计/逻辑是不是合理（看专家批判）
   ③ 转化效果好不好（看转化路径）
   ④ 决策怎么走（看🅰/🅑路径）
   ⑤ 综合评估（默认）

4. **有没有客观分布数据可以喂给我？**
   ① 有真实分布 JSON（请提供路径或商家 ID）
   ② 没有，用 mock 分布即可
   ③ 不需要采样（指定 1-N 个画像 ID 即可）
```

### Step 1.2：收完出 JSON

按 [brief.schema.json](../core/contracts/brief.schema.json) 输出，落 `.runtime/briefs/<sid>.json`：

- 用户用编号回答的，按映射填 `value`，`evidence` 引用用户原话（"用户回复 ③ 短视频成片"）
- 用户用自由文本的，按 [brief_inferrer.py](brief_inferrer.py) 的 hints 做候选，最终判断由 Agent 拍板
- 用户没回答到的字段，`value: null, sufficient: false`
- 如果 4 字段都填齐 + boundary_ack 全 true + 无冲突 → `verdict: SUFFICIENT`，进 Round 3 摘要确认（可跳过 Round 2）
- 否则 → `verdict: INSUFFICIENT`，`next_action.kind: ASK_USER`，questions 列出具体缺什么

---

## Round 2：冲突澄清（条件触发：仅当 consistency_check.passed=false 时进入）

### Step 2.1：把冲突说清楚

按 harness §② 一致性约束，4 类冲突的标准澄清话术：

| 冲突类型 | 澄清话术模板 |
|---|---|
| 类型与素材不符（如 PRD 类型但素材是图片） | "您选了 ① PRD 文档，但提供的是 `[file].png`，这不是文档。请确认：① 改选「设计稿」；② 还是说有 PRD 文档但走错路径，请补提供 .md/.pdf？" |
| 关心流失但受众是内部 | "您说最关心「劝退/流失」，但目标受众是「内部决策层」——内部决策不太适用流失视角。请确认：① 改成「设计/逻辑合理性」；② 还是说目标受众其实是终端用户，需要更正？" |
| 真实分布无路径 | "您提到有真实分布数据，但还没看到路径。请提供：① JSON 文件绝对路径；② 商家 ID + 查询路径；③ 没有的话改用 mock。" |
| 受众与画像谱系无匹配 | "您的目标受众是 [X]，目前画像谱系（personas/）没有完全匹配的角色。我建议三选一：① 用 `mode/persona-fit` 临时合成（带保真度声明）；② 退到最近的画像（[Y]）； ③ 您指定画像 ID。请选。" |

### Step 2.2：收完出新 JSON（round=2）

冲突解决后，重新按 schema 出 JSON：
- `consistency_check.passed = true`
- 如果还有字段不充分，继续 ASK_USER
- 全过则 → `verdict: SUFFICIENT`

---

## Round 3：Brief 摘要确认（必经，最后一关）

### Step 3.1：把 5 字段摘要发给用户

```
确认本次评审的 Brief 摘要：

| 项 | 值 |
|---|---|
| 评估对象 | <artifact_type> · <artifact_locator> |
| 目标受众 | <target_audience> |
| 关心维度 | <key_concern> |
| 分布意图 | <distribution_intent> |
| 边界共识 | ✅ 不预测绝对值 / ✅ 不裁决上下线 / ✅ 拟合画像带保真度 / ✅ 缺素材会问 |

按此 Brief 我会推荐如下评审 DAG：
<scenario.modes.required + scenario.modes.recommended 列表>

可调整：
① 直接进（推荐）
② 调整 DAG（增删原子模式）
③ 修改 Brief（哪一项不对？）
```

### Step 3.2：用户确认后 verdict 才能 SUFFICIENT

只有用户**显式回复确认**后，Agent 才能输出 `verdict: SUFFICIENT` + `next_action.kind: PROCEED_TO_DAG`，把 `summary_for_user` 写入 JSON。

---

## 跳过 Workshop 的唯一路径（半自动）

如果用户首次输入信息已经非常完整（例如"评一下 /Users/me/video.mp4 这个短视频，目标人群是三线小龙虾店周边消费者，最关心被劝退流失，没真实分布数据用 mock 就行"），Agent 可：

1. 调 [brief_inferrer.py](brief_inferrer.py) 抽取 hints
2. 自检 5 字段是否全 sufficient + 一致性是否通过
3. 如果通过，**直接进 Round 3 摘要确认**（跳过 Round 1 + Round 2）
4. 用户确认后才 SUFFICIENT

⚠️ **绝不允许跳过 Round 3 摘要确认**——这是防 Agent 误判的最后一道闸。

---

## 落地约束（给实现方）

1. 每轮 JSON 落到 `.runtime/briefs/<session_id>.json`，覆盖写（保留 round 字段做轨迹）；上一轮的 JSON 同时复制到 `.runtime/briefs/history/<session_id>_round<N>.json`
2. session_id 由 orchestrator 生成（推荐 `YYYYMMDD-HHMMSS-<short_uuid>`）
3. orchestrator 在每轮收完后**必须**跑 [brief_validator.py](brief_validator.py) 五重校验，校验失败把控制权交还给 Agent 重出 JSON
4. Round 1 的"4 条边界声明"在用户首次会话**必须先讲再问**，顺序不能颠倒
5. Round 3 的 DAG 推荐由 [orchestrator/pipeline.py](../orchestrator/pipeline.py) 读 `scenarios/<x>.md` 的 frontmatter `modes` 字段生成，不要在本协议里硬编码

---

## 与 Skill 其他文件的关系

- 形式契约：[brief.schema.json](../core/contracts/brief.schema.json)
- 充分性 prompt：[brief_harness.md](../core/prompts/brief_harness.md)
- 抽取脚手架：[brief_inferrer.py](brief_inferrer.py)
- 五重校验器：[brief_validator.py](brief_validator.py)
- DAG 调度：[orchestrator/pipeline.py](../orchestrator/pipeline.py)
- 架构总览：[docs/architecture-v0.2.md §9.1 / §9.2](../docs/architecture-v0.2.md)
