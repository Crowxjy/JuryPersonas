# 完整圆桌示例 (few-shot)

> 以下为虚构 + OneCampaign 投放升级议题改编的样例,用于锚定输出结构。

## 示例 1:某线索行业商家投放产品改版评审

**议题**:某商家投放后台新增「一键智能起量」入口,默认勾选「智能定向 + 智能出价」,无法关闭。要评审改动合理性。

### 投手独立陈述
```json
{
  "role": "ad_buyer",
  "reasonable": [
    {"point": "对新手投手降低决策门槛", "severity": "med", "evidence": ["help2_023"]},
    {"point": "起量速度可能提升", "severity": "low", "evidence": ["g3_017"]},
    {"point": "符合官方推荐的智能化方向", "severity": "low", "evidence": ["g1_009"]}
  ],
  "unreasonable": [
    {"point": "资深投手依赖手动定向+手动出价做精细调控,无法关闭等于强制接管账户", "severity": "high", "evidence": ["g9_004","jingjia_002"], "is_red_line": true},
    {"point": "对高客单价线索行业(医美/教培),智能定向人群质量不可控,易导致客资浪费", "severity": "high", "evidence": ["xs_zhx_03"]},
    {"point": "默认勾选不可见,容易误操作,违反平台 UI 透明原则", "severity": "med", "evidence": []}
  ]
}
```

### 产品专家独立陈述
```json
{
  "role": "product_expert",
  "reasonable": [
    {"point": "符合「智能灵动」设计原则,默认值帮助首次用户", "severity": "med", "evidence": ["zys_005"]},
    {"point": "减少配置步骤,符合 onboarding 简化最佳实践", "severity": "med", "evidence": ["pm_011"]},
    {"point": "与 OneCampaign 升级方向一致", "severity": "low", "evidence": []}
  ],
  "unreasonable": [
    {"point": "不可关闭违反「用户可控性」设计原则,关键功能不可达即红线", "severity": "high", "evidence": ["znld_004","pm_038"], "is_red_line": true},
    {"point": "未为资深用户保留专家模式入口,信息架构不分层", "severity": "high", "evidence": ["znld_006"]},
    {"point": "默认勾选 + 隐藏开关属反模式 (dark pattern)", "severity": "high", "evidence": ["aiwf_004"]}
  ]
}
```

### facilitator 整合输出

#### 共识不合理(2 项)
1. 🔴 **不可关闭违反用户可控性**:投手认为强制接管账户,产品认为违反设计原则,双方共识为红线
2. 🟡 **默认勾选不透明,信息架构未分层**:双方都指出新手友好不应牺牲专家用户

#### 主要分歧(1 项,< 3)
| 议题 | 投手 | 产品 |
|---|---|---|
| 智能定向对线索行业的影响 | 强烈反对,客资质量不可控 | 中性,认为可通过算法迭代解决 |

未收敛 → 升级人类决策。

#### 共识合理(1 项)
1. 默认值降低新手门槛的方向正确

---

## 示例 2 (略)
