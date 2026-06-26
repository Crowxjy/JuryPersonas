#!/usr/bin/env python3
"""
jury_react.py — mode/jury-react 实现

职责:
1. 读 brief + scenario(可选) + persona id 列表 + artifact JSON
2. 对每位陪审员独立编译 system_prompt(复用 compile_persona)
3. 按 scenario 协议(默认 review-short-video.md 三段式刷视频)拼出 user_prompt
4. 输出 reactions_bundle JSON——每位陪审员一份独立的 prompt + 响应槽位

⚠️ 不直接调用 LLM:
  - 输出 bundle 后,调用方(orchestrator / 上层 Agent / 测试桩 mock_llm_responder)
    自行并行调用模型,把响应回填到 bundle.participants[*].reaction
  - 这一约束保证脚本可单测、可替换、不依赖具体 LLM endpoint

使用模式:

    # 标准入口
    python3 jury_react.py \\
        --brief-file <brief.json> \\
        --artifact-file <artifact.json> \\
        --persona-ids consumer-bao-mom-tier2,consumer-silver-male

    # 输出到文件
    python3 jury_react.py ... --output bundle.json

    # 自定义场景协议(默认 review-short-video)
    python3 jury_react.py ... --scenario review-short-video

输出 bundle 结构:
    {
      "mode": "mode/jury-react",
      "session_id": "...",
      "scenario": "review-short-video",
      "artifact": {... 透传},
      "brief_summary": {...},
      "instructions_for_caller": "对每位 participant 独立调模型...",
      "participants": [
        {
          "role_id": "...",
          "name": "...",
          "category": "...",
          "system_prompt": "...",
          "user_prompt": "...",
          "reaction": null              // 调用方回填
        }
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent.parent

from compile_persona import compile_persona

GENERIC_SCORE_METRICS: dict[str, list[str]] = {
    "review-prd": ["必要性", "可行性", "完整性", "风险可控性", "推荐推进度"],
    "review-design": ["可用性", "一致性", "视觉层级", "信息密度", "行动清晰度"],
    "review-screen": ["可用性", "一致性", "视觉层级", "信息密度", "行动清晰度"],
    "review-detail-page": ["理解效率", "信任证据", "购买意愿", "价格清晰度", "行动清晰度"],
    "review-product-card": ["理解效率", "信任证据", "购买意愿", "价格清晰度", "行动清晰度"],
    "review-marketing-copy": ["读完意愿", "利益清晰度", "信任感", "转化意愿", "传播意愿"],
}

DEFAULT_SCORE_METRICS = ["理解意愿", "参与意愿", "行动意愿", "信任度", "推荐意愿"]

SHORT_VIDEO_USER_PROMPT_TEMPLATE = """\
你将以陪审员身份独立评审一条短视频成片。请**不要互相参考**其他陪审员的发言,严格按你的角色 L3 心智 + L4 行为做反应。

## 评审对象(短视频元信息)

- 标题: {title}
- 平台: {platform}
- 时长: {duration_sec} 秒
- 关键帧序列(按时间轴):
{key_frames_block}
- CTA: {cta_text}(出现在 {cta_ts} 秒)
- 视频核心 claims: {claims}

## 评审目标人群

- 本视频面向的目标受众: {target_audience}
- 调用方最关心的维度: {key_concern}

## 评审产物结构(必须按下面 5 个段落输出,中间用 `---` 分隔)

### 1) 我现在的场景(L4 推断)
一句话说明你在什么状态下刷到这条:中午吃饭外放?睡前静音?边走边看?

### 2) 三段式刷视频反应
- **0-3 秒(决定要不要继续看)**:第一眼看到什么、我的反应(继续/划走)、原因
- **3-15 秒(决定要不要看完)**:视频在讲什么、我能否 get、有没有"我能用上/我感兴趣/我有共鸣"、我的反应(继续/跳进度/划走/静音)
- **15 秒-结束(决定要不要互动)**:有没有想点赞/评论/转发/收藏/下单、CTA 我会跟着做吗

