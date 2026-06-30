# 专家方法 / 工具维度设计

## 结论

可以把所有专家角色使用的方法或工具提炼成单独维度,而且建议这么做。

但它不应该替代 persona。更合理的拆法是:

- **persona identity**:这个专家是谁、站在什么利益位置、有什么经验和盲区。
- **domain knowledge**:这个专家懂哪些行业事实、规则、红线和案例。
- **method/tool lens**:这个专家评审时调用哪些稳定方法、公式、检查表和工具。

这样可以避免两个问题:

1. 多个专家重复写同一套方法,导致 prompt 膨胀。
2. 把"会用某个方法"误写成人设性格,导致角色之间边界混乱。

## 为什么要抽成新维度

现有专家角色里已经出现大量可复用的方法组件:

| 方法 / 工具 | 典型角色 | 可复用价值 |
|---|---|---|
| 盈亏平衡计算 | 餐饮诊断专家 / 本地商家专家 | 判断单店能不能活、活动能不能回本 |
| 商圈动线检查 | 餐饮诊断专家 / 本地商家专家 | 识别真实客流、死动线、截流 |
| 漏斗拆解 | 广告投手 / 产品专家 | 曝光→点击→转化→成交定位卡点 |
| ROI / CPA / ECPM | 广告投手 | 判断投放价值和素材/出价问题 |
| HCI/可用性检查 | UX 设计专家 / 产品专家 | 判断理解成本、操作路径、误操作 |
| 合规红线清单 | 广告投手 / 本地商家 / 餐饮诊断 | 单独标注不可碰风险 |
| 竞品 benchmark | 广告投手 / 产品专家 / 餐饮专家 | 判断材料自述是否站得住 |

这些不是某个角色独有的"身份",而是评审时可调用的"方法资产"。

## 建议的数据结构

### 1. 新增方法资产目录

```text
knowledge/methods/
├── break_even.md
├── store_traffic_audit.md
├── franchise_risk_check.md
├── group_buy_roi_check.md
├── funnel_diagnosis.md
├── roi_cpa_ecpm.md
├── usability_walkthrough.md
└── compliance_redline_check.md
```

每个方法文件只写:

- 适用场景。
- 输入字段。
- 操作步骤。
- 输出格式。
- 常见误用。
- 哪些结论不能凭这个方法推出。

### 2. persona frontmatter 增加 method_lens

```yaml
method_lens:
  primary:
    - break_even
    - store_traffic_audit
  secondary:
    - compliance_redline_check
  forbidden:
    - taste_judgement_without_trial
```

含义:

- `primary`:角色高频主动使用的方法。
- `secondary`:遇到相关场景才调用。
- `forbidden`:禁止越界使用的方法或伪方法。

### 3. 编译 prompt 时按场景裁剪方法

`compile_persona.py` 可以后续增加:

1. 读取 `method_lens`。
2. 根据 `scenario/artifact_type` 选择相关方法。
3. 把方法卡片注入 system prompt 的"你评审时可用的方法"段。

这与现有 `imports` 不冲突。`imports` 偏行业知识,`method_lens` 偏评审动作。

## 对报告结构的影响

聚合报告可以新增一块"本轮专家使用的方法":

| 专家 | 使用方法 | 关键输入 | 得出的判断 | 证据强度 |
|---|---|---|---|---|
| 餐饮诊断专家 | 盈亏平衡 | 房租/人工/毛利/营业额 | 当前活动无法覆盖固定成本 | 中 |
| 广告投手 | 漏斗拆解 | CTR/CVR/CPA | CTA 弱影响点击后转化 | 低 |

这样用户能看懂:

- 专家不是只在表达态度。
- 每个判断来自哪个方法。
- 哪些判断证据强,哪些只是经验推断。

## 与餐饮诊断专家的关系

本次新增的 `restaurant-diagnosis-expert` 应该挂载:

```yaml
method_lens:
  primary:
    - break_even
    - store_traffic_audit
    - franchise_risk_check
  secondary:
    - group_buy_roi_check
    - compliance_redline_check
  forbidden:
    - visual_taste_judgement_without_trial
    - fengshui_location_reasoning
```

当前已直接启用该字段:`compile_persona.py` 会解析 `method_lens`,把 primary/secondary 方法卡按
`artifact_type` 注入 system prompt,并把 forbidden 项作为禁止越界判断写入 prompt。

## 实施顺序

1. 已把专家已有稳定方法整理成 `knowledge/methods/*.md`。
2. 已给活跃专家 persona 增加 `method_lens` frontmatter,编译器对未声明角色保持向后兼容。
3. 已修改 `compile_persona.py`,按 artifact_type 裁剪方法卡片。
4. 后续可修改 jury prompt,要求专家在 reaction 中标注"本条判断使用的方法"。
5. 后续可修改 aggregate/report,在报告中汇总方法覆盖和证据强度。

## 风险

- 方法维度过细会让 prompt 变重,应控制为少量高频方法。
- 不要把方法当作绝对真理。比如盈亏平衡只能判断账面生死线,不能证明口味、品牌长期价值或经营者执行力。
- 方法需要和证据边界绑定。没有房租/人工/毛利时,不能假装算出了可靠盈亏平衡。
