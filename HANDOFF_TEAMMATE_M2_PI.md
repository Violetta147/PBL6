# Hướng Dẫn Đồng Đội & AI Agent Tiếp Tục Làm Việc — PBL6 M2.2 (Pi 4B + Laptop Vision Backend + TightVNC)

Tài liệu này đóng gói toàn bộ kiến trúc, quyết định đã chốt, kết quả đo thực tế trên phần cứng **Raspberry Pi 4B**, các vấn đề vừa phát hiện và lộ trình làm tiếp để **bạn cùng nhóm** hoặc **AI Agent của máy khác** đọc là hiểu và làm tiếp được ngay.

> **Tài liệu liên quan trong repo:**
> - Kiến trúc, sơ đồ & các quyết định đã chốt (`1A, 2A, 3A, 4A, 5B`): [docs/PBL6_DECISION_AND_ARCHITECTURE.md](docs/PBL6_DECISION_AND_ARCHITECTURE.md)
> - Runbook kỹ thuật & benchmark Pi 4B chi tiết: [slr-m2/deployment/m2/PI4_M22_RUNBOOK.md](slr-m2/deployment/m2/PI4_M22_RUNBOOK.md)
> - Quy ước & chỉ dẫn cho AI Agent: [AGENTS.md](AGENTS.md) · [stt-app/AGENTS.md](stt-app/AGENTS.md)

---

## 0. Bản Bàn Giao Nhanh Cho AI Agent Tiếp Nhận (Cập nhật 21/11/2026)

### 0.1 Nhánh Git & Quy tắc bất biến
- **Nhánh ổn định gốc:** `origin/main` (commit `902df15d` — Gói 1 tách luồng camera + gói RAM `.pbl6` + Phương án A `utterance_rest = 4.0s`).
- **Nhánh tối ưu Realtime đang làm việc (MỚI NHẤT):** **`origin/perf/streaming-onnx`**
  - Chuyển sang nhánh này khi làm tiếp: `git fetch origin && git checkout perf/streaming-onnx && git pull origin perf/streaming-onnx`.
- **Quy tắc bắt buộc cho AI Agent:**
  1. **Không sửa lõi M1 bất biến:** Giữ nguyên `slr-m2/deployment/m1/` (`segmenter.py`, `frozen-config.json`) và trọng số gốc `slr-m2/models/checkpoints/sl_gcn_bone_07b/07b_bone_seed42/best.pt` (kiểm tra SHA-256 `7934805b...`). Mọi tùy chỉnh runtime đặt ở lớp M2 (`slr-m2/deployment/m2/`).
  2. **Không chạm vào file rời của nhánh khác:** Nếu trong working tree có các file bên `slr-app/MVP/` không liên quan tới `slr-m2`/`stt-app`, tuyệt đối không stage hoặc xóa.
  3. **Xin phép trước khi sửa kiến trúc / ngưỡng:** Không tự ý đổi ngưỡng phân đoạn, đổi nơi chạy model hoặc đổi hành vi UX khi người dùng chưa xác nhận.
  4. **Phong cách phản hồi:** Người dùng có ADHD — luôn trình bày ngắn gọn, chia mục/bảng rõ ràng, trả lời thẳng câu hỏi trước, không viết đoạn văn dài dòng và tuyệt đối không lộ/commit API key, mật khẩu SSH, `.env` hay `settings.json`.

### 0.2 Kiến trúc mới đã triển khai trên `perf/streaming-onnx` (Phương án 1)

```text
[Pi 4B :8765]                                            [Laptop Vision Backend :8767]
Luồng 1: Camera Reader (640x480 -> RAM _ring)
Luồng 2: Pose Consumer ──(1 luồng JPEG 640x480 + ts + seq + run_hands)──► /api/vision/pose-frame
         ▲               • READY/UNKNOWN: run_hands=0 (chỉ chạy Pose)      ├─► Lưu SessionStreamBuffer (20s RAM)
         │               • ONSET/CAPTURING/END_PENDING: run_hands=1        └─► Chạy Pose || Hands song song -> pack_frame()
         └─────────────── Trả 8 khớp Pose + visibility cho M1 Segmenter

Khi hạ tay >= 0.35s (Segmenter chốt [start, end]):
Worker FIFO trên Pi ───(JSON < 100B: {session_id, start, end, target_seq})──► /api/vision/extract-segment (hoặc classify-segment)
  ├─► Laptop đợi seq >= target_seq (<=0.25s), chỉ chạy bù Hands cho ~2-4 frame đệm đầu (-0.30s leading)
  ├─► Kiểm tra crop_rescue trực tiếp trên frame 640x480 có sẵn trong RAM Laptop (không gửi lại video .pbl6!)
  ├─► Chạy nguyên vẹn M1 assemble_frames() + pilot.process() (pair_guard)
  └─► Suy luận SL-GCN 07b bằng ONNX Runtime (slgcn_07b.onnx dùng chung cho cả Pi pi_local & Laptop backend_fallback)
```

