# Khảo sát vùng soạn và bàn phím ảo trong ứng dụng chat

**PBL6 · 09/11/2026.** Đối chiếu Messenger, Codex Desktop, DeepSeek Harness và LearnHarness để chọn bố cục khi sửa câu nhận dạng trên màn cảm ứng 1024 × 600. Hai người dùng chung vùng soạn và cần thấy câu đang sửa trước khi bấm **Gửi**.

## Đối chiếu bốn ứng dụng

| Ứng dụng | Điều quan sát được | Áp dụng vào PBL6 |
| --- | --- | --- |
| **Messenger trên điện thoại** | Ảnh chính thức của Meta về thao tác sửa một tin đã gửi cho thấy bàn phím ở dưới cùng, ô sửa và nút xác nhận ở ngay phía trên, còn một phần hội thoại vẫn nhìn thấy. [Ảnh Messenger của Meta](https://about.fb.com/wp-content/uploads/2023/12/01_Edit-a-Message.jpg) | Dùng vị trí tương tự cho vùng soạn và nút **Gửi** khi bàn phím mở. Phần màn hình còn lại dành cho các tin đã gửi. |
| **Codex Desktop** | Ảnh người dùng gửi cho thấy vùng soạn nằm dưới nội dung hội thoại. Tài liệu OpenAI mô tả việc đưa chữ nhận dạng vào vùng soạn để người dùng đọc và sửa trước khi gửi. [Ảnh Codex](ui_ux_20261107/assets/codex_conversation_user_reference.png) · [Tài liệu nhập bằng giọng nói](https://learn.chatgpt.com/docs/prompting#use-voice-dictation) | Giữ câu vừa nhận dạng trong vùng soạn để hai người đọc lại. **Gửi** đưa câu vào hội thoại. |
| **DeepSeek Harness (DSH)** | Tài liệu trên nhánh `master` mô tả vùng hội thoại cuộn phía trên vùng soạn. Trên điện thoại và máy tính bảng, người dùng chạm ô nhập để mở bàn phím. Nếu ô nhập đang có con trỏ và trở về rỗng sau khi gửi thành công, DSH đóng bàn phím. [Vùng hội thoại](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-chat/README.md#scroll-ownership) · [Vùng soạn và bàn phím](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-conversation/README.md) | Dùng vùng hội thoại có thể cuộn và tự đóng bàn phím sau khi **Gửi** thành công. |
| **LearnHarness `0.5.0`** | Bài kiểm thử xác nhận thao tác gõ chỉ <strong style="color:#087789;">cập nhật vùng soạn và trạng thái nút gửi</strong>. Bài kiểm thử cũng kiểm tra trường hợp ghép chữ nhận dạng vào bản nháp trước khi gửi. [Mã kiểm thử](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/tests/chat-input-performance.test.tsx#L818) | Khi sửa chữ, giới hạn phần giao diện cần cập nhật ở vùng soạn và trạng thái nút **Gửi**. Quy tắc đưa chữ nhận dạng vào vùng soạn đã có nội dung vẫn để bàn. |

## Quyết định cho PBL6 V1

<strong style="color:#087A47;">Đã chốt bố cục khi mở bàn phím.</strong> Bàn phím ảo nằm dưới cùng. Vùng soạn và nút **Gửi** luôn thấy được ngay phía trên bàn phím. Vùng hội thoại có thể cuộn và dùng phần chiều cao còn lại. Số tin nhìn thấy phụ thuộc vào chiều cao đó và độ dài từng tin.

Khi chữ nhận dạng xuất hiện, bàn phím vẫn đóng. Người dùng chạm vùng soạn để mở bàn phím, dùng **Backspace** hoặc gõ để sửa rồi bấm **Gửi**. <strong style="color:#087A47;">Bàn phím tự đóng sau khi gửi thành công.</strong> Khi triển khai, phần cần cập nhật theo từng phím là vùng soạn và trạng thái nút **Gửi**. [Đặc tả UI/UX](../STT_PRODUCT_UI_UX.md) · [Khung Bàn phím mở](ui_ux_20261107/assets/wireframe-ban-phim-ao.png)

<strong style="color:#946200;">Chưa đo độ trễ trên Pi 4.</strong> Bảng dựa trên ảnh, tài liệu và mã kiểm thử của các ứng dụng tham chiếu. Khi có bản chạy trên Pi 4, kiểm tra thời gian từ lúc chạm tới lúc bàn phím hiện và độ trễ khi gõ tiếng Việt trong một hội thoại dài. [Hướng dẫn thử trên NH2067](../HUONG_DAN_NH2067_PI4.md#23-thử-hình-ảnh-chạm-và-bàn-phím)
