# 圆桌评审报告 · 飞书 XML 模板(默认输出格式 · 三角色版)

> **说人话**:这是最终报告长什么样的模板,严格对齐评审模板 wiki。固定 3 个一级章节:**一、需求背景 → 二、页面测评(客观数据速览 + 单页可理解性走查)→ 三、圆桌纪要(共识要改的 + 有分歧的 + 共识做的好的 + 待办总结 + 决策建议)**;⛔ **不再有任何附录**——HCI 热力图与客观读数全部内嵌进第二节「客观数据速览」表格。表头统一灰底,高亮框用橘色,只放热力图不贴原图,能用表格就用表格,结论性/矛盾性描述黄色高亮或加粗。全文通俗、无黑话,切片 ID 节末灰字汇总不内联。**框架不可改。**

> 本模板用于通过 lark-doc 的 `+create` / `+update --command overwrite` 命令直接产出飞书 docx。
> **doc-format 必须为 `xml`,api-version 必须为 `v2`**。
> 飞书文档标题统一为:`【圆桌评审】<对象简称> - YYYY-MM-DD`。

---

## 样式约定(强制)

| 区域 | 规范 |
|---|---|
| 顶部信息块 | `<callout emoji="📌" background-color="light-blue" border-color="blue">` 装载评审对象/方式/角色/时间 |
| 表格表头 | **统一使用 `background-color="light-gray"`**,不用红/黄/绿/橙彩色区分(用户偏好) |
| **高亮/强调框配色** | 需要突出的 callout(核心张力、重要提示等)**统一用橘色**:`<callout background-color="light-orange" border-color="orange">`,⛔ 不用灰色底(用户明确反馈灰色丑)。仅顶部信息块沿用 `light-blue`、推测提示用 `light-yellow`。 |
| 表格用法 | **能用表格就用表格**:各分析段凡可结构化对比/罗列的内容一律用 `<table>` 结构化呈现,严禁退化为长 bullet;纯顺序步骤才用有序列表 |
| 链接 | 评审对象 URL 用 `<a type="url-preview" href="...">显示名</a>` |
| 列宽 | 每张表必须显式 `<colgroup><col width="..."/></colgroup>`,避免列宽塌缩 |
| **图片只放热力图(唯一例外:走查问题标注列)** | 正文涉及界面图时**只嵌注意力热力图**,⛔ 不贴原始设计稿截图(原图仅供工程上生成热力图);热力图**只嵌入第二节「客观数据速览 → 单页面分析表」第一列「页面热力图」单元格内**,⛔ 不放正文别处、⛔ 不另起附录。**唯一例外**:第二节「单页面可理解性走查」表的**「页面问题标注」列**允许嵌**红框标注的原图**(原始截图 + 红框框出出问题的模块),用于直观指出问题位置;此例外仅限该列 |
| **🔴 图片必须进单元格(硬性红线)** | 所有图片(热力图、红框图)**必须落在目标 `<td>` 单元格内部**,⛔ 严禁成为表格的兄弟块。落库后用 **`block_replace`** 把含占位符(`IMG_HEAT_Sx`/`IMG_ISSUE_Sx_NN`)的整个单元格 block 替换为内含 `<img src="token"/>` 的单元格 XML;⛔ **禁止**用 `+media-insert --selection-with-ellipsis` 嵌单元格图(会插成表格后的独立兄弟块 = 图跑到表格外)。`+media-insert`/`+upload-file` 仅用于上传本地图拿 image token |
| **🔴 图片必须保持原始宽高比(硬性红线)** | 嵌入的 `<img>` ⛔ 严禁被单元格拉伸变形,**必须按原图真实宽高比设置 width/height**(按目标列宽等比缩放)。生成报告前先用 `identify`/PIL 读出原图像素宽高,等比换算出 width/height 写进 `<img>`;⛔ 不得只给 width 不给 height,也不得给与原图比例不符的尺寸 |
| **结论性/矛盾性描述要高亮** | 凡结论性判断(议题判断、走查判断、共识/分歧定性、决策倾向)与具矛盾性/需关注的描述(冲突点、风险点、与 HCI 数据相悖处),用**黄色文字高亮 `<span background-color="yellow">…</span>`** 或**加粗 `<b>…</b>`** 在视觉上突出;表格内"结论:/观点:/建议:"等前缀沿用 `<b>` 加粗 |
| **指标必须带解释** | 「界面客观描述」列里每个 HCI 指标**不能只写数值**,必须紧跟一句"这个数值的高/低意味着什么"(对用户体验的客观含义),例:"首热点注意力份额 0.42——偏高,说明视线高度集中在单一区域,其余信息容易被略过" |
| **解释性文案用引用块** | 模块的"是什么/怎么算/背景说明"统一用引用块(blockquote)放在该模块**末尾**,正文先给判断与数据 |
| **语义通顺、无黑话** | 全文通俗可读,**禁止黑话/行话/未解释简写**。凡"N 屏 / N 态 / N 档"等压缩表达,首次出现必须展开(如"4 屏"→"4 个界面 / 4 屏页面";"6 态权益折叠为 3 态"→"权益从 6 种状态精简为 3 种状态")。专名/缩写首次给全称。**每条要点把判断放最前**(先给判断,再给依据)。 |
| **禁止元描述标签(但保留内容前缀)** | ⛔ 不要把"一句话结论""结论先行""一句话总结""一句话总览"等**元描述词**当成标题或表头写出来——直接把结论本身放最前即可。✅ 但 wiki 模板里的"结论:""观点:""建议:"这类**内容前缀保留**(它们标的是内容角色,不是元描述),沿用 `<b>` 加粗。 |
| **切片 ID 视觉弱化(形式 C)** | **正文句中不内联** `id: xxx_062_02`;改为在**每节末尾**用一行灰字小字汇总:`<p><span text-color="gray"><i>本节引用:xxx_062、xxx_071</i></span></p>`。去掉 `id:` 前缀与 `_02` 内部子码,只留可溯源主码。决策偏好因子用**纯名称**,不带 A1/B3 等 ID 序号。 |