1. **Pha 1 — SL-GCN `07b` ONNX Runtime dùng chung (`slgcn_07b.onnx`, `15.8 MB`):**
   - Xuất qua [slr-m2/deployment/m2/export_onnx.py](slr-m2/deployment/m2/export_onnx.py) (`opset=17`, input tĩnh `(1, 150, 28, 8)` `float32`, sai số logit tối đa `1.91e-5` so với `best.pt`, khớp Top-5 `100%`).
   - `BoneClassifier(backend="auto")` trong [slr-m2/deployment/m2/classifier.py](slr-m2/deployment/m2/classifier.py) tự động dùng `onnxruntime` (`ORT_ENABLE_ALL`, tiền xử lý xương thuần NumPy, tiết kiệm RAM vì không cần nạp `best.pt` vào PyTorch khi đã có `.onnx`).
   - **Lưu ý phụ thuộc quan trọng:** Trong [slr-m2/deployment/m2/requirements-vision.txt](slr-m2/deployment/m2/requirements-vision.txt) đã khóa **`protobuf>=4.25.3,<5`** vì `onnx>=1.23` kéo `protobuf 7.x` sẽ làm vỡ `mediapipe==0.10.14` (`AttributeError: 'MessageFactory' object has no attribute 'GetPrototype'`).
2. **Pha 2 — Extract While Signing (Hợp 1 luồng Streaming + RAM Laptop + Smart Gating):**
   - Hợp nhất 2 luồng cũ (`pose-frame 320px` + gửi lại clip `.pbl6`) thành **1 luồng `640×480` duy nhất** qua `/api/vision/pose-frame?session_id=...&ts=...&seq=...&run_hands=0|1`.
   - Giữ đủ 100% vùng đệm M1: **`leading = -0.30s`** (đệm trước lúc nhấc tay, được giữ sẵn trong RAM Laptop lúc `READY` và chỉ chạy bù `Hands` ~`2–4` frame khi chốt từ) và **`trailing = +0.20s`** (đệm sau lúc hạ tay, nằm gọn trong `rest = 0.35s` nên đã chạy xong `Pose || Hands` trên đường đi).
   - Tự động fallback an toàn: Nếu `/api/vision/extract-segment` hoặc `/api/vision/classify-segment` trả `404`/`405`, `SplitClassifierClient.classify_segment` trong [slr-m2/deployment/m2/remote_clients.py](slr-m2/deployment/m2/remote_clients.py) tự rơi về gửi gói RAM `.pbl6` như cũ.
3. **Phương án A (`utterance_rest = 4.0s`) & Sửa UI cảm ứng Pi (`stt-app`):**
   - **`utterance_rest = 4.0s` là logic Backend trên Pi** (`Segmenter` đếm đủ `4.0s` nghỉ → phát sự kiện WebSocket `utterance_ready`); Frontend [stt-app/app/page.tsx](stt-app/app/page.tsx) không tự đếm giờ mà chỉ nghe `utterance_ready` để lưu gộp các từ của câu đó vào khung chat khi bật `autoSaveOnRest`.
   - Ô **Địa chỉ máy chủ SLR** trong [stt-app/src/components/SettingsView.tsx](stt-app/src/components/SettingsView.tsx) đã gắn cố định tiền tố `http://` bên trái (`normalizeSlrBaseUrl`, `stripSlrUrlScheme` trong [stt-app/src/lib/slrSettings.ts](stt-app/src/lib/slrSettings.ts)) để trên bàn phím cảm ứng Pi không cần gõ ký tự `//`.

---

### 0.3 Số liệu đo thực tế đã kiểm chứng (Benchmark & Live trên Pi 4B)

