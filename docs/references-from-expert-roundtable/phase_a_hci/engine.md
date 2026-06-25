# 引擎细节与 A 档回退

## B 档(默认):MSI-Net 深度显著性模型

- 模型在 `assets/msinet_tf`(TF SavedModel,bundled,约 96MB)。
- 输入:任意尺寸 RGB;脚本内部按高度 resize 到 512、VGG 风格 BGR 均值减除。
- 输出:单通道显著图,上采样回原尺寸。
- **沙箱注意**:必须单线程,否则 TF 触发 `pthread_create() failed`。脚本已对
  `OMP_NUM_THREADS / TF_NUM_INTRAOP_THREADS / TF_NUM_INTEROP_THREADS` 等做 setdefault=1。
  若直接调用 TF 出现 pthread 错误,显式 `export OMP_NUM_THREADS=1 TF_NUM_INTRAOP_THREADS=1 TF_NUM_INTEROP_THREADS=1`。
- 依赖:`tensorflow-cpu`(Python 3.13 用 2.20+)、`numpy`、`scipy`、`pillow`。
  安装:`pip install --user --break-system-packages tensorflow-cpu scipy pillow`

## A 档(回退):规则加权

仅当 B 档不可用时使用。需要传 `--aoi-json`,内容是你目测界面后标注的主要元素:

```json
[
  {"label": "主CTA按钮", "x": 627, "y": 972, "intensity": 0.9, "radius": 95},
  {"label": "主标题",   "x": 300, "y": 685, "intensity": 0.9, "radius": 150}
]
```

- `x,y`:元素中心像素坐标(原图坐标系)
- `intensity`:0–1,按显著性规律给(人脸/大数字/主CTA高,正文低)
- `radius`:影响半径像素

引擎会叠加高斯 blob,再加中心偏好 + 上半部加权 + 平滑。完全可解释,但保真度低于 B 档,报告需注明 engine=A-rule。

## metrics.json 字段说明

```
meta.engine                 引擎标识(B-MSI-Net / A-rule)
meta.image_size             [W,H]
meta.calibration            校准手段列表
meta.confidence_note        可信度说明
attention_distribution.hotspots[]   {cx,cy,peak,bbox,attention_share}
scanpath[]                  {order,xy,peak,attention_share}
cognitive_load              {composite_score,level,edge_density,color_variety,
                             luminance_entropy,focal_competition}
coverage                    {fold_px,above_fold_attention_ratio,attention_gini,
                             hotspots_above_fold,hotspot_count,hot_pixel_ratio}
```

下游 skill(如专家圆桌)可直接读取:投手关注 attention_distribution.hotspots 的
attention_share;产品关注 cognitive_load;设计关注 coverage + cognitive_load 子项。
