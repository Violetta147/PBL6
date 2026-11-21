# Hướng Dẫn Đồng Đội Tiếp Tục Làm Việc — PBL6 M2.2 (Pi 4B + Laptop Vision Backend + TightVNC)

Tài liệu này giúp bạn clone repo về máy mới và làm việc được ngay trên **Raspberry Pi 4B**, chạy **SLR + STT + TightVNC + Web UI** y hệt phiên làm việc hiện tại.

> **Tài liệu liên quan:**
> - Kiến trúc & các quyết định đã chốt (`1A, 2A, 3A, 4A, 5B`): [docs/PBL6_DECISION_AND_ARCHITECTURE.md](docs/PBL6_DECISION_AND_ARCHITECTURE.md)
> - Runbook kỹ thuật & benchmark Pi 4B chi tiết: [slr-m2/deployment/m2/PI4_M22_RUNBOOK.md](slr-m2/deployment/m2/PI4_M22_RUNBOOK.md)
> - Quy ước & chỉ dẫn repo: [AGENTS.md](AGENTS.md) · [stt-app/AGENTS.md](stt-app/AGENTS.md)

---

## 1. Tổng Quan Kiến Trúc M2.2 Split (`1A, 2A, 3A, 4A, 5B`)

```text
USB Webcam + Mic (Pi 4B)
   ├──► Video Capture + M1 Segmenter + SL-GCN 07b (slr-m2 :8765) ◄── LAN HTTP :8767 ──► Laptop Vision Backend (MediaPipe + SL-GCN fallback)
   ├──► 400 Offline MP3 TTS (/api/tts/{id}.mp3, slr-app/MVP/local_data/tts/0..399.mp3)
   ├──► Unified Web UI stt-app (:3100 trên Pi & :3100/companion trên điện thoại/laptop LAN)
   └──► WayVNC (:5900, vòng lặp tự hồi pbl6-wayvnc-loop trên Firefox Wayland --new-window + Squeekboard)
```

- **Laptop LAN (`vision_backend.py`, cổng `8767`):** Chạy MediaPipe Pose từng khung (`/api/vision/pose-frame`), trích xuất landmark chuẩn hóa cho clip (`/api/vision/extract-landmarks`), và tự làm dự phòng SL-GCN (`/api/vision/classify-clip`) nếu Pi chạy chậm hơn ngưỡng `1.50s` `2` lần liên tiếp.
- **Raspberry Pi 4B 8GB (Debian 13 Trixie `aarch64`):** Chạy SLR Edge (`:8765`), Next.js standalone `stt-app` (`:3100`), Firefox Wayland (`--new-window` chromeless để không đè bàn phím ảo `Squeekboard`), `fcitx5`, và `wayvnc` (`:5900`).

---

## 2. Trạng Thái Thực Tế Hiện Tại (Đã Chạy Thật vs Việc Tiếp Theo)

### Đã kiểm chứng chạy thật trên phần cứng Pi 4B
- **Phần cứng & dịch vụ trên Pi:** USB Webcam (`Wed Camera 32e6:9221` video + USB Audio mic), Deepgram Nova-3 STT tiếng Việt, bàn phím ảo `Squeekboard` + `Fcitx5`, và `WayVNC :5900` tự khôi phục khi tắt/bật màn hình HDMI 7".
- **Nhận dạng ký hiệu live trên Pi (`mode=pi-split` + `backend_fallback`):** Các phiên thử thực tế trước camera đã nhận đúng nhiều từ VSL400 với **`incomplete = 0`**, ví dụ: **`Dài` (`99.6%`)**, **`Khăn quàng cổ` (`98.8%–99.8%`)**, **`Xin` (`99.8%`)**, **`Bơi lội` (`95.5%`)**, **`Cái quần` (`95.1%`)**.
- **Tối ưu Gói 1 & Phương án A (`utterance_rest = 4.0s`, giữ `pi-split`):** Đã tách luồng đọc camera trên Pi (`15–20 FPS` lưu RAM `_ring`) độc lập với luồng Pose (`320px`), bỏ ghi ổ đĩa `.avi` bằng gói RAM `.pbl6`, giữ nóng + chạy song song `Pose || Hands` trên Laptop, và bật Phương án A (`utterance_rest = 4.0s`, `autoSaveOnRest = true`) để gom chuỗi từ của cùng 1 câu gửi vào hội thoại khi buông 2 tay nghỉ `4s`. *(Ghi chú UX tùy chọn sau này: có thể bổ sung nút mềm **Tạm dừng (Pause)** trên khung camera nếu muốn đóng băng luồng để xem kỹ kết quả.)*

