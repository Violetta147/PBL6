# Nghiên cứu thứ tự hội thoại trong Lịch sử

**PBL6 · 07/11/2026.** Đối chiếu mã đi kèm các bản cài trên Windows và tài liệu chính thức. Phần so sánh tập trung vào mốc thời gian quyết định vị trí của một hội thoại trong danh sách.

## Đối chiếu ba ứng dụng

| Ứng dụng | Quy tắc sắp xếp | Tác động của thao tác thông thường |
| --- | --- | --- |
| **DeepSeek Harness `0.2.1-rc.5`** | Mặc định **Last updated**, sắp từ mới đến cũ theo thời điểm người dùng gửi lời nhắn gần nhất. Phiên ghim đứng trước phiên thường. DSH cũng hỗ trợ sắp xếp thủ công. | Mở lại hoặc đổi tên giữ nguyên mốc lời nhắn. Một lời nhắn mới có thể đưa phiên lên đầu nhóm đang hiển thị. [Tài liệu UI Workspace](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-workspace/README.md#reordering-and-view-options) |
| **Codex Desktop `26.1103.4239.0`** | Mã trong bản cài có các lựa chọn **Last updated** và **Created**. Phần **Recents** dùng mốc hoạt động riêng `recency_at` trong luồng đã kiểm tra. | Theo tài liệu App Server, mở lại giữ nguyên `updatedAt`, còn bắt đầu lượt mới cập nhật mốc đó. Riêng API `thread/list` mặc định sắp theo ngày tạo khi phía gọi bỏ trống tùy chọn sắp xếp. [OpenAI Docs — Codex App Server](https://learn.chatgpt.com/docs/app-server) |
| **LearnHarness `0.5.0`** | Sắp theo `updatedAt` giảm dần. Hàm lưu danh sách tin nhắn cập nhật mốc này. | Đổi tên và đổi cài đặt của phiên giữ nguyên mốc sắp xếp. [Mã sắp xếp và lưu tin](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/src/store/chats.ts#L115) · [Mã đổi tên và lưu cài đặt](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/src/store/chats.ts#L167) |

## Quyết định cho PBL6

Nhóm chọn quy tắc **Last updated** của DeepSeek Harness cho danh sách **Lịch sử**. Hội thoại có **tin nhắn được gửi thành công gần nhất** đứng đầu. Khi gửi tin đầu tiên, hội thoại xuất hiện trong danh sách. Gửi thêm tin đưa hội thoại lên đầu. Mở lại để xem, đổi tên hoặc bấm **Đọc to** giữ nguyên vị trí.

Ví dụ, người dùng mở một hội thoại từ hôm qua và đổi tên. Hội thoại vẫn ở vị trí cũ. Nếu nhóm chốt cho nhắn tiếp vào hội thoại đã mở lại, việc gửi thành công một tin mới sẽ đưa hội thoại đó lên đầu. [Đặc tả UI/UX PBL6](../STT_PRODUCT_UI_UX.md)
