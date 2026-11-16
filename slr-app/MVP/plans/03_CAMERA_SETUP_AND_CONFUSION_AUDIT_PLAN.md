# Kế Hoạch Mô-đun 03: Quy Trình Căn Chỉnh Góc Máy, Kiểm Toán Dữ Liệu Drive & Chọn Bộ Từ "Golden Demo" Cho Ngày Mai

## 1. Mục Tiêu Thực Thi Trước Buổi Demo Ngày Mai
Tối đa hóa xác suất nhận diện đúng ngay lần đầu (Top-1 Accuracy) khi demo trực tiếp trước giảng viên bằng cách loại bỏ triệt để sự lệch miền (Domain Shift) giữa tư thế ngồi trước laptop và dữ liệu huấn luyện VSL400.

---

## 2. Quy Chuẩn Góc Máy, Ánh Sáng & Tư Thế Ngồi/Đứng (Bắt Buộc Kiểm Tra)

Dựa trên phân tích hàm chuẩn hóa trong [normalization.py](../deployment/feature_extract/src/extraction/normalization.py) và hàm lọc chất lượng trong [slgcn_xy_adapter.py](../deployment/slgcn_feature_trial/vendor/slgcn_xy_adapter.py), mô hình **bất biến với phép tịnh tiến và tỷ lệ 2D trong mặt phẳng ảnh**, nhưng **rất nhạy cảm** với 4 yếu tố vật lý sau:

| Yếu tố vật lý | Hiện tượng lỗi khi ngồi gần Laptop | Quy chuẩn bắt buộc khi Demo ngày mai | Chỉ số nghiệm thu trong `report.json` |
| :--- | :--- | :--- | :--- |
| **1. Khoảng cách tới Camera (Framing)** | Ngồi cách laptop $40\text{--}50\text{ cm}$ làm nửa thân trên bị cắt ngang ngực; khi hạ nhẹ tay hoặc đưa tay sang ngang, cổ tay rơi ra ngoài mép dưới/mép bên $\to$ `pose_wrist.visibility <= 0.3` $\to$ toàn bộ bàn tay bị xóa trắng (`missing_after_pct > 55%`). | Đặt camera (hoặc ngồi lùi ghế) cách ống kính **$1.0\text{ m} - 1.4\text{ m}$** sao cho khung hình lấy trọn **từ đỉnh đầu xuống ngang thắt lưng (thấy rõ cả hai khuỷu tay và cổ tay khi buông nhẹ)**. Độ rộng hai vai chiếm khoảng **$22\% - 30\%$** chiều ngang khung hình (tương đương clip mẫu `014159.mp4`). | `missing_after_pct < 15.0%` và `geometry_blocked_source_frames == 0`. |
| **2. Góc nghiêng ống kính (Camera Pitch)** | Màn hình laptop ngửa lên làm camera nhìn hất từ dưới lên (upward pitch angle), làm biến dạng tỷ lệ dọc $\Delta y / \text{shoulder\_width}$ khi đưa tay lên mặt/ngực. | Đặt camera **ngang tầm ngực/vai** và ống kính **vuông góc với mặt phẳng thân người** (không hất từ dưới lên, không chúc từ trên cao xuống). | Tọa độ $y$ của mũi so với trung điểm hai vai trong `upper_body[:, 0, 1]` nằm trong khoảng $[-0.65, -0.45]$. |
| **3. Ánh sáng phòng & Tốc độ khung hình (FPS)** | Trong 11/15 lượt thử trước, thiếu sáng kích hoạt Auto-Exposure làm webcam giảm tốc độ xuống **`59 frames / 4s` ($\approx 15\text{ FPS}$)** và gây motion blur. Do `prepare_clip.py` có ràng buộc **`No time resampling`** (xếp thẳng chuỗi frame thực tế vào mảng mà không nội suy bù frame), mô hình SL-GCN (vốn được huấn luyện ở $25\text{--}30\text{ FPS}$ tương ứng $50\text{--}60$ frame/từ) sẽ "thấy" người ký chuyển động nhanh gấp đôi bình thường, phá vỡ trường tiếp nhận thời gian. | Bật đèn sáng trực diện phía trước người ký để webcam giữ tốc độ phơi sáng nhanh và ổn định $30\text{ FPS}$. | `decoded_frames` trong 4s phải đạt **`105 – 120` frames** ($\approx 26\text{--}30\text{ FPS}$). |
| **4. Quy ước Tay Thuận (Anatomical Handedness)** | Giao diện Kiosk lật gương (`scaleX(-1)`) để dễ căn khung, nhưng nếu người ký nhìn video mẫu `014159.mp4` rồi bắt chước theo kiểu đối xứng gương (dùng tay trái thay vì tay phải), dữ liệu vào mô hình sẽ bị ngược bên! | **Luôn dùng đúng tay giải phẫu** (tay phải thật của bạn cho động tác chính của các ký hiệu 1 tay hoặc ký hiệu bất đối xứng). | Trong `inspect_clip_qc.py`, `right_hand_valid_pct > 80%`. |