#### A. Benchmark độc lập SL-GCN `07b` trên CPU Raspberry Pi 4B (`aarch64`, 4 threads, `sample_014159_landmarks.npz`)
| Runtime trên Pi 4B | Cold Start | Median | p95 | Kết quả (`014159`) | Đánh giá ngưỡng `1.50s` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PyTorch `2.3.1` (Cũ — khi chạy live)** | `~5.0s` | `4.94s` | `4.94s` | `Dài` (`98.14%`) | Quá ngưỡng → trượt sang `backend_fallback` |
| **ONNX Runtime `1.32.0` FP32 (Mới)** | **`0.764s`** | **`0.741s`** | **`0.760s`** | **`Dài` (`98.14%`)** | **`PASS` (nhanh gấp ~6.6×, không mất độ chính xác)** |

#### B. Benchmark Streaming vs Batch trên Laptop Windows (`014159.mp4`, 59 frames)
- **Thời gian chờ trích xuất sau khi hạ tay:** Giảm từ **`3.960s`** (Batch `.pbl6`) xuống **`0.335s`** (Streaming + chạy bù 8 frame đệm đầu) — **nhanh gấp ~11.8×**.
- **Thời gian xử lý 1 frame trong lúc đang ký:** `34.0ms` (`Pose` khi nghỉ) · `54.9ms` (`Pose || Hands` song song khi đang ký).
- **Kiểm thử tự động:** Python `unittest` (`test_segmenter`, `test_m2`, `test_m2_split`) **`26/26` PASS**; TypeScript `stt-app` **`124/124` PASS**.

#### C. Bằng chứng phiên ký Live trên Pi 4B (`live-91a0955bb5` — 9 từ liên tiếp)
- `streaming_used = true` (`9/9` từ), `inference_backend = "onnx"`, `catchup_hands_frames = 2–4`, **`incomplete_events = 0`**, **`queue_depth = 0`** (hết hoàn toàn hiện tượng dồn hàng đợi!), `capture_fps = 10.0`, `pose_fps = 6.2–7.9`.
- **4 từ không kích hoạt `crop_rescue` đạt tốc độ realtime `< 0.8s` ngay khi hạ tay:**
  - Từ `#3` (`Cái bàn`, 32 frames): `prep = 0.16s`, `onnx = 0.29s` → **Tổng chờ `0.49s`**
  - Từ `#7` (`Bơi lội` **`92.5%`**, 26 frames): `prep = 0.18s`, `onnx = 0.30s` → **Tổng chờ `0.51s`**
  - Từ `#8` (`Bơi lội` `65.9%`, 21 frames): `prep = 0.21s`, `onnx = 0.51s` → **Tổng chờ `0.77s`**
  - Từ `#9` (`Khó` `62.6%`, 12 frames): `prep = 0.13s`, `onnx = 0.51s` → **Tổng chờ `0.69s`**
- **5 từ có kích hoạt `crop_rescue`** (trong đó có `Khăn quàng cổ` **`99.9%`**, `Dài` **`85.5%`**, `Bơi lội` `64.8%`): mất `prep = 1.12s – 1.68s` (tổng chờ `1.57s – 1.94s` trên `backend_fallback`, riêng Từ `#1` trên `pi_local` mất `3.30s`).

---

### 0.4 Ba vấn đề vừa phát hiện từ phiên Live & Việc cần làm tiếp (Cho AI Agent kế tiếp)

> [!IMPORTANT]
> **AI Agent tiếp nhận hãy đọc kỹ 3 mục dưới đây.** Đây là 3 điểm nghẽn thực tế duy nhất còn lại sau khi phân tích log phiên `live-91a0955bb5`. Hãy hỏi người dùng xác nhận trước khi sửa code:

1. **Vấn đề A — `crop_rescue` quét lại toàn bộ clip làm 5/9 từ bị cộng thêm `~1.1–1.5s` (`prep = 1.12s – 1.68s`):**
   - **Nguyên nhân:** Khi clip có `no_hand_fraction > 0.2` và `longest_gap >= 0.4s` (rất dễ xảy ra vì riêng vùng đệm `-0.30s` trước + `+0.20s` sau khi tay hạ ở hông đã chiếm `~5` frame không thấy bàn tay), `_run_crop_rescue_unlocked` trong [slr-m2/deployment/m2/classifier.py](slr-m2/deployment/m2/classifier.py) hiện chạy `crop_hands.process()` trên **tất cả `24–36` frame** của đoạn ký.
   - **Hướng sửa:** Chỉ chạy `crop_hands.process()` trên những frame thực sự thiếu tay (hoặc tận dụng kết quả đã có cho những frame bắt đủ 2 tay) trước khi đưa vào `rescue_candidates.assemble()`, giúp kéo cả 5 từ này về mức `~0.5–0.9s`.