### 标题层级与排版编号(强制)

- **一级标题(H1)用中文数字**:一、二、三、四、五、六、七…
- **二级标题(H2)用带圈数字**:①、②、③…
- 正文数字罗列用**有序列表**(`<ol>`),**不要**用"一、二、…"中文序号去做正文罗列。
- **分段 + 有序列表降低阅读压力**:长段落拆成短段或有序列表;能用表格对比/罗列的一律用表格(见上"表格用法")。
- **解释说明性文案用引用块放模块后**:某模块"是什么/怎么算/背景"的解释统一用 blockquote 放该模块末尾,正文先给判断与数据。

---

## 章节结构(三段式,顺序固定 · 对齐 wiki 模板)

> 本结构严格对齐评审模板 wiki(`document_id: Wumxdn0LioQB2ex3LaVcDQ73nUg`)。**正文固定三个一级标题:一、需求背景 / 二、页面测评 / 三、圆桌纪要**;⛔ **不再有任何附录**——HCI 热力图与客观读数全部内嵌进第二节「客观数据速览」表格。**框架不可改**,仅替换文案与数据。

**顶部信息块**(不算入一级标题):`<callout emoji="📌" background-color="light-blue" border-color="blue">` 装载 评审对象 / 评审方式 / 参与角色 / 评审时间。

1. **一、需求背景** — 先放一个 `<callout emoji="💡" background-color="light-orange" border-color="orange">` 一句话点明产品定位与主链路;再用三级标题 `<h3>` 分述:**业务起因** / **核心改动与最终方案**(最终方案用有序列表 `<ol>` 列主链路步骤)。

