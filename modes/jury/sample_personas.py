#!/usr/bin/env python3
"""
sample_personas.py — 按真实联合分布从画像池采样 N 个 Agent (PRD F3 群体层)

设计准则 (对齐《EAgents 消费者画像群体内容预评估 PRD v1.0》):
- 必须按"商家真实联合分布"采样,不允许等概率随机组合,避免幽灵用户
- 每个采样桶对应分布中一个非零概率的标签组合
- 桶内优先匹配现有 personas/ 池;匹配不到 → fit 兜底 (生成临时 _fit_ 画像设定,
  不落盘,直接进 system_prompts)
- 同时支持双分布对比 (PRD F6):current vs target,输出增量洞察

输入:
    --dist <distribution.json>       必填,商家/品类联合分布
    --target-dist <target.json>      可选,目标拓展分布,启用 F6 增量分析
    -n / --count <int>               采样 N 个 Agent,默认 12
    --pool personas/                 画像池目录,默认全 personas
    --seed <int>                     随机种子(默认 42,保证可重复)
    --output <dir>                   把采样结果包+ system prompt 写到目录;不传则 stdout JSON
    --strict-pool                    匹配不到画像就报错,而不是 fit 兜底

输出 JSON schema:
{
  "merchant_id": "...",
  "n": 12,
  "buckets": [
    {
      "bucket_id": "b1",
      "weight": 0.22,
      "target_count": 3,
      "axes": {"age_band":"25-35","gender":"女", ...},
      "tags_hint": [...],
      "agents": [
        {"role_id":"consumer-bao-mom-tier2","source":"pool","match_score":0.83},
        {"role_id":"_fit_bucket_b1_2","source":"fit","fit_spec":{...}}
      ]
    },
    ...
  ],
  "gap_vs_target": [                  # 仅当 --target-dist 给出
    {"bucket":"二线宝妈/中低","current":0.22,"target":0.12,"delta":-0.10,"note":"现状超配,目标弱化"},
    ...
  ],
  "missing_in_pool": ["..."],          # 池中找不到合适匹配的标签
  "seed": 42
}
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent

from compile_persona import parse_frontmatter, compile_persona
from fit_persona import build_persona as build_fit_persona, emit_prompt as emit_fit_prompt


def load_distribution(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    required = {"axes", "joint_distribution"}
    if not required.issubset(d.keys()):
        raise ValueError(f"分布文件缺字段: 需要 {required},当前 {set(d.keys())}")
    total = sum(b.get("weight", 0) for b in d["joint_distribution"])
    if abs(total - 1.0) > 0.05:
        print(f"WARN: 联合分布 weight 求和={total:.3f}, 偏离 1.0 超过 0.05", file=sys.stderr)
    return d


def load_pool(pool_dir: Path) -> list:
    pool = []
    for f in sorted(pool_dir.rglob("*.md")):
        if f.name.startswith("_template") or f.name.startswith("_fit_"):
            continue
        # 跳过 _ephemeral/ 下的临时画像,避免污染采样池
        if "_ephemeral" in f.parts:
            continue
        try:
            content = f.read_text(encoding="utf-8")
            meta, _ = parse_frontmatter(content)
        except Exception as e:
            print(f"WARN: 解析 {f.name} 失败: {e}", file=sys.stderr)
            continue
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in re.split(r"[,，、]", tags) if t.strip()]
        basic = meta.get("basic") or {}
        pool.append({
            "role_id": meta.get("id", f.stem),
            "category": meta.get("category", ""),
            "sub_category": meta.get("sub_category", ""),
            "tags": [str(t).strip("[] ") for t in tags],
            "basic": basic if isinstance(basic, dict) else {},
            "status": meta.get("status", ""),
            "path": str(f.relative_to(SKILL_ROOT)),
        })
    return pool


def match_score(bucket: dict, persona: dict) -> float:
    """计算桶与画像的匹配分。

    返回 -1 表示硬冲突(性别不同 / 年龄不在桶段),应直接走 fit 兜底,
    避免用 Z 世代女画像去演 25+ 中产男人这种跨桶错配。
    """
    hint = set(str(x) for x in bucket.get("tags_hint", []))
    ptags = set(persona["tags"])
    if not hint:
        jaccard = 0.0
    else:
        inter = sum(1 for h in hint if any(h in pt or pt in h for pt in ptags))
        union = max(len(hint), 1)
        jaccard = inter / union

    axes = bucket.get("axes", {})
    age = str(axes.get("age_band", ""))
    gender = str(axes.get("gender", ""))
    basic = persona.get("basic", {})

    p_age = str(basic.get("age", ""))
    age_ok = None  # None=无信息;True=命中;False=硬冲突
    if age and p_age and re.search(r"\d+", p_age):
        try:
            n = int(re.search(r"\d+", p_age).group())
            m = re.match(r"(\d+)\s*[-–]\s*(\d+)", age)
            if m:
                age_ok = int(m.group(1)) <= n <= int(m.group(2))
            elif age.endswith("+"):
                age_ok = n >= int(age.rstrip("+"))
        except Exception:
            age_ok = None

    p_gender = str(basic.get("gender", ""))
    gender_ok = None
    if gender and gender != "任意" and p_gender:
        gender_ok = gender[0] == p_gender[0]

    if age_ok is False or gender_ok is False:
        return -1.0

    axes_bonus = 0.0
    if age_ok:
        axes_bonus += 0.25
    if gender_ok:
        axes_bonus += 0.15

    return jaccard + axes_bonus


def allocate_counts(buckets: list, n: int) -> list:
    """按权重把 n 个名额分给各桶,余数按最大余数法分配。"""
    raw = [b["weight"] * n for b in buckets]
    floor = [int(x) for x in raw]
    remain = n - sum(floor)
    frac = sorted(enumerate(raw), key=lambda kv: -(kv[1] - int(kv[1])))
    for i in range(remain):
        floor[frac[i][0]] += 1
    return floor


def build_fit_spec(bucket: dict, idx: int) -> dict:
    axes = bucket.get("axes", {})
    sub_cat = "/".join([
        str(axes.get(k, ""))
        for k in ("age_band", "gender", "city_tier")
        if axes.get(k)
    ])
    return {
        "id": f"_fit_bucket_{bucket['bucket_id']}_{idx}",
        "category": "消费者",
        "sub_category": sub_cat or "未命名桶",
        "tags": list(bucket.get("tags_hint", [])),
        "basic": {
            "age_band": axes.get("age_band"),
            "gender": axes.get("gender"),
            "city_tier": axes.get("city_tier"),
        },
        "fragments": [
            {
                "source": "note",
                "text": f"本画像由 sample_personas.py 自桶 {bucket['bucket_id']} 兜底生成。"
                        f"该桶代表分布中 weight={bucket['weight']:.2f} 的一组人群,但 personas/ 池中"
                        f"无合适匹配。回答时若涉及该桶画像之外的话题,必须以盲区处理。",
            }
        ],
    }


def sample_agents(bucket: dict, n_slots: int, pool: list, rng: random.Random,
                  strict: bool) -> list:
    scored = sorted(
        ((match_score(bucket, p), p) for p in pool),
        key=lambda kv: -kv[0],
    )
    agents = []
    used = set()
    for score, p in scored:
        if len(agents) >= n_slots:
            break
        if score < 0.20:
            break
        if p["role_id"] in used:
            continue
        agents.append({
            "role_id": p["role_id"],
            "source": "pool",
            "match_score": round(score, 3),
            "path": p["path"],
        })
        used.add(p["role_id"])

    fit_idx = 0
    while len(agents) < n_slots:
        if strict:
            raise RuntimeError(
                f"桶 {bucket['bucket_id']} 池内无合适匹配,strict 模式禁用 fit 兜底。"
            )
        fit_idx += 1
        agents.append({
            "role_id": f"_fit_bucket_{bucket['bucket_id']}_{fit_idx}",
            "source": "fit",
            "fit_spec": build_fit_spec(bucket, fit_idx),
        })
    return agents


def compute_gap(current: dict, target: dict) -> list:
    """对齐 PRD F6:按轴向交集取桶 key,输出 delta。"""
    cur_axes = current.get("axes") or []
    tar_axes = target.get("axes") or []
    common_axes = [a for a in cur_axes if a in tar_axes]

    def key(b, axes):
        return tuple((a, b.get(a)) for a in axes)

    cur_map = {key(b, common_axes): b for b in current["joint_distribution"]}
    tar_map = {key(b, common_axes): b for b in target["joint_distribution"]}
    gap = []
    keys = set(cur_map) | set(tar_map)
    for k in keys:
        c = cur_map.get(k, {})
        t = tar_map.get(k, {})
        cw = c.get("weight", 0)
        tw = t.get("weight", 0)
        delta = tw - cw
        if abs(delta) < 0.02:
            continue
        label = "/".join(str(v) for _, v in k)
        note = ("目标增量(目前覆盖不足)" if delta > 0.05
                else "目标弱化(现状超配)" if delta < -0.05
                else "微调")
        gap.append({
            "bucket": label,
            "current_weight": round(cw, 3),
            "target_weight": round(tw, 3),
            "delta": round(delta, 3),
            "note": note,
            "tags_hint": (t.get("tags_hint") or c.get("tags_hint") or []),
        })
    gap.sort(key=lambda x: -abs(x["delta"]))
    return gap


def main():
    parser = argparse.ArgumentParser(
        description="按真实联合分布采样 N 个 Agent (PRD F3)"
    )
    parser.add_argument("--dist", required=True, help="商家/品类联合分布 JSON")
    parser.add_argument("--target-dist", help="目标拓展分布 JSON,启用 F6 增量")
    parser.add_argument("-n", "--count", type=int, default=12, help="采样总数 N")
    parser.add_argument("--pool", default="personas", help="画像池目录")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径")
    parser.add_argument("--strict-pool", action="store_true",
                        help="池内无匹配直接报错,不 fit 兜底")
    parser.add_argument("--brief", action="store_true",
                        help="只打 markdown 摘要(默认 stdout 是 JSON)")
    parser.add_argument("--emit-prompts", metavar="DIR",
                        help="把每个 Agent 的 System Prompt 落到目录(<dir>/<bucket>_<idx>_<role>.prompt.md)")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    current = load_distribution(Path(args.dist))
    target = load_distribution(Path(args.target_dist)) if args.target_dist else None
    pool = load_pool(SKILL_ROOT / args.pool)

    target_category = current.get("target_category")
    if target_category:
        pool = [p for p in pool if p["category"] == target_category]

    buckets = []
    axes_keys = current.get("axes") or []
    for i, raw in enumerate(current["joint_distribution"]):
        b = dict(raw)
        b["bucket_id"] = f"b{i+1}"
        b["axes"] = {k: raw.get(k) for k in axes_keys if k in raw}
        buckets.append(b)

    counts = allocate_counts(buckets, args.count)

    result_buckets = []
    missing = []
    for b, n_slots in zip(buckets, counts):
        if n_slots == 0:
            continue
        agents = sample_agents(b, n_slots, pool, rng, args.strict_pool)
        if any(a["source"] == "fit" for a in agents):
            missing.append({
                "bucket_id": b["bucket_id"],
                "tags_hint": b.get("tags_hint", []),
                "axes": b.get("axes", {}),
            })
        result_buckets.append({
            "bucket_id": b["bucket_id"],
            "weight": b["weight"],
            "target_count": n_slots,
            "axes": b.get("axes", {}),
            "tags_hint": b.get("tags_hint", []),
            "agents": agents,
        })

    result = {
        "merchant_id": current.get("merchant_id"),
        "merchant_name": current.get("merchant_name"),
        "n_requested": args.count,
        "n_actual": sum(len(b["agents"]) for b in result_buckets),
        "seed": args.seed,
        "buckets": result_buckets,
        "missing_in_pool": missing,
    }
    if target:
        result["gap_vs_target"] = compute_gap(current, target)

    if args.emit_prompts:
        out_dir = Path(args.emit_prompts)
        out_dir.mkdir(parents=True, exist_ok=True)
        emitted = []
        for b in result_buckets:
            for idx, a in enumerate(b["agents"], start=1):
                if a["source"] == "pool":
                    compiled = compile_persona(a["role_id"])
                    prompt = compiled["system_prompt"]
                else:
                    built = build_fit_persona(a["fit_spec"])
                    prompt = emit_fit_prompt(built["markdown"], built["role_id"])
                fname = f"{b['bucket_id']}_{idx:02d}_{a['role_id']}.prompt.md"
                (out_dir / fname).write_text(prompt, encoding="utf-8")
                emitted.append(fname)
        result["emitted_prompts"] = emitted

    if args.brief:
        render_brief(result)
    else:
        out = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(out, encoding="utf-8")
            print(f"OK: 已写入 {args.output} ({len(out)} chars)")
        else:
            print(out)


def render_brief(result):
    print(f"# 采样结果 · {result.get('merchant_name','(未命名商家)')}")
    print(f"- merchant_id: `{result.get('merchant_id')}`")
    print(f"- 请求样本数: {result['n_requested']},实际: {result['n_actual']},seed={result['seed']}")
    print()
    print("## 桶分配")
    print()
    print("| 桶 | 权重 | 名额 | 轴向 | 池命中 | fit 兜底 |")
    print("|---|---|---|---|---|---|")
    for b in result["buckets"]:
        ax = "/".join(str(v) for v in b["axes"].values())
        n_pool = sum(1 for a in b["agents"] if a["source"] == "pool")
        n_fit = sum(1 for a in b["agents"] if a["source"] == "fit")
        print(f"| {b['bucket_id']} | {b['weight']:.2f} | {b['target_count']} | {ax} | {n_pool} | {n_fit} |")
    print()
    print("## 采样到的 Agent 清单")
    for b in result["buckets"]:
        print(f"\n### {b['bucket_id']} · {'/'.join(str(v) for v in b['axes'].values())}")
        for a in b["agents"]:
            if a["source"] == "pool":
                print(f"- ✅ `{a['role_id']}` (pool, score={a['match_score']})")
            else:
                tags = ",".join(a["fit_spec"]["tags"])
                print(f"- 🧪 `{a['role_id']}` (fit, tags={tags})")
    if result.get("missing_in_pool"):
        print("\n## ⚠️ 池内无匹配的桶 (建议下一轮新增画像)")
        for m in result["missing_in_pool"]:
            print(f"- 桶 {m['bucket_id']}: 标签 {m['tags_hint']}")
    if result.get("gap_vs_target"):
        print("\n## F6 双分布增量洞察 (current → target)")
        print()
        print("| 桶 | 现状 | 目标 | Δ | 解读 |")
        print("|---|---|---|---|---|")
        for g in result["gap_vs_target"]:
            print(f"| {g['bucket']} | {g['current_weight']:.2f} | {g['target_weight']:.2f} | "
                  f"{g['delta']:+.2f} | {g['note']} |")


if __name__ == "__main__":
    main()