---

## 2.1. Hai Hướng Thí Nghiệm Khắc Phục Tụt FPS & Khôi Phục Nhịp Thời Gian

### Hướng 1: Thí nghiệm Phần mềm — Khôi phục nhịp thời gian (Temporal Resampling / Linear Interpolation)
1. **Nguyên lý kỹ thuật**:
   - Khi video chỉ có $T \approx 60$ frames thay vì $120$ frames trong 4 giây, cử chỉ bị thưa khung hình.
   - Thay vì nạp chuỗi thưa vào [slgcn_xy_adapter.py](../deployment/slgcn_feature_trial/vendor/slgcn_xy_adapter.py), ta thực hiện nội suy tuyến tính (Linear Interpolation) trên chuỗi đặc trưng sau trích xuất MediaPipe để nâng số frame từ $T \to T_{\text{target}} = 2 \times T$ (chuẩn hóa về đúng tần số lấy mẫu $30\text{ FPS}$).
   - **Công thức**: Với mỗi khớp xương $j \in \{0, \dots, 26\}$, nội suy tọa độ $(x_t, y_t)$ theo trục thời gian thực $t$:
     $$X_{\text{resampled}}(t') = \text{interp1d}(t_{\text{raw}}, X_{\text{raw}}, \text{kind}='linear')(t')$$
   - **Ưu điểm**: Nằm hoàn toàn ở tầng tiền xử lý trung gian, không can thiệp vào checkpoint `gcnCkpt.pt` và không làm hỏng khóa SHA-256 của [deployment/](../deployment/).
2. **Kế hoạch thực nghiệm kiểm chứng**:
   - **Dữ liệu thử**: Lấy các video thực nghiệm đã quay: clip chuẩn `webcam_20261115_161011_553730.avi` ($119$ frames) đối chiếu với clip lỗi `webcam_20261115_172227_753840.avi` ($57$ frames).
   - **Kịch bản A/B Test**:
     - *Baseline*: Chạy `check_clip.py` trực tiếp $\to$ ghi nhận Top-1 Gloss và xác suất softmax.
     - *Experiment (Có Resampling)*: Tăng gấp đôi số frame bằng nội suy thời gian $\to$ chạy qua `prepare_arrays()` và SL-GCN $\to$ so sánh mức độ phục hồi độ tự tin softmax.

### Hướng 2: Thí nghiệm Phần cứng / Thiết lập Camera — Khóa cố định 30 FPS trên OpenCV
1. **Nguyên lý kỹ thuật**:
   - Webcam USB trên Windows mặc định bật tính năng Auto Exposure Priority (tự động hạ FPS khi môi trường thiếu sáng để ảnh đủ sáng). Trong OpenCV (`cv2.VideoCapture`), can thiệp để cố định tốc độ:
     ```python
     # Tắt chế độ tự động thay đổi FPS theo độ sáng
     camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25) # Hoặc 0 tuỳ driver
     camera.set(cv2.CAP_PROP_EXPOSURE, -5)        # Khóa thời gian phơi sáng cố định
     camera.set(cv2.CAP_PROP_FPS, 30)
     ```
2. **Thử nghiệm thực tế trong phòng**:
   - Bật thêm 1 nguồn sáng chiếu thẳng vào nửa thân trên (đèn bàn hoặc màn hình mở nền trắng sáng).
   - Chạy thử 1 lượt quay 4s qua `demo.py`, kiểm tra xem file `.avi` mới có đạt trọn vẹn $\approx 115\text{--}120$ frames hay không.

---

## 3. Kết Quả Kiểm Toán Thực Nghiệm Tập Test (`outputs/drive_audit/`)

