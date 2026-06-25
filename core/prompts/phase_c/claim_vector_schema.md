# 主张向量结构化字段表（Claim Vector Schema）

> 本文件定义「圆桌决策透镜」中，如何把一个角色的发言（或 roundtable-facilitator 的 reasonable/unreasonable JSON）结构化为可计算的「主张向量」。
> 主张向量是连接【角色发言】与【决策偏好因子】的桥梁：通过 `mapped_factor` 字段引用 `preference_factors.md`，通过 `axis` 字段引用 `tension_axis_library.md`。

---

## 一、什么是主张向量

一个角色在某议题上的发言，本质是一个**有方向的诉求**。把它拆成结构化字段后，就能与其他角色的主张做"同轴异极"比对，从而涌现出张力。

> 主张向量 = 角色把"我想要什么 + 我担心什么 + 我指向哪端"压缩成的一条可比对记录。

---

## 二、字段定义表

| 字段 | 类型 | 必填 | 含义 | 取值/引用来源 | 示例 |
|---|---|---|---|---|---|
| `claim_id` | string | ✓ | 主张唯一标识 | 自增，如 `cv_01` | `cv_01` |
| `role` | string | ✓ | 发言角色 | 引用 roster.md 角色名 | `ad_buyer` |
| `source` | enum | ✓ | 主张来源 | `reasonable` / `unreasonable` | `unreasonable` |
| `raw_point` | string | ✓ | 角色原始论点（原话） | 直接取自角色 JSON 的 `point` | "第 5 位插广告会损害体验" |
| `demand` | string | ✓ | **诉求**：想要什么 | 从 raw_point 提炼 | "保住用户体验底线" |
| `concern` | string | ✓ | **顾虑**：担心什么 | 从 raw_point 提炼 | "广告过密导致用户反感流失" |
| `direction` | string | ✓ | **方向**：指向张力轴哪一端 | 自然语言短语 | "偏体验端" |
| `axis` | string | ✓ | **所属张力轴** | 引用 `tension_axis_library.md` 的轴 ID | `转化-体验` |
| `pole` | enum | ✓ | **极性**：在该轴的哪一极 | `+` / `−`（轴库定义两极语义） | `−`（体验极） |
| `mapped_factor` | string[] | ✓ | **激活的决策偏好因子 ID** | 引用 `preference_factors.md` 因子 ID | `["C1"]` |
| `weight` | enum | ✓ | **角色权重**：该角色在本议题的话语权 | `高` / `中` / `低` | `高`（投手对转化议题） |
| `severity` | enum | ○ | 严重度（继承自原 JSON） | `high` / `med` / `low` | `high` |
| `evidence` | string[] | ○ | 证据/知识库引用 ID | 继承自原 JSON 的 `evidence` | `["id_322"]` |
| `is_red_line` | bool | ○ | 是否红线（继承自原 JSON） | `true` / `false` | `false` |
| `note` | string | ○ | 主持人备注 | 自由文本 | "与产品主张正面对撞" |

---

## 三、与决策偏好因子的关联（核心）

主张向量通过**两个字段**与偏好因子库 / 张力轴库建立显式关联，关联链路如下：

```
角色发言 raw_point
   │  提炼
   ▼
demand + concern + direction
   │  归类
   ▼
axis（张力轴 ID）────────────► tension_axis_library.md（定义两极语义）
   │                                        │
   │  在轴上定位                              │ 轴的两极各挂靠因子
   ▼                                        ▼
pole（+ / −）           mapped_factor（因子 ID）──► preference_factors.md（因子定义 + 画像）
```

关联规则：
1. `axis` 决定这条主张参与"哪条张力轴"的对撞；只有**同轴**的主张才可能形成张力。
2. `pole` 决定它在该轴的**哪一极**；同轴**异极**才是真张力，同轴**同极**是共识。
3. `mapped_factor` 把这一极**绑定到具体的决策偏好因子**，从而在 Step 5 输出时能标注"这套建议背后是 C1 目标权重-体验优先"。
4. 一条主张可挂靠**多个因子**（如"先灰度再全量"同时激活 A1 风险厌恶 + E1 后悔规避），主因子放第一位。

### 关联示例（PM 评审"信息流第 5 位加广告"）

| claim_id | role | demand | direction | axis | pole | mapped_factor |
|---|---|---|---|---|---|---|
| cv_01 | ad_buyer | 提升 ARPU | 偏转化端 | `转化-体验` | `+` | `["C1","B1"]` |
| cv_02 | product_expert | 守住体验底线 | 偏体验端 | `转化-体验` | `−` | `["C1","A2"]` |

→ cv_01 与 cv_02 **同轴（转化-体验）异极（+ / −）** → 涌现【核心张力】
→ 🅰 画像挂靠 C1 增长优先 + B1 高贴现率；🅑 画像挂靠 C1 体验优先 + A2 高损失厌恶。

---

## 四、从角色 JSON 到主张向量的转换流程

输入（roundtable-facilitator 的角色输出）：
```json
{
  "role": "product_expert",
  "unreasonable": [
    {"point": "第 5 位插广告会损害体验", "severity": "high", "evidence": ["id_322"], "is_red_line": false}
  ]
}
```

转换后（主张向量）：
```json
{
  "claim_id": "cv_02",
  "role": "product_expert",
  "source": "unreasonable",
  "raw_point": "第 5 位插广告会损害体验",
  "demand": "守住用户体验底线",
  "concern": "广告过密导致反感与流失",
  "direction": "偏体验端",
  "axis": "转化-体验",
  "pole": "−",
  "mapped_factor": ["C1", "A2"],
  "weight": "高",
  "severity": "high",
  "evidence": ["id_322"],
  "is_red_line": false,
  "note": "与投手 cv_01 正面对撞"
}
```

转换要点：
- `demand` / `concern` / `direction` 是**主持人的提炼动作**，非机械搬运，需读懂论点的真实指向。
- `axis` / `pole` / `mapped_factor` 是**归类动作**，须查 `tension_axis_library.md` 和 `preference_factors.md` 对照填写。
- `severity` / `evidence` / `is_red_line` 是**透传字段**，原样继承不改写。

---

## 五、拓展规范

字段表设计为可拓展，新增维度时遵循：

1. **新增字段**：在"字段定义表"加一行，注明 类型 / 必填 / 含义 / 取值来源 / 示例。可选字段标 `○`，不破坏既有解析。
2. **新增枚举值**：如 `weight` 需要更细粒度，可扩为 `高/中高/中/中低/低`，但须同步更新 Step 3 的阵营归并与主导张力打分逻辑。
3. **新增关联维度**：若未来要把主张关联到"角色画像""历史决策记忆"等新底座，新增形如 `mapped_xxx` 的引用字段，并新建对应库文件（仿 `preference_factors.md`）。
4. **保持三段关联链完整**：任何新字段若参与张力计算，必须能回答"它如何影响 axis 判定 / pole 判定 / 因子挂靠"三者之一，否则只作备注字段。
5. **向后兼容**：新增字段一律设为可选（`○`），确保旧的主张向量记录仍可被解析，不强制回填。
