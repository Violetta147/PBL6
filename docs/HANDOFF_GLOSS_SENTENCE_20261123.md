# Bàn Giao Công Việc Sau Phiên GPT — Nhánh `codex/gloss-sentence-flow` (23/11/2026)

> **Mục đích:** Tóm tắt đầy đủ toàn bộ thay đổi, kết quả đo, trạng thái Pi 4B và danh sách việc còn mở kể từ khi tiếp nhận phiên GPT (lúc **12:40 ngày 23/11/2026**) để người tiếp theo `git pull` / nhận nhánh và làm tiếp ngay mà không mất ngữ cảnh.

---

## 1. Nhánh Git & Quy Tắc Repo Hiện Tại

- **Nhánh đang checkout:** `codex/gloss-sentence-flow` (tách từ `perf/streaming-onnx` tại `cd6d0917`, `origin/main` ở `902df15d`).
- **Trạng thái Git lúc bàn giao:** **Đã commit (3 commit tách theo `slr-m2`, `stt-app`, `docs`) và đã push lên `origin/codex/gloss-sentence-flow`** *(chưa merge về `main`; 3 file `slr-app/MVP/` không liên quan được giữ nguyên unstaged)*.
- **Tuyệt đối không sửa / không stage:**
  - `slr-m2/deployment/m1/` và checkpoint `slr-m2/models/checkpoints/sl_gcn_bone_07b/07b_bone_seed42/best.pt`
  - Cấu hình OS xoay màn hình & cảm ứng trên Pi (`~/.config/labwc/rc.xml`, `~/.config/labwc/rcgreeter.xml`, `~/.config/kanshi/config`)
  - 3 file tồn sẵn từ trước trong `slr-app/MVP/`:
    - `slr-app/MVP/segmentation/compare_short_gap_merge.py`
    - `slr-app/MVP/deployment/slgcn_feature_trial/reference.rar`
    - `slr-app/MVP/diagnostics/diagnose_remaining_thanks_errors.py`

---

## 2. Toàn Bộ Việc Đã Làm Từ Lúc Tiếp Nhận Phiên GPT

### A. Sửa lỗi Firefox Kiosk & Bàn phím ảo (`squeekboard`) trên Pi
1. **Hết bị che bàn phím ảo (`labwc #2926`):**
   - `slr-app/MVP/outputs/deploy_20261123_ui/activate.sh` và `rollback.sh`: đổi `--fullscreen-kiosk` → **`--windowed`** (tức `firefox --new-window`, đã ẩn `#TabsToolbar`, `#nav-bar`, `#PersonalToolbar` qua `userChrome.css`).
   - `slr-m2/deployment/m2/pi_start.sh`: thêm ghi chú cảnh báo không dùng `--fullscreen-kiosk` dưới `labwc`.
2. **Hết khoảng trống `210px` trên bàn phím ảo màn dọc (`768×1024`):**
   - `stt-app/app/page.tsx`: thêm `baseViewportHeightRef` vào `computeOskCeiling` (`vh <= 420 || (baseVh > 0 && baseVh - vh >= 120)`) để nhận diện compositor đã co viewport trên cả màn ngang lẫn màn dọc.
   - Đã kiểm chứng trực tiếp bằng `grim` trên Pi (`keyboard-windowed-closed.png`, `keyboard-windowed-open.png`).

### B. Sửa kẹt tab đăng nhập OAuth ChatGPT (tắt OpenAI = tắt app PBL6)
- `stt-app/src/components/SentenceServiceSettings.tsx`: mở trang đăng nhập ChatGPT và link quản lý hạn mức bằng **cửa sổ popup riêng** (`popup=yes,width=640,height=760`) + tự đóng popup khi `readStatus` báo hết `pending` hoặc khi bấm hủy.
- `stt-app/src/server/chatgptConnection.ts`: endpoint `/auth/callback` trả về HTML tiếng Việt có nút lớn **"Quay lại ứng dụng PBL6"** và tự gọi `window.close()` khi hoàn tất (fallback về `http://127.0.0.1:3100/` nếu lỡ mở thành tab đơn).
- `slr-m2/deployment/m2/pi_start.sh`: thêm `browser.link.open_newwindow=3`, `browser.link.open_newwindow.restriction=2`, `dom.allow_scripts_to_close_windows=true` vào `user.js`.
- `stt-app/tests/chatgpt-connection.test.ts`: cập nhật test kiểm tra `text/html` và script `window.close()` trong callback.

