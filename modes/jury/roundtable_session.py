#!/usr/bin/env python3
"""
roundtable_session.py — 多轮真实讨论圆桌会话骨架

目标:
1. 复用 compile_persona.py 产出的单角色 system prompt
2. 生成可执行的会话状态对象
3. 为上层调用方提供轮次上下文构建、turn 记录、共享讨论板更新等基础能力

说明:
- 本脚本不直接调用 LLM,只负责编排数据结构
- 调用方应自行注入模型调用,然后使用 append_turn() 回写结果
- 当前版本是 MVP 骨架,重点是流程和状态管理 contract

示例:
    python3 roundtable_session.py ad-buyer,consumer-genz-female \
      --topic "评价新的抖音购物车体验"
"""
import argparse
import json
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone

from compile_persona import compile_persona

SCHEMA_VERSION = "1.0"
MAX_PARTICIPANTS = 4
DEFAULT_MODERATOR = {
    "name": "中立主持人",
    "policy": "只做总结、追问、收束,不代表任何角色立场。",
}
DEFAULT_STOP_RULES = {
    "enable_early_stop": True,
    "stop_when_no_new_disagreement_rounds": 1,
    "stop_when_positions_stable": True,
}


def now_iso():
    """返回 UTC ISO 时间戳"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_role_ids(role_ids):
    """限制参与角色数量,避免上下文膨胀过快。"""
    if not role_ids:
        raise ValueError("至少需要一个角色 ID")
    if len(role_ids) > MAX_PARTICIPANTS:
        raise ValueError(
            f"参与角色过多: 当前 {len(role_ids)} 个,最大支持 {MAX_PARTICIPANTS} 个"
        )


def build_round_plan(max_rounds: int, role_ids):
    """生成固定轮次计划,后续可扩展为动态策略。"""
    templates = [
        ("初始立场陈述", "opening"),
        ("回应他人观点", "response"),
        ("收敛与最终建议", "conclusion"),
    ]
    rounds = []
    for index in range(max_rounds):
        if index < len(templates):
            goal, turn_type = templates[index]
        else:
            goal, turn_type = (f"第 {index + 1} 轮补充追问", "followup")
        rounds.append({
            "round_id": index + 1,
            "goal": goal,
            "turn_type": turn_type,
            "status": "pending",
            "speaker_order": list(role_ids),
            "turns": [],
        })
    return rounds


def build_participant(role_id: str):
    """构建 participant 对象,兼容现有 compile_persona 输出。"""
    result = compile_persona(role_id)
    meta = result["meta"]
    return {
        "role_id": role_id,
        "name": meta.get("name", role_id),
        "category": meta.get("category", ""),
        "sub_category": meta.get("sub_category", ""),
        "status": meta.get("status", ""),
        "system_prompt": result["system_prompt"],
        "stance": {
            "position": None,
            "score": None,
            "confidence": None,
        },
        "state": {
            "has_spoken": False,
            "last_round_seen": 0,
            "last_turn_id": None,
        },
    }


def build_session(
    role_ids,
    topic,
    artifact=None,
    max_rounds=3,
    speaker_policy="sequential",
    response_style="structured",
):
    """初始化一个多轮圆桌会话对象。"""
    validate_role_ids(role_ids)
    participants = [build_participant(role_id) for role_id in role_ids]
    session_id = f"rt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    created_at = now_iso()

    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "mode": "multi_round_roundtable",
        "status": "initialized",
        "topic": topic,
        "artifact": artifact or {
            "type": "text",
            "ref": None,
            "content": None,
        },
        "config": {
            "max_rounds": max_rounds,
            "max_participants": MAX_PARTICIPANTS,
            "speaker_policy": speaker_policy,
            "summary_strategy": "compressed_board",
            "response_style": response_style,
            "stop_rules": deepcopy(DEFAULT_STOP_RULES),
        },
        "participants": participants,
        "rounds": build_round_plan(max_rounds, [p["role_id"] for p in participants]),
        "shared_board": {
            "consensus": [],
            "disagreements": [],
            "open_questions": [],
            "proposals": [],
            "last_updated_round": 0,
        },
        "moderator": deepcopy(DEFAULT_MODERATOR),
        "final_summary": None,
        "meta": {
            "created_at": created_at,
            "updated_at": created_at,
            "source": "scripts/roundtable_session.py",
        },
    }


def get_round(session, round_id: int):
    """按 round_id 查找 round。"""
    for round_item in session["rounds"]:
        if round_item["round_id"] == round_id:
            return round_item
    raise KeyError(f"round_id 不存在: {round_id}")


def get_participant(session, role_id: str):
    """按 role_id 查找 participant。"""
    for participant in session["participants"]:
        if participant["role_id"] == role_id:
            return participant
    raise KeyError(f"role_id 不存在: {role_id}")


def summarize_latest_view(turn):
    """提取 turn 的简短摘要,避免把完整历史灌给其他角色。"""
    structured = turn["output"].get("structured", {})
    position = structured.get("position") or "未表态"
    concerns = structured.get("top_concerns") or []
    proposal = structured.get("proposal") or "暂无明确建议"
    concern_text = " / ".join(concerns[:2]) if concerns else "无显式风险点"
    return f"立场: {position}; 关注点: {concern_text}; 建议: {proposal}"


def list_other_views(session, speaker_role_id: str):
    """读取其他角色最近一轮的摘要。"""
    summaries = []
    latest_turn_by_speaker = {}
    for round_item in session["rounds"]:
        for turn in round_item["turns"]:
            latest_turn_by_speaker[turn["speaker"]] = turn

    for participant in session["participants"]:
        if participant["role_id"] == speaker_role_id:
            continue
        latest_turn = latest_turn_by_speaker.get(participant["role_id"])
        if not latest_turn:
            continue
        summaries.append({
            "role_id": participant["role_id"],
            "name": participant["name"],
            "summary": summarize_latest_view(latest_turn),
        })
    return summaries


def build_turn_instruction(round_item, participant):
    """生成当前轮次的结构化回答要求。"""
    return (
        f"你正在参加第 {round_item['round_id']} 轮圆桌讨论。\n"
        f"本轮目标: {round_item['goal']}\n"
        f"请继续保持角色 {participant['name']} 的身份与语言风格。\n"
        "请按以下结构回答:\n"
        "1. 本轮核心观点\n"
        "2. 你同意谁的哪一点\n"
        "3. 你反对谁的哪一点,理由是什么\n"
        "4. 你的立场是否变化\n"
        "5. 你的建议或追问\n"
    )


def build_turn_context(session, round_id: int, speaker_role_id: str):
    """为单个发言 turn 生成输入上下文。"""
    round_item = get_round(session, round_id)
    participant = get_participant(session, speaker_role_id)
    artifact = session.get("artifact") or {}
    return {
        "topic": session["topic"],
        "round_goal": round_item["goal"],
        "artifact_excerpt": artifact.get("content"),
        "other_views_summary": list_other_views(session, speaker_role_id),
        "shared_board_snapshot": deepcopy(session["shared_board"]),
        "instruction": build_turn_instruction(round_item, participant),
    }


def normalize_structured_output(structured=None):
    """为模型回写结果兜底默认字段。"""
    structured = structured or {}
    return {
        "position": structured.get("position"),
        "score": structured.get("score"),
        "confidence": structured.get("confidence"),
        "top_concerns": list(structured.get("top_concerns", [])),
        "agreements": list(structured.get("agreements", [])),
        "disagreements": list(structured.get("disagreements", [])),
        "proposal": structured.get("proposal"),
        "open_questions": list(structured.get("open_questions", [])),
        "changed_position": bool(structured.get("changed_position", False)),
    }


def append_turn(
    session,
    round_id: int,
    speaker_role_id: str,
    content: str,
    structured=None,
    meta=None,
    input_context=None,
):
    """记录一个新的角色发言 turn。"""
    round_item = get_round(session, round_id)
    participant = get_participant(session, speaker_role_id)
    turn_id = f"r{round_id}_t{len(round_item['turns']) + 1}"

    turn = {
        "turn_id": turn_id,
        "round_id": round_id,
        "speaker": speaker_role_id,
        "turn_type": round_item["turn_type"],
        "input_context": input_context or build_turn_context(session, round_id, speaker_role_id),
        "output": {
            "content": content,
            "structured": normalize_structured_output(structured),
        },
    }
    if meta:
        turn["meta"] = dict(meta)

    round_item["turns"].append(turn)
    participant["state"]["has_spoken"] = True
    participant["state"]["last_round_seen"] = round_id
    participant["state"]["last_turn_id"] = turn_id

    output = turn["output"]["structured"]
    participant["stance"]["position"] = output["position"]
    participant["stance"]["score"] = output["score"]
    participant["stance"]["confidence"] = output["confidence"]

    round_item["status"] = "done" if len(round_item["turns"]) >= len(round_item["speaker_order"]) else "running"
    session["status"] = "running"
    session["meta"]["updated_at"] = now_iso()
    update_shared_board(session, round_id)
    return turn


def dedupe_keep_order(items):
    """去重但保留原始顺序。"""
    seen = set()
    output = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def update_shared_board(session, round_id: int):
    """根据当前所有 turn 的 structured 输出,维护一个压缩讨论板。"""
    consensus = []
    disagreements = []
    open_questions = []
    proposals = []

    for round_item in session["rounds"]:
        for turn in round_item["turns"]:
            structured = turn["output"]["structured"]
            consensus.extend(structured.get("agreements", []))
            disagreements.extend(structured.get("disagreements", []))
            open_questions.extend(structured.get("open_questions", []))
            if structured.get("proposal"):
                proposals.append(structured["proposal"])

    session["shared_board"] = {
        "consensus": dedupe_keep_order(consensus),
        "disagreements": dedupe_keep_order(disagreements),
        "open_questions": dedupe_keep_order(open_questions),
        "proposals": dedupe_keep_order(proposals),
        "last_updated_round": round_id,
    }
    session["meta"]["updated_at"] = now_iso()


def should_stop_early(session):
    """MVP 停止条件: 全员在最近两轮都未改变立场,或已无分歧。"""
    stop_rules = session["config"].get("stop_rules", {})
    if not stop_rules.get("enable_early_stop", True):
        return False

    if not session["shared_board"]["disagreements"]:
        return True

    if len(session["rounds"]) < 2:
        return False

    changed_in_recent_rounds = False
    for round_item in session["rounds"][-2:]:
        for turn in round_item["turns"]:
            if turn["output"]["structured"].get("changed_position"):
                changed_in_recent_rounds = True
                break
        if changed_in_recent_rounds:
            break
    return not changed_in_recent_rounds


def finalize_session(session):
    """产出中立总结,供外层渲染给用户。"""
    session["final_summary"] = {
        "consensus": list(session["shared_board"]["consensus"]),
        "disagreements": list(session["shared_board"]["disagreements"]),
        "recommended_actions": list(session["shared_board"]["proposals"]),
        "unresolved_questions": list(session["shared_board"]["open_questions"]),
        "final_positions": [
            {
                "role_id": participant["role_id"],
                "name": participant["name"],
                "position": participant["stance"]["position"],
                "score": participant["stance"]["score"],
            }
            for participant in session["participants"]
        ],
    }
    session["status"] = "completed"
    session["meta"]["updated_at"] = now_iso()
    return session["final_summary"]


def render_markdown(session):
    """把当前 session 渲染为可读的圆桌纪要。"""
    summary = session.get("final_summary") or {
        "consensus": list(session["shared_board"]["consensus"]),
        "disagreements": list(session["shared_board"]["disagreements"]),
        "recommended_actions": list(session["shared_board"]["proposals"]),
        "unresolved_questions": list(session["shared_board"]["open_questions"]),
        "final_positions": [
            {
                "role_id": participant["role_id"],
                "name": participant["name"],
                "position": participant["stance"]["position"],
                "score": participant["stance"]["score"],
            }
            for participant in session["participants"]
        ],
    }

    lines = []
    lines.append(f"# 圆桌纪要: {session['topic']}")
    lines.append("")
    lines.append("## 会话信息")
    lines.append(f"- 会话 ID: `{session['session_id']}`")
    lines.append(f"- 状态: `{session['status']}`")
    lines.append(f"- 角色数: `{len(session['participants'])}/{session['config'].get('max_participants', MAX_PARTICIPANTS)}`")
    lines.append(f"- 轮次数: `{len(session['rounds'])}`")
    if session.get("artifact"):
        artifact = session["artifact"]
        if artifact.get("type") or artifact.get("ref"):
            lines.append(
                f"- 讨论对象: `{artifact.get('type', 'unknown')}` / `{artifact.get('ref') or 'inline-content'}`"
            )
    lines.append("")
    lines.append("## 参与角色")
    for participant in session["participants"]:
        position = participant["stance"]["position"] or "未定"
        score = participant["stance"]["score"]
        score_text = "未评分" if score is None else str(score)
        lines.append(
            f"- `{participant['name']}`: {participant['category']} / 最终立场 `{position}` / 评分 `{score_text}`"
        )

    for round_item in session["rounds"]:
        if not round_item["turns"]:
            continue
        lines.append("")
        lines.append(
            f"## 第 {round_item['round_id']} 轮: {round_item['goal']}"
        )
        for turn in round_item["turns"]:
            speaker = get_participant(session, turn["speaker"])
            structured = turn["output"]["structured"]
            lines.append("")
            lines.append(f"### {speaker['name']}")
            lines.append(f"- 立场: `{structured.get('position') or '未表态'}`")
            if structured.get("score") is not None:
                lines.append(f"- 评分: `{structured['score']}`")
            if structured.get("top_concerns"):
                lines.append(
                    f"- 关注点: {'; '.join(structured['top_concerns'])}"
                )
            if structured.get("agreements"):
                lines.append(
                    f"- 认同: {'; '.join(structured['agreements'])}"
                )
            if structured.get("disagreements"):
                lines.append(
                    f"- 分歧: {'; '.join(structured['disagreements'])}"
                )
            if structured.get("proposal"):
                lines.append(f"- 建议: {structured['proposal']}")
            if structured.get("open_questions"):
                lines.append(
                    f"- 待解问题: {'; '.join(structured['open_questions'])}"
                )
            lines.append("")
            lines.append(turn["output"]["content"].strip())

    lines.append("")
    lines.append("## 共识")
    if summary["consensus"]:
        for item in summary["consensus"]:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无明确共识")

    lines.append("")
    lines.append("## 分歧")
    if summary["disagreements"]:
        for item in summary["disagreements"]:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无明确分歧")

    lines.append("")
    lines.append("## 建议行动")
    if summary["recommended_actions"]:
        for item in summary["recommended_actions"]:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无明确建议")

    lines.append("")
    lines.append("## 未决问题")
    if summary["unresolved_questions"]:
        for item in summary["unresolved_questions"]:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无未决问题")

    lines.append("")
    lines.append("## 最终立场")
    for item in summary["final_positions"]:
        score_text = "未评分" if item.get("score") is None else str(item["score"])
        lines.append(
            f"- `{item['name']}`: `{item.get('position') or '未表态'}` / 评分 `{score_text}`"
        )

    return "\n".join(lines).strip() + "\n"


def build_session_bundle(role_ids, topic, artifact=None, max_rounds=3):
    """为调用方输出最小可执行 bundle。"""
    session = build_session(
        role_ids=role_ids,
        topic=topic,
        artifact=artifact,
        max_rounds=max_rounds,
    )
    return {
        "session": session,
        "instructions_for_caller": (
            "1. 为每个 round 按 speaker_order 选择 speaker;\n"
            "2. 用 participant.system_prompt 作为 system, build_turn_context() 结果作为 user 上下文;\n"
            "3. 调用模型后,用 append_turn() 回写 turn;\n"
            "4. 每轮结束后检查 should_stop_early();\n"
            "5. 结束时调用 finalize_session() 生成 final_summary。"
        ),
    }


def parse_args():
    parser = argparse.ArgumentParser(description="多轮真实讨论圆桌会话骨架生成器")
    parser.add_argument("role_ids", help="角色 ID 列表,逗号分隔")
    parser.add_argument("--topic", "-t", required=True, help="本次讨论议题")
    parser.add_argument("--max-rounds", type=int, default=3, help="最大轮次,默认 3")
    parser.add_argument("--artifact-type", default="text", help="产物类型,默认 text")
    parser.add_argument("--artifact-ref", help="产物引用路径或 URL")
    parser.add_argument("--artifact-content", help="产物摘要或正文")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="输出格式,默认 json",
    )
    parser.add_argument("--output", "-o", help="输出文件路径(默认 stdout)")
    return parser.parse_args()


def main():
    args = parse_args()
    role_ids = [item.strip() for item in args.role_ids.split(",") if item.strip()]
    try:
        validate_role_ids(role_ids)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    artifact = {
        "type": args.artifact_type,
        "ref": args.artifact_ref,
        "content": args.artifact_content,
    }
    bundle = build_session_bundle(
        role_ids=role_ids,
        topic=args.topic,
        artifact=artifact,
        max_rounds=args.max_rounds,
    )
    session = bundle["session"]
    output = (
        render_markdown(session)
        if args.format == "markdown"
        else json.dumps(bundle, ensure_ascii=False, indent=2)
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as file_obj:
            file_obj.write(output)
        print(f"OK: 会话骨架已生成 → {args.output}")
        print(f"   参与角色: {len(session['participants'])}")
        print(f"   预设轮次: {len(session['rounds'])}")
        print(f"   输出格式: {args.format}")
    else:
        print(output)


if __name__ == "__main__":
    main()
