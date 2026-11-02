#!/usr/bin/env bash
# 動画の生成環境（VOICEVOX + Playwright + ffmpeg）を用意する。何度実行してもよい。
set -euo pipefail
VV=${VV_DIR:-/home/claude/vv}
mkdir -p "$VV/vvms"
cd "$VV"
pip install --break-system-packages -q pyopenjtalk numpy 2>&1 | grep -v -i warning || true
python3 -c "import pyopenjtalk; pyopenjtalk.g2p('テスト')" >/dev/null   # 辞書を取得
WHL=voicevox_core-0.16.4-cp310-abi3-manylinux_2_34_x86_64.whl
[ -f "$WHL" ] || curl -sSL -o "$WHL" "https://github.com/VOICEVOX/voicevox_core/releases/download/0.16.4/$WHL"
python3 -c "import voicevox_core" 2>/dev/null || pip install --break-system-packages -q "./$WHL" 2>&1 | grep -v -i warning || true
ORT=voicevox_onnxruntime-linux-x64-1.17.3
[ -d "$ORT" ] || { curl -sSL -o ort.tgz "https://github.com/VOICEVOX/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/$ORT.tgz" && tar xzf ort.tgz; }
[ -s vvms/0.vvm ] || curl -sSL -o vvms/0.vvm "https://github.com/VOICEVOX/voicevox_vvm/releases/download/0.16.4/0.vvm"
which ffmpeg >/dev/null
python3 -c "import playwright"
echo "setup ok"
