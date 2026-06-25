# 知识库同步流程(Knowledge Base Sync)

> **说人话**:回答一个高频问题——"我改了多维表格,skill 里的知识库会自动更新吗?" **不会。** skill 是打包好的静态快照,和表格没有实时连接。改了表格,要手动重跑一条脚本 + 重新打包。本文件就是这套刷新流程的操作手册。

---

## 一、为什么不会自动同步

skill 本质是一份**静态打包文件**(SKILL.md + references + scripts + assets)。打包那一刻,多维表格的内容被"拍照"写进 `experts/*/knowledge_base.md`。运行时 skill **不会回查多维表格**,所以:

> 多维表格更新 ≠ skill 知识库更新。需要人工触发一次重建。

---

## 二、数据源(唯一真相)

| 项 | 值 |
|---|---|
| 多维表格 | 圆桌评审-切片标注库 v1 |
| base token | `Af2Kbh0xra3Fm0sCtqyc1DXknng` |
| table id | `tbldf19iuC7G47zJ` |
| 拆分字段 | `belongs_to`(shared / product_expert / ad_buyer / local_business) |
| 红线字段 | `is_red_line`(true → 进各角色「🚫 红线」段) |
| 内容字段 | content / type / topic_l1 / topic_l2 / confidence / source_doc_title / source_doc_url / id |

---

## 三、刷新三步(改表格后执行)

### Step 1 · 从多维表格拉全量(分页)
用 lark-cli 的 base 能力按 200 条/页拉取,直到 `has_more=false`,落成 `page_1.json … page_N.json`。
```bash
# 先 source lark-cli 环境(若 token 过期按 token_refresh 协议刷新)
source /data/plugins/market/lark-drive/skills/lark-drive/scripts/source_lark_cli_env.sh
# 逐页拉取(offset 递增),--format json
lark-cli base +record-list \
  --base-token Af2Kbh0xra3Fm0sCtqyc1DXknng --table tbldf19iuC7G47zJ \
  --format json --limit 200 --offset 0 > page_1.json
# offset=200 → page_2.json,以此类推,直到响应 data.has_more=false
```
> JSON envelope:记录在 `data.data`(每行是与 `data.fields` 名称列表**按下标对齐**的数组)。

### Step 2 · 拆分并重建 4 个知识库
```bash
python3 scripts/build_knowledge_base.py \
  --pages page_1.json page_2.json page_3.json page_4.json page_5.json page_6.json \
  --out-root references/phase_b_roundtable/experts
```
脚本会按 `belongs_to` 重写:
- `experts/shared/knowledge_base.md`
- `experts/product-expert/knowledge_base.md`
- `experts/ad-buyer-expert/knowledge_base.md`
- `experts/local-business-expert/knowledge_base.md`

并打印每个角色的切片数 / 红线数,**核对数量**是否符合预期。

### Step 3 · 重新打包并上传
用 skill-creator 校验 + 打包,然后上传归档替换旧版本。
```bash
export PYTHONPATH=/data/plugins/market/skill-creator/skills/skill-creator
python3 -m skill_creator.quick_validate Expert-Roundtable
python3 -m skill_creator.package_skill Expert-Roundtable
# 上传打包产物(zip),替换技能库中的旧版本
```

---

## 四、新增角色时的额外动作

若在多维表格 `belongs_to` 新增了枚举值(如再加一类角色):
1. 在 `scripts/build_knowledge_base.py` 的 `ROLE_MAP` 注册:`"新值": ("新目录名", "中文名")`
2. 在 `experts/新目录名/` 写 `SKILL.md`(参考现有 3 个角色)
3. 在 `references/phase_b_roundtable/roster.md` 加一行
4. 重跑 Step 2 + Step 3

---

## 五、自动化建议(可选)

可把 Step 1+2 封装成一个 `refresh_kb.sh`,一条命令完成"拉取 + 拆分";Step 3(打包上传)因涉及版本管理,建议保留人工确认。这样把维护成本压缩到:**跑一条命令 + 重新打包**。