### C. Bố cục dọc Cách 2 & UX Cài đặt Ký hiệu / Model
- **Bố cục dọc Cách 2 (`stt-app/app/page.tsx`):** đổi `<ConversationArea className="min-[900px]:landscape:-order-1" />` → `className="-order-1"` để cả màn dọc lẫn ngang đều đưa vùng hội thoại lên trên, giúp thẻ **`ĐANG KÝ TRỰC TIẾP`** áp sát ngay trên ô soạn tin nhắn (đã kiểm chứng qua ảnh `pi-screen-layout-v2.png`).
- **Model đã lưu & Tự động lưu:**
  - `stt-app/src/components/SentenceServiceSettings.tsx`: luôn render `<option value={active.model}>{active.model} (đã lưu)</option>` khi `/models` chưa tải xong và hiện thông báo xanh **`✓ Đã lưu model: ...`** khi chọn thành công.
  - `stt-app/src/components/SettingsView.tsx`: thêm nhãn trạng thái **`✓ Tự động lưu`** / **`✓ Đã lưu thay đổi`** ở đầu tab **Ký hiệu** để người dùng biết các nút gạt/IP/camera tự lưu ngay lập tức.

### D. Ổn định luồng Camera ↔ LAN Vision Backend (`pipeline.py`, `remote_clients.py`, `page.tsx`, `slrClient.ts`)
1. **Hết báo giả Firewall & treo dòng đỏ trên UI:**
   - `slr-m2/deployment/m2/remote_clients.py`: tăng `RemotePoseClient` `timeout` từ `2.5s` → **`4.0s`** (giữ nguyên băng thông `max_width=640`, `jpeg_quality=75` theo yêu cầu).
   - `slr-m2/deployment/m2/pipeline.py`: đếm `_consecutive_pose_errors`, chỉ báo lỗi `"Vision Backend"` khi lỗi **3 frame liên tiếp** (phân biệt *"phản hồi chậm"* với *"không kết nối được cổng 8767"*); tự xóa `last_error` và phát sự kiện WebSocket `error_cleared` khi pose khôi phục.
   - `stt-app/src/lib/slrClient.ts` & `stt-app/app/page.tsx`: xử lý `snapshot.last_error`, `error_cleared` và tự dọn cảnh báo `Vision Backend` khi nhận lại gói `status` bình thường.
2. **Gỡ khóa `cap.read()` và dồn 32 frame cũ (fix tụt `0.5 FPS`):**
   - Nguyên nhân gốc nằm từ commit `ca22a815` (`MAX_PENDING_POSE_FRAMES = 32` kèm `wait_for` khóa luồng đọc camera). Khi Wi-Fi trễ (`104–410 ms`), hàng đợi dồn 32 frame cũ kéo `capture_fps` tụt xuống `0.5 FPS`.
   - `slr-m2/deployment/m2/pipeline.py`: đặt **`MAX_PENDING_POSE_FRAMES = 1`**, bỏ `wait_for` chặn trước `cap.read()`, chỉ giữ frame mới nhất (`popleft` frame cũ chưa kịp gửi) để preview và ring buffer không bao giờ bị kéo chậm bởi mạng.
   - `slr-m2/deployment/m2/test_m2_split.py`: cập nhật 2 test (`test_slow_pose_drops_stale_frames_and_discards_stale_response`, `test_slow_pose_never_blocks_camera_reads`) và thêm `test_transient_pose_errors_require_3_frames_and_auto_clear`.

