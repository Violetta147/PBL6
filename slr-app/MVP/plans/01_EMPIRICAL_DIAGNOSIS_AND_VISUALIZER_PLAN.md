# Kế Hoạch Mô-đun 01: Chẩn Đoán Thực Nghiệm & Trực Quan Hóa Đa Hệ Tọa Độ (MediaPipe + SL-GCN Adapter)

## 1. Mục Tiêu Kỹ Thuật
Giải quyết vấn đề: Pipeline hiện tại tách rời hệ tọa độ thân người (`upper_body` chuẩn hóa theo vai) và hệ tọa độ nội bộ bàn tay (`left_hand_local`, `right_hand_local` chuẩn hóa theo cổ tay $\to$ khớp MCP ngón giữa), đồng thời mặc định tắt `raw_coordinates` (`"raw_coordinates": false` trong `extraction_config.json`). Do đó, cần một công cụ chẩn đoán độc lập trong `slr-app/MVP/diagnostics/` để:
1. Trích xuất đồng thời **tọa độ ảnh gốc (`save_raw=True` trong RAM)** và **tọa độ sau chuẩn hóa/sửa lỗi (`slgcn_xy_adapter.py`)** mà không chạm vào bất kỳ file nào trong `deployment/`.
2. Xuất video trực quan hóa 4 ô (Quad-View Diagnostic Video) giúp quan sát đồng thời:
   - **Ô 1 (Top-Left) — Raw Video Overlay**: Vẽ trực tiếp 7 điểm Pose, 21 điểm mỗi bàn tay và **vòng tròn bán kính `proximity_threshold = 0.15`** quanh 2 cổ tay Pose (`landmark 15, 16`) trên khung hình gốc để thấy ngay vì sao `handedness.py` chấp nhận hay từ chối bàn tay.
   - **Ô 2 (Top-Right) — Reconstructed 27-Joint Graph (Body Frame)**: Vẽ đồ thị 27 khớp xương (`sign_27.py` edges) sau khi ghép tay vào hệ tọa độ vai (`common = hand_local * hand_scales + palm_body[:, 0:1]`), tô màu đỏ các khớp bị `mask_rejected` hoặc `geometry_blocked`.
   - **Ô 3 (Bottom-Left) — Dual Local Hands (`left_hand_local` & `right_hand_local`)**: Vẽ riêng 2 bàn tay trong hệ quy chiếu cổ tay để kiểm tra hình dạng ngón tay (handshape) có mượt và tự nhiên không.
   - **Ô 4 (Bottom-Right) — Temporal Telemetry Strip**: Biểu đồ chạy theo thời gian thực từ frame $0 \to T$: trạng thái phát hiện `[Pose, L_Hand_Det, L_Hand_Valid, R_Hand_Det, R_Hand_Valid]`, khoảng cách cổ tay so với ngưỡng `1.0`, và vận tốc cổ tay $v_t$.

---

## 2. Phạm Vi File & Ràng Buộc Bảo Vệ (Harness Layer 1 & Layer 2)
- **File được phép tạo mới**:
  - `slr-app/MVP/diagnostics/__init__.py`
  - `slr-app/MVP/diagnostics/inspect_clip_qc.py`
  - `slr-app/MVP/diagnostics/render_diagnostic_video.py`
  - `slr-app/MVP/diagnostics/test_diagnostics.py`
- **File CẤM chỉnh sửa**:
  - Toàn bộ `slr-app/MVP/deployment/**` (giữ nguyên SHA-256).

---

## 3. Đặc Tả Triển Khai Chi Tiết

