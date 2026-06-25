# 00 · 三阶段流水线总览(Pipeline)

> **说人话**:这份文件是整个 skill 的"地图"。Expert-Roundtable 把原来三个独立 skill 串成一条流水线——先用机器量出客观数据(A,含像素显著性 + 页面语义层,只测不判),再让三位专家背靠这份数据吵架(B,含产品专家的单页面可理解性走查[逐页]与页面衔接可理解性走查[逐对相邻页面]),最后主持人把吵架升级成两种决策风格的建议(C)。**最终只产出一份三段式圆桌报告,⛔ 不再有任何附录**——机器测出的热力图与客观读数全部内嵌在第二节「页面测评 → 客观数据速览」表格里。

---

## 一、三阶段是什么 / 干什么

| 阶段 | 原 skill | 角色 | 输入 | 产出 |
|---|---|---|---|---|
| **A · HCI 客观分析** | hci-analysis | 机器(深度显著性引擎) | 界面截图 | 热力图 + 4 指标 + `metrics.json` + 页面语义 `semantic.json` + HCI 报告 |
| **B · 三角色圆桌** | roundtable-facilitator | 投手 / 产品 / 本地商家 | A 的客观报告 + semantic.json + 评审材料 | 共识区 + 分歧区(角色 JSON)+ 产品专家单页面可理解性走查(逐页)+ 页面衔接可理解性走查(逐对相邻页面,仅多界面) |
| **C · 决策透镜** | roundtable-decision-lens | 主持人(张力归纳者) | B 的共识/分歧 | 核心张力(通俗一句话)+ 🅰/🅑 决策路径(挂靠决策偏好因子,纯名称)+ 倾向提示 |

---

## 二、数据怎么流(关键)

```
界面截图(1 个或多个)
   │
   ▼  Phase A  scripts/generate_heatmap.py + metrics_theory(多界面 → 逐个各跑一次)
HCI 客观知识(每界面:热力图 + 4 指标 + metrics.json + HCI 报告)
   │
   │  ★ 即时生成的客观知识,在角色发言前共享给全部 3 个角色(多界面则全集一并共享)
   ▼  Phase B  workflow.md
三角色各自独立陈述(背靠 HCI 数据 + 各自 knowledge_base)
   │
   ▼  阶段 2:共识 / 分歧识别
共识区(直接纳入) + 分歧区(最多 3 个)
   │
   ▼  Phase C  facilitator_prompt.md(张力归纳 5 步)
核心张力(通俗一句话) → 🅰/🅑 决策路径(挂靠决策偏好因子,纯名称) → 倾向提示
   │
   ▼  report_assembly.md
圆桌报告(三段:一、需求背景 / 二、页面测评 / 三、圆桌纪要)
   热力图与客观读数全部内嵌第二节「客观数据速览」表格,⛔ 无任何附录
```

**核心理念**:HCI 数据是「即时生成的客观知识」,区别于各角色静态、提前准备好的 knowledge_base。三方主观判断必须建立在这份客观数据之上。

---

## 三、客观知识 vs 静态知识(两类知识)

| | 静态知识(角色 knowledge_base) | 即时知识(phase A HCI 报告) |
|---|---|---|
| 来源 | 多维表格「切片标注库 v1」,打包进 skill | 每个项目跑 phase A 现场生成 |
| 范围 | 行业经验、设计原则、平台规则 | 本次被测界面的真实注意力/动线/指标 |
| 共享性 | 按 `belongs_to` 分角色 + shared | 全部 3 角色共享 |
| 更新方式 | 改表格 + 重跑 build_knowledge_base(见 knowledge_base_sync.md) | 每次评审重新跑 generate_heatmap |

---

## 四、阶段边界(红线对齐)

- A **只测不判**:HCI 报告只陈述客观事实,不写"好/坏/应该",改版方案留给 B/C。**页面语义层(semantic.json)同样只测不判**——只采集"看见了什么、谁指向谁",不判断通顺/合理。
- B **只评不裁**:角色只给 reasonable/unreasonable,主持人只整理共识/分歧,不替角色发言。**单页面可理解性走查(逐页)与页面衔接可理解性走查(逐对相邻页面,仅多界面)均由产品专家主导**,基于 semantic.json 事实做判断(单页:读不读得懂、模块关系合不合理;衔接:从前页跳后页预期是否有落差)。
- C **只给路径不替人选**:两条决策路径(挂靠决策偏好因子,纯名称、不带 ID 序号)+ 倾向提示,核心张力用通俗一句话,标题为「决策建议」(不带"双画像"字样),最终决策权归人类。

---

## 五、关键引用
- `references/phase_a_hci/` — HCI 引擎 / 指标理论 / HCI 报告模板
- `references/phase_b_roundtable/workflow.md` — 三角色圆桌流程
- `references/phase_b_roundtable/roster.md` — 三角色名册
- `references/phase_c_decision/facilitator_prompt.md` — 张力归纳 5 步
- `references/integration/shared_knowledge.md` — HCI 客观知识如何共享给角色
- `references/integration/knowledge_base_sync.md` — 知识库与多维表格的同步流程
- `references/integration/report_assembly.md` — 报告拼装(三段正文,热力图内嵌客观数据速览,⛔ 无附录)