### E. Thiết lập SSH Key & Tài liệu Troubleshooting
- Đã nạp public key máy Windows (`~/.ssh/id_ed25519.pub`) vào `~/.ssh/authorized_keys` trên Pi (phân quyền `go-w ~`, `700 ~/.ssh`, `600 ~/.ssh/authorized_keys`) để SSH/SCP không cần nhập mật khẩu.
- Tạo [docs/troubleshooting/PI_KIOSK_KEYBOARD.md](troubleshooting/PI_KIOSK_KEYBOARD.md) và cập nhật [slr-app/MVP/plans/11_SENTENCE_APP_TRIAL.md](../slr-app/MVP/plans/11_SENTENCE_APP_TRIAL.md).

---

## 3. Kiểm Chứng Đã Chạy Trước Khi Bàn Giao

| Kiểm tra | Kết quả | Thời điểm / Ghi chú |
| :--- | :--- | :--- |
| **Python SLR (`deployment.m1.test_segmenter`, `m2.test_m2`, `m2.test_m2_split`)** | **35/35 OK** (`118.4s`) | Sau lần sửa cuối `pipeline.py` (không chặn `cap.read()`) |
| **`stt-app` `npm run typecheck`** | **PASS** (0 lỗi) | Sau lần sửa cuối UI (`ucY6PlkNulAS7oY_WPW4f`) |
| **`stt-app` Node unit tests** (`chatgpt-connection`, `sign-sentence`, `routes`, `slr-integration`) | **27/27 PASS** | Sau lần sửa cuối UI |
| **`stt-app` `npm run build` & `npm run curate:server`** | **PASS** | Build ID `ucY6PlkNulAS7oY_WPW4f`, đã đóng gói `ui.tar` |
| **Pi `192.168.1.8` dịch vụ & `display-before.sha256`** | **`active` / 3/3 OK** | `pbl6-ui.service` `active`, `:3100` và `:8765` OK, cấu hình xoay/cảm ứng nguyên vẹn |
| **Đo FPS camera live trên Pi sau sửa `pipeline.py`** | **`capture_fps: 15.3`, `pose_fps: 10.3`** | `queue_depth: 0`, `last_error: null` (trước khi sửa là `0.5 / 0.4 FPS`) |
| **Ảnh `grim` màn dọc Cách 2 trên Pi** | **Đạt** | `pi-screen-layout-v2.png` + `keyboard-windowed-open.png` sạch lỗi, đúng bố cục |

---

## 4. Hướng Dẫn Chạy Nhanh Cho Người Tiếp Nhận

### Trên Laptop Windows (Vision Backend `:8767`)
```powershell
cd "<PBL6>\slr-m2"
python -u -m deployment.m2.vision_backend --host 0.0.0.0 --port 8767 --no-fallback-classifier
```
*(Bỏ `--no-fallback-classifier` nếu cần bật dự phòng SL-GCN trên Laptop.)*

### Trên Raspberry Pi (`<PI_IP>`, ví dụ `192.168.1.8`)
```bash
bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh <LAPTOP_IP> --mode pi-split --threshold 0 --utterance-rest 4.0 --windowed
```

### Chụp màn hình Pi nhanh qua SSH để kiểm tra UI
```powershell
ssh pi@<PI_IP> "XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 grim /tmp/pi-screen.png"
scp pi@<PI_IP>:/tmp/pi-screen.png "<DEST>\pi-screen.png"
```

### Lệnh test trước khi sửa tiếp
```powershell
cd "<PBL6>\slr-m2"
python -m unittest -v deployment.m1.test_segmenter deployment.m2.test_m2 deployment.m2.test_m2_split

cd "<PBL6>\stt-app"
npm run typecheck
node --import tsx --test tests/chatgpt-connection.test.ts tests/sign-sentence.test.ts tests/routes.test.ts tests/slr-integration.test.ts
```

