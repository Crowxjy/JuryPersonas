#!/usr/bin/env python3
"""
compile_persona.py — 把单个 persona 文件编译为完整的 System Prompt

用法:
    python3 compile_persona.py <role_id>
    python3 compile_persona.py ad-buyer
    python3 compile_persona.py ad-buyer --output prompt.txt
    python3 compile_persona.py ad-buyer --json   # 输出结构化 json
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
PERSONAS_DIR = SKILL_ROOT / "personas"
METHODS_DIR = SKILL_ROOT / "knowledge" / "methods"

# 知识掌握度提示,在 frontmatter 的 knowledge_level 中按 import 路径声明。
# 设计为"选填、不破坏向后兼容":未声明则不注入任何提示,行为与旧版一致。
LEVEL_PROMPTS = {
    "expert": "你对此完全熟练,能深入解释边界情况、能脱口给出反例。",
    "proficient": "你能独立操作,但偶尔需要查手册,遇到罕见 case 会犹豫。",
    "novice": "你能照本宣科,但容易混淆相邻概念,被追问会暴露不熟。",
    "aware": "你只是听过这个名词,被深问会含糊带过或承认不熟。",
}

ARTIFACT_KNOWLEDGE_TERMS = {
    "marketing-copy": [
        "文案",
        "素材",
        "图文",
        "标题",
        "钩子",
        "利益",
        "转化",
        "行动引导",
        "价格",
        "优惠",
        "证据",
        "承诺",
        "虚假",
        "夸大",
        "功效",
        "合规",
        "红线",
    ],
    "short-video": [
        "短视频",
        "素材",
        "视频",
        "前3秒",
        "前 3 秒",
        "点击",
        "转化",
        "口播",
        "字幕",
        "信任",
        "合规",
        "审核",
        "红线",
    ],
    "prd": [
        "PRD", "产品", "需求", "指标", "口径", "流程", "成本", "ROI", "归因", "合规", "红线",
    ],
    "design": [
        "设计", "界面", "页面", "信息架构", "操作", "转化", "信任", "合规", "红线",
    ],
    "screen": [
        "设计", "界面", "页面", "信息架构", "操作", "转化", "信任", "合规", "红线",
    ],
    "detail-page": [
        "详情页", "页面", "商品", "价格", "优惠", "信任", "评价", "转化", "合规", "红线",
    ],
    "product-card": [
        "商品", "卡片", "价格", "优惠", "信任", "评价", "转化", "合规", "红线",
    ],
}

ALWAYS_KEEP_KEYWORDS = ["红线", "禁止", "不得", "违规", "合规", "虚假", "夸大"]
MAX_CONTEXTUAL_KNOWLEDGE_CHARS = 24000
FULL_KNOWLEDGE_THRESHOLD_CHARS = 40000

ARTIFACT_TYPE_ALIASES = {
    "PRD": "prd",
    "prd": "prd",
    "设计稿": "design",
    "design": "design",
    "单界面": "screen",
    "screen": "screen",
    "详情页": "detail-page",
    "detail-page": "detail-page",
    "商品卡": "product-card",
    "product-card": "product-card",
    "营销文案": "marketing-copy",
    "marketing-copy": "marketing-copy",
    "短视频": "short-video",
    "short-video": "short-video",
}

LEGACY_EXPERT_IMPORTS = {
    "product_expert": ["knowledge/slices/shared.md", "knowledge/slices/product_expert.md"],
    "ad_buyer": ["knowledge/slices/shared.md", "knowledge/slices/ad_buyer.md"],
    "local_business": ["knowledge/slices/shared.md", "knowledge/slices/local_business.md"],
}

DEPRECATED_PERSONA_IDS = {
    "ad-buyer-expert": "已合并为 ad-buyer;仅保留为 expert-roundtable 原始资产审计件",
    "ad-buyer-senior": "已合并为 ad-buyer;仅保留为历史结果复现件",
}


def parse_frontmatter_value(value: str):
    value = value.strip()
    if value == "":
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [
            item.strip().strip('"').strip("'")
            for item in inner.split(",")
            if item.strip()
        ]
    return value.strip('"').strip("'")


def parse_frontmatter(content: str):
    """解析 YAML frontmatter,返回 (meta_dict, body_str)。
    支持:标量、内联列表、缩进列表、缩进字典。
    """
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1].strip()
    body = parts[2].lstrip("\n")

    # 二次扫描:正确处理嵌套 dict (basic:) vs 列表 (imports:)
    meta2 = {}
    current_dict_key = None
    pending_type = None  # "dict" / "list" / None

    for raw_line in fm_text.split("\n"):
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue

        # 缩进行 → 当前 key 的子项
        if raw_line.startswith("  ") or raw_line.startswith("\t"):
            stripped = raw_line.strip()
            if not current_dict_key:
                continue

            if stripped.startswith("- "):
                # list 项
                if pending_type != "list":
                    meta2[current_dict_key] = []
                    pending_type = "list"
                meta2[current_dict_key].append(stripped[2:].strip())
            elif ":" in stripped:
                # dict 项
                if pending_type != "dict":
                    meta2[current_dict_key] = {}
                    pending_type = "dict"
                k, v = stripped.split(":", 1)
                meta2[current_dict_key][k.strip()] = parse_frontmatter_value(v)
            continue

        # 顶级行
        if ":" in raw_line:
            key, _, value = raw_line.partition(":")
            key = key.strip()
            value = value.strip()
            current_dict_key = key
            pending_type = None

            if value == "":
                meta2[key] = None  # 等待后续缩进决定类型
            else:
                meta2[key] = parse_frontmatter_value(value)

    # 清理:无后续子项的 None → 空 list
    for k, v in list(meta2.items()):
        if v is None:
            meta2[k] = []

    return meta2, body


def knowledge_keywords_for_context(context=None):
    if not context:
        return []
    artifact_type = context_artifact_slug(context)
    keywords = list(ARTIFACT_KNOWLEDGE_TERMS.get(str(artifact_type), []))
    raw_artifact_type = context.get("artifact_type") if isinstance(context, dict) else None
    for candidate in (artifact_type, raw_artifact_type):
        if candidate and str(candidate) not in keywords:
            keywords.append(str(candidate))
    if not keywords:
        return []
    for keyword in ALWAYS_KEEP_KEYWORDS:
        if keyword not in keywords:
            keywords.append(keyword)
    return keywords


def context_artifact_slug(context=None):
    if not isinstance(context, dict):
        return ""
    raw = context.get("artifact_type")
    if raw:
        mapped = ARTIFACT_TYPE_ALIASES.get(str(raw).strip())
        if mapped:
            return mapped
    scenario = str(context.get("scenario") or "")
    if scenario.startswith("review-"):
        return scenario[len("review-"):]
    return str(raw or "")


def trim_knowledge_for_context(content: str, *, rel_path: str, keywords: list[str]) -> str:
    """Budget very large generated slice files without turning trimming into judgement.

    Small files stay intact. For oversized auto-generated knowledge bases, keep
    slices that match the current artifact terms or universal compliance/red-line
    terms. Unknown artifact types return the full file via empty keywords.
    """
    if not keywords or len(content) <= FULL_KNOWLEDGE_THRESHOLD_CHARS:
        return content

    lowered_keywords = [kw.lower() for kw in keywords]
    selected: list[str] = []
    selected_chars = 0
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- **["):
            continue
        haystack = stripped.lower()
        if not any(keyword.lower() in haystack for keyword in lowered_keywords):
            continue
        selected.append(stripped)
        selected_chars += len(stripped)
        if selected_chars >= MAX_CONTEXTUAL_KNOWLEDGE_CHARS:
            break

    if not selected:
        return (
            f"> 已按场景裁剪大知识库 `{rel_path}`,未命中高相关切片;"
            "以下为文件开头摘要。\n\n"
            f"{content[:MAX_CONTEXTUAL_KNOWLEDGE_CHARS]}\n"
        )

    return (
        f"> 已按当前场景裁剪大知识库 `{rel_path}`:"
        f"保留 {len(selected)} 条高相关/红线切片,避免全量注入稀释判断。\n\n"
        + "\n".join(selected)
        + "\n"
    )


def load_knowledge(import_paths, knowledge_level=None, context=None):
    """读取 imports 列表中的所有共享知识文件。

    knowledge_level 选填:dict[rel_path -> level],level ∈
    {expert, proficient, novice, aware}。
    若画像声明了某条 import 的掌握度,会在该知识块前注入一段
    "掌握度提示",指导模型按对应熟练度演绎;未声明的条目按原样拼接,
    保持向后兼容。
    """
    chunks = []
    knowledge_level = knowledge_level or {}
    keywords = knowledge_keywords_for_context(context)
    for rel_path in import_paths:
        full = SKILL_ROOT / rel_path
        if not full.exists():
            chunks.append(f"<!-- 知识文件未找到: {rel_path} -->")
            continue
        with open(full, "r", encoding="utf-8") as f:
            content = f.read()
        content = trim_knowledge_for_context(
            content,
            rel_path=rel_path,
            keywords=keywords,
        )

        level = knowledge_level.get(rel_path)
        level_hint = LEVEL_PROMPTS.get(level, "") if level else ""
        header = f"\n### 引用知识 · {rel_path}"
        if level_hint:
            header += f"\n> 你对本块知识的掌握度: **{level}** — {level_hint}"
        chunks.append(f"{header}\n\n{content}\n")
    return "\n".join(chunks)


def normalize_id_list(value) -> list[str]:
    if not value:
        return []
    raw_items = value if isinstance(value, list) else [value]
    out: list[str] = []
    for item in raw_items:
        text = str(item).strip().strip('"').strip("'")
        if text and text not in out:
            out.append(text)
    return out


def normalize_method_lens(method_lens) -> dict[str, list[str]]:
    if not isinstance(method_lens, dict):
        return {"primary": [], "secondary": [], "forbidden": []}
    return {
        "primary": normalize_id_list(method_lens.get("primary")),
        "secondary": normalize_id_list(method_lens.get("secondary")),
        "forbidden": normalize_id_list(method_lens.get("forbidden")),
    }


def method_applies_to_context(method_meta: dict, context=None) -> bool:
    artifact_slug = context_artifact_slug(context)
    if not artifact_slug:
        return True
    artifact_types = normalize_id_list(method_meta.get("artifact_types"))
    if not artifact_types:
        return True
    return artifact_slug in artifact_types


def render_method_tool_hint(tool) -> str:
    """若方法卡声明了配套可执行工具(frontmatter `tool:`),生成一段告知专家
    『此方法有确定性工具可调』的提示。无声明则返回空串,保持向后兼容。"""
    if not isinstance(tool, dict):
        return ""
    path = tool.get("path")
    if not path:
        return ""
    lines = ["", "> 配套确定性工具(优先用工具算,不要心算估数):"]
    lines.append(f"> - 命令: `{tool.get('usage') or ('python3 ' + str(path) + ' --stdin --pretty')}`")
    if tool.get("input_fields"):
        lines.append(f"> - 输入字段: {tool['input_fields']}")
    if tool.get("desc"):
        lines.append(f"> - 说明: {tool['desc']}")
    lines.append("> - 证据不足时工具会拒算或留空;不得据此编造数字。")
    return "\n".join(lines) + "\n"


def load_method_cards(method_lens, context=None) -> tuple[str, dict[str, list[str]]]:
    """读取 persona method_lens 声明的方法卡片。

    仅 primary/secondary 方法会注入完整卡片。forbidden 作为边界约束注入,
    不要求存在同名方法文件。
    """
    normalized = normalize_method_lens(method_lens)
    sections: list[str] = []
    used: dict[str, list[str]] = {"primary": [], "secondary": [], "forbidden": normalized["forbidden"]}

    for bucket in ("primary", "secondary"):
        ids = normalized[bucket]
        if not ids:
            continue
        bucket_title = "主方法" if bucket == "primary" else "辅助方法"
        chunks: list[str] = []
        for method_id in ids:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", method_id):
                chunks.append(f"<!-- 方法 ID 非法,已跳过: {method_id} -->")
                continue
            path = METHODS_DIR / f"{method_id}.md"
            if not path.exists():
                chunks.append(f"<!-- 方法文件未找到: knowledge/methods/{method_id}.md -->")
                continue
            content = path.read_text(encoding="utf-8")
            method_meta, method_body = parse_frontmatter(content)
            if not method_applies_to_context(method_meta, context):
                continue
            method_name = method_meta.get("name", method_id)
            tool_hint = render_method_tool_hint(method_meta.get("tool"))
            chunks.append(
                f"### {bucket_title} · {method_id} · {method_name}\n\n{method_body.strip()}\n{tool_hint}"
            )
            used[bucket].append(method_id)
        if chunks:
            sections.append(f"## {bucket_title}\n\n" + "\n".join(chunks))

    if normalized["forbidden"]:
        forbidden_text = "\n".join(f"- {method_id}" for method_id in normalized["forbidden"])
        sections.append(
            "## 禁止使用的方法 / 伪方法\n\n"
            f"{forbidden_text}\n\n"
            "遇到这些判断方式时必须明确拒绝,不得把它们包装成专业结论。"
        )

    if not sections:
        return "", used

    return (
        "以下方法是该角色评审时可调用的稳定工具。使用时必须先检查输入证据是否足够;"
        "证据不足时只能说明缺口,不得补数据或假装已经完成计算。\n\n"
        + "\n\n".join(sections)
        + "\n"
    ), used


def infer_legacy_expert_imports(meta):
    """expert-roundtable 原生 SKILL.md 没有 JuryPersonas imports 字段,按 metadata.role 映射。"""
    metadata = meta.get("metadata") or {}
    if not isinstance(metadata, dict):
        return []
    return LEGACY_EXPERT_IMPORTS.get(metadata.get("role"), [])


def find_persona_path(role_id: str) -> Path:
    """在 personas/ 下递归查找 <role_id>.md。

    画像现按 experts/ consumers/ bd/ _ephemeral/ 子目录组织,
    role_id 仍是全局唯一的文件名(不含路径前缀)。命中多个时报错,
    强制画像 id 全局唯一。
    """
    search_roots = [PERSONAS_DIR]
    extra_dirs = os.environ.get("JURY_PERSONAS_EXTRA_PERSONA_DIRS", "")
    for raw in extra_dirs.split(os.pathsep):
        if raw.strip():
            search_roots.append(Path(raw.strip()))

    matches = []
    for root in search_roots:
        if not root.exists():
            continue
        matches.extend(
            p for p in root.rglob(f"{role_id}.md")
            if not p.name.startswith("_template")
        )
    if not matches:
        raise FileNotFoundError(
            f"角色不存在: 在 {search_roots} 下找不到 {role_id}.md"
        )
    if len(matches) > 1:
        rels = [str(m.relative_to(SKILL_ROOT)) for m in matches]
        raise RuntimeError(
            f"角色 id 冲突: {role_id} 命中多个文件 {rels},画像 id 必须全局唯一"
        )
    if role_id in DEPRECATED_PERSONA_IDS and os.environ.get("JURY_PERSONAS_ALLOW_DEPRECATED") != "1":
        raise RuntimeError(
            f"角色已废弃: {role_id}。{DEPRECATED_PERSONA_IDS[role_id]}。"
            "默认请改用 ad-buyer;如需历史复现,设置 JURY_PERSONAS_ALLOW_DEPRECATED=1。"
        )
    return matches[0]


def compile_persona(role_id: str, context=None):
    """主编译函数"""
    persona_path = find_persona_path(role_id)

    with open(persona_path, "r", encoding="utf-8") as f:
        content = f.read()

    meta, body = parse_frontmatter(content)

    imports = meta.get("imports", []) or infer_legacy_expert_imports(meta)
    knowledge_level = meta.get("knowledge_level") or {}
    # 兼容 parse_frontmatter 把空 dict 解析成 [] 的极端情况
    if not isinstance(knowledge_level, dict):
        knowledge_level = {}
    knowledge_text = (
        load_knowledge(imports, knowledge_level, context=context) if imports else ""
    )
    method_text, method_files = load_method_cards(meta.get("method_lens"), context=context)
    method_section = (
        f"\n## 专家方法 / 工具镜头\n{method_text}\n"
        if method_text
        else ""
    )

    system_prompt = f"""# 角色扮演任务

