# Khảo sát xử lý khi gửi tin thất bại trong Codex Desktop và LearnHarness

**PBL6 · Cập nhật 12/11/2026.** Phần này lưu các quan sát từ mã nguồn của LearnHarness `v0.5.0` và Codex Desktop `26.1106.6628.0` về cơ chế giữ bản nháp, hiển thị lỗi và cho phép thử lại khi gửi tin nhắn thất bại, phục vụ thiết kế V1 của PBL6.

## Kết quả khảo sát

| Ứng dụng | Điều đã xác nhận qua mã |
| --- | --- |
| **LearnHarness `v0.5.0`** | Khi lượt gửi thất bại (ví dụ lỗi mạng hoặc server từ chối 503), ứng dụng loại bỏ tin nhắn lạc quan khỏi danh sách hội thoại và khôi phục văn bản từ `draftRef.current` trở lại ô soạn để người dùng không mất nội dung. Lỗi được hiển thị ở một dòng cảnh báo cố định (`role="alert"`, màu `text-destructive`) gần vùng nhập. Dòng báo lỗi biến mất khi người dùng gửi lại hoặc đổi phiên. |
| **Codex Desktop `26.1106.6628.0`** | Khi gửi tin nhắn hoặc lời nhắc gặp lỗi, cấu hình gửi sử dụng cờ `draft: {kind: "preserve"}` kết hợp với thông báo lỗi dự phòng `submitErrorFallback`. Chuỗi thông báo trong mã ngắn gọn, rõ hành động khắc phục: *"Couldn't send this message. Click to retry"* hoặc *"Couldn't send that prompt. Try again."* Giao diện dùng thông báo nổi dạng toast. |

Kết luận dựa trên đọc mã nguồn và chuỗi giao diện trong bản cài, chưa chạy tương tác trực tiếp trong app.

## Tham chiếu cho PBL6

**Đã chốt cho PBL6.**
- Khi gửi tin không thành công: tin **không** xuất hiện trong vùng hội thoại và hội thoại chưa được thêm vào **Lịch sử** nếu đây là tin đầu tiên.
- Chữ đang soạn **vẫn nằm nguyên trong ô nhập** để người dùng không phải gõ hay nói lại.
- Nút **Gửi** giữ nguyên trạng thái sáng và bấm lại được ngay nếu ô nhập còn chữ.
- Thông báo lỗi hiển thị ở **vị trí thông báo chung ngay cạnh nút mic**: **“Không gửi được. Hãy thử lại.”**
- Thông báo tự động biến mất khi người dùng gõ sửa chữ, chạm mic hoặc bấm gửi lại. Nếu có thông báo khác xuất hiện, chỉ hiển thị thông báo mới nhất. [Tài liệu UI/UX PBL6](../STT_PRODUCT_UI_UX.md)
