#!/usr/bin/env bash
# Bootstrap idempotent runtime on Raspberry Pi 4B (Debian 13 Trixie arm64):
# - Disables wlan0 power_save & enables avahi-daemon for stable pi.local
# - Installs Python 3.11 venv via uv + Cortex-A72 safe torch==2.3.1 (whl/cpu)
# - Installs Node.js v22.23.5 ARM64 into ~/.local/node (no apt needed)
# - Enables Firefox audio autoplay for unattended Kiosk / /companion TTS
set -euo pipefail

RUN_BENCHMARK=0
for arg in "$@"; do
  case "$arg" in
    --benchmark) RUN_BENCHMARK=1 ;;
    *)
      echo "Usage: $0 [--benchmark]" >&2
      exit 2
      ;;
  esac
done

SLR_DIR="$HOME/PBL6/slr-m2"
VENV_DIR="$HOME/pbl6-venv"
NODE_DIR="$HOME/.local/node"
NODE_TAR_URL="https://nodejs.org/dist/latest-v22.x/node-v22.23.5-linux-arm64.tar.xz"

echo "[1/5] Stabilizing Wi-Fi mDNS (pi.local)..."
sudo -n nmcli connection modify preconfigured wifi.powersave 2 2>/dev/null || true
sudo -n iw dev wlan0 set power_save off 2>/dev/null || true
sudo -n systemctl enable --now avahi-daemon 2>/dev/null || true

echo "[2/5] Installing uv & Python 3.11 + torch==2.3.1 (Cortex-A72 safe)..."
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
if [ -f "$HOME/.local/bin/env" ]; then
  # shellcheck disable=SC1091
  source "$HOME/.local/bin/env"
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  uv venv --python 3.11 "$VENV_DIR"
fi

VIRTUAL_ENV="$VENV_DIR" uv pip install \
  torch==2.3.1 \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple

VIRTUAL_ENV="$VENV_DIR" uv pip install \
  "numpy==1.26.4" \
  "opencv-python-headless==4.11.0.86" \
  fastapi==0.115.6 \
  uvicorn==0.34.0 \
  httpx==0.28.1 \
  websockets==14.2

echo "[3/5] Checking Node.js 22 ARM64..."
if [ ! -x "$NODE_DIR/bin/node" ]; then
  mkdir -p "$NODE_DIR"
  curl -fsSL "$NODE_TAR_URL" | tar -C "$NODE_DIR" --strip-components=1 -xJf -
fi
echo "Node version: $("$NODE_DIR/bin/node" -v)"
echo "Python/Torch check:"
"$VENV_DIR/bin/python" -c "import torch, numpy, cv2; print('  python:', torch.__version__, 'numpy:', numpy.__version__, 'cv2:', cv2.__version__)"

echo "[4/5] Configuring dedicated Firefox Kiosk profile (autoplay + mic permission + chromeless)..."
KIOSK_PROFILE="$HOME/.local/share/pbl6-kiosk-profile"
mkdir -p "$KIOSK_PROFILE/chrome"
cat > "$KIOSK_PROFILE/user.js" <<'EOF'
user_pref("media.autoplay.default", 0);
user_pref("media.autoplay.blocking_policy", 0);
user_pref("permissions.default.microphone", 1);
user_pref("media.navigator.permission.disabled", true);
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
user_pref("browser.tabs.inTitlebar", 1);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("datareporting.policy.dataSubmissionPolicyBypassNotification", true);
EOF
cat > "$KIOSK_PROFILE/chrome/userChrome.css" <<'EOF'
#TabsToolbar, #nav-bar, #PersonalToolbar {
  visibility: collapse !important;
}
EOF
cat > "$KIOSK_PROFILE/xulstore.json" <<'EOF'
{"chrome://browser/content/browser.xhtml":{"main-window":{"screenX":"0","screenY":"0","width":"1024","height":"568","sizemode":"maximized"}}}
EOF
echo "  Wrote $KIOSK_PROFILE/user.js, chrome/userChrome.css and xulstore.json"

echo "[5/5] Bootstrap checks..."
if [ "$RUN_BENCHMARK" -eq 1 ]; then
  if [ -f "$SLR_DIR/outputs/sample_014159_landmarks.npz" ]; then
    cd "$SLR_DIR"
    "$VENV_DIR/bin/python" -m deployment.m2.benchmark_pi_gcn \
      --npz outputs/sample_014159_landmarks.npz \
      --runs 5 --warmup 1 --threads 4 --threshold 1.5
  else
    echo "Skip benchmark: $SLR_DIR/outputs/sample_014159_landmarks.npz not found"
  fi
fi

echo "=== Pi 4B Bootstrap COMPLETE ==="
