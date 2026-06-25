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

# 知识掌握度提示,在 frontmatter 的 knowledge_level 中按 import 路径声明。
# 设计为"选填、不破坏向后兼容":未声明则不注入任何提示,行为与旧版一致。
LEVEL_PROMPTS = {
    "expert": "你对此完全熟练,能深入解释边界情况、能脱口给出反例。",
    "proficient": "你能独立操作,但偶尔需要查手册,遇到罕见 case 会犹豫。",
    "novice": "你能照本宣科,但容易混淆相邻概念,被追问会暴露不熟。",
    "aware": "你只是听过这个名词,被深问会含糊带过或承认不熟。",
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
                meta2[current_dict_key][k.strip()] = v.strip()
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
            elif value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                meta2[key] = [x.strip() for x in inner.split(",")] if inner else []
            else:
                meta2[key] = value

    # 清理:无后续子项的 None → 空 list
    for k, v in list(meta2.items()):
        if v is None:
            meta2[k] = []

    return meta2, body


def load_knowledge(import_paths, knowledge_level=None):
    """读取 imports 列表中的所有共享知识文件。

    knowledge_level 选填:dict[rel_path -> level],level ∈
    {expert, proficient, novice, aware}。
    若画像声明了某条 import 的掌握度,会在该知识块前注入一段
    "掌握度提示",指导模型按对应熟练度演绎;未声明的条目按原样拼接,
    保持向后兼容。
    """
    chunks = []
    knowledge_level = knowledge_level or {}
    for rel_path in import_paths:
        full = SKILL_ROOT / rel_path
        if not full.exists():
            chunks.append(f"<!-- 知识文件未找到: {rel_path} -->")
            continue
        with open(full, "r", encoding="utf-8") as f:
            content = f.read()

        level = knowledge_level.get(rel_path)
        level_hint = LEVEL_PROMPTS.get(level, "") if level else ""
        header = f"\n### 引用知识 · {rel_path}"
        if level_hint:
            header += f"\n> 你对本块知识的掌握度: **{level}** — {level_hint}"
        chunks.append(f"{header}\n\n{content}\n")
    return "\n".join(chunks)


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


def compile_persona(role_id: str):
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
        load_knowledge(imports, knowledge_level) if imports else ""
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