2. **Vấn đề B — Tranh chấp CPU trên Pi 4B khi chạy live làm ONNX Từ `#1` tăng từ `0.74s` lên `2.12s` (rồi tự trượt sang Laptop Fallback):**
   - **Nguyên nhân:** Khi benchmark độc lập, CPU Pi 4B rảnh nên ONNX chạy `0.741s`. Khi chạy live, 4 nhân Cortex-A72 đồng thời gánh Firefox Wayland + stream MJPEG `/video_feed` (`20 FPS` trong [slr-m2/deployment/m2/server.py](slr-m2/deployment/m2/server.py)) + `wayvnc` (`30 FPS`) + đọc/nén Camera + `onnxruntime` (`4` threads) gây tranh chấp luồng.
   - **Hướng sửa:** Giảm tần suất `/video_feed` trong `server.py` từ `20 FPS` (`sleep 0.05`) xuống `~10–12 FPS` (`sleep 0.09`), đặt mặc định `onnx_threads = 3` trên Pi để nhường 1 nhân cho Camera/UI, và dùng `--no-vnc` khi demo trực tiếp trên màn hình 7".

3. **Vấn đề C — Bộ đếm `utterance_rest = 4.0s` bị hủy khi người dùng bước ra ngoài / rớt 1 frame khớp (`arms: [null, null]`):**
   - **Nguyên nhân:** Trong [slr-m2/deployment/m1/segmenter.py](slr-m2/deployment/m1/segmenter.py), để phát `utterance_end`, người ký phải đứng nguyên trong khung với đủ 8 khớp (`visibility >= 0.5`) và hạ tay liên tục suốt `4.0s`. Chỉ cần 1 frame bị `None in arms` (ví dụ nghiêng người nhìn màn hình hoặc bước ra khỏi camera), `Segmenter` chuyển về `UNKNOWN` và xóa `rest_since = None`. Hệ quả là trong phiên `live-91a0955bb5`, dù nghỉ `19.8s` và `88.5s` giữa các lượt ký, cả 9 từ vẫn dính chung trong `utterance_id = "0"` và chưa chốt câu (`utterances = []`).
   - **Hướng sửa (ở lớp M2 `pipeline.py`, KHÔNG sửa `deployment/m1/segmenter.py`):** Trong `LiveSessionManager`, theo dõi thời gian trôi qua kể từ segment hoàn chỉnh cuối cùng; nếu sau `>= 4.0s` không có cử động tay `active` nào (dù đang ở `READY` hay `UNKNOWN` do bước ra ngoài khung), lớp M2 chủ động chốt `utterance_ready` cho câu hiện tại và đồng bộ `utterance_id` mới.

#### Hàng đợi công việc kế tiếp (Next Steps)
- [ ] **Bước 5.6:** Xin người dùng duyệt và sửa 3 điểm A, B, C ở trên trên nhánh `perf/streaming-onnx` → deploy `-FastSync` test lại trên Pi 4B → merge `perf/streaming-onnx` vào `main`.
- [ ] **Bước 6 (Giai đoạn cuối — M3 LLM + IoT ThingsBoard tối giản):**
  - Khi nhận `utterance_ready`, gọi 1 lần **LLM API (JSON Structured Output)** trả về `revised_glosses` + `vietnamese_sentence` (timeout `~3–4s` thì giữ nguyên `raw_glosses`, không chặn câu tiếp theo).
  - Đẩy telemetry tối giản (~50 dòng code: `online`, `session_count`, `gloss_count`, `latency_ms`) lên **ThingsBoard**.
- [ ] **Bước 7:** Kiểm thử tích hợp toàn trình (SLR + STT + Companion + ThingsBoard) và review độc lập.
- [ ] **Bước 8 (Tùy chọn sau MVP):** Thử nghiệm nhánh VLM trên 20 clip VSL400 low-confidence.

---

## 1. Tổng Quan Kiến Trúc M2.2 Split (`1A, 2A, 3A, 4A, 5B`)