### 3) 我看完后的至少 3 个具体问题(对齐 5 字段聚合表)
必须逐条输出,每条都使用下面的标题 + 5 行列表格式;字段名不能改,不要输出字段说明表:

#### 问题 1
- 所属人群: 你的 category + sub_category
- 关注点: 钩子无力 / 信息密度 / 信任感 / 字幕音频 / 节奏 / CTA / 与我无关 / 套路太重 / 信息缺失(8 选 1)
- 卡点位置: 视频内时间点或元素(如"0-3 秒封面字太小""32 秒处 CTA")
- 可能流失原因: 用你角色口吻说的原因(不允许平台话术)
- 改进建议: 可执行的修改方向(单句口语化)

#### 问题 2
- 所属人群: ...
- 关注点: ...
- 卡点位置: ...
- 可能流失原因: ...
- 改进建议: ...

#### 问题 3
- 所属人群: ...
- 关注点: ...
- 卡点位置: ...
- 可能流失原因: ...
- 改进建议: ...

### 4) 我会让博主怎么改(用我的话说,3 条)

### 5) 我的真实行为(0-10 量化)
- 完播倾向: x/10
- 互动倾向: x/10
- 转化倾向: x/10
- 信任度: x/10
- 推荐倾向: x/10

最后用一句话浓缩结论,符合你的语言风格。

## 评审硬约束(违反作废)

1. ❌ 不允许平台话术(不要说"完播率""黄金 3 秒""钩子设计")——这些只能在中立汇总段出现
2. ❌ 不允许"挺好的""还行"等无信息量评价
3. ❌ 评估视角是"会不会被劝退/流失",不是"会不会喜欢";"我觉得很好"必须立刻补一句"但是 XX 类型的人可能会卡在 YY"
4. ❌ 视频内容完全在你盲区时(如让蓝领评高端美妆),坦诚说"这条不是给我看的",再从"被错误推荐"角度评价
5. ❌ 转化倾向打分必须保守,除非真的让你想下单/转发,否则默认 ≤ 4
6. ❌ 严禁编造视频内容,关键帧描述模糊不清时必须先指出"画面看不清,我没法准确评论"
7. ❌ 严禁预测完播率/转化率绝对值
"""

GENERIC_USER_PROMPT_TEMPLATE = """\
你将以陪审员身份独立评审一个「{scenario_name}」对象。请**不要互相参考**其他陪审员的发言,严格按你的角色画像、知识边界和语言风格做判断。

## 评审场景协议

{scenario_protocol}

## 评审对象

- 类型: {artifact_type}
- 定位: {artifact_locator}
- 标题/名称: {artifact_title}

### 原始素材/结构化内容

```json
{artifact_json}
```

## Observe 阶段结构化证据

```json
{observations_json}
```

注意:除 heatmap / cross-page / annotate-issues 等 HCI 结果外,Observe 内容主要是对原始素材的结构化整理,不是机器已经完成的价值判断。你可以引用它定位证据,但不能把它当成真实用户效果或最终结论。

## Brief 摘要

- 目标受众: {target_audience}
- 关键关心点: {key_concern}
- 分布/陪审员选择方式: {distribution_intent}

## 评审产物结构

请按以下结构输出,中间用 `---` 分隔:

### 1) 我的第一反应
用你的角色口吻说明第一眼/第一遍读完的直觉反应,不超过 3 句。

### 2) 我重点看的问题
结合你的角色立场,说明你优先检查哪些点,以及 Observe 阶段证据对你的判断有什么帮助。

### 3) 我发现的至少 3 个具体问题
必须逐条输出,每条都使用下面的标题 + 5 行列表格式;字段名不能改,不要输出字段说明表:

