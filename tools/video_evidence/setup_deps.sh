#!/usr/bin/env bash
#
# Install optional video evidence dependencies into a writable cache.
#
set -euo pipefail

CACHE="${CACHE:-$HOME/.cache/jurypersonas-video-evidence}"
mkdir -p "$CACHE"

echo "[deps] npm install into $CACHE ..."
npm install --prefix "$CACHE" puppeteer whisper-node ffmpeg-static

WMODELS="$CACHE/node_modules/whisper-node/lib/whisper.cpp/models"
mkdir -p "$WMODELS"
for model in ggml-small.bin ggml-base.bin; do
  if [ ! -s "$WMODELS/$model" ]; then
    echo "[deps] download $model ..."
    curl -L -o "$WMODELS/$model" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$model"
  fi
done

WCPP="$CACHE/node_modules/whisper-node/lib/whisper.cpp"
if [ ! -x "$WCPP/main" ] && [ -d "$WCPP" ]; then
  echo "[deps] build whisper.cpp main ..."
  (cd "$WCPP" && make -j4) || true
fi

case "$(uname -s)" in
  Linux)
    cat <<'MSG'
[deps] If puppeteer/chrome fails with missing system libraries, install them in
your sandbox or rerun with your environment's package manager. Common packages:
libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2
libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1
libasound2
MSG
    ;;
  Darwin)
    echo "[deps] macOS detected. Ensure ffmpeg is available, e.g. brew install ffmpeg."
    ;;
esac

echo "[deps] done. Export NODE_PATH=$CACHE/node_modules when running custom node tools."