```text
USB Webcam + Mic (Pi 4B)
   ├──► Video Capture + M1 Segmenter + SL-GCN 07b ONNX (slr-m2 :8765) ◄── LAN HTTP :8767 ──► Laptop Vision Backend (Streaming MediaPipe + ONNX Fallback)
   ├──► 400 Offline MP3 TTS (/api/tts/{id}.mp3, slr-app/MVP/local_data/tts/0..399.mp3)
   ├──► Unified Web UI stt-app (:3100 trên Pi & :3100/companion trên điện thoại/laptop LAN)
   └──► WayVNC (:5900, vòng lặp tự hồi pbl6-wayvnc-loop trên Firefox Wayland --new-window + Squeekboard)
```

- **Laptop LAN (`vision_backend.py`, cổng `8767`):** Nhận luồng frame `640×480` (`/api/vision/pose-frame`), chạy `Pose` (và song song `Hands` khi tay chuyển động), giữ bộ đệm RAM 20s `SessionStreamBuffer`, hoàn tất chuẩn hóa đoạn ký từ RAM (`/api/vision/extract-segment`), và tự làm dự phòng SL-GCN ONNX (`/api/vision/classify-segment`) nếu Pi chạy chậm hơn ngưỡng `1.50s` `2` lần liên tiếp.
- **Raspberry Pi 4B 8GB (Debian 13 Trixie `aarch64`):** Chạy SLR Edge (`:8765`), Next.js standalone `stt-app` (`:3100`), Firefox Wayland (`--new-window` chromeless để không đè bàn phím ảo `Squeekboard`), `fcitx5`, và `wayvnc` (`:5900`).

---

## 2. Cài Đặt Trên Máy Tính Của Bạn (Lần Đầu)

> Không đưa file `.env`, Deepgram API key hay mật khẩu Pi lên GitHub — hãy nhắn riêng trong nhóm để lấy **mật khẩu tài khoản `pi`** và **Deepgram API key**.

### 2.1 Clone repo, chuyển sang nhánh `perf/streaming-onnx` & tạo môi trường Python (`pbl6_slr`)

```powershell
git clone https://github.com/Violetta147/PBL6.git
cd PBL6
git checkout perf/streaming-onnx
```

*(Nếu đã clone trước đó: `git fetch origin && git checkout perf/streaming-onnx && git pull origin perf/streaming-onnx`.)*

Dùng Conda (hoặc `venv`) với **Python 3.11**:

```powershell
conda create -n pbl6_slr python=3.11 -y
conda activate pbl6_slr
cd slr-m2
pip install -r .\deployment\m2\requirements-vision.txt
```

*(File `requirements-vision.txt` đã khóa đúng `mediapipe==0.10.14`, `protobuf>=4.25.3,<5`, `numpy==1.26.4`, `opencv-contrib-python==4.11.0.86`, `onnxruntime>=1.19.0`, `fastapi`, `uvicorn`, `httpx`, `websockets` và `torch>=2.5.1`.)*

### 2.2 Build bản standalone của `stt-app` (Node.js >= 22)

Script `deploy_to_pi.ps1` đóng gói từ `stt-app\.next\standalone\server.js`, nên **phải build `stt-app` trước ít nhất 1 lần** (và build lại mỗi khi sửa code UI):

```powershell
cd ..\stt-app
npm ci
npm run build
npm run curate:server
```

### 2.3 Mở Windows Firewall cổng `8767`

Mở **PowerShell bằng quyền Administrator** (*Run as Administrator*) trên Windows và chạy 1 lần:

```powershell
netsh advfirewall firewall delete rule name="PBL6 Vision Backend 8767" 2>$null; netsh advfirewall firewall add rule name="PBL6 Vision Backend 8767" dir=in action=allow protocol=TCP localport=8767 profile=any
```

*(Dùng `profile=any` để dù mang laptop sang Wi-Fi trường/quán/hotspot chế độ Public thì Pi vẫn gọi được vào cổng `8767`.)*

### 2.4 Cấu hình Deepgram API Key

- Khi chạy `deploy_to_pi.ps1`, nếu trên Windows có sẵn `%LOCALAPPDATA%\PBL6-STT\settings.json`, script sẽ tự đẩy sang `~/.config/pbl6-stt/settings.json` trên Pi (ghi `selectedMicrophoneId=default`).
- Hoặc bạn mở Web UI trên Pi/VNC → bấm **Cài đặt** → **Giọng nói thành chữ** → dán **Deepgram API key** → **Lưu**.

