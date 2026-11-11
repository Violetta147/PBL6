# Khảo sát nút hội thoại mới trong Codex Desktop

**PBL6 · Cập nhật 12/11/2026.** Phần này lưu quan sát về cách Codex Desktop xử lý nút **New chat**, để thiết kế nút **+ Hội thoại mới** trong Lịch sử.

## Kết quả khảo sát

| Điều đã quan sát | Cơ sở |
| --- | --- |
| Nút **New chat** ở thanh bên chuyển sang route `"/"`, tức màn soạn trống. Nút này không tạo hội thoại. | Bản cài `26.1106.6628.0` (`resources/app.asar`, mô-đun thanh bên của webview): hành động gọi `navigate("/", {state: ...})`. |
| Hội thoại thật được tạo khi gửi lượt đầu tiên. | Mã gọi `startConversation(...)` với `onFirstTurnReady` và `afterConversationCreated`. Callback chạy sau khi hội thoại đã được tạo. |
| Chưa thấy đoạn mã kiểm tra "hội thoại hiện tại còn trống" để chặn hoặc tái dùng. | Tìm theo các từ khóa về hội thoại trống và `newThread`, chỉ thấy nhãn giao diện. Có thể không cần kiểm tra vì màn `"/"` chưa phải hội thoại. |

Kết luận về hành vi dựa trên đọc mã, chưa thử bấm trong ứng dụng. Việc không thấy đoạn kiểm tra hội thoại trống là kết quả tìm kiếm, chưa phải bằng chứng rằng không có.

## Tham chiếu cho PBL6

**Đã chốt cho PBL6.** **+ Hội thoại mới** mở một màn soạn trống chưa lưu. Hội thoại chỉ vào **Lịch sử** sau khi gửi thành công tin đầu tiên. Nếu màn đang mở đã trống, nút chỉ đóng bảng Lịch sử. Nếu có bản nháp chưa gửi, bản nháp bị bỏ theo quy tắc bản nháp. [Tài liệu UI/UX PBL6](../STT_PRODUCT_UI_UX.md)
