#!/usr/bin/env bash
# Start (or stop) PBL6 M2.2 services on Raspberry Pi 4B:
# - SLR Edge (:8765, pi-split or remote-fallback -> Laptop Vision Backend :8767)
# - Web UI stt-app (:3100, standalone Next.js)
# - Firefox Wayland Kiosk on 7" display (unless --no-kiosk)
set -euo pipefail

LAPTOP_IP="${PBL6_VISION_HOST:-192.168.1.155}"
INFERENCE_MODE="pi-split"
FALLBACK_THRESHOLD="0"
UTTERANCE_REST="4.0"
ENABLE_VNC=1
LAUNCH_KIOSK=1
KIOSK_FLAG="--new-window"
STOP_ONLY=0
POSITIONAL_IP_SET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --mode)
      INFERENCE_MODE="${2:?missing mode value}"
      shift 2
      ;;
    --threshold)
      FALLBACK_THRESHOLD="${2:?missing threshold value}"
      shift 2
      ;;
    --utterance-rest)
      UTTERANCE_REST="${2:?missing utterance-rest value}"
      shift 2
      ;;
    --no-vnc)
      ENABLE_VNC=0
      shift
      ;;
    --no-kiosk)
      LAUNCH_KIOSK=0
      shift
      ;;
    --windowed)
      KIOSK_FLAG="--new-window"
      shift
      ;;
    --fullscreen-kiosk)
      KIOSK_FLAG="--kiosk"
      shift
      ;;
    --stop)
      STOP_ONLY=1
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [LAPTOP_IP] [--mode pi-split|remote-fallback] [--threshold SECONDS] [--utterance-rest 4.0] [--no-vnc] [--windowed] [--fullscreen-kiosk] [--no-kiosk] [--stop]"
      echo "  Automatic laptop inference fallback is off by default (--threshold 0). Use --threshold 1.5 to enable it."
      exit 0
      ;;
    *)
      if [ "$POSITIONAL_IP_SET" -eq 0 ] && [[ "$1" != -* ]]; then
        LAPTOP_IP="$1"
        POSITIONAL_IP_SET=1
        shift
      else
        echo "Unknown argument: $1" >&2
        exit 2
      fi
      ;;
  esac
done

stop_services() {
  pkill -f "deployment\.m2\.server" 2>/dev/null || true
  pkill -f "PBL6/stt-app/server\.js" 2>/dev/null || true
  pkill -f "next-server" 2>/dev/null || true
  pkill -f "\.local/node/bin/node" 2>/dev/null || true
  fuser -k 8765/tcp 2>/dev/null || true
  fuser -k 3100/tcp 2>/dev/null || true
  pkill -f "pbl6-kiosk-profile" 2>/dev/null || true
  pkill -f "firefox.*--kiosk" 2>/dev/null || true
  pkill -x firefox 2>/dev/null || true
  pkill -x firefox-esr 2>/dev/null || true
  pkill -f "pbl6-wayvnc-loop" 2>/dev/null || true
  pkill -x wayvnc 2>/dev/null || true
}

stop_services
if [ "$STOP_ONLY" -eq 1 ]; then
  echo "Stopped PBL6 Pi services."
  exit 0
fi
sleep 1

SLR_DIR="$HOME/PBL6/slr-m2"
UI_DIR="$HOME/PBL6/stt-app"
PY_BIN="$HOME/pbl6-venv/bin/python"
NODE_BIN="$HOME/.local/node/bin/node"

if [ ! -x "$PY_BIN" ]; then
  echo "Missing $PY_BIN. Run: bash $SLR_DIR/deployment/m2/pi_bootstrap.sh" >&2
  exit 1
fi
if [ ! -x "$NODE_BIN" ]; then
  echo "Missing $NODE_BIN. Run: bash $SLR_DIR/deployment/m2/pi_bootstrap.sh" >&2
  exit 1
fi
if [ ! -f "$UI_DIR/server.js" ]; then
  echo "Missing $UI_DIR/server.js. Deploy standalone bundle from Windows first." >&2
  exit 1
fi

echo "[Hardware & Settings Check]"
VIDEO_NODES="$(ls -1 /dev/video[0-9] 2>/dev/null | tr '\n' ' ' || true)"
echo "  USB Video : ${VIDEO_NODES:-NONE (chưa nhận USB camera!)}"
MIC_CARDS="$( (arecord -l 2>/dev/null | grep '^card' | tr '\n' ';') || true )"
echo "  Audio In  : ${MIC_CARDS:-NONE (chưa nhận USB mic!)}"
SETTINGS_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/pbl6-stt/settings.json"
DG_STATUS="$("$PY_BIN" -c 'import json, os, sys; p=sys.argv[1]; d=json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}; print("Configured" if str(d.get("apiKey","")).strip() else "MISSING")' "$SETTINGS_FILE" 2>/dev/null || echo "MISSING")"
echo "  Deepgram  : $DG_STATUS ($SETTINGS_FILE)"

VISION_URL="http://${LAPTOP_IP}:8767"
if ! curl -fsS --max-time 2 "${VISION_URL}/api/vision/health" >/dev/null 2>&1; then
  echo "[WARN] Laptop Vision Backend ${VISION_URL} is not reachable yet (start vision_backend on Windows before signing)."
fi

cd "$SLR_DIR"
nohup "$PY_BIN" -u -m deployment.m2.server \
  --host 0.0.0.0 \
  --port 8765 \
  --inference-mode "$INFERENCE_MODE" \
  --vision-backend-url "$VISION_URL" \
  --fallback-threshold "$FALLBACK_THRESHOLD" \
  --utterance-rest "$UTTERANCE_REST" \
  >/tmp/pbl6-slr.log 2>&1 </dev/null &
