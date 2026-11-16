# Báo Cáo Kiểm Toán Tập Test (`3,714` Mẫu) & Danh Sách Từ "Platinum / Golden Demo"

Tài liệu này lưu trữ toàn bộ kết quả phân tích chéo từ bộ dữ liệu kiểm toán chính thức trên tập Test ([outputs/drive_audit/](../outputs/drive_audit/)) gồm **3,714 clips**, **400 lớp**, trên **4 người ký độc lập (`002`, `010`, `014`, `025`)**.

---

## 1. Tổng Quan Hiệu Năng & Ngưỡng Chất Lượng Đầu Vào Tập Test

- **Độ chính xác tổng thể ([test_metrics.json](../outputs/drive_audit/test_metrics.json))**:
  - **Top-1 Accuracy**: **`89.53%`** (`89.5261%`)
  - **Top-5 Accuracy**: **`96.42%`** (`96.4190%`)
  - **Macro-F1**: **`90.37%`** (`90.3737%`)
- **Số lớp đạt hoàn hảo (`F1 = 1.000`, `Precision = 1.000`, `Recall = 1.000`)**: **`150 / 400` lớp (`37.5%`)**.
- **Ngưỡng phân phối tỷ lệ mất khớp hậu sửa lỗi (`missing_after_pct_full_original` trong [test_cache_qc.json](../outputs/drive_audit/test_cache_qc.json))**:
  - Trung bình (`Mean`): **`4.16%`** (`4.159%`)
  - Trung vị (`P50`): **`0.55%`**
  - Phân vị thứ 95 (`P95`): **`20.00%`**
  - Cực đại (`Max`): **`62.60%`**
- **Đối chiếu thực nghiệm Webcam ([verification_results.json](../outputs/empirical_verification/verification_results.json))**:
  - 13/15 lượt quay webcam khi ngồi sát màn hình có `missing_after_pct = 48.3% – 72.2%`, nằm vượt ngưỡng `P99` của tập Test nên mất khớp tay nghiêm trọng.
  - Khi điều chỉnh khoảng cách/ánh sáng đưa `missing_after_pct` về miền phân phối chuẩn của tập Test (`3.11%` ở `Khăn quàng cổ`, `11.52%` ở `Trường Cao đẳng`), mô hình khôi phục khả năng nhận diện chính xác.

---

## 2. Bảng Top Từ "Platinum & Golden Demo" Cho Buổi Thuyết Trình

### 2.1. Nhóm 1 — "Platinum Demo Words" (`F1 = 1.000`, 0 nhầm lẫn, `0.00%` mất khớp trên 100% clip Test)

Lọc đồng thời từ [per_class_test_results.csv](../outputs/drive_audit/per_class_test_results.csv) và [test_index_qc.csv](../outputs/drive_audit/test_index_qc.csv): toàn bộ **9 lớp** dưới đây có `0` frame mất khớp hậu sửa lỗi (`missing_after = 0.00%`), `0` frame bị kiểm dịch hình học và `0` khớp bị từ chối trên mọi mẫu Test:

| Index | Gloss | Support (Đúng/Tổng) | P / R / F1 | Missing After Mean | Mean Frames | Ghi chú |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| `86` | **Cảm ơn** | `8 / 8` | `1.000` | **`0.00%`** | `62.4` | **Ưu tiên #1** (thuộc 4 từ chuẩn bàn giao) |
| `395` | **Đồng ý** | `8 / 8` | `1.000` | **`0.00%`** | `52.4` | Động tác ngắn gọn, dễ ký |
| `328` | **Trung Quốc** | `10 / 10` | `1.000` | **`0.00%`** | `57.8` | Support cao nhất nhóm Platinum |
| `137` | **Hư** | `10 / 10` | `1.000` | **`0.00%`** | `65.3` | Support cao nhất nhóm Platinum |
| `287` | **Tham lam** | `10 / 10` | `1.000` | **`0.00%`** | `60.7` | Support cao nhất nhóm Platinum |
| `128` | **Hay (khen)** | `9 / 9` | `1.000` | **`0.00%`** | `59.8` | Ổn định trên cả 4 người ký Test |
| `202` | **Mềm** | `9 / 9` | `1.000` | **`0.00%`** | `63.9` | Ổn định trên cả 4 người ký Test |
| `164` | **Lùn** | `9 / 9` | `1.000` | **`0.00%`** | `62.1` | Ổn định trên cả 4 người ký Test |
| `68` | **Cung cấp** | `8 / 8` | `1.000` | **`0.00%`** | `61.5` | Ổn định trên cả 4 người ký Test |

### 2.2. Nhóm 2 — "Golden Demo Words" (`F1 = 1.000`, 0 nhầm lẫn, `mean_missing_after < 2.0%` hoặc đã kiểm chứng Webcam)