---

## 3. Quy Trình Bật Hệ Thống Hàng Ngày (SSH, Vision Backend, Deploy Lên Pi)

### Bước 1 — Tìm IP của Raspberry Pi trên mạng hiện tại

Đảm bảo Laptop và Pi dùng **chung một mạng Wi-Fi** (hoặc cùng hotspot điện thoại). Xem IPv4 của Pi bằng 1 trong các cách:
- Xem danh sách thiết bị đang kết nối trong Hotspot / Router (tên host thường là `raspberrypi`).
- Trên máy Windows, tìm địa chỉ MAC của Pi (`2c-cf-67-...` hoặc `dc-a6-32-...` / `b8-27-eb-...`) qua `arp -a`.
- Hoặc nếu Pi đang nối màn hình, chạy `hostname -I` trên Pi.

Kiểm tra SSH từ PowerShell (`<PI_IP>` là IP thật của Pi):

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

*(Kết quả trả về phải có `"status": "ok"`, `"fallback_classifier_loaded": true` và `"runtime_backend": "onnx"`.)*

### Bước 3 — Đồng bộ & khởi chạy toàn bộ dịch vụ trên Pi (Terminal 2)

- **Chạy hàng ngày (Nhanh — `-FastSync`, Pi đã bootstrap sẵn):**
  Script tự dò IP Laptop cùng dải `/24` hoặc `/16` với `<PI_IP>` (hoặc truyền tường minh `-LaptopIp <LAPTOP_IP>`), đẩy UI standalone + runtime `slr-m2` + `slgcn_07b.onnx` + cài `onnxruntime` + settings Deepgram, rồi khởi động lại SLR (`:8765`), Web UI (`:3100`), Firefox Wayland (`--new-window`), Squeekboard và `WayVNC` (`:5900`):

  ```powershell
  cd <THU_MUC_REPO>\PBL6\slr-m2
  powershell -ExecutionPolicy Bypass -File .\deployment\m2\deploy_to_pi.ps1 -PiHost <PI_IP> -FastSync
  ```

  *(Gợi ý: thêm `-SetupKey` ở lần đầu nếu trên Windows bạn đã có `%USERPROFILE%\.ssh\id_ed25519.pub` để không phải gõ mật khẩu SSH nhiều lần.)*

- **Nếu thẻ SD vừa flash mới hoàn toàn (Chưa cài Python/Torch/ONNX/Node/TTS):**
  Chạy bản đầy đủ (bỏ `-FastSync`), sau đó bật dịch vụ trên Pi:

  ```powershell
  cd <THU_MUC_REPO>\PBL6\slr-m2
  powershell -ExecutionPolicy Bypass -File .\deployment\m2\deploy_to_pi.ps1 -PiHost <PI_IP>
  ssh pi@<PI_IP> "bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh <LAPTOP_IP>"
  ```

- **Chỉ khởi động lại hoặc tắt dịch vụ trên Pi qua SSH (không sửa code):**

  ```powershell
  ssh pi@<PI_IP> "bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh <LAPTOP_IP>"
  ssh pi@<PI_IP> "bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh <LAPTOP_IP> --no-vnc"
  ssh pi@<PI_IP> "bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh --stop"
  ```

Khi chạy xong, kiểm tra cuối log có đủ 4 dòng xác nhận:
`Active BUILD_ID: ...`, `Verified UI button: osk-button`, `Verified OSK: {"visible":false,"supported":true}`, `Verified VNC (5900): :5900`.

---

## 4. Kết Nối TightVNC Viewer & Sử Dụng Không Cần Màn Hình

### 4.1 Kết nối TightVNC Viewer (`:5900`)

1. Cài **TightVNC Viewer** trên Windows (hoặc VNC client tương thích RFB 3.8).
2. Tại ô **Remote Host**, nhập:
   - **`<PI_IP>`** hoặc **`<PI_IP>::5900`** *(lưu ý TightVNC dùng **2 dấu hai chấm `::`** khi ghi kèm số cổng; không dùng 1 dấu `:`)*
