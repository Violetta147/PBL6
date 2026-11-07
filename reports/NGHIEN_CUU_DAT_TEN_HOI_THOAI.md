# Nghiên cứu cách đặt tên hội thoại cho PBL6

**Đối chiếu ngày 07/11/2026.** Kiểm tra mã và cấu hình đi kèm Codex Desktop, DeepSeek Harness và LearnHarness trên Windows. Đối chiếu thêm tài liệu chính thức để phân biệt cách tạo tên ban đầu, cách đổi tên và mã định danh của hội thoại.

## 1. Cách ba ứng dụng đặt tên

| Ứng dụng | Tạo tên ban đầu | Đổi tên và lưu tên |
| --- | --- | --- |
| **Codex Desktop** · bản cài `26.1103.4239.0` | <strong style="color:#087789;">Tên tạm từ lời nhắn</strong>, sau đó một lượt gọi mô hình ở nền có thể tạo tiêu đề ngắn. Bản cài có thêm cơ chế tùy cấu hình để xem xét lại tên khi trọng tâm cuộc trò chuyện thay đổi. | Tên được lưu theo `threadId` qua `thread/name/set`. Luồng tạo tên đã kiểm tra chỉ ghi kết quả nếu tiêu đề hiện tại vẫn khớp tên mà luồng đó dự kiến. [OpenAI Docs — Codex App Server](https://learn.chatgpt.com/docs/app-server) |
| **DeepSeek Harness** · `dsh 0.2.1-rc.5` | Cấu hình cơ sở tạo tên tạm từ các từ đầu tiên của tin nhắn có chữ, giới hạn 5 từ và 40 byte. Sau đó, mô hình <strong style="color:#087789;">tóm tắt tin đầu tiên một lần</strong>. Bản cài còn đóng gói chế độ thử nghiệm dựa trên nhiều tin nhắn của người dùng. [Tạo tên từ tin đầu](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/session/session-title-first-prompt-llm/README.md) · [Tạo tên từ nhiều tin](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/experimental/session-title-all-prompts-llm/README.md) | Khi đổi tên, DSH <strong style="color:#087789;">ghim tên người dùng đặt</strong>. Tên được lưu như một sự kiện của phiên. Yêu cầu tạo lại tên là thao tác riêng. [Tài liệu Session Titles](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/session-title) |
| **LearnHarness** · `0.5.0` | Hàm `titleFromPrompt()` <strong style="color:#087789;">rút gọn trực tiếp câu mở đầu</strong>. Hàm gộp khoảng trắng và xuống dòng, rồi ưu tiên cắt ở ranh giới từ quanh mốc 72 ký tự. Cách này chạy tại chỗ khi tạo phiên. | Bấm tiêu đề để sửa. Ứng dụng lưu tên mới vào bản ghi theo ID hiện có và cập nhật mục trong danh sách phiên. |

**Dấu vết trong bản cài.** Ở Codex Desktop, phần tạo tên tạm, gọi mô hình và kiểm tra tên hiện tại nằm trong `webview/assets/async/182735.bb2cb0d2af.js` bên trong `app.asar`. Ở DSH, cấu hình cơ sở nằm trong `dsh/node_modules/@deepseek-ai/dsh-base/cordis.patch.yml` bên trong `app.asar`. Với LearnHarness, các đoạn đã đối chiếu nằm trong thư mục `resources/server/standalone` của bản cài. [Hàm tạo tên của LearnHarness](<C:/Users/LAPTOP T&T/AppData/Local/Programs/learnharness/resources/server/standalone/src/core/contracts/graph.ts:359>) · [Thao tác đổi tên của LearnHarness](<C:/Users/LAPTOP T&T/AppData/Local/Programs/learnharness/resources/server/standalone/components/chat.tsx:278>)

**Phạm vi xác nhận.** Kết quả dựa trên đọc mã, cấu hình đi kèm và tài liệu. Mức độ áp dụng chế độ xem xét lại tên của Codex hoặc chế độ tạo tên từ nhiều tin của DSH trong một phiên cụ thể cần kiểm tra riêng khi chạy.

## 2. Phương án đề xuất cho PBL6

1. Khi gửi thành công tin đầu tiên, hội thoại xuất hiện trong **Lịch sử**. <strong style="color:#087789;">Dùng chính tin đã gửi để tạo tên ban đầu</strong> theo cách của LearnHarness. Gộp khoảng trắng, rút gọn câu dài ở ranh giới từ và thêm dấu ba chấm khi cần.
2. Có thao tác **Đổi tên** cho hội thoại đã lưu. <strong style="color:#087789;">Tên hiển thị và ID được lưu riêng</strong>. Khi người dùng đổi tên, các tin cũ vẫn thuộc cùng hội thoại.

Ví dụ, nếu tin đầu tiên là “Mai gặp lúc mấy giờ?”, ứng dụng dùng câu đó làm tên. Người dùng có thể đổi thành “Hẹn giờ gặp”. <strong style="color:#6E4900;">Câu mở đầu chung chung</strong> như “Chào bạn” sẽ cho tên chung chung. Nếu gặp tình trạng này thường xuyên khi dùng thử, nhóm có thể cân nhắc gợi ý tên từ vài tin đã gửi và giữ ưu tiên cho tên người dùng đã đặt. [Quy tắc hội thoại trong tài liệu UI/UX](../STT_PRODUCT_UI_UX.md)
