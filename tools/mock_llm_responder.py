#!/usr/bin/env python3
"""
mock_llm_responder.py — M3 测试桩:把 jury-react bundle 转为假 reactions

职责:
1. 读 jury-react bundle JSON(由 modes/jury/jury_react.py 产出)
2. 为每位 participant 合成一份固定结构的假 reaction(三段式 + 5 字段卡点 + 0-10 打分)
3. 写回 bundle.participants[*].reaction(字符串,Markdown 格式)
4. 输出回填后的 bundle 给 mode/aggregate-consensus 消费

设计原则:
- 不调真 LLM、不联网,任意环境可跑
    - 短视频按角色输出行为差异;非视频按 scenario 输出差异化测试桩,便于验证场景化聚合
- 故意制造 1~2 个共识卡点(0-3 秒封面、32 秒 CTA),验证 aggregate 频次聚合
- 故意让宝妈静音、银发字幕、蓝领外放各执一词,验证 aggregate 分布矩阵
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REACTION_TEMPLATE = """\
### 1) 我现在的场景
{scene}

---

### 2) 三段式刷视频反应

- **0-3 秒(决定要不要继续看)**:第一眼看到的是「{frame0_view}」。{frame0_action}({frame0_reason})
- **3-15 秒(决定要不要看完)**:视频在讲{mid_topic},{mid_understand}。{mid_action}({mid_reason})
- **15 秒-结束(决定要不要互动)**:看到 32 秒 CTA「点击下方小黄车」,{cta_action}({cta_reason})

---

### 3) 我看完后的至少 3 个具体问题

#### 问题 1
- 所属人群: {category} / {sub_category}
- 关注点: {q1_concern}
- 卡点位置: {q1_pos}
- 可能流失原因: {q1_reason}
- 改进建议: {q1_fix}

#### 问题 2
- 所属人群: {category} / {sub_category}
- 关注点: {q2_concern}
- 卡点位置: {q2_pos}
- 可能流失原因: {q2_reason}
- 改进建议: {q2_fix}

#### 问题 3
- 所属人群: {category} / {sub_category}
- 关注点: {q3_concern}
- 卡点位置: {q3_pos}
- 可能流失原因: {q3_reason}
- 改进建议: {q3_fix}

---

### 4) 我会让博主怎么改

- {fix1}
- {fix2}
- {fix3}

---

### 5) 我的真实行为(0-10 量化)

- 完播倾向: {wan_bo}/10
- 互动倾向: {hu_dong}/10
- 转化倾向: {zhuan_hua}/10
- 信任度: {xin_ren}/10
- 推荐倾向: {tui_jian}/10

一句话结论: {one_liner}
"""

GENERIC_REACTION_TEMPLATE = """\
### 1) 我的第一反应
{first_reaction}

---

### 2) 我重点看的问题
  我会先看目标用户能不能理解、关键信息是否缺失、信任证据是否足够,再看有没有决策或转化上的风险。Observe 阶段如果给了结构化抽取,我会优先引用那些章节/字段;除 HCI 结果外,我会把它当作结构化原文,不当作机器已经完成的价值判断。

---

### 3) 我发现的至少 3 个具体问题

#### 问题 1
- 所属人群: {category} / {sub_category}
- 关注点: {q1_concern}
- 卡点位置: {q1_pos}
- 可能流失原因: {q1_reason}
- 改进建议: {q1_fix}

#### 问题 2
- 所属人群: {category} / {sub_category}
- 关注点: {q2_concern}
- 卡点位置: {q2_pos}
- 可能流失原因: {q2_reason}
- 改进建议: {q2_fix}

#### 问题 3
- 所属人群: {category} / {sub_category}
- 关注点: {q3_concern}
- 卡点位置: {q3_pos}
- 可能流失原因: {q3_reason}
- 改进建议: {q3_fix}

---

### 4) 我建议优先怎么改

- {fix1}
- {fix2}
- {fix3}

---

### 5) 我的真实行为/判断(0-10 量化)

- {score1_label}: {score1}/10
- {score2_label}: {score2}/10
- {score3_label}: {score3}/10
- {score4_label}: {score4}/10
- {score5_label}: {score5}/10