2. **二、页面测评** — 下设**三个**三级标题:
   - **`<h3 seq="1" seq-level="1">客观数据速览`** — 先放一个 `<callout emoji="💡" background-color="light-orange" border-color="orange">` 总览全部界面的关键客观读数(认知负荷区间、首热点份额、首屏可见度走势,只测不判);再给**两张表**:
     - **单页面分析表**(3 列:`页面热力图` / `界面客观描述` / `对用户的影响`)。每个界面一行;**`页面热力图`列直接嵌入该界面的注意力热力图**(界面名 bullet 下方用 `IMG_HEAT_Sx` 占位,落库后用 **`block_replace`** 把整单元格换成内含 `<img src="token" width=".." height=".."/>` 的单元格,图进单元格内、保持原比例;⛔ 不贴原始设计稿、⛔ 不放正文别处或附录、⛔ 不用 selection-with-ellipsis);`界面客观描述`列用嵌套 bullet 列 4 项 HCI 指标,**每个指标不能只写数值,必须紧跟一句"高/低意味着什么"的客观解释**;`对用户的影响`列给客观影响判断(结论性描述加粗或高亮)。
     - **跨页面动线分析表**(2 列:`观察` / `逐页读数`)。每行一个跨页面观察(动线接力 / 认知负荷走势 / 首屏可见度走势 / 注意力集中度走势),右列给逐页数值。**单界面时本表可省略。**
   - **`<h3>单页面可理解性走查`** — **逐页评测,用一张大表 + colspan 分组标题行**(每个页面一个 `<td colspan="4">` 分组标题行,加序号 + 加粗,组内 4 列:`走查项` / `页面问题标注` / `严重度` / `判断`):产品专家主导,基于 phase A 的 semantic.json(事实)+ 业务目标,**对每个页面**各按 5 条清单判断单页能否从上到下读懂(模块关系自洽 / 承诺-路径衔接 / 指代链完整 / 自上而下可读懂业务 / 零状态负向暗示)。**把判断放最前**(不写"结论先行"字样)。
     - **`页面问题标注`列**:该走查项若判定有问题,本列嵌**对应界面「红框标注原图」**(原始截图上用红框框出出问题的**模块**,模块级,框 semantic.json 该模块 bbox);占位 `IMG_ISSUE_Sx_NN`(x=界面序号,NN=走查项序号),落库后用 **`block_replace`** 把整单元格换成内含 `<img src="token" width=".." height=".."/>` 的单元格(图进单元格、保持原比例);无问题则填「—」不嵌图。红框图由 `scripts/annotate_issues.py`(PIL)生成。**这是「图片只放热力图」铁律的唯一例外**——仅本列允许放红框原图,其余正文仍只放热力图。
   - **`<h3>页面衔接可理解性`** — **逐对相邻页面评测,用一张大表 + colspan 分组标题行**(每对相邻页面一个 `<td colspan="3">` 分组标题行,格式「页面A → 页面B」,加序号 + 加粗,组内 3 列:`走查项` / `严重度` / `判断`,**无「页面问题标注」列**):产品专家主导,判断从前页跳到后页**预期是否有落差**(用户在前页形成的预期,后页能否承接;有无断层、跳转突兀、看不到想看的内容),可发散更多维度。**仅多界面时有本模块**(单界面可省略)。
     - 节末用灰字汇总本节引用。

3. **三、圆桌纪要** — 下设五个三级标题,依次:
   - **`<h3 seq="1" seq-level="1">共识要改的`** — 表格(5 列:`#` / `议题` / `优先级` / `问题描述` / `整改建议`)。问题描述列内用有序列表分列「产品专家 / 本地商家 / HCI 佐证」三方依据;整改建议列用有序列表。
   - **`<h3>有分歧的`** — 表格(5 列:`#` / `议题` / `<角色1>` / `<角色2>` / `折中方案`)。每方立场一列(本模板默认两角色:产品专家、本地服务商家;若启用三角色则相应增列),各列内用「**观点** + 有序列表论据」。
   - **`<h3>共识做的好的`** — 表格(3 列:`#` / `议题` / `合理性说明`)。合理性说明列内用「**加粗总判断** + 有序列表(产品专家 / 本地商家 / HCI 佐证)」。
   - **`<h3>待办总结`** — 表格(5 列:`#` / `优先级` / `具体待办` / `来源` / `建议时间节点`)。优先级用 P0/P1/P2;来源回指「共识要改的 #N / 有分歧的 #N」。
   - **`<h3>决策建议`** — 来自 phase C 决策透镜:先用 `<ul>` 点出决策对象(如"权益与任务模块的信息密度策略");再用 `<blockquote>` 一句通俗话讲清**核心分歧**(同轴两极在纠结什么,不堆术语);最后给 **🅰 / 🅑 两条决策路径表**(列:`一句话` / `核心动作` / `验证方式` / `适用前提` / `决策偏好因子`),决策偏好因子用**纯名称、不带 A1/B3 等 ID 序号**。

4. **`<hr/>` + 全文引用** — 正文末尾加分隔线,再用一行灰字 `<blockquote>` 汇总「本报告由 Expert-Roundtable 圆桌评审技能产出。全文引用切片:…」。**报告到此结束,⛔ 无任何附录。**