SLR_PID=$!

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ -S "$XDG_RUNTIME_DIR/bus" ]; then
  export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
fi
WL_SOCK=""
for sock in "$XDG_RUNTIME_DIR"/wayland-*; do
  if [ -S "$sock" ]; then
    WL_SOCK="$(basename "$sock")"
    break
  fi
done
if [ -z "$WL_SOCK" ] && command -v labwc >/dev/null 2>&1; then
  WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 nohup labwc >/tmp/pbl6-labwc.log 2>&1 </dev/null &
  sleep 1.5
  for sock in "$XDG_RUNTIME_DIR"/wayland-*; do
    if [ -S "$sock" ]; then
      WL_SOCK="$(basename "$sock")"
      break
    fi
  done
fi
export WAYLAND_DISPLAY="${WL_SOCK:-wayland-0}"
export MOZ_ENABLE_WAYLAND=1

if command -v wlr-randr >/dev/null 2>&1; then
  for out in NOOP-1 HEADLESS-1; do
    wlr-randr --output "$out" --custom-mode 1024x600@60Hz 2>/dev/null || true
  done
fi

if [ "$ENABLE_VNC" -eq 1 ] && command -v wayvnc >/dev/null 2>&1; then
  sudo -n systemctl stop wayvnc.service 2>/dev/null || true
  pkill -f "pbl6-wayvnc-loop" 2>/dev/null || true
  pkill -x wayvnc 2>/dev/null || true
  nohup bash -c '
    # pbl6-wayvnc-loop
    while true; do
      rm -f "${XDG_RUNTIME_DIR}/wayvncctl" 2>/dev/null || true
      if command -v wlr-randr >/dev/null 2>&1; then
        wlr-randr --output NOOP-1 --custom-mode 1024x600 2>/dev/null || true
        wlr-randr --output HEADLESS-1 --custom-mode 1024x600 2>/dev/null || true
      fi
      wayvnc --render-cursor --max-fps=30 0.0.0.0 5900
      sleep 1
    done
  ' >/tmp/pbl6-wayvnc.log 2>&1 </dev/null &
else
  sudo -n systemctl stop wayvnc.service 2>/dev/null || true
  pkill -f "pbl6-wayvnc-loop" 2>/dev/null || true
  pkill -x wayvnc 2>/dev/null || true
fi

gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled true 2>/dev/null || true
if command -v squeekboard >/dev/null 2>&1 && ! pgrep -x squeekboard >/dev/null 2>&1; then
  nohup squeekboard >/tmp/pbl6-squeekboard.log 2>&1 </dev/null &
fi
if command -v fcitx5 >/dev/null 2>&1 && ! pgrep -x fcitx5 >/dev/null 2>&1; then
  fcitx5 -d >/dev/null 2>&1 || true
fi

cd "$UI_DIR"
PBL6_STT_RUNTIME_OS=linux \
PBL6_STT_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/pbl6-stt" \
PBL6_STT_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/pbl6-stt" \
HOSTNAME=0.0.0.0 PORT=3100 nohup "$NODE_BIN" "$UI_DIR/server.js" \
  >/tmp/pbl6-ui.log 2>&1 </dev/null &
UI_PID=$!

wait_http() {
  local url="$1"
  local label="$2"
  local logfile="$3"
  local pid="$4"
  local i=0
  while [ "$i" -lt 90 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "[ERROR] $label exited early ($url). Last log lines:" >&2
      tail -n 30 "$logfile" >&2 || true
      return 1
    fi
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      echo "[OK] $label ready ($url)"
      return 0
    fi
    sleep 0.5
    i=$((i + 1))
  done
  echo "[ERROR] $label failed to start ($url). Last log lines:" >&2
  tail -n 30 "$logfile" >&2 || true
  return 1
}

wait_http "http://127.0.0.1:8765/api/health" "SLR Edge ($SLR_PID)" "/tmp/pbl6-slr.log" "$SLR_PID"
wait_http "http://127.0.0.1:3100/" "stt-app UI ($UI_PID)" "/tmp/pbl6-ui.log" "$UI_PID"

if [ "$LAUNCH_KIOSK" -eq 1 ]; then
  KIOSK_PROFILE="$HOME/.local/share/pbl6-kiosk-profile"
  mkdir -p "$KIOSK_PROFILE/chrome"
  rm -rf "$KIOSK_PROFILE/cache2" 2>/dev/null || true
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

  CACHE_BUST="$(date +%s)"
  nohup firefox --profile "$KIOSK_PROFILE" --no-remote "$KIOSK_FLAG" "http://127.0.0.1:3100/?v=${CACHE_BUST}" >/tmp/pbl6-kiosk.log 2>&1 </dev/null &
  echo "[OK] Firefox ($KIOSK_FLAG) launched on WAYLAND_DISPLAY=$WAYLAND_DISPLAY (profile=$KIOSK_PROFILE)"
fi

PI_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "=== PBL6 Pi Running ==="
echo "  SLR Edge : http://${PI_IP:-127.0.0.1}:8765/api/health (mode=$INFERENCE_MODE, utterance_rest=${UTTERANCE_REST}s -> $VISION_URL)"
echo "  Web UI   : http://${PI_IP:-127.0.0.1}:3100/"
echo "  Companion: http://${PI_IP:-127.0.0.1}:3100/companion"
if [ "$ENABLE_VNC" -eq 1 ]; then
  echo "  TightVNC : ${PI_IP:-127.0.0.1}:5900"
else
  echo "  TightVNC : disabled (--no-vnc)"
fi
echo "  Logs     : /tmp/pbl6-slr.log | /tmp/pbl6-ui.log | /tmp/pbl6-kiosk.log"