| Index | Gloss | Support | F1 | Mean Missing After | Max Missing | Mean Frames | Ghi chú thực nghiệm |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `95` | **Dài** | `9 / 9` | `1.000` | `1.91%` | `7.3%` | `65.4` | **Ưu tiên #2** (thuộc 4 từ bàn giao; mẫu chuẩn `014159.mp4` đạt `0.9969`) |
| `154` | **Khăn quàng cổ** | `8 / 8` | `1.000` | `9.20%` | `21.0%` | `77.8` | **Đã test webcam**: `0.9498` (chưa cắt) $\to$ **`0.9790`** (sau cắt) |
| `60` | **Con gái** | `9 / 9` | `1.000` | `0.06%` | `0.6%` | `72.2` | Gần như không mất khớp |
| `85` | **Cảm thấy** | `9 / 9` | `1.000` | `0.06%` | `0.6%` | `65.0` | Gần như không mất khớp |
| `47` | **Chậm chạp** | `10 / 10` | `1.000` | `0.15%` | `1.5%` | `63.0` | Support cao (`10`) |
| `270` | **Quần đùi** | `10 / 10` | `1.000` | `0.19%` | `1.9%` | `66.9` | Support cao (`10`) |
| `9` | **Bàn phím** | `8 / 8` | `1.000` | `0.36%` | `2.8%` | `71.6` | Quỹ đạo rõ trước ngực |
| `162` | **Làm bài tập** | `10 / 10` | `1.000` | `0.42%` | `4.2%` | `55.9` | Support cao (`10`) |
| `44` | **Chăm chỉ** | `8 / 8` | `1.000` | `0.50%` | `4.0%` | `70.6` | Ít tự che khuất |
| `53` | **Chụp hình** | `8 / 8` | `1.000` | `0.51%` | `4.1%` | `57.6` | Động tác trực quan |
| `345` | **Tốt bụng** | `8 / 8` | `1.000` | `0.51%` | `4.1%` | `59.8` | Ít tự che khuất |
| `330` | **Trà** | `8 / 8` | `1.000` | `0.54%` | `4.4%` | `65.5` | Ít tự che khuất |
| `351` | **Việt Nam** | `8 / 8` | `1.000` | `0.59%` | `4.7%` | `61.0` | Ít tự che khuất |
| `380` | **Đi** | `8 / 8` | `1.000` | `0.60%` | `4.8%` | `61.1` | Từ phổ thông ngắn gọn |
| `358` | **Xe buýt** | `8 / 8` | `1.000` | `0.60%` | `3.1%` | `66.1` | Ổn định qua kiểm toán đầy đủ |
| `62` | **Con mèo** | `8 / 8` | `1.000` | `0.62%` | `4.9%` | `63.8` | Từ phổ thông |
| `1` | **Ba lô** | `8 / 8` | `1.000` | `0.82%` | `3.6%` | `62.6` | Ít tự che khuất |
| `276` | **Rửa mặt** | `8 / 8` | `1.000` | `0.90%` | `3.8%` | `67.9` | Ổn định qua kiểm toán đầy đủ |
| `274` | **Rộng** | `9 / 9` | `1.000` | `1.32%` | `11.9%` | `62.2` | 0 nhầm lẫn |
| `46` | **Chạy** | `9 / 9` | `1.000` | `1.40%` | `7.1%` | `62.9` | 0 nhầm lẫn |
| `22` | **Bóng đá** | `8 / 8` | `1.000` | `1.82%` | `8.2%` | `63.2` | 0 nhầm lẫn |
| `105` | **Dừng lại** | `8 / 8` | `1.000` | `3.81%` | `11.3%` | `58.5` | Lưu ý đứng/ngồi đủ xa để không mất cổ tay |

---

## 3. Kiểm Toán 4 Từ Bàn Giao & Ghi Chú Các Cặp Hay Nhầm Lẫn Nhất (Blacklist)

### 3.1. Trạng thái 4 từ chuẩn bàn giao ([BAN_GIAO_QUAN.md](../BAN_GIAO_QUAN.md#L44))
- **`Cảm ơn` (`86`)**: `8/8` (`F1 = 1.000`, `missing_after = 0.00%`, 0 FN/FP) — **Khuyên dùng #1**.
- **`Dài` (`95`)**: `9/9` (`F1 = 1.000`, `missing_after = 1.91%`, 0 FN/FP) — **Khuyên dùng #2**.
- **`Xin lỗi` (`364`)**: `8/9` (`P = 0.889`, `R = 0.889`, `F1 = 0.889`, `missing_after = 7.21%`), nhầm 1 lần với `Đồ dùng` (FN) và `Rửa chén` (FP) — **Dự phòng**.
- **`Nước` (`243`)**: `8/8` (`Recall = 1.000`, `Precision = 0.727`, `F1 = 0.842`, `missing_after = 1.33%`), bị lớp `Xôi` (`2` lần) và `Không nên` (`1` lần) dự đoán nhầm sang `Nước` (FP).

