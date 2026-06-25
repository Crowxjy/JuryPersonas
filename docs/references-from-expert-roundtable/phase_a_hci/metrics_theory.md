# 四项指标的理论来源、可衡量性与仿真方法

本文件给报告提供"专业可信度"弹药:每个指标的学界出处、为什么客观可量化、以及如何还原真实实验数据。渲染报告时按需引用。

## 总览:四者的关联链

视觉特征(对比/尺寸/语义)
  → ① 注意力分布(看哪里,空间维度)
  → ② 视觉动线(先看后看,时间维度,是①的时间展开)
  → 当元素过多/杂乱 → ③ 认知负荷升高、动线变乱、注意力被稀释
  → 最终决定 ④ 覆盖与集中度(重要信息是否被有效触达)

③ 是 ①② 的成因/约束;④ 是 ①②③ 共同作用的结果。

---

## ① 注意力分布(Attention Distribution / Visual Saliency)

- **是什么**:逐像素的"被注视概率"图,刻画注意力如何在界面上分配。
- **理论来源**:视觉显著性理论(Itti & Koch, 1998 特征整合模型起源)。现代深度显著性模型被证明同时学到低层(对比/颜色)、中层(布局)、高层(语义)特征 — Hayes & Henderson (2021), "Deep saliency models learn low-, mid-, and high-level features to predict scene attention", https://trhayes.org/publication/hayeshenderson21a
- **为什么客观可衡量**:与真实眼动的吻合度有标准量化指标 AUC / NSS / CC / KLD,即 MIT/Tübingen Saliency Benchmark 体系 — Judd et al., "A Benchmark of Computational Models of Saliency to Predict Human Fixations", https://dspace.mit.edu/entities/publication/4085d89d-071a-496c-8275-733f1407e31c
- **本 skill 怎么算**:MSI-Net 深度模型预测显著图,再做校准。
- **UI 适配依据**:界面注视规律不同于自然图像 — UEyes (CHI 2023), https://github.com/YueJiang-nj/UEyes-CHI2023

## ② 视觉动线(Scanpath)

- **是什么**:预测的"注视(fixation)+ 扫视(saccade)"先后序列。
- **理论来源**:眼动序列模型 + F型/Z型/古登堡图阅读路径理论;视觉层级引导注意力 — NN/g, "Visual Hierarchy in UX", https://www.nngroup.com/articles/visual-hierarchy-ux-definition
- **为什么客观可衡量**:扫描路径预测有专门评测(Normalized Scanpath Saliency 等) — UEyes supplementary, https://yuejiang-nj.github.io/Publications/2023CHI_UEyes/project_page/supp.pdf
- **本 skill 怎么算**:对检测出的热点按"入口先验(左上/上方)+ 显著性 + 扫视成本"排序,给出注视顺序;空间真值以显著图为准。
- **注意**:这是热点级别的顺序近似,非逐注视点轨迹。报告需如实说明。

## ③ 认知负荷 / 视觉复杂度(Cognitive Load / Visual Complexity)

- **是什么**:界面让用户处理信息所需的脑力开销。
- **理论来源(认可度最高,务必标注)**:
  - Rosenholtz 等的 **Feature Congestion(特征拥挤度)** 杂乱度模型,已证明与人对"视觉杂乱"的主观评分高度相关 — Rosenholtz et al., "Feature congestion: A measure of visual clutter", https://www.researchgate.net/publication/239450341_Feature_congestion_A_measure_of_visual_clutter
  - 针对移动 GUI 的视觉复杂度测量模型(多元回归建模)— "A Measurement Model for Visual Complexity in HCI", https://www.mdpi.com/2079-9292/14/5/942
- **为什么客观可衡量**:由边缘密度、颜色多样度、亮度熵、焦点竞争数等纯计算得出。
- **本 skill 怎么算**:edge_density(Sobel 边缘比)、color_variety(量化色数)、luminance_entropy(亮度香农熵)、focal_competition(同强度热点数),加权成 0–100 composite,并列出各子项让下游可自定义权重。

## ④ 首屏覆盖与注意力集中度(Coverage & Concentration)