---

## 5. Danh Sách Việc & Lỗi Còn Mở Cần Xử Lý Tiếp (Ưu Tiên Từ Cao Đến Thấp)

1. **[MỞ — ƯU TIÊN CAO] Lỗi chọn model ChatGPT trên giao diện Pi báo lỗi:**
   - **Triệu chứng người dùng báo (14:06):** Chọn model ở giao diện báo lỗi không lưu được (lưu ý: trước đó trên server Pi vẫn đang lưu sẵn `active: true, connected: true, model: "gpt-6-astra"`, `/tmp/pbl6-ui.log` chưa ghi log exception do lỗi trả HTTP 4xx/5xx dạng JSON).
   - **Điểm kiểm tra đầu tiên cho người sau:**
     - `ChatGptConnection.select(id, model)` trong `stt-app/src/server/chatgptConnection.ts` hiện gọi lại `await this.models(id)` lên OpenAI mỗi lần đổi model — nếu mạng Pi lúc đó vừa rớt Wi-Fi hoặc token cần refresh, `select` sẽ fail với `401/502` dù danh sách model đang hiển thị sẵn trên UI.
     - Kiểm tra luôn trình duyệt trên Pi đang mở đúng `http://127.0.0.1:3100/` hay IP LAN (nếu mở qua LAN, `requireLocalOrigin` trả `403 local_only` và nút bị disable); mở DevTools Network / kiểm tra phản hồi `POST /api/chatgpt` trực tiếp trên Pi.
2. **[MỞ] Test End-to-End luồng ký thật trên người thật:**
   - Chưa test đủ vòng khép kín trên Pi: ký tay tạo gloss (có gloss cam `low_confidence`) → sửa gloss → bấm **Kết thúc câu** (hoặc chờ `utterance_rest=4.0s`) → gọi **GPT tạo câu tiếng Việt** → sửa/bấm **Gửi câu** → kiểm tra phát loa thật trên Pi + đồng bộ sang `/companion`.
   - Chưa bấm thử luồng popup OAuth ChatGPT bản mới (`popup=yes` + auto `window.close()`) trực tiếp trên tay.
3. **[HẠ TẦNG] Wi-Fi 2.4GHz không ổn định:**
   - Mạng 2.4GHz đang dùng từng ghi nhận trễ `104–410ms` và rớt ARP (`Destination host unreachable`). Khuyến nghị test/demo bằng Wi-Fi **5GHz** hoặc **Mobile Hotspot phát trực tiếp từ Laptop** để giữ `pose_fps` ổn định `>= 10 FPS`.
4. **[GIT & BUILD] Tổ chức commit & lỗi test đóng gói Electron cũ:**
   - Các thay đổi của đợt gloss-to-sentence, Pi OSK/Firefox popup, Vision Backend hysteresis và docs bàn giao đã được gom thành 3 commit gọn trên nhánh `codex/gloss-sentence-flow` và push lên `origin/codex/gloss-sentence-flow` (không chạm 3 file `slr-app/MVP/` tồn sẵn, không đưa file bí mật hay build artifact tạm).
   - Bộ test cũ `npm test` vẫn còn lỗi kiểm tra đường dẫn đóng gói Electron (đã có từ `main`: test tìm `.next` ở đường dẫn cũ thay vì `resources/server/standalone`) — cần xử lý trước khi merge về `main`.
5. **[ĐỂ SAU MVP] Tối ưu tốc độ SL-GCN / Telemetry (từ `perf/streaming-onnx`):**
   - Tối ưu `crop_rescue` chỉ chạy trên các frame thiếu tay, giảm tranh chấp CPU trên Pi (`onnx_threads=3`, throttle `/video_feed` 10 FPS), cân nhắc đóng lượt ở M2 khi rời khung hình quá `4.0s`, đo INT8 ONNX khi có cache `val`, và tích hợp ThingsBoard telemetry tối giản (~50 dòng).