> **重要**:
> - **⛔ 不产出任何附录**:报告只有三段正文,HCI 热力图与客观读数全部内嵌第二节「客观数据速览」表格;⛔ 不再有「附录 0 / 附录 A/B/…/N」整套机制。
> - 第二节「页面测评」**客观在前、判断在后**,共 **3 个子级**:子级「客观数据速览」是 Phase A 客观事实(只测不判);子级「单页面可理解性走查」(逐页)与「页面衔接可理解性」(逐对相邻页面)是 Phase B 产品专家判断(只评不裁),两层严格分工不可混淆。
> - **热力图嵌入位置铁律**:每个界面的注意力热力图**只嵌「单页面分析表」第一列「页面热力图」单元格内**(界面名 bullet 下方,`IMG_HEAT_Sx` 占位 → **block_replace** 把整单元格换成内含 `<img>` 的单元格,图进单元格、保持原比例),⛔ 不用 selection-with-ellipsis、⛔ 不放正文别处、⛔ 不另起附录;有几个界面表里就加几行。
> - **指标必须带解释**:「界面客观描述」列每个 HCI 指标不能只写数值,必须紧跟一句"高/低意味着什么"的客观含义。
> - 第三节「圆桌纪要」内部顺序固定:**共识要改的 → 有分歧的 → 共识做的好的 → 待办总结 → 决策建议**,不可调换。
> - 「有分歧的」只装载**真正立场对立**且仅靠折中无法消除的议题;某方无明确立场填"—"。"配套条件可同步满足"的议题视为**共识**(进「共识要改的 / 共识做的好的」),不进「有分歧的」。
> - **结论性/矛盾性描述要高亮**:结论性判断与具矛盾性/需关注的描述,用 `<span background-color="yellow">…</span>` 或 `<b>…</b>` 突出。
> - **每节末尾**用一行灰字汇总本节引用切片(形式 C),正文句中不内联 `id:`。
> - **多界面**:第二节「客观数据速览」用单页面分析表(每界面一行,各嵌自己的热力图)+ 跨页面动线分析表;单界面时单页面分析表只一行、跨页面动线分析表可省略。**无论几个界面,都不产出附录**(见 `references/integration/report_assembly.md`)。
> - **框架不可改**:一级标题固定「一、需求背景 / 二、页面测评 / 三、圆桌纪要」三个,不得增删或重命名;各三级标题名称对齐 wiki 模板。

---

## XML 骨架(可直接复制改文案)