### Hàng đợi việc tiếp theo (chỉ sửa khi nhóm chốt/duyệt)
1. **Test lại độ mượt & độ chính xác sau tối ưu Gói 1 trên Pi 4B** (`pose_fps`, `capture_fps`, tỷ lệ nhận đúng nhiều từ liên tiếp).
2. **Bước 6 (Giai đoạn cuối — sau khi test Gói 1 đạt mượt & chính xác):**
   - Gắn 1 lần gọi **LLM JSON** vào cuối mỗi `utterance` để biến chuỗi gloss thô thành câu tiếng Việt tự nhiên + đẩy telemetry tối giản (`online`, `session_count`, `gloss_count`, `latency_ms`) lên **ThingsBoard**.

---

## 3. Cài Đặt Trên Máy Tính Của Bạn (Lần Đầu)

> Không đưa file `.env`, Deepgram API key hay mật khẩu Pi lên GitHub — hãy nhắn riêng trong nhóm để lấy **mật khẩu tài khoản `pi`** và **Deepgram API key**.

### 3.1 Clone repo & tạo môi trường Python Vision Backend (`pbl6_slr`)

```powershell
git clone https://github.com/Violetta147/PBL6.git
cd PBL6
```

*(Nếu đã clone trước đó: `git pull origin main`.)*

Dùng Conda (hoặc `venv`) với **Python 3.11**:

```powershell
conda create -n pbl6_slr python=3.11 -y
conda activate pbl6_slr
cd slr-m2
pip install -r .\deployment\m2\requirements-vision.txt
```

*(File `requirements-vision.txt` đã khóa đúng `mediapipe==0.10.14`, `numpy==1.26.4`, `opencv-contrib-python==4.11.0.86`, `fastapi`, `uvicorn`, `httpx`, `websockets` và `torch>=2.5.1`.)*

### 3.2 Build bản standalone của `stt-app` (Node.js >= 22)

Script `deploy_to_pi.ps1` đóng gói từ `stt-app\.next\standalone\server.js`, nên **phải build `stt-app` trước ít nhất 1 lần** (và build lại mỗi khi sửa code UI):

```powershell
cd ..\stt-app
npm ci
npm run build
npm run curate:server
```

### 3.3 Mở Windows Firewall cổng `8767`

Mở **PowerShell bằng quyền Administrator** (*Run as Administrator*) trên Windows và chạy 1 lần:

```powershell
netsh advfirewall firewall delete rule name="PBL6 Vision Backend 8767" 2>$null; netsh advfirewall firewall add rule name="PBL6 Vision Backend 8767" dir=in action=allow protocol=TCP localport=8767 profile=any
```

*(Dùng `profile=any` để dù mang laptop sang Wi-Fi trường/quán/hotspot chế độ Public thì Pi vẫn gọi được vào cổng `8767`.)*

### 3.4 Cấu hình Deepgram API Key

- Khi chạy `deploy_to_pi.ps1`, nếu trên Windows có sẵn `%LOCALAPPDATA%\PBL6-STT\settings.json`, script sẽ tự đẩy sang `~/.config/pbl6-stt/settings.json` trên Pi (ghi `selectedMicrophoneId=default`).
- Hoặc bạn mở Web UI trên Pi/VNC → bấm **Cài đặt** → **Giọng nói thành chữ** → dán **Deepgram API key** → **Lưu**.

---

## 4. Quy Trình Bật Hệ Thống Hàng Ngày (SSH, Vision Backend, Deploy Lên Pi)

### Bước 1 — Tìm IP của Raspberry Pi trên mạng hiện tại

