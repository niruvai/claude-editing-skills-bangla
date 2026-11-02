#!/usr/bin/env bash
# One-time setup for the editing skills: checks ffmpeg and Node, makes kit/.venv, fetches GSAP,
# warms up HyperFrames and (with --cutout) downloads the matting model. Safe to run again.
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
say() { printf '\033[1m%s\033[0m\n' "$*"; }

command -v ffmpeg >/dev/null || { echo "ffmpeg is missing. Mac: brew install ffmpeg"; exit 1; }
# (grep -q under pipefail would SIGPIPE ffmpeg and warn falsely, so read the list first)
ENC=$(ffmpeg -hide_banner -encoders 2>/dev/null || true)
grep -q libvpx-vp9 <<<"$ENC" || echo "warning: this ffmpeg has no libvpx-vp9, so cutouts (behind-the-person, explainer) will fail"
command -v npx >/dev/null || { echo "Node.js is missing (HyperFrames renders with it). Mac: brew install node"; exit 1; }
# onnxruntime (the cutout) ships wheels for Python 3.10-3.13 only, so prefer one of those over a newer python3
PY=""
for c in python3.12 python3.13 python3.11 python3.10 python3; do
  p=$(command -v "$c" 2>/dev/null) || continue
  if "$p" -c 'import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)'; then PY="$p"; break; fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10-3.13 is needed (your python3 is $(python3 --version 2>&1))."
  echo "Mac: brew install python@3.12   Ubuntu/WSL: sudo apt install -y python3.12 python3.12-venv"
  echo "then run ./install.sh again"
  exit 1
fi
# a venv made earlier with an unsupported python is replaced
if [ -x "$KIT/.venv/bin/python" ] && ! "$KIT/.venv/bin/python" -c 'import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)'; then
  say "replacing kit/.venv (it was made with an unsupported python)"
  rm -rf "$KIT/.venv"
fi

if [ ! -x "$KIT/.venv/bin/python" ]; then
  say "making kit/.venv"
  "$PY" -m venv "$KIT/.venv"
fi
"$KIT/.venv/bin/python" -m pip install -q --upgrade pip
"$KIT/.venv/bin/python" -m pip install -q groq numpy pillow onnxruntime

mkdir -p "$KIT/vendor"
if [ ! -s "$KIT/vendor/gsap.min.js" ]; then
  say "fetching GSAP"
  # cdnjs first; cloud sessions (Claude app "Code" tab) often only reach the npm registry, so fall back to it
  curl -fsSL -m 30 https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js -o "$KIT/vendor/gsap.min.js" 2>/dev/null || {
    t=$(mktemp -d); (cd "$t" && npm pack -q gsap@3.12.5 >/dev/null && tar xzf gsap-3.12.5.tgz) && cp "$t/package/dist/gsap.min.js" "$KIT/vendor/gsap.min.js"; rm -rf "$t"; }
fi

say "warming up HyperFrames (first run downloads it)"
npx --yes hyperframes@0.8.34 --version >/dev/null 2>&1 || echo "warning: could not run hyperframes yet; the first render will retry"

if [ "${1:-}" = "--cutout" ]; then
  say "downloading the matting model"
  "$KIT/.venv/bin/python" -c "import sys; sys.path.insert(0, '$KIT'); import cutout; cutout.model_path('mobilenetv3')"
fi

[ -n "${GROQ_API_KEY:-}" ] || echo "note: set GROQ_API_KEY (free at https://console.groq.com/keys) so clips can be transcribed"
say "ready: $KIT/.venv/bin/python"