```xml
<title>【圆桌评审】<对象简称>履约/主链路评审 - YYYY-MM-DD</title>

<callout emoji="📌" background-color="light-blue" border-color="blue">
<p><b>评审对象：</b><对象全称>设计稿(共 N 个界面:界面1 / 界面2 / …)</p>
<p><b>评审方式：</b>三阶段(HCI 客观分析 → 角色独立陈述 → 分歧识别 → 决策收敛)</p>
<p><b>参与角色：</b>产品专家、本地服务商家</p>
<p><b>评审时间：</b>YYYY-MM-DD</p>
</callout>

<h1>一、需求背景</h1>
<callout emoji="💡" background-color="light-orange" border-color="orange">
<p><一句话点明产品定位 + 主链路:用一句话说清这是什么产品、解决谁的什么问题、主链路是哪几步></p>
</callout>

<h3>业务起因</h3>
<p><业务起因:目标用户的真实处境与痛点,平台为什么要做这个产品></p>

<h3>核心改动与最终方案</h3>
<p><核心改动一句话(在什么已有框架上扩展、压成什么主链路)>:</p>
<ol>
<li seq="auto"><b>步骤1</b>:...</li>
<li seq="auto"><b>步骤2</b>:...</li>
<li seq="auto"><b>步骤3</b>:...</li>
</ol>

<h1>二、页面测评</h1>

<h3 seq="1" seq-level="1">客观数据速览</h3>
<callout emoji="💡" background-color="light-orange" border-color="orange">
<p><全部界面关键客观读数总览(只测不判):认知负荷区间与走势、首热点份额走势、首屏可见度走势,指出最低/最高点对应哪一屏。多界面才写走势,单界面写本屏读数。></p>
</callout>
<p><b>单页面分析</b></p>
<table>
<colgroup><col width="220"/><col width="330"/><col width="190"/></colgroup>
<thead>
<tr>
<th background-color="light-gray"><p>页面热力图</p></th>
<th background-color="light-gray"><p>界面客观描述</p></th>
<th background-color="light-gray"><p>对用户的影响</p></th>
</tr>
</thead>
<tbody>
<tr>
<td><ul><li>界面 1 · <名称></li></ul><p>IMG_HEAT_S1</p></td>
<td><ul><li>主热区位置与焦点结构客观描述。<ul><li>认知负荷综合分:<值>(档位,序数)——<偏高/适中/偏低,说明信息量对用户的客观含义>。</li><li>首热点注意力份额:<值>——<偏高=视线高度集中在单一区域、其余信息易被略过 / 偏低=注意力分散>;首屏可见度 <值>——<高=核心信息进入首屏 / 低=关键信息需滚动才可见>。</li><li>注意力基尼:<值>——<高=注意力分布不均、少数区域吃掉大部分关注 / 低=较均匀>。</li><li>边缘密度:<值>,色彩数 <值>——<对视觉繁简程度的客观含义>。</li></ul></li></ul></td>
<td><p><对用户的客观影响判断(只描述影响,不给改版方案)></p></td>
</tr>
<!-- 每个界面一行;`页面热力图`列用 IMG_HEAT_Sx 占位,落库后用 block_replace 把整单元格替换为内含 <img src="token" width=".." height=".."/> 的单元格(图进单元格、保持原比例);⛔ 不用 selection-with-ellipsis、⛔ 不贴原始设计稿 -->
</tbody>
</table>
<p><b>跨页面动线分析</b></p>
<!-- 单界面时可省略本表 -->
<table>
<colgroup><col width="280"/><col width="460"/></colgroup>
<thead>
<tr>
<th background-color="light-gray" vertical-align="top"><p>观察</p></th>
<th background-color="light-gray" vertical-align="top"><p>逐页读数</p></th>
</tr>
</thead>
<tbody>
<tr>
<td vertical-align="top"><p><动线接力一致性的一句话客观结论></p></td>
<td vertical-align="top"><p>相邻界面主热区落点位移:界面 1→2 为 <值>、2→3 为 <值>…;峰值锚点稳定在 <位置>。</p></td>
</tr>
<tr>
<td vertical-align="top"><p><认知负荷走势的一句话客观结论></p></td>
<td vertical-align="top"><p>认知负荷综合分序列 <值序列>(均值 <值>,方差 <值>,极差 <值>)。</p></td>
</tr>
<tr>
<td vertical-align="top"><p><首屏可见度走势的一句话客观结论></p></td>
<td vertical-align="top"><p>首屏注意力可见度 <值序列>;最低点落在界面 N。</p></td>
</tr>
<tr>
<td vertical-align="top"><p><注意力集中度走势的一句话客观结论></p></td>
<td vertical-align="top"><p>首热点注意力份额 <值序列>;注意力基尼 <值序列>。</p></td>
</tr>
</tbody>
</table>

<h3>单页面可理解性走查</h3>
<!-- 逐页评测:一张大表 + 每页一个 <td colspan="4"> 分组标题行(加序号+加粗);组内 4 列:走查项 / 页面问题标注(嵌红框标注原图) / 严重度 / 判断 -->
<table>
<colgroup><col width="180"/><col width="240"/><col width="80"/><col width="300"/></colgroup>
<thead>
<tr>
<th background-color="light-gray" vertical-align="top"><p>走查项</p></th>
<th background-color="light-gray" vertical-align="top"><p>页面问题标注</p></th>
<th background-color="light-gray" vertical-align="top"><p>严重度</p></th>
<th background-color="light-gray" vertical-align="top"><p>判断</p></th>
</tr>
</thead>
<tbody>
<tr><td colspan="4" background-color="light-gray"><ol><li seq="1"><b>界面 1 · <名称>(以下为本页面的可理解性走查)</b></li></ol></td></tr>
<tr>
<td vertical-align="top"><p>模块关系自洽(并列/因果/解锁关系是否讲清)</p></td>
<td vertical-align="top"><p>IMG_ISSUE_S1_01</p></td>
<td vertical-align="top"><p>低/中/高</p></td>
<td vertical-align="top"><p><判断放最前 + 依据(引用 semantic.json 事实)></p></td>
</tr>
<tr>
<td vertical-align="top"><p>承诺-路径衔接(承诺的权益下文有无对应入口/路径)</p></td>
<td vertical-align="top"><p>IMG_ISSUE_S1_02</p></td>
<td vertical-align="top"><p>低/中/高</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<tr>
<td vertical-align="top"><p>指代链完整(出现的术语/状态有无先交代清楚)</p></td>
<td vertical-align="top"><p>IMG_ISSUE_S1_03</p></td>
<td vertical-align="top"><p>低/中/高</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<tr>
<td vertical-align="top"><p>自上而下可读懂业务(陌生用户顺读一遍能否理解)</p></td>
<td vertical-align="top"><p>IMG_ISSUE_S1_04</p></td>
<td vertical-align="top"><p>低/中/高</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<tr>
<td vertical-align="top"><p>零状态/负向暗示(空态、待解锁/未完成等是否劝退)</p></td>
<td vertical-align="top"><p>IMG_ISSUE_S1_05</p></td>
<td vertical-align="top"><p>低/中/高</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<tr><td colspan="4" background-color="light-gray"><ol><li seq="2"><b>界面 2 · <名称>(以下为本页面的可理解性走查)</b></li></ol></td></tr>
<tr>
<td vertical-align="top"><p>模块关系自洽(并列/因果/解锁关系是否讲清)</p></td>
<td vertical-align="top"><p>IMG_ISSUE_S2_01</p></td>
<td vertical-align="top"><p>低/中/高</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<!-- 每个页面一组(分组标题行 + 5 条走查行);有几个界面就加几组,seq 顺延 -->
</tbody>
</table>

<h3>页面衔接可理解性</h3>
<!-- 新增模块。仅多界面有。逐对相邻页面评测:一张大表 + 每对一个 <td colspan="3"> 分组标题行(格式「页面A → 页面B」,加序号+加粗);组内 3 列:走查项 / 严重度 / 判断(无「页面问题标注」列) -->
<table>
<colgroup><col width="320"/><col width="80"/><col width="400"/></colgroup>
<thead>
<tr>
<th background-color="light-gray" vertical-align="top"><p>走查项</p></th>
<th background-color="light-gray" vertical-align="top"><p>严重度</p></th>
<th background-color="light-gray" vertical-align="top"><p>判断</p></th>
</tr>
</thead>
<tbody>
<tr><td colspan="3" background-color="light-gray"><ol><li seq="1"><b>界面 1 · <名称> → 界面 2 · <名称></b></li></ol></td></tr>
<tr>
<td vertical-align="top"><p>预期落差(用户在前页形成的预期,后页能否承接;有无断层、看不到想看的内容)</p></td>
<td vertical-align="top"><p>低/中/高</p></td>
<td vertical-align="top"><p><判断放最前 + 依据;可发散更多衔接维度(跳转突兀、信息连续性、操作连贯性等)></p></td>
</tr>
<tr><td colspan="3" background-color="light-gray"><ol><li seq="2"><b>界面 2 · <名称> → 界面 3 · <名称></b></li></ol></td></tr>
<tr>
<td vertical-align="top"><p>预期落差(同上,可发散更多维度)</p></td>
<td vertical-align="top"><p>低/中/高</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<!-- 每对相邻页面一组(分组标题行 + 若干走查行);N 个界面有 N-1 组,seq 顺延 -->
</tbody>
</table>
<blockquote><p><span text-color="gray"><i>本节引用:<切片主码>(语义事实与模块坐标来自 Phase A semantic.json)</i></span></p></blockquote>

> **「页面问题标注」列填法**:
> - 每条走查项**若该项判定有问题**,在本列嵌入**对应界面的「红框标注原图」**——原始设计稿截图上,用红框框出**出问题的模块**(模块级,框 semantic.json 该模块的 bbox);占位符 `IMG_ISSUE_Sx_NN`(x=界面序号,NN=走查项序号),落库后用 **`block_replace`** 把整单元格替换为内含 `<img src="token" width=".." height=".."/>` 的单元格(图进单元格、保持原比例)。⛔ 不用 `+media-insert --selection-with-ellipsis`(会插成表格后的兄弟块)。
> - **若该走查项无问题**,本列留空或填「—」,不嵌图。
> - 红框图由 `scripts/annotate_issues.py` 生成:输入 原图 + semantic.json(带 bbox)+ 产品专家走查问题清单(模块序号 → 是否有问题),用 PIL 在对应模块 bbox 画红框(模块级)。
> - **这是「图片只放热力图」铁律的唯一例外**:仅本列允许放红框标注的原图;其余正文(含客观数据速览)仍只放热力图、不贴原图。

<h1>三、圆桌纪要</h1>

<h3 seq="1" seq-level="1">共识要改的</h3>
<table>
<colgroup><col width="40"/><col width="150"/><col width="70"/><col width="260"/><col width="240"/></colgroup>
<thead>
<tr>
<th background-color="light-gray" vertical-align="top"><p>#</p></th>
<th background-color="light-gray" vertical-align="top"><p>议题</p></th>
<th background-color="light-gray" vertical-align="top"><p>优先级</p></th>
<th background-color="light-gray" vertical-align="top"><p>问题描述</p></th>
<th background-color="light-gray" vertical-align="top"><p>整改建议</p></th>
</tr>
</thead>
<tbody>
<tr>
<td vertical-align="top"><p><b>1</b></p></td>
<td vertical-align="top"><p>议题摘要</p></td>
<td vertical-align="top"><p><b>P0</b></p></td>
<td vertical-align="top"><p><b>问题一句话(判断放最前)。</b></p><ol><li seq="auto">产品专家:...</li><li seq="auto">本地商家:...</li><li seq="auto">HCI 佐证:...</li></ol></td>
<td vertical-align="top"><ol><li seq="auto">...</li><li seq="auto">...</li></ol></td>
</tr>
</tbody>
</table>
<blockquote><p><span text-color="gray"><i>本节引用:<切片主码></i></span></p></blockquote>

<h3>有分歧的</h3>
<table>
<colgroup><col width="40"/><col width="160"/><col width="220"/><col width="220"/><col width="200"/></colgroup>
<thead>
<tr>
<th background-color="light-gray" vertical-align="top"><p>#</p></th>
<th background-color="light-gray" vertical-align="top"><p>议题</p></th>
<th background-color="light-gray" vertical-align="top"><p>产品专家</p></th>
<th background-color="light-gray" vertical-align="top"><p>本地服务商家</p></th>
<th background-color="light-gray" vertical-align="top"><p>折中方案</p></th>
</tr>
</thead>
<tbody>
<tr>
<td vertical-align="top"><p><b>1</b></p></td>
<td vertical-align="top"><p>分歧议题(同轴两极的选择题)?</p></td>
<td vertical-align="top"><p><b>观点:...</b></p><ol><li seq="auto">...</li><li seq="auto">...</li></ol></td>
<td vertical-align="top"><p><b>观点:...</b></p><ol><li seq="auto">...</li><li seq="auto">...</li></ol></td>
<td vertical-align="top"><p><b>建议:...</b></p><ol><li seq="auto">...</li><li seq="auto">...</li></ol></td>
</tr>
</tbody>
</table>
<blockquote><p><span text-color="gray"><i>本节引用:<切片主码></i></span></p></blockquote>

<h3>共识做的好的</h3>
<table>
<colgroup><col width="40"/><col width="200"/><col width="520"/></colgroup>
<thead>
<tr>
<th background-color="light-gray" vertical-align="top"><p>#</p></th>
<th background-color="light-gray" vertical-align="top"><p>议题</p></th>
<th background-color="light-gray" vertical-align="top"><p>合理性说明</p></th>
</tr>
</thead>
<tbody>
<tr>
<td vertical-align="top"><p><b>1</b></p></td>
<td vertical-align="top"><p>做得好的点</p></td>
<td vertical-align="top"><p><b>加粗总判断。</b></p><ol><li seq="auto">产品专家:...</li><li seq="auto">本地商家:...</li><li seq="auto">HCI 佐证:...</li></ol></td>
</tr>
</tbody>
</table>
<blockquote><p><span text-color="gray"><i>本节引用:<切片主码></i></span></p></blockquote>

<h3>待办总结</h3>
<table>
<colgroup><col width="40"/><col width="80"/><col width="280"/><col width="180"/><col width="160"/></colgroup>
<thead>
<tr>
<th background-color="light-gray" vertical-align="top"><p>#</p></th>
<th background-color="light-gray" vertical-align="top"><p>优先级</p></th>
<th background-color="light-gray" vertical-align="top"><p>具体待办</p></th>
<th background-color="light-gray" vertical-align="top"><p>来源</p></th>
<th background-color="light-gray" vertical-align="top"><p>建议时间节点</p></th>
</tr>
</thead>
<tbody>
<tr>
<td vertical-align="top"><p><b>1</b></p></td>
<td vertical-align="top"><p>P0</p></td>
<td vertical-align="top"><p>具体待办动作</p></td>
<td vertical-align="top"><p>共识要改的 #1</p></td>
<td vertical-align="top"><p>研发启动前</p></td>
</tr>
</tbody>
</table>

<h3>决策建议</h3>
<ul><li><决策对象,如 权益与任务模块的信息密度策略></li></ul>
<blockquote><p>核心分歧:<用一句通俗话讲清同轴两极在纠结什么>,这是"<极A> ↔ <极B>"同一根轴上的两极,得选一个主方向。</p></blockquote>
<table>
<colgroup><col width="100"/><col width="320"/><col width="320"/></colgroup>
<thead>
<tr>
<th background-color="light-gray" vertical-align="top"><p> </p></th>
<th background-color="light-gray" vertical-align="top"><p>🅰 <路径A名称></p></th>
<th background-color="light-gray" vertical-align="top"><p>🅑 <路径B名称></p></th>
</tr>
</thead>
<tbody>
<tr>
<td vertical-align="top"><p><b>一句话</b></p></td>
<td vertical-align="top"><p>...</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<tr>
<td vertical-align="top"><p><b>核心动作</b></p></td>
<td vertical-align="top"><p>...</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<tr>
<td vertical-align="top"><p><b>验证方式</b></p></td>
<td vertical-align="top"><p>...</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<tr>
<td vertical-align="top"><p><b>适用前提</b></p></td>
<td vertical-align="top"><p>...</p></td>
<td vertical-align="top"><p>...</p></td>
</tr>
<tr>
<td vertical-align="top"><p><b>决策偏好因子</b></p></td>
<td vertical-align="top"><ol><li seq="auto"><b>因子纯名称</b>:说明。</li></ol></td>
<td vertical-align="top"><ol><li seq="auto"><b>因子纯名称</b>:说明。</li></ol></td>
</tr>
</tbody>
</table>
<blockquote><p><span text-color="gray"><i>本节引用:<切片主码></i></span></p></blockquote>

<hr/>
<blockquote><p><span text-color="gray"><i>本报告由 Expert-Roundtable 圆桌评审技能产出。全文引用切片:<全文切片主码列表>。</i></span></p></blockquote>
```