Bộ dữ liệu kiểm toán đầy đủ từ Google Drive ([test_metrics.json](../outputs/drive_audit/test_metrics.json), [test_cache_qc.json](../outputs/drive_audit/test_cache_qc.json), [per_class_test_results.csv](../outputs/drive_audit/per_class_test_results.csv), [test_index_qc.csv](../outputs/drive_audit/test_index_qc.csv), [confusion_pairs.csv](../outputs/drive_audit/confusion_pairs.csv)) gồm **3,714 clips**, **400 lớp**, trên **4 người ký độc lập (`002`, `010`, `014`, `025`)**:

- **Độ chính xác tổng thể**: **Top-1 = `89.53%`** (`89.5261%`), **Top-5 = `96.42%`** (`96.4190%`), **Macro-F1 = `90.37%`** (`90.3737%`).
- **Số lớp đạt hoàn hảo (`F1 = 1.000`, `Precision = 1.000`, `Recall = 1.000`)**: **`150 / 400` lớp (`37.5%`)**.
- **Phân phối tỷ lệ mất khớp hậu sửa lỗi (`missing_after_pct_full_original`) trên 3,714 clips Test**:
  - Trung bình: **`4.16%`** (`4.159%`), Trung vị (`P50`): **`0.55%`**, Phân vị thứ 95 (`P95`): **`20.00%`**, Cực đại: **`62.60%`**.
  - Kết quả này chứng minh thực nghiệm: 13/15 lượt quay webcam khi ngồi sát màn hình (`missing_after_pct = 48.3% – 72.2%`) vượt ngưỡng `P99` của tập Test; ngược lại, 2 lượt quay đạt `missing_after_pct = 3.11%` (`Khăn quàng cổ`) và `11.52%` (`Trường Cao đẳng`) nằm gọn trong vùng `P50 – P90` của tập Test và nhận diện chính xác.

---

## 4. Danh Sách Từ "Golden Demo" & Bảng Loại Bỏ (Đã Kiểm Chứng 3,714 Mẫu Test)

### 4.1. Bảng 1 — Nhóm "Platinum Demo Words" (Tier 1: `F1 = 1.000`, 0 nhầm lẫn, `0.00%` mất khớp trên 100% clip Test)

Đây là **9 từ an toàn tuyệt đối**: vừa đạt độ chính xác 100% trên cả 4 người ký Test, vừa không bị bất kỳ frame mất khớp, kiểm dịch hình học hay từ chối khớp nào (`missing_after = 0.00%`, `quarantined = 0`, `rejected = 0`):

