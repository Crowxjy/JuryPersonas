# 角色名册 (Roster)

> **说人话**:这张表就是"圆桌请了哪几位专家"。现在固定请 3 位——投手、产品、本地商家。每次开圆桌三位都到场,谁也别缺席,这样视角才全。

## 角色列表(v2 · 三角色)

| 角色 | 路径 | 触发权 | 发言侧重 |
|---|---|---|---|
| 广告投手专家 | `experts/ad-buyer-expert/SKILL.md` | 始终召唤 | 议题含投放/转化/ROI/起量/合规时优先发言 |
| 产品专家 | `experts/product-expert/SKILL.md` | 始终召唤 | 议题含交互/信息架构/设计原则/用户体验时优先发言 |
| 本地服务商家专家 | `experts/local-business-expert/SKILL.md` | 始终召唤 | 议题含门店经营/上手成本/获客核销/回本时优先发言 |

## 召唤规则(防膨胀)
- 单次圆桌**固定 3 个角色**(投手 + 产品 + 本地商家),三方视角互为对照,避免单边话术。
- 即使议题明显偏向某一方,**仍必须召唤另外两方**,以保留对照视角。
- 三方对同一议题的判断差异,正是 phase C 决策透镜要归纳的「张力」来源。

## 知识库来源(统一)
三个角色的知识库均来自同一个多维表格「圆桌评审-切片标注库 v1」,按 `belongs_to` 字段拆分:
- `shared`(607 条)→ `experts/shared/knowledge_base.md`,**三角色共享**
- `product_expert`(402 条)→ 产品专家
- `ad_buyer`(103 条)→ 投手
- `local_business`(22 条)→ 本地商家(v2 新增角色)

更新知识库 = 改多维表格后重跑 `scripts/build_knowledge_base.py`(见 `references/integration/knowledge_base_sync.md`),**不要手工编辑 md**。

## 增删角色
- **新增**:在多维表格 `belongs_to` 增加新枚举值 → 复制一个 `experts/<新角色>/` 目录写 SKILL.md → 在本表加一行 → 在 `scripts/build_knowledge_base.py` 的 `ROLE_MAP` 注册映射 → 重跑脚本。
- **删除**:从本表移除该行即可;圆桌不引用本表外角色。