---

## 优先级判定规则

| 优先级 | 含义 | 时间节点关键词 |
|---|---|---|
| **P0** | 涉及合规/红线/规格不一致,进入研发前必修 | 研发启动前 |
| **P1** | 体验风险/视觉层级问题,上线前完成 | 上线前 |
| **P2** | 需决策人定夺或上线后小流量观察 | 上线后 1-4 周 |

---

## 写入流程(主持人必跑)

1. 用 `lark-doc` 的 `+create --api-version v2 --doc-format xml --title "【圆桌评审】<对象简称> - YYYY-MM-DD" --content @body.xml` 首次落库。
2. 如需迭代,用 `+update --command overwrite --api-version v2 --doc-format xml --content @body_vN.xml`。
3. 文件放在当前工作目录,用 `@相对路径` 传入。
4. **落库后嵌热力图(两条硬性红线:进单元格 + 保持原比例)**:① 用 `+media-insert`/`+upload-file` 上传每个界面热力图拿 image token;② 用 `+fetch --detail with-ids` 取含占位符 `IMG_HEAT_Sx` 的单元格 block_id;③ 用 **`block_replace`** 把该整个 `<td>` 替换为内含 `<img src="token" width=".." height=".."/>` 的单元格(width/height 先用 identify/PIL 读原图像素宽高,按列宽 ≈220 等比换算)。逐界面替换 IMG_HEAT_S1 / S2 / …。⛔ **禁止**用 `+media-insert --selection-with-ellipsis`(会插成表格后的兄弟块 = 图没进表格);⛔ 热力图只嵌客观数据速览表。
5. **落库后嵌问题标注图(同两条硬性红线)**:对「单页面可理解性走查」表中**判定有问题**的走查项,先跑 `scripts/annotate_issues.py`(原图 + semantic.json[带 bbox] + 走查问题清单)生成红框标注图 `issue_annotated_Sx_NN.png`;再用 `+media-insert`/`+upload-file` 上传拿 token → `+fetch --detail with-ids` 取含 `IMG_ISSUE_Sx_NN` 占位符的单元格 block_id → **`block_replace`** 把该整个 `<td>` 替换为内含 `<img src="token" width=".." height=".."/>` 的单元格(按列宽 ≈240 等比换算);无问题的走查项占位符删除或留「—」。⛔ 不用 `+media-insert --selection-with-ellipsis`。
6. 完成后向用户回传文档 URL。
