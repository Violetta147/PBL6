# M2.2 Deployment Runbook — LAN Vision Backend ↔ Raspberry Pi 4B Edge

> **Hướng dẫn tổng hợp cho đồng đội (Clone, Firewall, SSH, TightVNC, Launch):** Xem [HANDOFF_TEAMMATE_M2_PI.md](../../../HANDOFF_TEAMMATE_M2_PI.md).

Kiến trúc phân tải **1A** sau Bước 5:
- **Laptop / Server LAN (`vision_backend.py`, `:8767`)**: chạy MediaPipe (`pose-frame` real-time + `extract-landmarks` chuẩn hóa trả `.npz` ~15–100 KB), đồng thời giữ sẵn `/api/vision/classify-clip` để dự phòng.
- **Raspberry Pi 4B (`Debian 13 Trixie`, `aarch64`, `Python 3.11` qua `uv`, `:8765` + `stt-app`, `:3100`, `WayVNC :5900`)**: đọc USB Webcam, chạy `M1 Segmenter`, chạy `SL-GCN 07b` (`best.pt`, **không cần cài MediaPipe**), giữ 400 MP3 TTS offline và phục vụ giao diện `stt-app` + `/companion` trên LAN.

---

## 0. Khôi phục nhanh 1 lệnh sau khi flash lại thẻ SD / chạy hàng ngày (Khuyên dùng)

Nếu vừa flash lại OS cho Pi, dùng 3 script tự động (`deploy_to_pi.ps1`, `pi_bootstrap.sh`, `pi_start.sh`) để đồng bộ mã nguồn, cài `uv` + `torch==2.3.1` + Node 22 ARM64 và tự xóa file tạm:

```powershell
# 0. Xóa host key cũ nếu vừa flash lại OS (chỉ chạy 1 lần)
ssh-keygen -R pi.local
ssh-keygen -R <PI_IP>

# 1. Đẩy toàn bộ code + TTS + stt-app standalone và cài môi trường lên Pi (thêm -SetupKey nếu muốn nạp public key)
cd "<PBL6>\slr-m2"
powershell -ExecutionPolicy Bypass -File .\deployment\m2\deploy_to_pi.ps1 -PiHost <PI_IP>
```

*(Nếu Pi đã bootstrap sẵn và chỉ cập nhật code/UI/script hàng ngày, thêm `-FastSync` — script tự dò IP Laptop cùng subnet, đồng bộ và khởi chạy luôn `:8765`, `:3100`, Firefox Wayland `--new-window`, Squeekboard & TightVNC `wayvnc :5900`.)*

Sau bước deploy lần đầu, bật Vision Backend `:8767` trên Laptop (mục 1), rồi khởi chạy toàn bộ dịch vụ trên Pi bằng 1 lệnh:

```powershell
ssh pi@<PI_IP> "bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh <LAPTOP_IP>"
```

*(Các mục 1–3 bên dưới ghi chi tiết từng bước thủ công để tra cứu khi cần.)*

---

## 1. Khởi chạy Vision Backend & Mở tường lửa trên Laptop Windows

1. Chạy dịch vụ Vision Backend (trong môi trường Python `pbl6_slr`):

```powershell
cd "<PBL6>\slr-m2"
python -m deployment.m2.vision_backend --host 0.0.0.0 --port 8767
```

2. Mở cổng inbound TCP `8767` trong Windows Firewall cho mọi profile Wi-Fi (`profile=any`, **PowerShell Run as Administrator**):

```powershell
netsh advfirewall firewall delete rule name="PBL6 Vision Backend 8767" 2>$null; netsh advfirewall firewall add rule name="PBL6 Vision Backend 8767" dir=in action=allow protocol=TCP localport=8767 profile=any
```

3. Kiểm tra thông mạng từ SSH trên Pi (thay `<LAPTOP_LAN_IP>` bằng IP Wi-Fi Laptop):

```bash
curl -sS --max-time 4 http://<LAPTOP_LAN_IP>:8767/api/vision/health
```

---

## 1.5. Đồng bộ mã nguồn gọn lên Pi vừa flash (`<PI_IP>`)

> [!NOTE]
> Nếu Windows không phân giải được mDNS `pi.local` (`No such host is known`) — thường do `wlan0` trên Pi bật chế độ tiết kiệm điện Wi-Fi (`power_save`) làm trễ gói multicast mDNS — dùng thẳng **IPv4 `wlan0` của Pi** (`hostname -I` trên Pi hoặc dò bảng MAC `2c-cf-67-...` bằng `arp -a` trên Windows).
> Để `pi.local` ổn định hơn trên Pi:
> ```bash
> sudo nmcli connection modify preconfigured wifi.powersave 2 2>/dev/null || true
> sudo iw dev wlan0 set power_save off 2>/dev/null || true
> sudo systemctl enable --now avahi-daemon
> ```

