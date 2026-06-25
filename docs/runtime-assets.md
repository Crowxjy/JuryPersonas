# 运行依赖、评测数据与可选资产

本文回答两个边界问题:

1. 差评、人工标注、业务复盘数据用于什么。
2. heatmap 等 observe 模式需要的模型资产缺失时会影响什么。

## 一、差评和标注数据

差评、人工标注、业务复盘数据是**评测材料**,不是 Skill 运行依赖。

它们的作用:

- 建立 F7 对照评测集。
- 检查陪审团输出的 complaints/consensus 是否覆盖真实问题。
- 发现哪些场景、画像、observe mode 容易漏判。
- 给后续 persona 和 prompt 调优提供证据。

当前没有这些数据时:

- 不影响 Skill 安装。
- 不影响 Brief Harness、DAG plan、observe、jury-react、aggregate、synthesize、render。
- 不影响本地 seed regression。
- 只影响“真实效果评估”的可信度:只能证明工程链路可跑,不能证明线上问题覆盖率。

当前替代物:

- `evals/cases/seed_cases.jsonl`:用于验证评测 runner 的结构和回归链路。
- `tools/evaluation_runner.py`:用于后续把真实数据接入后直接跑 coverage。

## 二、heatmap 的模型资产

`modes/observe/heatmap.py` 有两档:

| 档位 | 依赖 | 用途 | 缺失影响 |
|---|---|---|---|
| B 档 | MSI-Net TensorFlow SavedModel | 深度显著性热力图 | 缺权重时无法跑高精度 heatmap |
| A 档 | `--aoi-json` | 规则热力图 fallback | 可解释,但不是深度模型预测 |

当前轻量 Skill 包没有内置 MSI-Net 权重,原因是权重约 96 MB,不适合直接进入轻量上传包。说明见 `assets/msinet_tf/README_model_weights.md`。

缺少 MSI-Net 权重时:

- 不影响 PRD、营销文案、设计稿文本描述、单界面文本描述、详情页、商品卡、短视频 keyframe JSON 等已接入 e2e 的主链路。
- 只影响需要像素级/视觉显著性的 heatmap B 档。
- `--engine auto` 会尝试加载本地权重或 HuggingFace 缓存;失败后需要用户确认是补权重还是接受 A 档 fallback。

## 三、当前 Skill 可用性判断

在没有真实差评/标注数据、没有 MSI-Net 权重的情况下,Skill 仍可用:

- 可以完成结构化评审和报告生成。
- 可以执行宿主 Agent/模型 reaction handoff。
- 可以跑当前本地完整回归(步数以 `tools/regression.py` 输出为准)。
- 不能宣称已有真实线上覆盖率。
- 不能宣称 heatmap B 档深度显著性可用,除非权重已恢复。

## 四、后续补齐顺序

1. 先导入真实反馈 JSONL,提升评测结论可信度。
2. 如真实项目需要视觉热力图,再恢复 `assets/msinet_tf/` 下的 MSI-Net SavedModel。
3. 如果只评审文本化的设计/页面/商品卡描述,暂不需要 heatmap 权重。
