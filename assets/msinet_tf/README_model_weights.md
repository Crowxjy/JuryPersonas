# 关于深度显著性模型权重(msinet_tf)

本轻量包**未内置** B 档深度显著性模型(MSI-Net)权重(约 96 MB),以便通过上传网关。

## 影响
- `modes/observe/heatmap.py` 默认 `--engine auto`:加载 B 档失败时可回退 A 档规则引擎,但 A 档必须显式提供 `--aoi-json`。
- 发生 B→A 降级时脚本会在 stderr 打出 `[DOWNGRADE B->A]`,上层 Harness 必须暂停并让用户确认「修复 B 档」还是「接受 A 档」。
- 想用 B 档高精度热力图,需把权重放回 `assets/msinet_tf/`。

## 恢复 B 档(可选)
把 MSI-Net SavedModel 放到本目录下,形成:
```
assets/msinet_tf/
├── saved_model.pb
├── keras_metadata.pb
└── variables/
    ├── variables.data-00000-of-00001
    └── variables.index
```
然后用 `--engine B` 验证可正常加载。完整权重见技能维护者归档的完整包(`Expert-Roundtable.skill`,89 MB)。
