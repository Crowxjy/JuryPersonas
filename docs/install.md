# 安装与运行依赖

Jury Personas 以 Skill 形态运行。宿主 Agent/模型负责理解用户需求、判断 Brief 是否充分、回填 `jury-react` 结果;仓库内脚本只做结构校验、DAG 编排、observe、聚合和报告生成。

## 最小运行

只跑 Brief plan、文本类 observe、jury-react bundle、consensus 和报告时,主要依赖 Python 3 标准库。

推荐安装轻量依赖:

```bash
python3 -m pip install -r requirements.txt
```

这些依赖用于:

| 依赖 | 用途 |
|---|---|
| `jsonschema` | Brief / contract 严格校验;缺失时 `brief_validator.py` 会软跳过 schema 层 |
| `numpy` / `scipy` / `Pillow` | HCI A 档 heatmap、图片标注、fixture 回归 |
| `huggingface_hub` | MSI-Net B 档权重可选下载辅助 |

## 可选重依赖

`mode/heatmap` 的 B 档需要 MSI-Net TensorFlow SavedModel 和 TensorFlow runtime。它不是默认 Skill 主链路依赖,不写入 `requirements.txt`。

如果真实项目需要 B 档深度显著性:

1. 按 [assets/msinet_tf/README_model_weights.md](../assets/msinet_tf/README_model_weights.md) 恢复或下载模型权重。
2. 在业务环境中安装与本机兼容的 TensorFlow。
3. 用 `--hci-engine B` 或 `--hci-engine auto` 运行专项验证。

缺少 B 档时,PRD、短视频、营销文案、设计稿文本描述、单界面文本描述、详情页、商品卡等主链路不受影响。

## 快速验证

```bash
python3 tools/regression.py \
  --runtime-root /tmp/jp_regression \
  --pretty
```

回归只写 `/tmp` 下的运行产物,不会修改源码。

## 默认陪审团

`jury_review.py` 和 `orchestrator/pipeline.py --execute` 支持不传 `--personas`;此时会按场景选择保守默认组合。显式传入 `--personas` 时永远以用户指定为准。

| 场景 | 默认角色 |
|---|---|
| 短视频 | `consumer-bao-mom-tier2`, `consumer-silver-male`, `consumer-bluecollar-male` |
| PRD | `product-expert`, `ad-buyer` |
| 设计稿 | `ux-designer-senior`, `product-expert` |
| 单/多界面 | `ux-designer-senior`, `consumer-genz-female` |
| 详情页 | `consumer-bao-mom-tier2`, `local-business-expert` |
| 商品卡 | `consumer-genz-female`, `ad-buyer` |
| 营销文案 | `consumer-genz-female`, `ad-buyer` |
