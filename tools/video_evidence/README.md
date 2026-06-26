# Real Video Evidence Pipeline

This folder contains an optional pipeline for turning a Douyin video URL into
auditable short-video evidence for JuryPersonas.

The core rule is separation of evidence and judgement:

- Evidence layer: real `play_addr`, downloaded video, sampled frames, audio, ASR.
- Jury layer: persona reactions based only on observed evidence.

`observed:false` inferred frames are never evidence. They are excluded before
handoff. Real extracted frames are marked `observed:true`, but a frame with an
empty `description` still needs visual interpretation before a jury can comment
on the画面.

## Workflow

```bash
# One-time dependency setup into a writable cache.
bash tools/video_evidence/setup_deps.sh

# Run outside the Skill root. The pipeline cd's into WORK before launching node.
VIDEO_URL=https://www.douyin.com/video/<aweme_id> \
WORK=$HOME/.session/<sid>/douyin_run \
bash tools/video_evidence/run_douyin_realframe_pipeline.sh
```

Outputs:

- `meta.json`: real Douyin metadata and `play_addr`
- `video.mp4`: downloaded video file
- `frames/f_*.jpg`: uniformly sampled frames
- `audio.wav`: extracted audio
- `transcript.txt`: ASR output when whisper.cpp is available
- `artifact.realframe.json`: JuryPersonas short-video artifact template

## Fill Visual Descriptions

The generated artifact includes image paths but does not pretend to understand
the images. Use a multimodal host Agent/model to inspect frames and write a
description file:

```json
{
  "f_00001.jpg": "片头出现店门招牌和价格贴纸",
  "f_00002.jpg": "老板娘半身出镜,背景是厨房"
}
```

Then rebuild:

```bash
node tools/video_evidence/build_artifact.js \
  --work "$WORK" \
  --descriptions "$WORK/frame_descriptions.json" \
  --out "$WORK/artifact.realframe.json"
```

Now run JuryPersonas with `artifact.realframe.json`. Frames with descriptions are
real observed evidence; frames without descriptions remain marked
`needs_visual_description:true` and the prompt tells jurors not to comment on
unseen画面.

## Notes From The Patch

The original tested workaround decoupled a brittle all-in-one
`fetchVideoData()` chain:

1. use browser interception only to get real `play_addr`;
2. download/transcode/frame extraction/ASR as separate commands;
3. keep every intermediate artifact on disk;
4. install dependencies into a writable cache and expose them through
   `NODE_PATH`;
5. run node outside the Skill root when the upstream parser has an
   `assertOutsideSkill` guard.

