#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_knowledge_base.py — 从「圆桌评审-切片标注库 v1」多维表格生成 JuryPersonas 切片库

用途:
  把多维表格(base + table)拉取的切片,按 belongs_to 拆分为 4 个知识切片 md:
    - shared              → 共享客观知识(所有角色可见)
    - product_expert      → 产品专家
    - ad_buyer            → 投手(广告投放)
    - local_business      → 本地服务商家

输入(二选一):
  A) 已下载的分页 JSON(page_1.json..page_N.json),每个 envelope: data.fields + data.data
  B) 直接用 lark-cli 拉取(见 references/integration/knowledge_base_sync.md)

输出:
  knowledge/slices/shared.md
  knowledge/slices/product_expert.md
  knowledge/slices/ad_buyer.md
  knowledge/slices/local_business.md

字段对齐: data.fields(名称列表) 与 data.data(每行数组) 按下标对齐。

用法:
  python3 tools/build_knowledge_base.py --pages page_1.json page_2.json ...
  python3 tools/build_knowledge_base.py --pages page_1.json ... --out-root knowledge/slices
"""
import argparse, json, os, sys
from collections import defaultdict, OrderedDict

# belongs_to 值 → 输出文件 stem + 中文名
ROLE_MAP = OrderedDict([
    ("shared",          ("shared",          "共享客观知识(所有角色)")),
    ("product_expert",  ("product_expert",  "产品专家")),
    ("ad_buyer",        ("ad_buyer",        "投手(广告投放)")),
    ("local_business",  ("local_business",  "本地服务商家")),
])

def norm(v):
    """多维表格的单选/多选常被包成 list,取首元素;None→空串。"""
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v if x is not None)
    return str(v)

def first(v):
    if isinstance(v, list):
        return str(v[0]) if v else ""
    return "" if v is None else str(v)

def load_rows(page_files):
    rows = []
    for pf in page_files:
        d = json.load(open(pf, encoding="utf-8"))
        data = d["data"]
        fields = data["fields"]
        for arr in data["data"]:
            rows.append(dict(zip(fields, arr)))
    return rows

def belongs_list(row):
    v = row.get("belongs_to")
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]

def truthy(v):
    s = first(v).strip().lower()
    return s in ("true", "1", "yes", "是")

def build():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="+", required=True)
    ap.add_argument(
        "--out-root",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "knowledge", "slices"),
        help="输出目录,默认 knowledge/slices",
    )
    args = ap.parse_args()

    rows = load_rows(args.pages)
    # 仅保留 keep != False 的切片
    rows = [r for r in rows if first(r.get("keep")).strip().lower() != "false"]

    by_role = defaultdict(list)
    for r in rows:
        for b in belongs_list(r):
            if b in ROLE_MAP:
                by_role[b].append(r)

    stats = {}
    for role, (filename, cn) in ROLE_MAP.items():
        recs = by_role.get(role, [])
        red = [r for r in recs if truthy(r.get("is_red_line"))]
        normal = [r for r in recs if not truthy(r.get("is_red_line"))]
        # 按 topic_l1 / type 分组,提升可读性
        grouped = defaultdict(list)
        for r in normal:
            key = (first(r.get("topic_l1")) or "未分类", first(r.get("type")) or "fact")
            grouped[key].append(r)

        os.makedirs(args.out_root, exist_ok=True)
        path = os.path.join(args.out_root, f"{filename}.md")
        lines = []
        lines.append(f"# 知识库 · {cn}")
        lines.append("")
        lines.append(f"> 自动生成自多维表格「圆桌评审-切片标注库 v1」,按 `belongs_to = {role}` 拆分。")
        lines.append(f"> 切片数:{len(recs)}(含红线 {len(red)} 条)。**请勿手工编辑,改动请回到多维表格后重跑 `build_knowledge_base.py`。**")
        lines.append("")

        if red:
            lines.append("## 🚫 红线(is_red_line=true · 不可逾越)")
            lines.append("")
            for r in red:
                cid = first(r.get("id"))
                conf = first(r.get("confidence"))
                src = norm(r.get("source_doc_title"))
                url = first(r.get("source_doc_url"))
                content = norm(r.get("content")).replace("\n", " ")
                tail = f" [{src}]({url})" if url else (f" 〔{src}〕" if src else "")
                lines.append(f"- **[{cid}]** {content}{tail}")
            lines.append("")

        lines.append("## 知识切片")
        lines.append("")
        for (l1, typ), recs2 in sorted(grouped.items()):
            lines.append(f"### {l1} · {typ}")
            lines.append("")
            for r in recs2:
                cid = first(r.get("id"))
                conf = first(r.get("confidence"))
                l2 = first(r.get("topic_l2"))
                src = norm(r.get("source_doc_title"))
                url = first(r.get("source_doc_url"))
                content = norm(r.get("content")).replace("\n", " ")
                meta = []
                if l2: meta.append(l2)
                if conf: meta.append(f"置信:{conf}")
                metas = f" ({' · '.join(meta)})" if meta else ""
                tail = f" [{src}]({url})" if url else (f" 〔{src}〕" if src else "")
                lines.append(f"- **[{cid}]**{metas} {content}{tail}")
            lines.append("")

        open(path, "w", encoding="utf-8").write("\n".join(lines))
        stats[role] = {"file": f"{filename}.md", "total": len(recs), "red": len(red), "path": path}

    print(json.dumps(stats, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    build()
