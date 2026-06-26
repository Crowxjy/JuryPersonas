# JuryPersonas

> 陪审团画像 Skill —— 把 EAgents(消费者群体流失评审)与 expert-roundtable(专家深度评审 + HCI 客观度量)合并为一个**面向 PM/设计/内容/运营的通用陪审团 Skill**。

## 项目状态

✅ **当前本地状态: v0.15 真实视频证据流水线已接入**(2026-06-26,待提交)

当前主链路支持 PRD、设计稿、单/多界面、短视频、详情页、商品卡、营销文案等场景的 Brief → DAG → observe/persona/jury-react → aggregate/synthesize → HTML/Markdown/DocxXML 报告。场景配置以 `scenarios/review-*.md` 为单一事实源;飞书发布默认 dry-run,传 `--lark-execute` 时使用 DocxXML 走 lark-doc v2 真创建,失败不会伪降级。当前本地回归覆盖 47 步;短视频可选使用 `tools/video_evidence/` 取真实 `play_addr`、下载视频、等距抽帧、抽音与 ASR,并把真实帧转成 `observed:true` artifact。

完整架构设计:[docs/architecture-v0.2.md](docs/architecture-v0.2.md)

## 五大组件

| 组件 | 目录 | 说明 |
|---|---|---|
| ① 需求 Brief | `brief/` | 调用前必经的需求收集与充分性判定 |
| ② 知识 Knowledge | `knowledge/` | 双源:手写行业知识 + 切片标注库 |
| ③ 画像 Persona | `personas/` | 四种生成方式:handcraft / slice-built / fit / pool |
| ④ 场景 Scenario | `scenarios/` | 评估对象的评审 SOP,声明可用模式 |
| ⑤ 模式 Mode | `modes/` | 19 个原子能力,按场景 DAG 组合 |

## 快速使用(当前真实入口)

```bash
# 由宿主 Agent/模型先按 Brief Harness 收集信息,充分后生成 brief.json

# 本地执行已有 brief + artifact
python3 jury_review.py \
  --brief tests/fixtures/short_video_demo/brief.json \
  --artifact tests/fixtures/short_video_demo/artifact.json \
  --personas consumer-bao-mom-tier2,consumer-silver-male

# 不传 --personas 时会使用场景默认陪审团组合
python3 jury_review.py \
  --brief tests/fixtures/prd_demo/brief.json \
  --artifact tests/fixtures/prd_demo/prd.md

# 更底层的 orchestrator 入口
python3 orchestrator/pipeline.py --brief-file tests/fixtures/prd_demo/brief.json
```

### 真实短视频证据流水线(可选)

```bash
VIDEO_URL=https://www.douyin.com/video/<aweme_id> \
WORK=$HOME/.session/<sid>/douyin_run \
bash tools/video_evidence/run_douyin_realframe_pipeline.sh
```

流水线产物见 `tools/video_evidence/README.md`。注意:抽出的图片是真实证据,但空白画面描述仍需宿主 Agent/多模态模型查看图片后填写;未查看图片时陪审员不得评价画面内容。

## 上游项目

- [EAgents](https://github.com/Crowxjy/EAgents) — 消费者群体流失评审,提供画像 + 采样 + 短视频评审
- [expert-roundtable](https://github.com/wuhaadesign/expert-roundtable) — 提供专家圆桌 + HCI 客观度量 + Phase C 决策透镜
  - v0.3 迁入锁定 commit: `7921f97c8911809078946e4e2c928db60907b46f`

## 维护者指南

- 增删画像 → 见 [personas/_template.md](personas/_template.md)
- 新增场景 → 见 [scenarios/](scenarios/) 现有模板
- 新增模式 → 见 [docs/architecture-v0.2.md §3.1](docs/architecture-v0.2.md)
- 宿主 Agent/模型正式使用流 → 见 [docs/host-agent-workflow.md](docs/host-agent-workflow.md)
- 真实短视频证据流水线 → 见 [tools/video_evidence/README.md](tools/video_evidence/README.md)
- HTML 报告执行约束 → 见 [reporting/design.md](reporting/design.md);当前视觉参考为 `/Users/bytedance/Downloads/linear`,[reporting/reference-design.md](reporting/reference-design.md) 仅保留历史 SpaceX-inspired 参考
- 源仓迁移映射 → 见 [docs/migration-guide.md](docs/migration-guide.md)
- 场景模式 cookbook → 见 [docs/mode-cookbook.md](docs/mode-cookbook.md)
- 安装与运行依赖 → 见 [docs/install.md](docs/install.md)
- 真实评测集 → 见 [evals/README.md](evals/README.md)
- 画像合并决策 → 见 [docs/persona-merge-decision.md](docs/persona-merge-decision.md)
- 运行依赖和可选资产 → 见 [docs/runtime-assets.md](docs/runtime-assets.md)