3. Bấm **Connect**. Khi hộp thoại hỏi `"This host does not support a compatible encrypted connection. Do you want to connect without encryption?"`, bấm **`Connect without encryption`** (vì `wayvnc` chạy không TLS để tương thích với TightVNC Viewer trên Windows).

> [!TIP]
> **Khi rút hoặc tắt nguồn màn hình HDMI 7":** `labwc` hủy ngõ ra `HDMI-A-1` và chuyển sang màn ảo `NOOP-1`. Script [slr-m2/deployment/m2/pi_start.sh](slr-m2/deployment/m2/pi_start.sh) đã cài sẵn vòng lặp **`pbl6-wayvnc-loop`** tự cấu hình `NOOP-1` thành `1024×600` và tự bật lại `wayvnc` sau `~1 giây`. Nếu TightVNC bị văng đúng lúc tắt màn hình, chỉ cần chờ 1–2 giây rồi bấm **Connect** lại.

### 4.2 Dùng trực tiếp trên trình duyệt Laptop / Điện thoại (Không cần VNC)

- **Giao diện đầy đủ:** `http://<PI_IP>:3100/`
- **Chế độ Companion (xem live + lịch sử + bật/tắt phiên ký từ điện thoại):** `http://<PI_IP>:3100/companion`

---

## 5. Kiểm Tra Log Sống, Lưu Ý Phần Cứng & Chạy Bộ Test

### 5.1 Xem log & trạng thái sống trên Pi

- **API JSON từ trình duyệt / PowerShell:**
  - Sức khỏe SLR Edge, `runtime_backend` (`onnx`) & trạng thái fallback: `http://<PI_IP>:8765/api/health`
  - Toàn bộ gloss, `segmenter_state`, `capture_fps`, `pose_fps`, `incomplete_events`, `timing` (`streaming_used`, `catchup_hands_frames`, `inference_backend`): `http://<PI_IP>:8765/api/state`
  - Trạng thái cài đặt STT (`hasApiKey`, `selectedMicrophoneId`): `http://<PI_IP>:3100/api/settings`
- **File log text qua SSH trên Pi:**
  ```bash
  tail -n 50 /tmp/pbl6-slr.log
  tail -n 50 /tmp/pbl6-ui.log
  tail -n 50 /tmp/pbl6-kiosk.log
  tail -n 50 /tmp/pbl6-wayvnc.log
  ```

### 5.2 Lưu ý phần cứng đã đúc kết trên Pi 4B

- **Cắm USB Webcam vào cổng USB 3.0 xanh dương** nếu thấy hiện tượng webcam sụt nguồn / mất `/dev/video0`.
- **Giữ `torch==2.3.1` (`whl/cpu`) + `onnxruntime>=1.19.0` + Python 3.11 trên Pi 4B:** Các bản `torch>=2.6` ARM64 phát lệnh ARMv8.1+ gây `Illegal instruction (SIGILL)` trên Cortex-A72 (ARMv8.0-A).
- **Trình duyệt trên Pi dùng Firefox Wayland `--new-window`:** Đã chủ động thay thế Chromium 156 (bị lỗi trên Trixie) và không dùng cờ `--kiosk` (vì `--kiosk` che mất bàn phím ảo `Squeekboard`).
- **Tư thế test SLR chuẩn M1:** Giữ vai, khuỷu, cổ tay và hông trong khung hình; buông 2 tay ở hông `0.35s` để từ *"Đưa vai & 2 tay vào khung"* chuyển sang *"Sẵn sàng ký"*.

### 5.3 Chạy kiểm thử đơn vị & benchmark trước khi sửa/commit code

```powershell
# Bộ test Python M1 + M2.1 + M2.2 split + Streaming + ONNX (chạy từ slr-m2\ — 26/26 tests)
conda activate pbl6_slr
cd <THU_MUC_REPO>\PBL6\slr-m2
python -m unittest -v deployment.m1.test_segmenter deployment.m2.test_m2 deployment.m2.test_m2_split

# Benchmark ONNX vs PyTorch (trên Laptop hoặc trên Pi qua SSH)
python -m deployment.m2.benchmark_pi_gcn --npz outputs/sample_014159_landmarks.npz --backend onnx --runs 5 --warmup 1 --threads 4

# Bộ test TypeScript & typecheck UI (chạy từ stt-app\ — 124/124 tests)
cd ..\stt-app
npm run typecheck
node --import tsx --test tests/*.test.ts
```