| Index | Gloss | Support (Đúng/Tổng) | Precision | Recall | F1 | Mean Missing After | Mean Frames | Ghi chú |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `86` | **Cảm ơn** | `8 / 8` | `1.000` | `1.000` | `1.000` | **`0.00%`** | `62.4` | **Từ chuẩn bàn giao (#1)** |
| `395` | **Đồng ý** | `8 / 8` | `1.000` | `1.000` | `1.000` | **`0.00%`** | `52.4` | Độ dài ngắn gọn, dễ ký |
| `128` | **Hay (khen)** | `9 / 9` | `1.000` | `1.000` | `1.000` | **`0.00%`** | `59.8` | Ổn định trên cả 4 signers |
| `328` | **Trung Quốc** | `10 / 10` | `1.000` | `1.000` | `1.000` | **`0.00%`** | `57.8` | Support cao nhất Tier 1 |
| `137` | **Hư** | `10 / 10` | `1.000` | `1.000` | `1.000` | **`0.00%`** | `65.3` | Support cao nhất Tier 1 |
| `287` | **Tham lam** | `10 / 10` | `1.000` | `1.000` | `1.000` | **`0.00%`** | `60.7` | Support cao nhất Tier 1 |
| `202` | **Mềm** | `9 / 9` | `1.000` | `1.000` | `1.000` | **`0.00%`** | `63.9` | 0% mất khớp tuyệt đối |
| `164` | **Lùn** | `9 / 9` | `1.000` | `1.000` | `1.000` | **`0.00%`** | `62.1` | 0% mất khớp tuyệt đối |
| `68` | **Cung cấp** | `8 / 8` | `1.000` | `1.000` | `1.000` | **`0.00%`** | `61.5` | 0% mất khớp tuyệt đối |

### 4.2. Bảng 2 — Nhóm "Golden Demo Words" (Tier 2: `F1 = 1.000`, 0 nhầm lẫn, `mean_missing_after < 2.0%` hoặc đã kiểm chứng Webcam)

| Index | Gloss | Support | F1 | Mean Missing After | Max Missing | Mean Frames | Ghi chú thực nghiệm |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `95` | **Dài** | `9 / 9` | `1.000` | `1.91%` | `7.3%` | `65.4` | **Từ chuẩn bàn giao (#2)**; clip mẫu `014159.mp4` đạt `0.9969` |
| `154` | **Khăn quàng cổ** | `8 / 8` | `1.000` | `9.20%` | `21.0%` | `77.8` | **Đã test webcam**: `0.9498` (chưa cắt) $\to$ **`0.9790`** (sau cắt) |
| `60` | **Con gái** | `9 / 9` | `1.000` | `0.06%` | `0.6%` | `72.2` | Gần như 0% mất khớp |
| `85` | **Cảm thấy** | `9 / 9` | `1.000` | `0.06%` | `0.6%` | `65.0` | Gần như 0% mất khớp |
| `47` | **Chậm chạp** | `10 / 10` | `1.000` | `0.15%` | `1.5%` | `63.0` | Support cao (`10`) |
| `270` | **Quần đùi** | `10 / 10` | `1.000` | `0.19%` | `1.9%` | `66.9` | Support cao (`10`) |
| `9` | **Bàn phím** | `8 / 8` | `1.000` | `0.36%` | `2.8%` | `71.6` | Quỹ đạo rõ trước ngực |
| `162` | **Làm bài tập** | `10 / 10` | `1.000` | `0.42%` | `4.2%` | `55.9` | Support cao (`10`) |
| `44` | **Chăm chỉ** | `8 / 8` | `1.000` | `0.50%` | `4.0%` | `70.6` | Ít tự che khuất |
| `53` | **Chụp hình** | `8 / 8` | `1.000` | `0.51%` | `4.1%` | `57.6` | Động tác trực quan |
| `345` | **Tốt bụng** | `8 / 8` | `1.000` | `0.51%` | `4.1%` | `59.8` | Ít tự che khuất |
| `330` | **Trà** | `8 / 8` | `1.000` | `0.54%` | `4.4%` | `65.5` | Ít tự che khuất |
| `351` | **Việt Nam** | `8 / 8` | `1.000` | `0.59%` | `4.7%` | `61.0` | Ít tự che khuất |
| `380` | **Đi** | `8 / 8` | `1.000` | `0.60%` | `4.8%` | `61.1` | Từ thông dụng, ngắn gọn |
| `358` | **Xe buýt** | `8 / 8` | `1.000` | `0.60%` | `3.1%` | `66.1` | Ổn định qua kiểm toán đầy đủ |
| `62` | **Con mèo** | `8 / 8` | `1.000` | `0.62%` | `4.9%` | `63.8` | Từ thông dụng |
| `1` | **Ba lô** | `8 / 8` | `1.000` | `0.82%` | `3.6%` | `62.6` | Ít tự che khuất |
| `276` | **Rửa mặt** | `8 / 8` | `1.000` | `0.90%` | `3.8%` | `67.9` | Ổn định qua kiểm toán đầy đủ |
| `274` | **Rộng** | `9 / 9` | `1.000` | `1.32%` | `11.9%` | `62.2` | Ít nhầm lẫn |
| `46` | **Chạy** | `9 / 9` | `1.000` | `1.40%` | `7.1%` | `62.9` | Ít nhầm lẫn |
| `22` | **Bóng đá** | `8 / 8` | `1.000` | `1.82%` | `8.2%` | `63.2` | Từ thông dụng |
| `105` | **Dừng lại** | `8 / 8` | `1.000` | `3.81%` | `11.3%` | `58.5` | Lưu ý đứng xa để không mất cổ tay |

### 4.3. Kiểm toán 4 từ bàn giao ([BAN_GIAO_QUAN.md](../BAN_GIAO_QUAN.md#L44)) & Danh sách loại bỏ (Blacklist khi Demo)

- **4 từ bàn giao chính thức**:
  1. `Cảm ơn` (`idx = 86`): **Khuyên dùng #1** (`8/8`, `F1 = 1.000`, `missing_after = 0.00%`, 0 nhầm lẫn).
  2. `Dài` (`idx = 95`): **Khuyên dùng #2** (`9/9`, `F1 = 1.000`, `missing_after = 1.91%`, 0 nhầm lẫn).
  3. `Xin lỗi` (`idx = 364`): **Dự phòng** (`8/9`, `F1 = 0.889`, `missing_after = 7.21%`, có 1 FN sang `Đồ dùng` và 1 FP từ `Rửa chén`).
  4. `Nước` (`idx = 243`): **Lưu ý Precision** (`8/8`, `Recall = 1.000`, nhưng `Precision = 0.727`, `F1 = 0.842` do `Xôi` bị đoán nhầm thành `Nước` 2 lần và `Không nên` 1 lần; khi ký cần tránh làm lỏng tay).
- **Danh sách loại bỏ khỏi kịch bản Demo (Blacklist — hiệu chỉnh từ tập sơ bộ 36 mẫu cũ)**:
  - **Không dùng từ bộ sơ bộ cũ (sai số thực tế cao trên 3,714 mẫu Test)**: `Tủ lạnh` (`346`, `F1 = 0.545`, `missing_after = 12.76%`), `Thứ ba` (`318`, `F1 = 0.556`, hay nhầm với `Thứ tư`, `Thứ hai`), `Thứ tư` (`323`, `F1 = 0.522`), `Bố` (`33`, `F1 = 0.571`, nhầm với `Anh, Nhạt, Thơm`), `Nhẹ` (`236`, `F1 = 0.759`, nhầm 2 chiều 7 lần với `Bây giờ`), `Bác` (`10`, `F1 = 0.667`, `missing_after = 14.13%`), `Trường Cao đẳng` (`331`, `F1 = 0.778`, `7/10`).
  - **Các cặp hay nhầm lẫn hàng đầu trong `confusion_pairs.csv`**:
    - `Nắng` $\leftrightarrow$ `Mùa hè` (`6 + 2 = 8` lần).
    - `Bánh tét` $\to$ `Bánh chưng` (`5` lần).
    - `Thức dậy` $\to$ `Màu nâu` (`5` lần).
    - `Ướt` $\to$ `Xôi` (`5` lần — khớp hiện tượng thực nghiệm trên webcam khi `Ướt (0.706)` và `Xôi (0.023)` cùng đứng đầu Top-5).
    - `Dữ` $\to$ `Nếm` (`4` lần), `Nhầm lẫn` $\leftrightarrow$ `Hát` (`4 + 2 = 6` lần), `Nhẹ` $\leftrightarrow$ `Bây giờ` (`4 + 3 = 7` lần), `Rửa tay` $\to$ `Thú vị` (`4` lần), `Nên` $\leftrightarrow$ `Không nên` (`3 + 2 = 5` lần), `Thơm` $\to$ `Bố` (`3` lần), `Thứ năm` $\to$ `Thứ tư` (`3` lần).
    - `Cái bàn` (`70`, `Precision = 0.500` vì 8 từ chỉ tháng `Tháng một`..`Tháng tám` bị dự đoán nhầm vào `Cái bàn`).
    - Cụm `{Màu hồng (F1 = 0.824), Bác (F1 = 0.667), Sai (F1 = 0.933)}`: Có cạnh nhầm lẫn chéo trong ma trận nhầm lẫn khi khớp tay bị suy giảm (`Sai` $\to$ `Bác`, `Màu hồng` $\leftrightarrow$ `Bác`).

---

## 5. Quy Trình Thực Nghiệm Chọn "Golden Demo Words" Tối Nay (30 Phút)

1. **Bước 1 — Chạy công cụ chẩn đoán trên 15 clip webcam đã quay hôm nay**:
   - Thực thi `diagnostics/inspect_clip_qc.py` và `diagnostics/render_diagnostic_video.py` (từ Kế hoạch 01) trên clip thành công (`webcam_20261115_161011_553730.avi`) và clip thất bại (`webcam_20261115_172227_753840.avi`) để thấy rõ sự khác biệt về góc máy và tỷ lệ mất khớp.
2. **Bước 2 — Căn chỉnh góc máy theo Quy chuẩn Mục 2**:
   - Đảm bảo đèn sáng (`decoded_frames >= 105` trong 4s) và ngồi lùi khoảng $1.1\text{--}1.3\text{ m}$ (`missing_after_pct < 15%`).
3. **Bước 3 — Quay thử nghiệm từng từ đơn (Isolated Sign Benchmark)**:
   - Thực hiện mỗi từ ứng viên 3 lần liên tiếp qua `demo.py` hoặc `benchmark_demo_words.py`.
   - **Tiêu chí chọn vào danh sách Demo ngày mai (Human Review Gate)**: Chỉ giữ lại những từ đạt **Top-1 đúng trong cả $3/3$ lần thử** với **`softmax >= 0.75`**.
