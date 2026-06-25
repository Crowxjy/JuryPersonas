#!/usr/bin/env python3
"""
keyframe_extract.py - normalize supplied video keyframes into observation JSON.

This MVP does not decode video files. It accepts a JSON artifact that already
contains key_frames, transcript, or storyboard entries and converts them into a
stable timeline for jury-react. If only a raw video path is supplied, it returns
NEEDS_KEYFRAMES instead of hallucinating visual content.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".webm", ".mkv"}


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"artifact 不存在: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_ts(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_keyframes(artifact: dict) -> list[dict]:
    raw_frames = (
        artifact.get("key_frames")
        or artifact.get("keyframes")
        or artifact.get("storyboard")
        or []
    )
    frames = []
    for idx, frame in enumerate(raw_frames):
        if not isinstance(frame, dict):
            continue
        ts = normalize_ts(frame.get("ts_sec", frame.get("time_sec", frame.get("time"))))
        frames.append(
            {
                "index": idx,
                "ts_sec": ts,
                "description": frame.get("description") or frame.get("visual") or "",
                "voiceover": frame.get("voiceover") or frame.get("text") or frame.get("caption") or "",
                "image": frame.get("image") or frame.get("image_path") or frame.get("url"),
            }
        )
    frames.sort(key=lambda x: (x["ts_sec"] is None, x["ts_sec"] if x["ts_sec"] is not None else x["index"]))
    for idx, frame in enumerate(frames):
        frame["index"] = idx
    return frames


def transcript_segments(artifact: dict) -> list[dict]:
    raw = artifact.get("transcript") or []
    if isinstance(raw, str):
        return [{"ts_sec": None, "text": raw}]
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, str):
            out.append({"ts_sec": None, "text": item})
        elif isinstance(item, dict):
            out.append(
                {
                    "ts_sec": normalize_ts(item.get("ts_sec", item.get("time_sec"))),
                    "text": item.get("text") or item.get("caption") or "",
                }
            )
    return out


def build_keyframe_observation(artifact: dict, *, source: str | None = None) -> dict:
    frames = normalize_keyframes(artifact)
    transcript = transcript_segments(artifact)
    locator = artifact.get("locator") or artifact.get("path") or artifact.get("url") or source
    suffix = Path(str(locator)).suffix.lower() if locator else ""

    if not frames and suffix in VIDEO_SUFFIXES:
        return {
            "mode": "mode/keyframe-extract",
            "status": "NEEDS_KEYFRAMES",
            "source": source,
            "artifact_locator": locator,
            "message": (
                "当前 MVP 不本地解码视频文件。请提供关键帧截图序列、storyboard 或 transcript 后再进入 jury-react。"
            ),
            "required_fields": ["key_frames[].ts_sec", "key_frames[].description"],
            "boundary": {"do_not_hallucinate_video_content": True},
        }

    return {
        "mode": "mode/keyframe-extract",
        "status": "OK",
        "source": source,
        "artifact_title": artifact.get("title"),
        "duration_sec": artifact.get("duration_sec"),
        "platform": artifact.get("platform"),
        "key_frames": frames,
        "transcript": transcript,
        "timeline_summary": {
            "n_key_frames": len(frames),
            "n_transcript_segments": len(transcript),
            "first_ts_sec": frames[0]["ts_sec"] if frames else None,
            "last_ts_sec": frames[-1]["ts_sec"] if frames else None,
        },
        "boundary": {
            "normalized_supplied_frames_only": True,
            "no_video_decoding": True,
            "do_not_hallucinate_missing_visuals": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize supplied keyframes into observation JSON")
    parser.add_argument("--artifact", required=True, help="Artifact JSON path")
    parser.add_argument("--out", help="Output JSON path; default stdout")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    artifact_path = Path(args.artifact)
    observation = build_keyframe_observation(load_json(artifact_path), source=str(artifact_path))
    text = json.dumps(observation, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0 if observation["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
