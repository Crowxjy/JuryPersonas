# Mode Cookbook

本 cookbook 记录各场景的推荐 DAG、当前 execute 覆盖和依赖边界。它是使用说明,不是路线承诺;状态以 `tools/regression.py` 覆盖为准。

## 一、状态标记

| 标记 | 含义 |
|---|---|
| `e2e` | 已接入 `orchestrator --execute` 并纳入回归 |
| `script` | 脚本独立可用,但未接入 execute |
| `bundle` | 生成 prompt/bundle,由宿主 Agent/模型回填 |
| `optional` | 依赖可选资产或外部输入 |
| `planned` | 计划项存在,实现未完成 |

## 二、通用主链路

```text
brief harness
  -> observe
  -> persona-pick
  -> jury-react
  -> aggregate-consensus
  -> synthesize-tension
  -> synthesize-paths
  -> render-report
```

正式 Skill 使用时,`jury-react` 后可以停在 bundle,交给宿主 Agent/模型回填:

```bash
python3 orchestrator/pipeline.py \
  --brief-file tests/fixtures/prd_demo/brief.json \
  --artifact-file tests/fixtures/prd_demo/prd.md \
  --personas product-expert,ad-buyer \
  --execute --no-mock-llm \
  --runtime-dir /tmp/jp_host_agent
```

## 三、场景配方

| 场景 | 推荐 observe | 推荐 persona | 状态 |
|---|---|---|---|
| 短视频评审 | `mode/keyframe-extract` | `consumer-bao-mom-tier2`, `consumer-silver-male`, `consumer-bluecollar-male` | `e2e` |
| PRD 评审 | `mode/prd-extract` | `product-expert`, `ad-buyer` | `e2e` |
| 设计稿评审 | `mode/design-extract` | `ux-designer-senior`, `product-expert` | `e2e` |
| 单/多界面评审 | `mode/screen-extract` | `ux-designer-senior`, `consumer-genz-female` | `e2e` |
| 详情页评审 | `mode/detail-page-extract` | `consumer-bao-mom-tier2`, `local-business-expert` | `e2e` |
| 商品卡评审 | `mode/product-card-extract` | `consumer-genz-female`, `ad-buyer` | `e2e` |
| 营销文案评审 | `mode/copy-extract` | `consumer-genz-female`, `ad-buyer` | `e2e` |
| 视觉热力图 | `mode/heatmap` | 专家/UX | `e2e`, `optional` |
| 跨页动线 | `mode/cross-page` | UX/产品 | `e2e`(需 ≥2 metrics) |
| 红框问题图 | `mode/annotate-issues` | UX/产品 | `e2e` |
| 双分布 gap | `mode/aggregate-distribution-gap` | 采样陪审团 | `e2e` |

## 四、Persona 配方

### 显式画像

当前主链路支持两种显式画像方式。用户传 `--personas` 时严格使用用户指定角色:

```bash
--personas product-expert,ad-buyer
```

用户不传 `--personas` 时,`orchestrator/pipeline.py --execute` 会读取场景 frontmatter 的 `default_personas.role_ids`,并在输出 plan 的 `persona_selection.source` 标为 `scenario_default`。

适用场景:

- 用户明确指定角色。
- 需要复现实验。
- 场景样本较少,不应假装有真实分布。

### 临时拟合画像

`mode/persona-fit` 对应脚本:

```bash
python3 modes/jury/fit_persona.py --input tests/fixtures/fit_demo.json --emit json
```

当前状态:`e2e`。通过 `--include mode/persona-fit --fit-spec-file <fit.json>` 接入 execute。拟合画像落 runtime `personas/`,并带 fidelity 声明,不能冒充真实用户。

### 分布采样画像

`mode/persona-sample` 对应脚本:

```bash
python3 modes/jury/sample_personas.py \
  --dist tests/fixtures/distributions/merchant_current.json \
  --target-dist tests/fixtures/distributions/category_target.json \
  --count 3 \
  --brief
```

当前状态:`e2e`。通过 `--include mode/persona-sample --current-dist <json> --target-dist <json>` 接入 execute。采样结果写入 `runtime/personas/`,并进入 `jury-react`。

## 五、双分布 Gap 配方

`mode/aggregate-distribution-gap` 当前是独立脚本,用于比较商家当前联合分布和目标/品类联合分布:

```bash
python3 modes/aggregate/distribution_gap.py \
  --current-dist tests/fixtures/distributions/merchant_current.json \
  --target-dist tests/fixtures/distributions/category_target.json \
  --pretty
```

输出包括:

- `gap_rows`:每个桶的 current/target/delta。
- `summary.top_increase`:目标增配最明显的人群。
- `summary.top_decrease`:目标降配最明显的人群。
- `boundary.no_real_effect_claim_without_feedback_data`:明确没有真实反馈时不宣称效果。

当前状态:`e2e`。通过 `--include mode/aggregate-distribution-gap --current-dist <json> --target-dist <json>` 接入 execute。它读取双分布和 `aggregate-consensus` 结果,生成报告里的 F6 证据区。

## 六、HCI 配方

HCI 三件套来自 expert-roundtable:

| Mode | 当前能力 | 接入状态 |
|---|---|---|
| `mode/heatmap` | MSI-Net / AOI fallback | execute 已接入;A 档 fixture 回归通过 |
| `mode/cross-page` | 多页动线摘要 | execute 已接入;需要 ≥2 个 metrics.json |
| `mode/annotate-issues` | 红框标注图 | execute 已接入 |

MSI-Net 权重不是 Skill 主链路依赖。缺权重时,只影响 heatmap B 档深度显著性预测。

## 七、报告配方

当前报告链路:

- `modes/render/report.py`
- `reporting/markdown_renderer.py`
- `reporting/html_renderer.py`
- `reporting/design.md`
- `reporting/docx_xml_renderer.py`
- `reporting/lark_renderer.py` dry-run/local fallback

报告优先生成 HTML,布局根据 `scenario` 和实际 Mode 组合动态选择;Markdown 作为纯文本/飞书 fallback。DocxXML 当前生成 expert-roundtable 兼容草稿,严格飞书图片上传与 block_replace 仍由后续 lark-doc 环境执行。

## 八、回归命令

```bash
python3 tools/regression.py \
  --runtime-root /tmp/jp_regression \
  --pretty
```

回归覆盖是 cookbook 状态的判定依据。新增 mode 时必须补 fixture 或专项回归步骤。
