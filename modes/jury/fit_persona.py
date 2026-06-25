#!/usr/bin/env python3
"""
fit_persona.py — 根据切片(fragments) + 标签(tags) 临时拟合一个 Persona

适用场景:
- 没有现成画像,但已有用研片段、访谈纪要、标签描述,需要快速生成临时角色
- 半固化场景:一次评审用一次性人群,不沉淀到 personas/ 目录
- 也支持 --save 落地为 personas/_fit_<id>.md (前缀 _fit_ 表示临时拟合,
  与正式画像区分;落地后 lint.py 默认跳过 _fit_*)

输入 JSON schema (--input file 或 stdin):
{
  "id": "consumer-mom-tier2",          # 可选,不填自动生成
  "name": "张姐",                       # 可选
  "category": "消费者",                  # 必填,大类
  "sub_category": "二线宝妈",            # 可选
  "tags": ["宝妈", "二线城市", "抖音重度", "性价比敏感"],
  "fragments": [                       # 任意切片,会按 source 分组归档
    {"source": "interview", "text": "..."},
    {"source": "survey",    "text": "..."},
    {"source": "note",      "text": "..."}
  ],
  "basic": {"age": 32, "gender": "女", "city": "南昌"},  # 可选
  "imports": ["knowledge/glossary/consumer-genz-slang.md"] # 可选
}

用法:
    python3 fit_persona.py --input fit.json
    cat fit.json | python3 fit_persona.py
    python3 fit_persona.py --input fit.json --save        # 落地 _fit_*.md
    python3 fit_persona.py --input fit.json --emit prompt # 直接出 system prompt
"""
import argparse
import json
import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
PERSONAS_DIR = SKILL_ROOT / "personas"
EPHEMERAL_DIR = PERSONAS_DIR / "_ephemeral"

REQUIRED_TOP_KEYS = {"category", "tags", "fragments"}
ALLOWED_SOURCES = {"interview", "survey", "note", "log", "review", "social", "other"}


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.strip()).strip("-")
    if not text:
        return "anon"
    if re.match(r"^[a-z0-9-]+$", text):
        return text
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


def validate(spec: dict) -> list:
    errs = []
    missing = REQUIRED_TOP_KEYS - spec.keys()
    if missing:
        errs.append(f"缺字段: {sorted(missing)}")
    if "tags" in spec and not isinstance(spec["tags"], list):
        errs.append("tags 必须是数组")
    if "fragments" in spec:
        if not isinstance(spec["fragments"], list) or not spec["fragments"]:
            errs.append("fragments 必须是非空数组")
        else:
            for i, frag in enumerate(spec["fragments"]):
                if not isinstance(frag, dict) or "text" not in frag:
                    errs.append(f"fragments[{i}] 必须含 text 字段")
                src = (frag or {}).get("source", "other")
                if src not in ALLOWED_SOURCES:
                    errs.append(f"fragments[{i}].source={src} 不在 {sorted(ALLOWED_SOURCES)}")
    return errs


