# ĐẶC TẢ THIẾT KẾ UI/UX SLR KIOSK (1024 × 600) — CHÍNH THỨC

> **Trạng thái tài liệu:** ĐÃ DUYỆT (ACCEPTED) ngày 14/11/2026.  
> **Mục tiêu:** Bản giao diện độc lập tối ưu cho luồng chính Demo SLR trên màn hình cảm ứng 7 inch (1024 × 600 px) phục vụ nghiệm thu với Khoa.  
> **Định hướng hệ thống:** Đồng bộ 100% Design System (Light Theme, Typography, Button Layout) với `stt-app` để thuận tiện hợp nhất Kiosk sau này.

---

## 1. Hệ Màu & Typography (Đồng Bộ `stt-app`)

| Thành phần | Mã màu HEX / Quy chuẩn | Ghi chú vai trò |
| :--- | :--- | :--- |
| **Nền tổng thể Kiosk** | `#F5F7F9` | Nền sáng xám trung tính, chống mỏi mắt trên màn 7 inch |
| **Bề mặt thẻ / Panel** | `#FFFFFF` | Thẻ bảng kết quả và các khối chứa nội dung chính |
| **Đường viền ngăn cách** | `#BAC5D0` | Viền chuẩn 1px–2px, sắc nét, không dùng đổ bóng mờ ảo |
| **Màu chữ chính** | `#18212B` | Chữ hiển thị từ dự đoán, tiêu đề, độ tương phản cao |
| **Màu chữ phụ** | `#4F5D6B` | Nhãn trạng thái, thông số phụ |
| **Nút hành động chính** | `#273D53` | Nền nút "Bắt đầu [R]", "Xác nhận & phát [F]" (chữ trắng `#FFFFFF`) |
| **Nút hành động phụ** | `#FFFFFF` / Viền `#BAC5D0` | Nền nút "Thử lại [R]" (chữ `#18212B`) |
| **Font chữ & Bộ icon** | `Inter` (sans-serif) + Lucide SVG | Nét mảnh hiện đại, không dùng emoji |

---

## 2. Bố Cục Không Gian 2 Cột (1024 × 600 px Không Cuộn)

Thiết bị chạy ở độ phân giải cố định `1024 × 600` (chiều cao khả dụng trừ thanh tiêu đề gọn là `560px`):

```
+-----------------------------------------------------------------------------------+
|  PBL6 · NHẬN DẠNG KÝ HIỆU TIẾNG VIỆT                            [Kiosk 1024×600]  |  Header (40px)
+-----------------------------------------------------------------------------------+
|                             |                                                     |
|   CỘT TRÁI: CAMERA VIEW     |   CỘT PHẢI: BẢNG KẾT QUẢ & ĐIỀU KHIỂN               |
|   (Tỷ lệ 1.15fr ~ 540px)    |   (Tỷ lệ 1.0fr ~ 440px)                             |
|                             |                                                     |
|   - Luồng camera 640×480    |   - Tiêu đề trạng thái: KẾT QUẢ / SẴN SÀNG          |
|   - Không lật gương (gốc)   |   - Hàng từ chính: DÀI (40px font-bold)             |
|   - Không vẽ viền người giả |   - Hàng gợi ý phụ: [Dài] [Cảm ơn] [Nước]           |
|   - Số đếm ngược 3s to      |                                                     |
|     khổng lồ (250px), màu   |   - BẢNG ĐO THỜI GIAN 4 DÒNG (Semantic Mode B):     |
|     vàng trong suốt (#F59E0B/30)| [pipeline]                     1.20s (Highlight)|
|   - Viền đổi màu:           |     [mediapipe extraction]     1.13s                |
|     + Sẵn sàng: #BAC5D0     |     [tiền xử lý]               0.02s                |
|     + Đếm ngược 3s: #D97706 |     [SL-GCL forward first ...] 0.05s                |
|     + Đang quay 4s: #DC2626 |                                                     |
|     + Thanh progress đỏ đáy |   - CẶP NÚT CẢM ỨNG CHUẨN (52px):                   |
|                             |     [ (Loa) Xác nhận & phát  F ]   [ (Xoay) Thử lại R ]|
+-----------------------------------------------------------------------------------+
```

---

## 3. Quy Chuẩn Chi Tiết Từng Vùng