一句话结论: {one_liner}
"""

# 三位陪审员的差异化模板:故意让大家在不同位置卡住,但都提到 0-3 秒封面 + 32 秒 CTA(共识),
# 让聚合阶段能正确算出"提及频次"和"分布矩阵差异"。
ROLE_PROFILES: dict[str, dict] = {
    "consumer-bao-mom-tier2": {
        "scene": "晚上把娃哄睡了,客厅躺沙发上静音刷,屏幕亮度调低怕吵着娃。",
        "frame0_view": "招牌红色背景 + '今日推荐' 白底大字,但没有字幕",
        "frame0_action": "差点直接划走",
        "frame0_reason": "我静音刷,前 3 秒没有字幕完全不知道讲啥",
        "mid_topic": "一个老板娘做小龙虾",
        "mid_understand": "不抓我重点,我家娃挑食吃不了辣",
        "mid_action": "拖进度条到 22 秒看成品",
        "mid_reason": "中间煮的过程对我来说太长了",
        "cta_action": "不会跟着点",
        "cta_reason": "三线小镇我又不在那个城市,买了也吃不到",
        "category": "consumer",
        "sub_category": "三线宝妈 25-35",
        "q1_concern": "字幕音频",
        "q1_pos": "0-3 秒封面",
        "q1_reason": "我静音看完全没字幕,不知道是啥内容",
        "q1_fix": "封面加一句'三线小店家庭版小龙虾'让我立刻 get",
        "q2_concern": "与我无关",
        "q2_pos": "整体定位",
        "q2_reason": "三线小镇我没法消费,买不到",
        "q2_fix": "标注下能不能寄,或者改成教做法",
        "q3_concern": "CTA",
        "q3_pos": "32 秒处 CTA",
        "q3_reason": "小黄车我没看到地域限制,点进去白点",
        "q3_fix": "CTA 前加一句'同城配送/不发外地'明确范围",
        "fix1": "封面前 3 秒必须加大字幕,我们静音的多",
        "fix2": "标注配送范围,别让我点进去白点",
        "fix3": "可以拍个'家庭做法版',吸引在家做的妈妈",
        "wan_bo": 3,
        "hu_dong": 2,
        "zhuan_hua": 1,
        "xin_ren": 5,
        "tui_jian": 2,
        "one_liner": "看着挺好但跟我没关系,刷 3 秒就走。",
    },
    "consumer-silver-male": {
        "scene": "下午茶时间在沙发上看,音量正常外放,边喝茶边切。",
        "frame0_view": "店门口红招牌特写,字大",
        "frame0_action": "瞄了一眼继续看",
        "frame0_reason": "招牌字够大我看得清,听到一半声音还行",
        "mid_topic": "一位老板娘自己做小龙虾",
        "mid_understand": "讲得挺地道,老板娘说话清楚",
        "mid_action": "继续看",
        "mid_reason": "我退休了爱看这种烟火气",
        "cta_action": "不会跟着点",
        "cta_reason": "我不会用小黄车,而且我吃不了辣的",
        "category": "consumer",
        "sub_category": "银发男 60+",
        "q1_concern": "信息密度",
        "q1_pos": "3-15 秒中段",
        "q1_reason": "煮的步骤讲太快,我没记住",
        "q1_fix": "步骤可以放慢点,或者每步停 1 秒",
        "q2_concern": "CTA",
        "q2_pos": "32 秒处 CTA",
        "q2_reason": "我不会用小黄车,看到角标也不知道点哪",
        "q2_fix": "CTA 旁边写一句'点这里下单'引导我们老人",
        "q3_concern": "信任感",
        "q3_pos": "整体",
        "q3_reason": "28 元一份听起来不贵,但没看到分量,怕被骗",
        "q3_fix": "成品装盘旁边加个秤或参照物,给个分量感",
        "fix1": "讲菜的步骤别太快,我们年纪大记不住",
        "fix2": "小黄车要写得明白点,别只放角标",
        "fix3": "标一下分量,28 块到底是多少只",
        "wan_bo": 7,
        "hu_dong": 3,
        "zhuan_hua": 2,
        "xin_ren": 6,
        "tui_jian": 4,
        "one_liner": "老板娘做菜挺地道,但我不会下单,看个热闹。",
    },
    "consumer-bluecollar-male": {
        "scene": "中午吃盒饭,工地工友群转的,声音外放图个热闹。",
        "frame0_view": "红招牌 + '今日推荐',我没特别注意,直接听声",
        "frame0_action": "继续看",
        "frame0_reason": "外放有声,我边吃边听就行",
        "mid_topic": "做小龙虾的步骤",
        "mid_understand": "听明白了,挺香",
        "mid_action": "拖到 22 秒看成品",
        "mid_reason": "我饿了想看红油浓的",
        "cta_action": "不会跟着点",
        "cta_reason": "28 块一份对我太贵,我中午外卖才 15",
        "category": "consumer",
        "sub_category": "蓝领男 30-45",
        "q1_concern": "钩子无力",
        "q1_pos": "0-3 秒封面",
        "q1_reason": "前 3 秒就讲'今日推荐',太虚,没说便宜没说量",
        "q1_fix": "前 3 秒直接喊'28 一份管饱'比啥都强",
        "q2_concern": "套路太重",
        "q2_pos": "32 秒处 CTA",
        "q2_reason": "刚说做菜就让点小黄车,有点突兀",
        "q2_fix": "CTA 前加一句'兄弟们想吃私我',别这么硬卖",
        "q3_concern": "信任感",
        "q3_pos": "成品装盘",
        "q3_reason": "光看红油不知道有几只虾,28 不一定值",
        "q3_fix": "给个分量参照,比如几只虾几两肉",
        "fix1": "前 3 秒直接喊价格管饱,别整虚的",
        "fix2": "CTA 软一点,别突然推销",
        "fix3": "成品给个分量感,我们最关心值不值",
        "wan_bo": 5,
        "hu_dong": 3,
        "zhuan_hua": 2,
        "xin_ren": 4,
        "tui_jian": 3,
        "one_liner": "看着挺香,但 28 一份我吃不起,看完就划。",
    },
}


SCENARIO_MOCKS: dict[str, dict] = {
    "review-prd": {
        "focus": ("信息缺失", "决策风险", "证据口径"),
        "positions": ("目标/背景章节", "方案设计", "指标/证据"),
        "expert_reasons": (
            "目标描述有了,但用户场景和触发时机还不够具体,评审时容易各看各的。",
            "方案 A/B 的取舍标准不够显式,后续评审会变成偏好争论。",
            "指标和证据只有方向,缺少口径说明和反例边界,会影响可信度。",
        ),
        "consumer_reasons": (
            "我不知道这东西到底是给我解决哪个问题,第一眼会有点懵。",
            "两个方案都像有道理,但我不知道你到底想让我选什么。",
            "看到指标我会想'这个怎么算的',如果说不清楚就不太信。",
        ),
        "fixes": (
            "补一段'谁在什么场景下遇到什么问题'的具体例子。",
            "把两条路径的适用条件、风险和验证指标放到同一张表里。",
            "补指标口径、数据来源和不能承诺的边界说明。",
        ),
        "metrics": ["必要性", "可行性", "完整性", "风险可控性", "推荐推进度"],
        "expert_scores": [7, 6, 5, 5, 6],
        "consumer_scores": [5, 4, 4, 3, 4],
        "one_liner": "方向能评,但要先把场景、取舍和证据口径补硬。",
    },
    "review-design": {
        "focus": ("视觉层级", "行动清晰度", "信任感"),
        "positions": ("首屏/主视觉", "CTA/行动入口", "信任/说明"),
        "expert_reasons": (
            "主视觉抓眼,但主次信息没有形成稳定阅读路径。",
            "CTA 出现了,但按钮文案和前置信息之间缺少承接。",
            "说明区提供了素材,但没有把可信证据放到用户做决定的位置。",
        ),
        "consumer_reasons": (
            "我第一眼看得到大标题,但不知道先看价格还是看功能。",
            "按钮能看到,但我不确定点了以后会发生什么。",
            "我会想这个承诺靠不靠谱,页面没有马上让我放心。",
        ),
        "fixes": (
            "把首屏信息改成'主承诺 + 关键证据 + 单一行动'三层。",
            "CTA 文案改成结果导向,旁边补一句点击后的预期。",
            "把背书、限制条件或安全说明前置到行动入口附近。",
        ),
        "metrics": ["可用性", "一致性", "视觉层级", "信息密度", "行动清晰度"],
        "expert_scores": [6, 6, 5, 4, 5],
        "consumer_scores": [5, 5, 4, 3, 4],
        "one_liner": "画面有方向,但第一屏还没有把下一步讲清楚。",
    },
    "review-screen": {
        "focus": ("理解成本", "体验断点", "行动清晰度"),
        "positions": ("信息架构", "交互反馈", "CTA/行动入口"),
        "expert_reasons": (
            "页面模块都在,但信息分组不够贴合用户决策顺序。",
            "关键状态反馈不显眼,用户容易不知道操作是否成功。",
            "主行动被次要信息稀释,会降低完成任务的确定性。",
        ),
        "consumer_reasons": (
            "我能看出这是一个页面,但得多扫几眼才知道重点。",
            "点完之后如果没有明显反馈,我会担心是不是没点上。",
            "我不知道应该先填信息还是先看说明。",
        ),
        "fixes": (
            "按用户任务顺序重排模块,把解释文字压缩到关键节点。",
            "给操作状态补明确反馈,包括成功、失败和处理中。",
            "把主 CTA 固定到最清晰的位置,次要入口降权。",
        ),
        "metrics": ["可用性", "一致性", "视觉层级", "信息密度", "行动清晰度"],
        "expert_scores": [6, 5, 5, 4, 5],
        "consumer_scores": [5, 4, 4, 3, 4],
        "one_liner": "页面能用,但用户要多想一步才敢继续。",
    },
    "review-detail-page": {
        "focus": ("利益清晰度", "信任证据", "购买阻力"),
        "positions": ("标题/卖点", "评价/信任", "CTA/购买入口"),
        "expert_reasons": (
            "首屏卖点和目标人群的核心购买理由还没有直接对齐。",
            "信任证据存在,但离价格和下单入口太远。",
            "购买按钮前缺少价格、规格或配送的最后确认。",
        ),
        "consumer_reasons": (
            "我知道在卖东西,但没马上看出为什么值得买。",
            "我会想有没有人买过、靠不靠谱,但证据不够近。",
            "快下单时还要确认价格和配送,不清楚就会停住。",
        ),
        "fixes": (
            "首屏改成'适合谁 + 解决什么 + 立即利益'。",
            "把评价、销量或保障说明前移到价格/CTA 附近。",
            "在 CTA 上方补价格、规格、配送和售后的一屏确认。",
        ),
        "metrics": ["理解效率", "信任证据", "购买意愿", "价格清晰度", "行动清晰度"],
        "expert_scores": [6, 5, 4, 5, 5],
        "consumer_scores": [5, 4, 3, 4, 4],
        "one_liner": "页面能解释商品,但还没有把下单前的疑虑一次消掉。",
    },
    "review-product-card": {
        "focus": ("卖点清晰度", "价格清晰度", "点击动机"),
        "positions": ("标题/卖点", "价格/权益", "CTA/购买入口"),
        "expert_reasons": (
            "卡片标题能描述商品,但没有突出最强差异点。",
            "价格和权益信息分散,用户很难一眼判断划不划算。",
            "点击后的收益不明确,卡片容易只被扫过。",
        ),
        "consumer_reasons": (
            "我能看出是什么,但不知道它比旁边那个好在哪。",
            "价格看到了,但优惠怎么用还要想一下。",
            "如果没有明确理由,我不会特地点进去。",
        ),
        "fixes": (
            "标题保留商品名,副标题补一个最强利益点。",
            "把到手价、权益和限制条件放到同一视觉组。",
            "CTA 改成具体收益,例如'看优惠'或'领券下单'。",
        ),
        "metrics": ["理解效率", "信任证据", "购买意愿", "价格清晰度", "行动清晰度"],
        "expert_scores": [6, 5, 4, 5, 5],
        "consumer_scores": [5, 4, 3, 4, 4],
        "one_liner": "卡片信息够基本,但缺少让我点开的明确理由。",
    },
    "review-marketing-copy": {
        "focus": ("钩子力度", "利益清晰度", "证据可信度"),
        "positions": ("标题/钩子", "核心卖点", "证据/背书"),
        "expert_reasons": (
            "开头能进入主题,但没有在第一句建立强冲突或强收益。",
            "卖点有表达,但和目标人群的具体痛点连接不够紧。",
            "证据偏描述性,缺少可验证的案例、数字或边界。",
        ),
        "consumer_reasons": (
            "我能读懂,但第一句没有让我非看不可。",
            "好处听起来有点泛,还没戳到我的具体场景。",
            "说得不错,但我会想有没有真实例子。",
        ),
        "fixes": (
            "标题改成'具体人群 + 明确痛点/收益'。",
            "每个卖点后补一个目标用户能代入的使用场景。",
            "增加一个真实案例、数字或不可承诺边界。",
        ),
        "metrics": ["读完意愿", "利益清晰度", "信任感", "转化意愿", "传播意愿"],
        "expert_scores": [6, 5, 5, 4, 4],
        "consumer_scores": [4, 4, 4, 3, 3],
        "one_liner": "文案能说明事情,但还不够尖锐到让人继续读和行动。",
    },
}

DEFAULT_GENERIC_MOCK = {
    "focus": ("信息缺失", "决策风险", "信任感"),
    "positions": ("目标/背景", "方案/内容主体", "证据/信任"),
    "expert_reasons": (
        "目标描述有了,但用户场景和触发时机还不够具体。",
        "方案取舍标准不够显式,后续评审会变成偏好争论。",
        "指标和证据只有方向,缺少口径说明和反例边界。",
    ),
    "consumer_reasons": (
        "我不知道这东西到底是给我解决哪个问题。",
        "两个方向都像有道理,但我不知道你想让我怎么做。",
        "看到证据我会想'这个怎么算的',如果说不清楚就不太信。",
    ),
    "fixes": (
        "补一段具体用户场景。",
        "把取舍标准显式化。",
        "补证据口径和边界说明。",
    ),
    "metrics": ["理解意愿", "参与意愿", "行动意愿", "信任度", "推荐意愿"],
    "expert_scores": [6, 5, 4, 6, 5],
    "consumer_scores": [4, 3, 2, 4, 3],
    "one_liner": "能大概看懂,但还没到让人放心行动的程度。",
}


# 默认兜底模板:遇到未注册角色时使用,避免直接抛错把流水线搞断
def _fallback_profile(category: str, sub_category: str) -> dict:
    base = ROLE_PROFILES["consumer-silver-male"].copy()
    base["category"] = category or "unknown"
    base["sub_category"] = sub_category or "unknown"
    base["one_liner"] = "(默认桩响应,无角色定制模板)"
    return base


def fake_reaction_for(participant: dict) -> str:
    role_id = participant["role_id"]
    profile = ROLE_PROFILES.get(role_id) or _fallback_profile(
        participant.get("category", ""), participant.get("sub_category", "")
    )
    return REACTION_TEMPLATE.format(**profile)


def fake_generic_reaction_for(participant: dict, scenario: str) -> str:
    category = participant.get("category", "") or "unknown"
    sub_category = participant.get("sub_category", "") or participant.get("role_id", "")
    is_expert = "专家" in category or "expert" in participant.get("role_id", "")
    mock = SCENARIO_MOCKS.get(scenario, DEFAULT_GENERIC_MOCK)
    reasons = mock["expert_reasons"] if is_expert else mock["consumer_reasons"]
    scores = mock["expert_scores"] if is_expert else mock["consumer_scores"]
    metrics = mock["metrics"]
    profile = {
        "category": category,
        "sub_category": sub_category,
        "first_reaction": (
              f"我会把这个 {scenario} 当作一份需要落地的方案来看,先看目标、证据和边界是否说清楚。"
            if is_expert
            else f"我先看这个 {scenario} 跟我有没有关系,以及我能不能马上看懂下一步。"
        ),
          "q1_concern": mock["focus"][0],
          "q1_pos": mock["positions"][0],
          "q1_reason": reasons[0],
          "q1_fix": mock["fixes"][0],
          "q2_concern": mock["focus"][1],
          "q2_pos": mock["positions"][1],
          "q2_reason": reasons[1],
          "q2_fix": mock["fixes"][1],
          "q3_concern": mock["focus"][2],
          "q3_pos": mock["positions"][2],
          "q3_reason": reasons[2],
          "q3_fix": mock["fixes"][2],
          "fix1": mock["fixes"][0],
          "fix2": mock["fixes"][1],
          "fix3": mock["fixes"][2],
          "score1_label": metrics[0],
          "score2_label": metrics[1],
          "score3_label": metrics[2],
          "score4_label": metrics[3],
          "score5_label": metrics[4],
          "score1": scores[0],
          "score2": scores[1],
          "score3": scores[2],
          "score4": scores[3],
          "score5": scores[4],
          "one_liner": mock["one_liner"],
    }
    return GENERIC_REACTION_TEMPLATE.format(**profile)


def fill_bundle(bundle: dict) -> dict:
    scenario = bundle.get("scenario", "")
    for p in bundle.get("participants", []):
        if p.get("reaction") is not None:
            continue  # 已经有真 reaction,不覆盖
        if scenario == "review-short-video":
            p["reaction"] = fake_reaction_for(p)
        else:
            p["reaction"] = fake_generic_reaction_for(p, scenario)
    bundle["responder"] = "mock_llm_responder@v0.2"
    return bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="mock LLM 响应器 (M3 测试桩)")
    parser.add_argument(
        "--bundle-file",
        required=True,
        help="jury-react bundle JSON 路径(由 modes/jury/jury_react.py 产出)",
    )
    parser.add_argument("--output", "-o", help="输出回填后的 bundle 路径(默认 stdout)")
    parser.add_argument("--pretty", action="store_true", help="美化 JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    path = Path(args.bundle_file)
    if not path.exists():
        sys.stderr.write(f"[error] bundle 文件不存在: {path}\n")
        return 2

    bundle = json.loads(path.read_text(encoding="utf-8"))
    fill_bundle(bundle)

    out = json.dumps(bundle, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        n = sum(1 for p in bundle["participants"] if p.get("reaction"))
        sys.stdout.write(f"[OK] mock reactions 回填 {n} 位陪审员 → {args.output}\n")
    else:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