Đảm bảo Laptop và Pi dùng **chung một mạng Wi-Fi** (hoặc cùng hotspot điện thoại). Xem IPv4 của Pi bằng 1 trong các cách:
- Xem danh sách thiết bị đang kết nối trong Hotspot / Router (tên host thường là `raspberrypi`).
- Trên máy Windows, tìm địa chỉ MAC của Pi (`2c-cf-67-...` hoặc `dc-a6-32-...` / `b8-27-eb-...`) qua `arp -a`.
- Hoặc nếu Pi đang nối màn hình, chạy `hostname -I` trên Pi.

Kiểm tra SSH từ PowerShell (`<PI_IP>` là IP thật của Pi, ví dụ `10.56.236.233`):

```powershell
ssh pi@<PI_IP>
```

*(Nếu từng flash lại thẻ nhớ hoặc gặp cảnh báo `REMOTE HOST IDENTIFICATION HAS CHANGED`, chạy `ssh-keygen -R <PI_IP>` rồi `ssh` lại.)*

### Bước 2 — Bật Vision Backend (`:8767`) trên Laptop (Terminal 1)

```powershell
conda activate pbl6_slr
cd <THU_MUC_REPO>\PBL6\slr-m2
python -m deployment.m2.vision_backend --host 0.0.0.0 --port 8767
```

Kiểm tra backend đã nghe đúng cổng (thay `<LAPTOP_IP>` bằng IP Wi-Fi của máy bạn trên `ipconfig`):

```powershell
Invoke-RestMethod -Uri "http://<LAPTOP_IP>:8767/api/vision/health"
```

### Bước 3 — Đồng bộ & khởi chạy toàn bộ dịch vụ trên Pi (Terminal 2)

- **Chạy hàng ngày (Nhanh — `-FastSync`, Pi đã bootstrap sẵn):**
  Script tự dò IP Laptop cùng subnet với `<PI_IP>`, đẩy UI standalone + runtime `slr-m2` + settings Deepgram, khởi động lại SLR (`:8765`), Web UI (`:3100`), Firefox Wayland (`--new-window`), Squeekboard và `WayVNC` (`:5900`):

  ```powershell
  cd <THU_MUC_REPO>\PBL6\slr-m2
  powershell -ExecutionPolicy Bypass -File .\deployment\m2\deploy_to_pi.ps1 -PiHost <PI_IP> -FastSync
  ```

  *(Gợi ý: thêm `-SetupKey` ở lần đầu nếu trên Windows bạn đã có `%USERPROFILE%\.ssh\id_ed25519.pub` để không phải gõ mật khẩu SSH nhiều lần.)*

- **Nếu thẻ SD vừa flash mới hoàn toàn (Chưa cài Python/Torch/Node/TTS):**
  Chạy bản đầy đủ (bỏ `-FastSync`), sau đó bật dịch vụ trên Pi:

  ```powershell
  cd <THU_MUC_REPO>\PBL6\slr-m2
  powershell -ExecutionPolicy Bypass -File .\deployment\m2\deploy_to_pi.ps1 -PiHost <PI_IP>
  ssh pi@<PI_IP> "bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh <LAPTOP_IP>"
  ```

- **Chỉ khởi động lại hoặc tắt dịch vụ trên Pi qua SSH (không sửa code):**

  ```powershell
  ssh pi@<PI_IP> "bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh <LAPTOP_IP>"
  ssh pi@<PI_IP> "bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh --stop"
  ```

Khi chạy xong, kiểm tra cuối log có đủ 4 dòng xác nhận:
`Active BUILD_ID: ...`, `Verified UI button: osk-button`, `Verified OSK: {"visible":false,"supported":true}`, `Verified VNC (5900): :5900`.

---

## 5. Kết Nối TightVNC Viewer & Sử Dụng Không Cần Màn Hình

### 5.1 Kết nối TightVNC Viewer (`:5900`)