1. *(Tùy chọn, tránh gõ lại mật khẩu SSH)* Nạp khóa công khai có lọc `\r` CRLF của Windows:

```powershell
Get-Content -Raw "$HOME\.ssh\id_ed25519.pub" | ssh pi@<PI_IP> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && tr -d '\r' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

2. Đóng gói `.tar.gz` vào `$env:TEMP` rồi gửi qua `scp` (tránh lỗi pipe `|` nhị phân làm hỏng archive trên Windows PowerShell 5.1), dọn phần lỗi cũ trên Pi khi giải nén và xóa file tạm trên Windows:

```powershell
tar -C "<PBL6>\slr-m2" --exclude "__pycache__" -czf "$env:TEMP\slr-m2-pi.tar.gz" deployment models/checkpoints/sl_gcn_bone_07b/07b_bone_seed42 outputs/sample_014159_landmarks.npz
tar -C "<PBL6>\slr-app\MVP\local_data" -czf "$env:TEMP\pbl6-tts.tar.gz" tts
scp "$env:TEMP\slr-m2-pi.tar.gz" "$env:TEMP\pbl6-tts.tar.gz" pi@<PI_IP>:/tmp/
Remove-Item "$env:TEMP\slr-m2-pi.tar.gz","$env:TEMP\pbl6-tts.tar.gz" -Force
ssh pi@<PI_IP> "rm -rf ~/PBL6/slr-m2 ~/PBL6/slr-app/MVP/local_data/tts && mkdir -p ~/PBL6/slr-m2 ~/PBL6/slr-app/MVP/local_data && tar -C ~/PBL6/slr-m2 -xzf /tmp/slr-m2-pi.tar.gz && tar -C ~/PBL6/slr-app/MVP/local_data -xzf /tmp/pbl6-tts.tar.gz && rm -f /tmp/slr-m2-pi.tar.gz /tmp/pbl6-tts.tar.gz"
```

---

## 2. Cài phụ thuộc nhẹ trong `venv` & Đo `SL-GCN 07b` trên Pi 4B (`Trixie` / `ARMv8.0-A`)

> [!WARNING]
> **Không dùng `torch>=2.6` hoặc wheel mặc định `+cu132` từ PyPI trên Raspberry Pi 4B:** CPU **Cortex-A72 (ARMv8.0-A)** thiếu tập lệnh ARMv8.1+ LSE nên sẽ văng **`Illegal instruction`** khi suy luận mạng SL-GCN. Thay bằng **`uv` + Python `3.11` + `torch==2.3.1` (`whl/cpu`)** (không phụ thuộc `apt`).

```bash
cd ~/PBL6/slr-m2
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv venv --python 3.11 ~/pbl6-venv
source ~/pbl6-venv/bin/activate

uv pip install torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
uv pip install "numpy==1.26.4" "onnxruntime>=1.19.0" "opencv-python-headless==4.11.0.86" fastapi==0.115.6 uvicorn==0.34.0 httpx==0.28.1 websockets==14.2
```

Chạy benchmark bằng file landmark trích sẵn từ mẫu thật `014159.mp4` (`Dài`, `98.14%`, không dùng MediaPipe):

```bash
python -m deployment.m2.benchmark_pi_gcn --npz outputs/sample_014159_landmarks.npz --backend onnx --runs 5 --warmup 1 --threads 4 --threshold 1.5
```

- **Kết quả đo thực tế trên Raspberry Pi 4B (`Linux-6.18.50+rpt-rpi-v8-aarch64`, `Python 3.11.18`, `threads=4`, `mediapipe_imported=false`):**
  - **ONNX Runtime `1.32.0` (`--backend onnx`, mặc định trên nhánh `perf/streaming-onnx`):** `cold = 0.764s`, `min = 0.737s`, **`median = 0.741s`**, **`p95 = 0.760s <= 1.50s`**, `max = 0.761s`, top-1 **`Dài` (`98.14%`)** → **Verdict: `PASS` (`--inference-mode pi-split`, nhanh gấp ~6.6× so với `4.94s` khi chạy PyTorch live)**.
  - **PyTorch `2.3.1` (`--backend torch`):** `cold = 1.108s`, `median = 1.116s`, `p95 = 1.168s` khi CPU rảnh (nhưng khi chạy live kèm Firefox/VNC/Camera lên tới `4.94s`).
- Nếu về sau đổi checkpoint nặng hơn làm `p95 > 1.5s`, chuyển sang `--inference-mode remote-fallback` (hoặc giữ `pi-split` — server tự fallback sang `:8767/api/vision/classify-clip` sau `2` lần liên tiếp `> 1.5s`).

---

## 3. Chạy dịch vụ trên Raspberry Pi 4B

### 3.1 SLR Edge Server (`:8765`, Terminal SSH #1 trên Pi)

```bash
cd ~/PBL6/slr-m2
source ~/pbl6-venv/bin/activate
python -m deployment.m2.server \
  --host 0.0.0.0 \
  --port 8765 \
  --inference-mode pi-split \
  --vision-backend-url http://<LAPTOP_IP>:8767 \
  --fallback-threshold 1.5