### 3.1. Cột Trái — Khung Camera Cố Định 640 × 480
1. **Luồng hình ảnh:**
   - Đọc trực tiếp từ camera USB rời Aioneus qua OpenCV (`cv2.CAP_DSHOW` trên Windows hoặc V4L2 trên Linux Pi 4).
   - **Lật gương tách tầng (UI Mirrored / Backend Raw):** Áp dụng `transform: scaleX(-1)` riêng lên phần tử ảnh `<img id="preview">` trên giao diện để người ký nhìn thuận mắt như soi gương (chữ trạng thái và số đếm ngược vẫn xuôi chiều), trong khi luồng video thu tại Backend (`demo.py`) giữ nguyên hướng gốc không lật để đồng bộ 100% với `handedness.py` và `normalization.py`. Chi tiết xem tại [CO_CHE_LAT_GUONG_UI_VA_PIPELINE_SLR.md](file:///C:/Users/LAPTOP%20T&T/VIOLETTA/Documents/ChatGPT/PBL6/mynotes/CO_CHE_LAT_GUONG_UI_VA_PIPELINE_SLR.md).
   - **Không vẽ khung viền nét đứt đầu–vai cố định:** Thuật toán tự động tìm `shoulder_midpoint` và chia tỷ lệ cho `shoulder_width` bất biến với vị trí người đứng trong khung.
2. **Trạng thái viền Camera:**
   - `Sẵn sàng (ready)`: Viền xám trung tính `#BAC5D0` (3px).
   - `Đếm ngược 3s (countdown)`: Viền vàng hổ phách `#D97706` (3px).
   - `Đang quay 4s (recording)`: Viền đỏ `#DC2626` (3px) kèm thanh tiến trình (progress bar) mảnh 6px chạy rút ngắn dần từ `4.0s → 0.0s` ngay sát mép đáy camera.
3. **Số đếm ngược khổng lồ (Countdown Number):**
   - Kích thước: `250px`, `font-black`, căn chính giữa khung camera.
   - Màu sắc & Hiệu ứng: Màu vàng hổ phách trong suốt **`#F59E0B / 30% opacity`**, không làm mờ (không blur), nhìn xuyên thấu rõ cử chỉ chuẩn bị của người ký phía sau.

### 3.2. Cột Phải — Bảng Kết Quả & Điều Khiển
1. **Từ dự đoán (Gloss):**
   - Từ Top-1 hiển thị lớn `40px–48px`, font-bold, màu `#18212B`.
   - Ngay bên cạnh/dưới là các chip gợi ý Top-2, Top-3 (ví dụ: `Cảm ơn`, `Nước`). Người dùng chạm vào chip nào thì từ đó đổi thành từ đang chọn.
2. **Bảng đo thời gian (Timing Breakdown — Chuẩn Mode B Semantic Highlighting):**
   - **Dòng 1 — Tổng toàn trình (Nổi bật):** Nền vàng hổ phách `#FFF8E1`, viền nhấn `#FDE68A`. Nhãn `pipeline` viết hoa font-mono chữ đậm trên badge `#FDE68A`, số giây `1.20s` (bold, `#78350F`). Đã loại bỏ chữ thừa *"Tổng toàn trình"*.
   - **Dòng 2 — Trích xuất khớp:** Nhãn `mediapipe extraction` (`background-color:#DFF8FC; color:#087789; font-weight:700;`), số giây `1.13s`.
   - **Dòng 3 — Tiền xử lý mảng:** Nhãn `tiền xử lý` (`background-color:#F0E9FF; color:#713DB0; font-weight:700;`), số giây `0.02s`.
   - **Dòng 4 — Mô hình suy luận:** Nhãn `SL-GCL forward first inference` (`background-color:#FBE7F0; color:#B22563; font-weight:700;`), số giây `0.05s`.
   *(Toàn bộ các dòng đều đã xóa bỏ phần text mô tả màu xám rườm rà).*
3. **Cặp nút cảm ứng tròn (Chuẩn Touch Kiosk 68px — Approved 15/11/2026):**
   - **Nút Tròn Loa (Xác nhận & phát):** Nút tròn đường kính lớn `68px`, nền xanh sẫm `#273D53` (hover `#1D2F41`), viền nhấn `#38536F`, icon loa trắng `28px` căn chính giữa. Phía dưới nút là nhãn chữ `Xác nhận & phát` kèm phím tắt cơ học **`[F]`** (`#E2E8F0`, viền `#CBD5E1`).
   - **Nút Tròn Retry (Thử lại):** Nút tròn đường kính lớn `68px`, nền trắng `#FFFFFF` (hover `#F8FAFC`), viền xám `#BAC5D0`, icon xoay lại `26px` màu `#18212B`. Phía dưới nút là nhãn chữ `Thử lại` kèm phím tắt **`[R]`** (`#F1F5F9`, viền `#CBD5E1`).
   - *Ưu điểm:* Vùng chạm cảm ứng ngón tay siêu lớn, tách biệt độc lập icon và chữ nên giải quyết triệt để vấn đề đè chữ, mang lại diện mạo trực quan và hiện đại cho Kiosk.
   - Cả 2 nút hỗ trợ song song chạm màn hình cảm ứng hoặc bấm phím vật lý `F` / `R` từ vị trí đứng ký.

---

## 4. Bảng Kiểm Thử Nghiệm Thu (Acceptance Criteria Cho Khoa)

- [ ] Hiển thị vừa khít toàn màn hình `1024 × 600`, không sinh thanh cuộn dọc/ngang.
- [ ] Số đếm ngược `3 → 2 → 1` to `250px` màu vàng trong suốt hiển thị rõ ràng trên camera.
- [ ] Thanh đỏ 4s chạy mượt mà sát đáy camera và tự động dừng sau 4 giây (tối đa 150 frames).
- [ ] Hiển thị đầy đủ 4 chỉ số thời gian chính xác từ `report["seconds"]`.
- [ ] Bấm **`Xác nhận & phát [F]`** phát đúng file MP3 tiếng Việt tương ứng (`95.mp3` cho "Dài", cùng trọn bộ 400/400 file `.mp3` trong `local_data/tts/`).
- [ ] Bấm **`Thử lại [R]`** xóa sạch kết quả cũ, reset trạng thái về đầu.
