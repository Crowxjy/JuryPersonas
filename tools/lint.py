#!/usr/bin/env python3
"""
lint.py — 角色画像完整性校验

用法:
    python3 lint.py                  # 校验所有 personas
    python3 lint.py <role_id>        # 校验单个
    python3 lint.py --strict         # 严格模式(L1-L5 任一段缺失即 fail)

校验项:
1. frontmatter 必填字段(id/name/category/version/status)
2. L1-L5 五层结构是否齐全
3. Few-shot 示例数量(至少 2 段)
4. imports 引用的知识文件是否存在
5. id 是否与文件名一致
"""
import argparse
import importlib.util
import sys
from pathlib import Path

# tools/ 与 modes/jury/ 同属 JuryPersonas/ 二级目录,这里反查项目根
TOOLS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TOOLS_DIR.parent


def load_bootstrap():
    spec = importlib.util.spec_from_file_location(
        "jury_personas_bootstrap",
        SKILL_ROOT / "orchestrator" / "bootstrap.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 orchestrator/bootstrap.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


load_bootstrap().ensure_skill_import_paths()

from compile_persona import infer_legacy_expert_imports, parse_frontmatter  # noqa: E402

REQUIRED_META = ["id", "name", "category", "version", "status"]
REQUIRED_SECTIONS = [
    "L1 身份背景",
    "L2 核心标签",
    "L3 心智层",
    "L4 行为层",
    "L5 知识层",
]
# Few-shot 段落不再要求标题里出现 "Few-shot" 字样,
# 改由下方的 "### 片段" 计数来识别(标题可纯中文,如"## 典型对话片段")。


def is_legacy_expert_roundtable(meta: dict, body: str, persona_path: Path) -> bool:
    """expert-roundtable 原生专家 SKILL.md:有 name/description/metadata.role,无 Jury id。"""
    metadata = meta.get("metadata") or {}
    return (
        persona_path.parent.name == "experts"
        and isinstance(metadata, dict)
        and bool(metadata.get("role"))
        and "## 角色立场" in body
        and "## 工作流" in body
        and "## 红线" in body
    )


def lint_legacy_expert(meta: dict, body: str):
    """兼容 byte-identical 迁入的 expert-roundtable 专家 prompt。"""
    errors, warnings = [], []
    if not meta.get("name"):
        errors.append("legacy expert 缺少 frontmatter.name")
    metadata = meta.get("metadata") or {}
    if not isinstance(metadata, dict) or not metadata.get("role"):
        errors.append("legacy expert 缺少 metadata.role")
    for section in ("## 角色立场", "## 工作流", "## 红线"):
        if section not in body:
            errors.append(f"legacy expert 缺少结构段落: {section}")
    imports = infer_legacy_expert_imports(meta)
    if not imports:
        errors.append("legacy expert metadata.role 无法映射到 knowledge/slices")
    for import_path in imports:
        full = SKILL_ROOT / import_path
        if not full.exists():
            errors.append(f"legacy expert 隐式知识引用不存在: {import_path}")
    warnings.append("legacy expert-roundtable SKILL.md 格式,按 metadata.role 兼容")
    return errors, warnings


def lint_persona(persona_path: Path, strict: bool = False):
    """返回 (errors, warnings)"""
    errors, warnings = [], []
    role_id_from_filename = persona_path.stem

    if role_id_from_filename.startswith("_"):
        return [], []  # template 跳过

    with open(persona_path, "r", encoding="utf-8") as f:
        content = f.read()

    meta, body = parse_frontmatter(content)

    if is_legacy_expert_roundtable(meta, body, persona_path):
        return lint_legacy_expert(meta, body)

    # 1. frontmatter 必填
    for field in REQUIRED_META:
        if not meta.get(field):
            errors.append(f"frontmatter 缺少必填字段: {field}")

    # 2. id 与文件名一致
    if meta.get("id") and meta["id"] != role_id_from_filename:
        errors.append(
            f"id ({meta['id']}) 与文件名 ({role_id_from_filename}) 不一致"
        )

    # 3. L1-L5 + Few-shot 段落
    for section in REQUIRED_SECTIONS:
        if section not in body:
            msg = f"缺少结构段落: {section}"
            (errors if strict else warnings).append(msg)

    # 4. Few-shot 数量(至少 2 段以 "### 片段" 开头)
    fewshot_count = body.count("### 片段")
    if fewshot_count < 2:
        msg = f"Few-shot 示例数量不足: 当前 {fewshot_count} 段,建议 >= 3 段"
        (errors if strict else warnings).append(msg)

    # 5. imports 引用文件存在性
    for import_path in meta.get("imports", []) or []:
        full = SKILL_ROOT / import_path
        if not full.exists():
            errors.append(f"imports 引用不存在的文件: {import_path}")

    # 6. status=draft 提示
    if meta.get("status") == "draft":
        warnings.append("status=draft,本画像仍是测试版")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="校验角色画像完整性")
    parser.add_argument("role_id", nargs="?", help="角色 ID(不传则校验全部)")
    parser.add_argument("--strict", action="store_true", help="严格模式")
    args = parser.parse_args()

    personas_dir = SKILL_ROOT / "personas"
    if args.role_id:
        # 递归查找子目录下的同名画像
        matches = [p for p in personas_dir.rglob(f"{args.role_id}.md")
                   if "_ephemeral" not in p.parts]
        targets = matches if matches else [personas_dir / f"{args.role_id}.md"]
    else:
        # 递归扫描所有子目录(experts/ consumers/ bd/),跳过 _ephemeral/
        targets = sorted(p for p in personas_dir.rglob("*.md")
                         if "_ephemeral" not in p.parts)

    total_errors = 0
    total_warnings = 0
    print(f"=== 校验 {len(targets)} 个角色 (strict={args.strict}) ===\n")

    for path in targets:
        if not path.exists():
            print(f"❌ {path.name}: 文件不存在")
            total_errors += 1
            continue
        if path.stem.startswith("_"):
            continue

        errors, warnings = lint_persona(path, args.strict)
        if not errors and not warnings:
            print(f"✅ {path.name}: PASS")
        else:
            symbol = "❌" if errors else "⚠️ "
            print(f"{symbol} {path.name}:")
            for e in errors:
                print(f"   ERROR  | {e}")
            for w in warnings:
                print(f"   WARN   | {w}")
        total_errors += len(errors)
        total_warnings += len(warnings)
        print()

    print(f"=== 汇总: errors={total_errors}, warnings={total_warnings} ===")
    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()
