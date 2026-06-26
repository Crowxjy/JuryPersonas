#!/usr/bin/env bash
#
# Douyin URL -> real mp4 -> sampled frames -> audio -> optional ASR -> JuryPersonas artifact.
#
# Required:
#   VIDEO_URL=https://www.douyin.com/video/<aweme_id>
#   WORK=$HOME/.session/<sid>/douyin_run
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${WORK:?need WORK dir}"
VIDEO_URL="${VIDEO_URL:?need VIDEO_URL}"
CACHE="${CACHE:-$HOME/.cache/jurypersonas-video-evidence}"
FRAME_INTERVAL="${FRAME_INTERVAL:-3}"
WHISPER_MODEL="${WHISPER_MODEL:-$CACHE/node_modules/whisper-node/lib/whisper.cpp/models/ggml-small.bin}"
WHISPER_BIN="${WHISPER_BIN:-$CACHE/node_modules/whisper-node/lib/whisper.cpp/main}"

mkdir -p "$WORK" "$WORK/frames"
export NODE_PATH="$CACHE/node_modules${NODE_PATH:+:$NODE_PATH}"
export DOUYIN_WORK_DIR="$WORK"
export VIDEO_URL

echo "[1/6] grab real play_addr ..."
(cd "$WORK" && node "$SCRIPT_DIR/grab_douyin_play_addr.js")
PLAY_URL="$(node -e "const m=require(process.argv[1]); console.log((m.play_addr||[])[0]||'')" "$WORK/meta.json")"
if [ -z "$PLAY_URL" ]; then
  echo "NO_PLAY_ADDR" >&2
  exit 3
fi

echo "[2/6] download mp4 ..."
curl -sL -A 'Mozilla/5.0' -e 'https://www.douyin.com/' -o "$WORK/video.mp4" "$PLAY_URL"
ls -lh "$WORK/video.mp4"

echo "[3/6] extract frames every ${FRAME_INTERVAL}s ..."
rm -f "$WORK"/frames/f_*.jpg
ffmpeg -y -loglevel error -i "$WORK/video.mp4" -vf "fps=1/${FRAME_INTERVAL}" "$WORK/frames/f_%05d.jpg"
echo "frames: $(find "$WORK/frames" -maxdepth 1 -type f -name 'f_*.jpg' | wc -l | tr -d ' ')"

echo "[4/6] extract audio ..."
if ffmpeg -y -loglevel error -i "$WORK/video.mp4" -ar 16000 -ac 1 -c:a pcm_s16le "$WORK/audio.wav"; then
  echo "audio -> $WORK/audio.wav"
else
  echo "[warn] audio extraction failed; continuing without ASR" >&2
fi

echo "[5/6] transcribe if whisper.cpp is available ..."
if [ -x "$WHISPER_BIN" ] && [ -s "$WHISPER_MODEL" ] && [ -s "$WORK/audio.wav" ]; then
  "$WHISPER_BIN" -m "$WHISPER_MODEL" -f "$WORK/audio.wav" -l zh -otxt -of "$WORK/transcript" -t 4
else
  echo "[warn] whisper.cpp binary/model missing; write empty transcript.txt" >&2
  : > "$WORK/transcript.txt"
fi

echo "[6/6] build JuryPersonas artifact template ..."
node "$SCRIPT_DIR/build_artifact.js" --work "$WORK" --frame-interval "$FRAME_INTERVAL" --out "$WORK/artifact.realframe.json"

echo "DONE. Review these outputs:"
echo "  $WORK/meta.json"
echo "  $WORK/video.mp4"
echo "  $WORK/frames/f_*.jpg"
echo "  $WORK/transcript.txt"
echo "  $WORK/artifact.realframe.json"
echo
echo "Next: inspect frames with a multimodal host Agent/model, write frame_descriptions.json,"
echo "then rerun build_artifact.js with --descriptions before jury review."