```

*(Thay `<LAPTOP_IP>` bằng IP Wi-Fi của Laptop; kiểm tra nhanh trên Pi: `curl -s http://127.0.0.1:8765/api/health`.)*

### 3.2 Web UI `stt-app` (`:3100`) chế độ standalone (Pi + LAN Companion)

1. **Từ Windows PowerShell**, đóng gói bản `.next/standalone` đã curate (loại bỏ binary `*win32*`) và đẩy qua `scp` rồi tự xóa file tạm:

```powershell
tar -C "<PBL6>\stt-app\.next\standalone" --exclude "*win32*" -czf "$env:TEMP\stt-app-standalone.tar.gz" .
scp "$env:TEMP\stt-app-standalone.tar.gz" pi@<PI_IP>:/tmp/
Remove-Item "$env:TEMP\stt-app-standalone.tar.gz" -Force
ssh pi@<PI_IP> "rm -rf ~/PBL6/stt-app && mkdir -p ~/PBL6/stt-app && tar -C ~/PBL6/stt-app -xzf /tmp/stt-app-standalone.tar.gz && rm -f /tmp/stt-app-standalone.tar.gz"
```

2. **Trên Terminal SSH #2 của Pi**, cài Node.js 22 ARM64 trực tiếp vào `~/.local/node` (không cần `apt` / tránh lỗi `sqv` và không tải Electron) rồi khởi chạy `server.js`:

```bash
mkdir -p ~/.local/node
curl -fsSL https://nodejs.org/dist/latest-v22.x/node-v22.23.5-linux-arm64.tar.xz | tar -C ~/.local/node --strip-components=1 -xJf -
~/.local/node/bin/node -v
PBL6_STT_RUNTIME_OS=linux HOSTNAME=0.0.0.0 PORT=3100 ~/.local/node/bin/node ~/PBL6/stt-app/server.js
```

> [!NOTE]
> Quyền truy cập LAN: `/api/conversations` (`GET`) và `/api/conversations/[id]` (`GET`) cho phép xem lịch sử từ thiết bị cùng mạng nội bộ (`192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`, `*.local`) để `/companion` hoạt động bình thường. Các endpoint nhạy cảm (`Cài đặt`, `Ghi âm/Mic`, `POST/PATCH/DELETE` hội thoại) vẫn khóa chặt chỉ chấp nhận loopback trên Pi.

### 3.3 Mở Kiosk 7 inch (`1024×600`), TightVNC (`:5900`) & `/companion` trên điện thoại

- **Trên Pi 4B (dùng Firefox Wayland `--new-window` chromeless — đã xác minh lên hình thật):** Trên Debian 13 Trixie (`labwc`), bản Chromium `156` mặc định bị `Illegal instruction` / màn hình trắng, còn `--kiosk` che mất bàn phím ảo `Squeekboard`. Dùng `pi_start.sh` để mở Firefox `--new-window` chromeless + `Squeekboard` + `fcitx5` + vòng lặp `pbl6-wayvnc-loop` (`wayvnc --render-cursor --max-fps=30 0.0.0.0 5900`, tự bám sang màn ảo `NOOP-1` `1024×600` nếu tắt/rút HDMI).
- **TightVNC Viewer trên Windows:** nhập `<PI_IP>` (hoặc `<PI_IP>::5900`) và chọn **`Connect without encryption`** khi được hỏi.
- **Trong `Cài đặt -> SLR` trên UI Pi:** để trống (tự dùng `http://127.0.0.1:8765`) hoặc nhập `http://127.0.0.1:8765`.
- **Trên điện thoại / Laptop trong LAN:** mở `http://<PI_IP>:3100/companion` (trình duyệt tự suy ra `http://<PI_IP>:8765`).

---

## 4. Đường OTA cập nhật model `best.pt` sau này

`BoneClassifier` kiểm tra SHA-256 trước khi nạp mô hình. Khi phát hành checkpoint `07b` mới cho Pi 4B, thay thư mục:

```text
slr-m2/models/checkpoints/sl_gcn_bone_07b/07b_bone_seed42/
├── best.pt
├── best.pt.sha256
├── config.json
├── label_map.json
└── code/
```

Sau đó khởi động lại `deployment.m2.server` trên Pi.