### 3.1. Kịch bản `diagnostics/inspect_clip_qc.py`
- **Chức năng**: Nhận đường dẫn 1 file video (`.mp4` hoặc `.avi`) hoặc quét toàn bộ `local_data/webcam_*.avi`, chạy `extract_video(video, cfg_with_raw)` với bản sao cấu hình trong bộ nhớ có `cfg["feature_groups"]["raw_coordinates"] = True`, sau đó chạy `slgcn_xy_adapter.convert()`.
- **Các chỉ số chẩn đoán xuất ra bảng Markdown & JSON**:
  1. `fps_header` vs `decoded_frames` (cảnh báo nếu $< 24\text{ FPS}$ trong 4s, tức $< 96$ frames).
  2. `pose_detected_pct`: Tỷ lệ frame có Pose.
  3. `left_hand_detected_pct` vs `left_hand_valid_pct`: Độ chênh lệch giữa hai số này chỉ ra chính xác bao nhiêu % frame MediaPipe Hands **có nhìn thấy tay** nhưng bị `handedness.py` đánh trượt (`valid=False`) do cổ tay Pose bị khuất (`visibility <= 0.3`) hoặc khoảng cách $> 0.15$!
  4. `right_hand_detected_pct` vs `right_hand_valid_pct`.
  5. `shoulder_width_px_mean` & `shoulder_y_mean`: Khoảng cách hai vai trung bình (tính theo tỷ lệ khung ảnh) để so sánh trực tiếp tư thế ngồi của người dùng với clip chuẩn `014159.mp4`.
  6. `active_frame_range`: Frame đầu tiên và frame cuối cùng có ít nhất 1 bàn tay hợp lệ (`valid=True`), giúp đo chính xác thời gian trễ đầu/cuối trong 4 giây.

### 3.2. Kịch bản `diagnostics/render_diagnostic_video.py`
- **Đầu vào**: `python -X utf8 diagnostics/render_diagnostic_video.py local_data/webcam_xxx.avi --out outputs/diagnostics/webcam_xxx_quad.mp4`
- **Bố cục khung hình xuất ra (`1280 × 720`)**:
  - `Quad 1 (640×480)`: Ảnh gốc + 7 điểm Pose (`POSE_INDICES`) + vòng tròn xanh lá quanh cổ tay Pose nếu `visibility > 0.3` (màu xám nếu `<= 0.3`) với bán kính `0.15 * min(W, H)` + 21 điểm mỗi bàn tay (`raw_left_hand`, `raw_right_hand`).
  - `Quad 2 (640×480)`: Hệ tọa độ thân người 27 điểm (`slgcn_xy_adapter.py`: `raw_joints` vs `repaired joints`), vẽ các cạnh `edges_parent_child` trong `training_config.json`.
  - `Quad 3 (640×240)`: Hai ô vuông hiển thị `left_hand_local` (21 điểm) và `right_hand_local` (21 điểm).
  - `Quad 4 (640×240)`: Thanh timeline đánh dấu màu theo từng frame $t \in [0, T)$:
    - Xanh lá: Cả Pose và Hand đều `valid` (`observed`).
    - Vàng: Hand được nội suy qua `team_repair.py` (`imputed`, gap $\le 5$).
    - Cam: MediaPipe Hands bắt được tay nhưng bị `mask_rejected` do `handedness_valid == False`.
    - Đỏ: Bị chặn bởi `geometry_blocked` (`wrist_distance > 1.0`).
    - Xám: Không phát hiện thấy tay (idle / ngoài khung hình).

---

## 4. Kiểm Chứng Tự Động (Harness Layer 3 — Verification)
Chạy các lệnh sau và kiểm tra đầu ra:
```powershell
cd slr-app/MVP
python -m py_compile diagnostics/inspect_clip_qc.py diagnostics/render_diagnostic_video.py
python -X utf8 diagnostics/inspect_clip_qc.py local_data/014159.mp4
python -X utf8 diagnostics/test_diagnostics.py
```
- **Tiêu chí đạt (Pass Criteria)**:
  - Trên `014159.mp4`, `inspect_clip_qc.py` phải khớp tuyệt đối `decoded_frames = 59`, `missing_after_pct = 4.39%`, `geometry_blocked_source_frames = 0`.
  - Video xuất ra mở được bằng `cv2.VideoCapture`, có đúng `59` frames và kích thước `1280 × 720`.
  - `check_clip.py` vẫn vượt qua kiểm tra SHA-256 100%.

## 5. Điểm Chặn Kiểm Duyệt (Harness Layer 5 — Human Review)
- Người dùng mở video `outputs/diagnostics/014159_quad.mp4` song song với `outputs/diagnostics/webcam_<latest>_quad.mp4` để đối chiếu trực quan tỷ lệ `shoulder_width` và vị trí vòng tròn cổ tay `0.15` trước khi điều chỉnh vị trí đặt ghế/camera.