### 3.2. Danh sách loại bỏ khỏi kịch bản Demo (Blacklist) & Top Cặp Nhầm Lẫn ([confusion_pairs.csv](../outputs/drive_audit/confusion_pairs.csv))
- **Các từ có độ chính xác Test thấp (Bỏ khỏi danh sách sơ bộ cũ)**:
  - `Tủ lạnh` (`346`, `F1 = 0.545`, `6/10`, `missing_after = 12.76%`).
  - `Thứ ba` (`318`, `F1 = 0.556`, `5/10`), `Thứ tư` (`323`, `F1 = 0.522`, `6/10`).
  - `Bố` (`33`, `F1 = 0.571`, `6/10`, nhầm lẫn chéo với `Anh`, `Nhạt`, `Thơm`).
  - `Nhẹ` (`236`, `F1 = 0.759`, `11/15`, nhầm 2 chiều với `Bây giờ` tổng cộng `7` lần).
  - `Bác` (`10`, `F1 = 0.667`, `8/12`, `missing_after = 14.13%`).
  - `Trường Cao đẳng` (`331`, `F1 = 0.778`, `7/10`).
- **Top các cặp hay nhầm lẫn nhất trên tập Test**:
  - `Nắng` $\to$ `Mùa hè`: **`6` lần** (cộng `2` lần chiều ngược lại = `8` lần).
  - `Bánh tét` $\to$ `Bánh chưng`: **`5` lần**.
  - `Thức dậy` $\to$ `Màu nâu`: **`5` lần**.
  - `Ướt` $\to$ `Xôi`: **`5` lần** (khớp với log webcam khi 2 lớp này đứng sát nhau trong Top-5).
  - `Dữ` $\to$ `Nếm` (`4` lần), `Nhầm lẫn` $\leftrightarrow$ `Hát` (`4 + 2 = 6` lần), `Nhẹ` $\leftrightarrow$ `Bây giờ` (`4 + 3 = 7` lần), `Rửa tay` $\to$ `Thú vị` (`4` lần), `Nên` $\leftrightarrow$ `Không nên` (`3 + 2 = 5` lần), `Thơm` $\to$ `Bố` (`3` lần), `Thứ năm` $\to$ `Thứ tư` (`3` lần).
  - `Cái bàn` (`70`, `Precision = 0.500`, `F1 = 0.645`): bị 8 từ chỉ tháng (`Tháng một`..`Tháng tám`), `Giường` và `Yên tĩnh` dự đoán nhầm vào làm FP.
  - Cụm `{Bác (F1 = 0.667), Màu hồng (F1 = 0.824), Sai (F1 = 0.933)}`: có liên kết nhầm lẫn chéo khi mất khớp tay (`Sai` $\to$ `Bác`, `Màu hồng` $\leftrightarrow$ `Bác`).

---

## 4. Khuyến Nghị Thực Thi Cho Buổi Demo
- Chọn **5–6 từ** từ **Nhóm 1 (`Cảm ơn`, `Đồng ý`, `Hay (khen)`)** và **Nhóm 2 (`Dài`, `Khăn quàng cổ`, `Con mèo`/`Đi`/`Chạy`)**.
- Đặt camera cách `1.1–1.3 m`, bật đủ sáng (`decoded_frames >= 105` trong 4s), quay thử mỗi từ `3` lần qua [demo.py](../desktop_mvp/demo.py) và chỉ giữ vào kịch bản demo các từ đạt `Top-1` đúng `3/3` lần (`softmax >= 0.75`).


## 5. Đề xuất gợi ý sửa nhãn từ các cặp nhầm lẫn

- Khi người dùng chọn **Kết quả chưa đúng**, dùng nhãn mô hình vừa trả để tra các nhãn thật từng bị dự đoán thành nhãn đó trong `outputs/drive_audit/confusion_pairs.csv`. Kết hợp các cặp đã xác nhận trên webcam với danh sách Top-k để xếp gợi ý. Giữ cả lựa chọn **Chọn nhãn khác** và **Quay lại**.
- Chỉ sau khi người dùng chọn và xác nhận nhãn thay thế, cập nhật kết quả hiển thị và từ sẽ phát, rồi đặt `status = "fixed"` cho kết quả đó. Với nhiều ký hiệu trong một lượt, lưu trạng thái riêng cho từng đoạn và giữ thứ tự. Lưu cả `predicted_label` và `confirmed_label` để tính Top-1 gốc và tỷ lệ sửa thành công.
- Ví dụ webcam đã xác nhận: nhãn thật **Cảm ơn** (`86`) bị dự đoán thành **Tham ăn** (`288`) ở hai clip `WIN_20261115_22_34_23_Pro.mp4` và `WIN_20261115_22_34_39_Pro.mp4`. Tra theo chiều **dự đoán Tham ăn → gợi ý Cảm ơn** khi người dùng báo sai. Đây là hai lượt của cùng một người ký và chỉ làm căn cứ gợi ý. `fixed` đánh dấu kết quả đã được người dùng sửa, còn việc cải thiện mô hình cần được kiểm chứng riêng.