#### 问题 1
- 所属人群: 你的 category + sub_category
- 关注点: 信息缺失 / 理解成本 / 信任感 / 转化阻力 / 合规红线 / 体验断点 / 与我无关 / 决策风险
- 卡点位置: 文档章节、页面区域、文案句子、商品卡字段或具体证据位置
- 可能流失原因: 用你角色口吻说明为什么会卡住
- 改进建议: 可执行的修改方向

#### 问题 2
- 所属人群: ...
- 关注点: ...
- 卡点位置: ...
- 可能流失原因: ...
- 改进建议: ...

#### 问题 3
- 所属人群: ...
- 关注点: ...
- 卡点位置: ...
- 可能流失原因: ...
- 改进建议: ...

### 4) 我建议优先怎么改
给 3 条建议,按优先级排序。

### 5) 我的真实行为/判断(0-10 量化)
请严格使用当前场景的 5 个指标名,每行格式为 `- 指标名: x/10`:
{score_metrics_block}

最后用一句话浓缩结论,符合你的语言风格。

## 硬约束

1. 不允许预测转化率/点击率/完播率等绝对值
2. 不允许把素材中没有出现的信息当成事实
3. Observe 阶段没有覆盖的内容,必须标明"缺失/无法判断",不能脑补
4. 你只独立陈述,不要替其他陪审员总结
5. 如果素材完全不适合你的角色,要承认盲区并说明为什么
"""


def load_json_file(path: Path, label: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{label} 文件不存在: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def render_short_video_user_prompt(brief: dict, artifact: dict) -> str:
    key_frames = artifact.get("key_frames", [])
    if key_frames:
        kf_lines = []
        for kf in key_frames:
            ts = kf.get("ts_sec", "?")
            desc = kf.get("description", "")
            vo = kf.get("voiceover")
            line = f"  - [{ts}s] {desc}"
            if vo:
                line += f" / 台词: \"{vo}\""
            kf_lines.append(line)
        kf_block = "\n".join(kf_lines)
    else:
        kf_block = "  - (无关键帧,只有视频链接,你必须明确指出'画面看不清,我没法准确评论')"

    cta = artifact.get("cta") or {}
    claims = artifact.get("claims", [])

    return SHORT_VIDEO_USER_PROMPT_TEMPLATE.format(
        title=artifact.get("title", "(未提供)"),
        platform=artifact.get("platform", "(未提供)"),
        duration_sec=artifact.get("duration_sec", "(未提供)"),
        key_frames_block=kf_block,
        cta_text=cta.get("text", "(无)"),
        cta_ts=cta.get("ts_sec", "?"),
        claims="、".join(claims) if claims else "(未提供)",
        target_audience=brief["fields"]["target_audience"].get("value", "(未指定)"),
        key_concern=brief["fields"]["key_concern"].get("value", "(未指定)"),
    )


def compact_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def render_generic_user_prompt(
    brief: dict,
    artifact: dict,
    *,
    scenario: str,
    observations: dict | None = None,
) -> str:
    scenario_path = SKILL_ROOT / "scenarios" / f"{scenario}.md"
    scenario_protocol = (
        scenario_path.read_text(encoding="utf-8")
        if scenario_path.exists()
        else f"(未找到场景协议: {scenario})"
    )
    fields = brief.get("fields", {})
    score_metrics = GENERIC_SCORE_METRICS.get(scenario, DEFAULT_SCORE_METRICS)
    score_metrics_block = "\n".join(f"- {metric}: x/10" for metric in score_metrics)
    return GENERIC_USER_PROMPT_TEMPLATE.format(
        scenario_name=scenario,
        scenario_protocol=scenario_protocol,
        artifact_type=fields.get("artifact_type", {}).get("value", "(未指定)"),
        artifact_locator=fields.get("artifact_locator", {}).get("value", "(未指定)"),
        artifact_title=artifact.get("title") or artifact.get("name") or "(未提供)",
        artifact_json=compact_json(artifact),
        observations_json=compact_json(observations or {}),
          score_metrics_block=score_metrics_block,
        target_audience=fields.get("target_audience", {}).get("value", "(未指定)"),
        key_concern=fields.get("key_concern", {}).get("value", "(未指定)"),
        distribution_intent=fields.get("distribution_intent", {}).get("value", "(未指定)"),
    )


SCENARIO_RENDERERS = {
    "review-short-video": render_short_video_user_prompt,
}


def build_jury_react_bundle(
    brief: dict,
    artifact: dict,
    persona_ids: list[str],
    scenario: str = "review-short-video",
    observations: dict | None = None,
) -> dict:
    renderer = SCENARIO_RENDERERS.get(scenario)
    if renderer:
        user_prompt = renderer(brief, artifact)
        if observations:
            user_prompt += "\n\n## Observe 阶段补充观察\n\n```json\n"
            user_prompt += compact_json(observations)
            user_prompt += "\n```\n"
    else:
        user_prompt = render_generic_user_prompt(
            brief,
            artifact,
            scenario=scenario,
            observations=observations,
        )

    bundle = {
        "mode": "mode/jury-react",
        "session_id": brief.get("session_id"),
        "scenario": scenario,
        "artifact": artifact,
        "observations": observations or {},
        "brief_summary": {
            k: v.get("value") for k, v in brief.get("fields", {}).items()
        },
        "instructions_for_caller": (
            "对每位 participant 独立调用 LLM:system 用其 system_prompt,"
            "user 用其 user_prompt。陪审员之间严禁互相参考。"
            "调用完成后将 LLM 响应填入 participants[*].reaction(string),"
            "再交给 mode/aggregate-consensus 聚合。"
        ),
        "participants": [],
        "errors": [],
    }

    for rid in persona_ids:
        try:
            compiled = compile_persona(
                rid,
                context={
                    "scenario": scenario,
                    "artifact_type": bundle["brief_summary"].get("artifact_type"),
                },
            )
        except (FileNotFoundError, RuntimeError) as e:
            bundle["errors"].append(f"role_id={rid}: {e}")
            continue
        bundle["participants"].append(
            {
                "role_id": rid,
                "name": compiled["meta"].get("name", rid),
                "category": compiled["meta"].get("category", ""),
                "sub_category": compiled["meta"].get("sub_category", ""),
                "status": compiled["meta"].get("status", ""),
                "system_prompt": compiled["system_prompt"],
                "user_prompt": user_prompt,
                "reaction": None,
            }
        )

    return bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="mode/jury-react 实现")
    parser.add_argument("--brief-file", required=True, help="brief JSON 路径")
    parser.add_argument("--artifact-file", required=True, help="评审对象 JSON 路径")
    parser.add_argument(
        "--persona-ids",
        required=True,
        help="陪审员 role_id 列表,逗号分隔",
    )
    parser.add_argument(
        "--scenario",
        default="review-short-video",
        help="场景模板(默认 review-short-video)",
    )
    parser.add_argument("--output", "-o", help="输出 bundle 文件(默认 stdout)")
    parser.add_argument("--pretty", action="store_true", help="美化 JSON 输出")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    brief = load_json_file(Path(args.brief_file), "brief")
    artifact = load_json_file(Path(args.artifact_file), "artifact")
    persona_ids = [r.strip() for r in args.persona_ids.split(",") if r.strip()]
    if not persona_ids:
        sys.stderr.write("[error] --persona-ids 至少要有一个\n")
        return 2

    bundle = build_jury_react_bundle(brief, artifact, persona_ids, args.scenario)
    indent = 2 if args.pretty else None
    out = json.dumps(bundle, ensure_ascii=False, indent=indent)

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        sys.stdout.write(
            f"[OK] jury-react bundle → {args.output} "
            f"({len(bundle['participants'])} 位陪审员"
            f"{'，' + str(len(bundle['errors'])) + ' 条错误' if bundle['errors'] else ''})\n"
        )
    else:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