- **是什么**:核心元素是否落在首屏、首屏注意力占比、注意力是聚焦还是分散。
- **理论来源**:首屏/折叠线研究 + "注意力是有限资源、需被有效引导"的视觉层级理论 — NN/g, https://www.nngroup.com/articles/visual-hierarchy-ux-definition
- **为什么客观可衡量**:above_fold_attention_ratio(首屏注意力占比)、attention_gini(集中度基尼系数,0=均匀 1=全集中于一点)、hotspots_above_fold 等均为算出的比值。
- **本 skill 怎么算**:对显著图按折叠线积分求占比;对全图显著值求基尼系数。

---

## ⑤ 页面语义层(Semantic Layer / 只测不判)

> ①~④ 测的是"像素层"的显著与负荷;本层测的是"语义层"的事实——界面写了什么、模块怎么排、谁指向谁。**只采集事实,不下判断**(读不读得懂、模块关系合不合理归专家圆桌的产品专家)。产出落 `semantic.json`,在 HCI 报告里以「页面语义层」模块如实呈现。

- **是什么**:对界面做 OCR + 结构标注,逐模块记录「序号 / 文案 / 类型」、各模块「承诺(claims)」、模块间「关系(relations,只标类型不下判断)」、「自上而下阅读序(reading_order)」。
- **理论来源**:
  - 信息架构(Information Architecture)——模块如何组织、自上而下的层级关系 — NN/g, https://www.nngroup.com/articles/information-architecture-study-guide
  - 格式塔分组(Gestalt grouping)——相邻、相似元素被读作同一模块,用于把视觉块切成语义模块。
  - 指代消解(Coreference / Anaphora resolution)——文案里"它/该权益/上述任务"等指代指向哪个模块,据此连出指代关系。
- **为什么客观可采集**:OCR 文案、模块边界、文案里的承诺句式("完成 X 可解锁 Y")、指代词与被指代对象,均为可从界面直接读取或抽取的事实,不含主观评价。
- **本 skill 怎么算**:OCR 取文案 → 按版面位置与格式塔分组切模块、标类型(标题/入口按钮/任务卡/权益卡/说明文案/状态标签等)→ 从承诺句式抽 claims → 从指代与逻辑连接词标 relations 的**类型**(并列/因果/解锁依赖/指代)→ 按版面从上到下排 reading_order。
- **字段结构(`semantic.json`)**:`blocks[]`(序号 / 文案 / 类型 / **`bbox:[x0,y0,x1,y1]`** 模块在原图上的像素包围框)、`claims[]`(模块 → 承诺原文语义)、`relations[]`(关系类型 / 涉及模块,只标类型)、`reading_order[]`(自上而下模块序)。
  - **`bbox` 说明(只测不判)**:OCR 切模块时本就按版面位置分组,把每个模块的像素包围框 `[左,上,右,下]` 如实落盘即可——这是**客观坐标事实**,不含判断。它服务于 Phase B 产品专家走查生成「红框标注原图」(在出问题的模块 bbox 上画红框),坐标归 A、判断归 B,分工不破。
- **红线**:本层**只测不判**——禁止出现"好/坏/应该/不清晰/容易误解"等判断词;通顺与否、模块关系是否合理的**判断**归 Phase B 产品专家的「单页面可理解性走查」(逐页)与「页面衔接可理解性走查」(逐对相邻页面,仅多界面)。

---

## 仿真:如何尽可能还原真实实验数据

业界用预测式显著性替代昂贵的真人眼动,与真实眼动相关性可达约 85–95% — eyecaptain, https://eyecaptain.io/en/heatmap-analysis-guide (商业工具自报数据,作参考)。本 skill 采用以下经基准验证的还原手段:

1. **三层特征建模**:与真实眼动相关性最高的是高层语义 + 低层显著性(Hayes & Henderson 2021)。
2. **中心偏好(center bias)**:基准证明带中心偏好 + 适度模糊的模型最贴近真实注视(Judd et al. 2012)。
3. **中央凹高斯平滑**:模拟中央凹 ~2° 视野,提升吻合度(同上基准)。
4. **UI 场景适配**:按界面而非自然图像调参(UEyes)。

**可信度标签(报告必带)**:本结果为预测式,适用于上线前设计自查,**不能完全替代真实用户眼动测试**。

## 提升准确性的可选升级(C 档,未来)

若需"自带可信度自证":可用 MIT300 / UEyes 公开眼动数据反算 AUC/NSS/CC,把分数写进报告当可信度标签。需引入参考数据集,较重,默认不启用。
