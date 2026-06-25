# {{title}}

- **会话 ID**:`{{session_id}}`
- **场景**:{{scenario_name}}
- **评估对象**:{{artifact_title}}({{artifact_platform}} · {{artifact_duration}} 秒)
- **目标受众**:{{target_audience}}
- **关心维度**:{{key_concern}}
- **本次陪审员人数**:{{n_participants}} 位

---

## 一、Brief 摘要

{{brief_summary_block}}

---

## 二、反应分布矩阵(0-10)

| 角色 | 子类 | 完播倾向 | 互动倾向 | 转化倾向 | 信任度 | 推荐倾向 | 个人均分 |
|---|---|---|---|---|---|---|---|
{{score_matrix_rows}}
| **均值** |  | **{{avg_wan_bo}}** | **{{avg_hu_dong}}** | **{{avg_zhuan_hua}}** | **{{avg_xin_ren}}** | **{{avg_tui_jian}}** |  |

---

## 三、流失点热力(共识)

> 频次 ≥ 2 的卡点视为陪审员共识——优先改这些。

| 频次 | 卡点位置 | 关注点 | 提及人群 | 建议改法 |
|---|---|---|---|---|
{{consensus_rows}}

---

## 四、分歧点(单人卡点 + 评分断层)

{{divergence_block}}

---

## 五、各陪审员独立陈述

{{participants_block}}

---

## 六、边界声明

- 本报告只输出**盲点 + 流失点定位**,不预测完播率/转化率绝对值
- 本汇总只代表参与陪审的 {{n_participants}} 位画像反应,**样本量不代表真实分布**;真实分布采样能力见路线图 v0.3
- 陪审员之间在评审阶段**独立陈述**、不互相参考;主持人**只汇总不裁决**
- 临时拟合画像(`_fit_*`)和 draft 画像在每次回答末尾会自带保真度声明
