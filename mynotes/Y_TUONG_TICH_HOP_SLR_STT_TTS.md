# [CHƯA CHỐT - BẢN NHÁP LƯU TRỮ] Ý TƯỞNG TÍCH HỢP HÀI HÒA SLR + STT + TTS TRÊN KIOSK 1024×600

> [!WARNING]
> **Trạng thái tài liệu: CHƯA CHỐT (Bản nháp lưu trữ ý tưởng để quyết định sau).**
>
> Hiện tại `slr-app` vẫn phát triển và tối ưu độc lập để hoàn thành nghiệm thu MVP nhận dạng ký hiệu đơn với Khoa. Tài liệu này chỉ lưu lại các phương án bố cục kết hợp **SLR** (Camera nhận diện ký hiệu) + **STT** (Micro & vùng soạn thảo) + **TTS** (Phát giọng nói) cho giai đoạn sau, khi Quân thấy mô hình SLR đã đủ chín để hợp nhất thành một ứng dụng Kiosk chung.

---

## 1. Bối cảnh & Nguyên tắc Hợp nhất

- **Đồng bộ Design System ngay từ đầu:** Cả `slr-app` và `stt-app` cùng dùng chung **Light Theme** (`#F5F7F9` nền, `#FFFFFF` thẻ/panel, `#BAC5D0` viền, `#18212B` chữ chính, `#4F5D6B` chữ phụ, `#273D53` nút hành động chính), font `Inter` và bộ icon `Lucide` trên độ phân giải mục tiêu **1024 × 600 px**.
- **Lý do chưa gộp thành dạng chat ngay lúc này:** `stt-app` hiện thiết kế theo luồng hội thoại giống ứng dụng nhắn tin (nhập/thu từng câu dài qua micro, chỉnh sửa theo con trỏ rồi bấm Gửi). Trong khi đó, bản MVP của `slr-app` mới nhận diện **từng ký hiệu đơn lẻ mỗi lượt** (`3s` chuẩn bị + `4s` quay) và chỉ phát âm thanh xác nhận. Việc ghép cưỡng ép ngay sẽ gây lủng củng trải nghiệm.

---

## 2. Ghi chú về Dải Lưu Từ Đã Xác Nhận (Confirmed Signs Strip)

- **Bản chất kỹ thuật:** Là tính năng **100% Frontend** (lưu mảng tạm trên state React/trình duyệt, gần như không tốn chi phí hay sửa API backend).
- **Tính tương thích với quy tắc "Xác nhận 2 bước":** Không mâu thuẫn nếu áp dụng đúng thứ tự:
  1. Mô hình trả về kết quả → người dùng kiểm tra (không tự phát tiếng).
  2. Nếu bấm **Thử lại `[R]`** → hủy kết quả, không lưu vào dải.
  3. Chỉ khi người dùng bấm **Xác nhận & phát `[F]`** → vừa phát tiếng ra loa, vừa đẩy từ đã xác nhận vào dải chip tích lũy.
- **Quyết định tạm thời:** Tạm giữ `slr-app` ở dạng 1 ký hiệu/lượt theo đúng kỳ vọng MVP của Khoa; giữ ý tưởng dải tích lũy này làm cầu nối cho **Phương án B** khi tích hợp vào `stt-app` sau này.

---

## 3. Ba Phương Án Bố Cục Tham Khảo Cho Giai Đoạn Hợp Nhất (1024 × 600)

### Phương án A — Chuyển đổi Chế độ Linh hoạt trên cùng Header 56px (Tab / Mode Switcher)
- Giữ chung 1 thanh Header gọn ở cạnh trên (`56px`) gồm công tắc chuyển nhanh 2 chế độ: `[🎙️ Giọng nói (STT)]` ↔ `[✋ Ký hiệu (SLR)]`.
- **Ưu điểm:** Mỗi màn hình vẫn giữ trọn không gian `1024 × 544` rộng rãi để hiển thị khung camera SLR hoặc ô soạn thảo + bàn phím ảo Squeekboard khi dùng STT; không bị chật chội trên màn 7 inch.

### Phương án B — SLR Đẩy Từ Vào Vùng Soạn Chung (Composer) Của STT + TTS
- Mở rộng dải từ đã xác nhận ở SLR: Thay vì chỉ lưu thụ động, người dùng ký có thể ghép vài ký hiệu liên tiếp thành cụm/câu ngắn, sau đó bấm nút **Đưa vào hội thoại** để đẩy thẳng vào vùng soạn thảo (Composer) chung của `stt-app`, nơi vừa gõ sửa được vừa bấm **Gửi** hoặc **Đọc to (TTS)**.
- **Điều kiện áp dụng:** Phù hợp khi mô hình SLR hỗ trợ nhận diện liên tục hoặc tốc độ xử lý đủ nhanh để ghép nhiều từ thành câu tự nhiên.

### Phương án C — Chia Đôi Màn Hình Song Công (Dual-Pane Kiosk 1024 × 600)
- **Nửa trái (~420px):** Khung Camera SLR thu gọn (tỷ lệ dọc/vuông) + 2 nút `Bắt đầu [R]` / `Xác nhận [F]`.
- **Nửa phải (~580px):** Khung hội thoại STT + nút Micro + dải TTS đọc to tin nhắn.
- **Thách thức cần khảo sát thêm:** Phải kiểm tra thực tế trên màn 7 inch khi mở bàn phím ảo Squeekboard xem vùng Camera bên trái có bị che hoặc co quá nhỏ khi đứng xa ký hiệu hay không.