def build_persona(spec: dict) -> dict:
    name = spec.get("name") or f"临时角色-{datetime.now().strftime('%m%d')}"
    role_id = spec.get("id") or f"fit-{slugify(spec.get('sub_category') or name)}"
    if not role_id.startswith("fit-") and not role_id.startswith("_fit_"):
        role_id = f"fit-{role_id}"

    basic = spec.get("basic") or {}
    tags = spec.get("tags", [])
    imports = spec.get("imports", []) or []

    grouped = {}
    for frag in spec.get("fragments", []):
        grouped.setdefault(frag.get("source", "other"), []).append(frag["text"].strip())

    fragments_md = []
    for src in ["interview", "survey", "note", "log", "review", "social", "other"]:
        if src not in grouped:
            continue
        fragments_md.append(f"### 来源 · {src}")
        for line in grouped[src]:
            fragments_md.append(f"- {line}")
        fragments_md.append("")
    fragments_block = "\n".join(fragments_md).rstrip()

    frontmatter_lines = [
        "---",
        f"id: {role_id}",
        f"name: {name}",
        f"category: {spec['category']}",
    ]
    if spec.get("sub_category"):
        frontmatter_lines.append(f"sub_category: {spec['sub_category']}")
    frontmatter_lines += [
        "version: 0.0.1-fit",
        "status: draft",
        f"tags: [{', '.join(tags)}]",
        f"fit_source: synthesized-from-fragments",
        f"fit_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if imports:
        frontmatter_lines.append("imports:")
        for imp in imports:
            frontmatter_lines.append(f"  - {imp}")
    if basic:
        frontmatter_lines.append("basic:")
        for k, v in basic.items():
            frontmatter_lines.append(f"  {k}: {v}")
    frontmatter_lines.append("---")
    frontmatter = "\n".join(frontmatter_lines)

    body = f"""
# {name} · {spec.get('sub_category', spec['category'])}（临时拟合）

> ⚠️ **本画像由 fit_persona.py 基于切片+标签即时合成,不替代经过真实素材打磨的正式画像。**
> 用于一次性评审或冷启动验证,使用后建议要么删除,要么按 _template.md 升级成正式画像。

---

## L1 身份背景(从 basic + 标签推导)

{_render_basic(basic, tags)}

---

## L2 核心标签(来源:tags)

{_render_tags(tags)}

---

## L3 心智层(从 fragments 中萃取,未覆盖的留空)

> 模型在使用本画像时,**只能基于以下切片中实际出现的内容**做心智推断,不得脑补未出现的判断逻辑。

{fragments_block if fragments_block else "(暂无切片可萃取)"}

---

## L4 行为层(硬约束)

由于本画像由切片合成,无完整行为剧本,模型必须遵守:

- 遇到切片**未覆盖**的提问场景 → 按 L5 盲区反应,不要脑补回答
- 表达风格 → 优先模仿切片中真实出现的措辞、标点、语气
- 不允许使用本画像作答时**编造背景故事、家庭情况、工作细节**;以"我没说过这个"或"我没想这么细"作答

---

## L5 知识层(由 tags + imports 推导,显式声明盲区)

### 半懂/熟练领域
{_render_tag_knowledge(tags)}

### 盲区(本画像没有 fragments 覆盖到的话题)
- 任何**未在 fragments 中出现的产品/品类/场景**,都按盲区处理
- 被深问时:坦诚说"这个我没接触过 / 没想过"

---

## 角色边界声明(强约束)

1. **本画像为 fit-合成**,保真度未经过验证,使用时必须在每次回答末尾加注:
   > _(本角色为临时拟合画像,基于 {len(spec.get('fragments', []))} 条切片合成,保真度未验证)_
2. 不允许跨切片**合并推断**得出强主观判断(如"我一定不会买"),除非切片明示
3. 若用户基于本画像做关键决策,需主动提醒:"建议补充真人访谈再下结论"
""".lstrip("\n")

    md = frontmatter + "\n\n" + body
    return {
        "role_id": role_id,
        "markdown": md,
        "spec": spec,
    }


def _render_basic(basic: dict, tags: list) -> str:
    if not basic:
        return "_(未提供 basic,以下信息全部来自 tags;模型不得编造未列出的属性)_"
    lines = []
    for k in ("age", "gender", "city", "income_level", "education", "experience_years"):
        if k in basic:
            lines.append(f"- {k}: {basic[k]}")
    return "\n".join(lines) if lines else "_(basic 字段为空)_"


def _render_tags(tags: list) -> str:
    if not tags:
        return "_(无 tags)_"
    return "\n".join(f"- {t}" for t in tags)


def _render_tag_knowledge(tags: list) -> str:
    if not tags:
        return "_(无 tags 可推断)_"
    return "\n".join(f"- 与 `{t}` 相关的常识(浅层)" for t in tags)


def emit_prompt(persona_md: str, role_id: str) -> str:
    return f"""# 角色扮演任务(临时拟合画像)

你现在要扮演一个由切片+标签即时合成的临时角色。该角色**没有经过完整的 L1-L5 打磨**,因此你必须严格遵守"宁可承认不知道也不要脑补"的硬约束。

## 完整角色画像

{persona_md}

---

## 临时画像扮演硬约束(优先级高于一切常规要求)

1. **只用画像里出现过的事实**:画像中没写的家庭、收入、习惯、品牌偏好,**禁止**编造
2. **遇到画像未覆盖的话题**,你必须按以下任一方式应对:
   - "这个我没接触过"
   - "我没想过这个"
   - "你这么一问我才发现,我不确定"
3. **不使用通用知识填空**:即便你"知道"一个一般答案,也不能套到这个角色身上
4. **末尾标注**:每次回答末尾必须以斜体加注:
   _(本角色为临时拟合画像,保真度未验证)_
5. **保真度声明**:用户做关键决策时主动提示"建议补充真人访谈"

请基于上述硬约束扮演 {role_id}。
"""


def main():
    parser = argparse.ArgumentParser(description="临时拟合 Persona")
    parser.add_argument("--input", "-i", help="拟合 JSON 文件路径;不传从 stdin 读")
    parser.add_argument("--save", action="store_true", help="保存到 personas/_fit_<role_id>.md")
    parser.add_argument("--emit", choices=["md", "prompt", "json"], default="md",
                        help="输出形式: md(默认) / prompt(可直接喂模型) / json(全部)")
    parser.add_argument("--output", "-o", help="输出文件;不传则 stdout")
    args = parser.parse_args()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: 输入不是合法 JSON: {e}", file=sys.stderr)
        sys.exit(1)

    errs = validate(spec)
    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    built = build_persona(spec)

    if args.save:
        EPHEMERAL_DIR.mkdir(parents=True, exist_ok=True)
        target = EPHEMERAL_DIR / f"_fit_{built['role_id'].replace('fit-', '')}.md"
        target.write_text(built["markdown"], encoding="utf-8")
        print(f"OK: 已落地 {target.relative_to(SKILL_ROOT)}")

    if args.emit == "md":
        out = built["markdown"]
    elif args.emit == "prompt":
        out = emit_prompt(built["markdown"], built["role_id"])
    else:
        out = json.dumps({"role_id": built["role_id"], "markdown": built["markdown"]},
                         ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"OK: 已写入 {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