1. Cài **TightVNC Viewer** trên Windows (hoặc VNC client tương thích RFB 3.8).
2. Tại ô **Remote Host**, nhập:
   - **`<PI_IP>`** hoặc **`<PI_IP>::5900`** *(lưu ý TightVNC dùng **2 dấu hai chấm `::`** khi ghi kèm số cổng; không dùng 1 dấu `:`)*
3. Bấm **Connect**. Khi hộp thoại hỏi `"This host does not support a compatible encrypted connection. Do you want to connect without encryption?"`, bấm **`Connect without encryption`** (vì `wayvnc` chạy không TLS để tương thích với TightVNC Viewer trên Windows).

> [!TIP]
> **Khi rút hoặc tắt nguồn màn hình HDMI 7":** `labwc` hủy ngõ ra `HDMI-A-1` và chuyển sang màn ảo `NOOP-1`. Script [pi_start.sh](slr-m2/deployment/m2/pi_start.sh) đã cài sẵn vòng lặp **`pbl6-wayvnc-loop`** tự cấu hình `NOOP-1` thành `1024×600` và tự bật lại `wayvnc` sau `~1 giây`. Nếu TightVNC bị văng đúng lúc tắt màn hình, chỉ cần chờ 1–2 giây rồi bấm **Connect** lại.

### 5.2 Dùng trực tiếp trên trình duyệt Laptop / Điện thoại (Không cần VNC)

- **Giao diện đầy đủ:** `http://<PI_IP>:3100/`
- **Chế độ Companion (xem live + lịch sử + bật/tắt phiên ký từ điện thoại):** `http://<PI_IP>:3100/companion`

---

## 6. Kiểm Tra Log Sống, Lưu Ý Phần Cứng & Chạy Bộ Test

### 6.1 Xem log & trạng thái sống trên Pi

- **API JSON từ trình duyệt / PowerShell:**
  - Sức khỏe SLR Edge & trạng thái fallback: `http://<PI_IP>:8765/api/health`
  - Toàn bộ gloss, `segmenter_state`, `capture_fps`, `incomplete_events`, `timing`: `http://<PI_IP>:8765/api/state`
  - Trạng thái cài đặt STT (`hasApiKey`, `selectedMicrophoneId`): `http://<PI_IP>:3100/api/settings`
- **File log text qua SSH trên Pi:**
  ```bash
  tail -n 50 /tmp/pbl6-slr.log
  tail -n 50 /tmp/pbl6-ui.log
  tail -n 50 /tmp/pbl6-kiosk.log
  tail -n 50 /tmp/pbl6-wayvnc.log
  ```

### 6.2 Lưu ý phần cứng đã đúc kết trên Pi 4B

- **Cắm USB Webcam vào cổng USB 3.0 xanh dương** nếu thấy hiện tượng webcam sụt nguồn / mất `/dev/video0`.
- **Giữ `torch==2.3.1` (`whl/cpu`) + Python 3.11 trên Pi 4B:** Các bản `torch>=2.6` ARM64 phát lệnh ARMv8.1+ gây `Illegal instruction (SIGILL)` trên Cortex-A72 (ARMv8.0-A).
- **Trình duyệt trên Pi dùng Firefox Wayland `--new-window`:** Đã chủ động thay thế Chromium 156 (bị lỗi trên Trixie) và không dùng cờ `--kiosk` (vì `--kiosk` che mất bàn phím ảo `Squeekboard`).
- **Tư thế test SLR chuẩn M1:** Giữ vai, khuỷu, cổ tay và hông trong khung hình; buông 2 tay ở hông `0.35s` để từ *"Đưa vai & 2 tay vào khung"* chuyển sang *"Sẵn sàng ký"*.

### 6.3 Chạy kiểm thử đơn vị trước khi sửa/commit code

```powershell
# Bộ test Python M1 + M2.1 + M2.2 split (chạy từ slr-m2\)
conda activate pbl6_slr
cd <THU_MUC_REPO>\PBL6\slr-m2
python -m unittest deployment.m1.test_segmenter deployment.m2.test_m2 deployment.m2.test_m2_split

# Bộ test TypeScript & typecheck UI (chạy từ stt-app\)
cd ..\stt-app
npm run typecheck
node --import tsx --test tests/*.test.ts
```