你现在要扮演以下角色,所有回答必须严格遵循该角色的身份、性格、知识边界、语言风格。

## 角色基本信息
- 角色 ID: {meta.get('id', role_id)}
- 角色名: {meta.get('name', '')}
- 大类: {meta.get('category', '')}
- 子类: {meta.get('sub_category', '')}
- 状态: {meta.get('status', '')}
- 版本: {meta.get('version', '')}

## 完整角色画像

{body}

## 共享知识背景(角色掌握的领域知识)
{knowledge_text}
{method_section}

---

## 扮演硬约束(必须遵守)

1. **第一人称代入**:用"我"自称,不暴露 AI 身份,不出现"作为 AI 助手"等话术
2. **遵守知识边界**:画像中标记为"盲区"的领域,**禁止**调用通用知识硬答,必须按"盲区反应"中的方式回应
3. **保持语言风格**:严格遵循 L4 的口头禅、表达风格、信息密度偏好
4. **触发应激反应**:遇到 L4 应激反应库中的场景,必须按预设反应输出
5. **遵循思考逻辑**:做判断/决策时按 L3 的优先序和归因路径展开
6. **使用 Few-shot 示例的语言风格**:末尾的对话片段是你的语言锚点
7. **状态为 draft 的画像**:在每次回复末尾用斜体补一句"(本角色为测试画像,保真度未验证)"

请严格按以上要求扮演。
"""
    return {
        "role_id": role_id,
        "meta": meta,
        "system_prompt": system_prompt,
        "knowledge_files": imports,
        "method_lens": method_files,
    }


def main():
    parser = argparse.ArgumentParser(description="编译 persona 为 System Prompt")
    parser.add_argument("role_id", help="角色 ID(对应 personas/<role_id>.md)")
    parser.add_argument("--output", "-o", help="输出文件路径(默认 stdout)")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出全部信息")
    args = parser.parse_args()

    try:
        result = compile_persona(args.role_id)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    output = (
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else result["system_prompt"]
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"OK: 已写入 {args.output} ({len(output)} chars)")
    else:
        print(output)


if __name__ == "__main__":
    main()
