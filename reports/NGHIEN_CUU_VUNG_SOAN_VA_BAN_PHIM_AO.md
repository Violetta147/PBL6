# Khảo sát vùng soạn và bàn phím ảo trong ứng dụng chat

**PBL6 · 09/11/2026.** Đối chiếu Messenger, Codex Desktop, DeepSeek Harness và LearnHarness để chọn bố cục khi sửa câu nhận dạng trên màn cảm ứng 1024 × 600. Hai người dùng chung vùng soạn và cần thấy câu đang sửa trước khi bấm **Gửi**.

## Đối chiếu bốn ứng dụng

| Ứng dụng | Điều quan sát được | Áp dụng vào PBL6 |
| --- | --- | --- |
| **Messenger trên điện thoại** | Ảnh chính thức của Meta về thao tác sửa một tin đã gửi cho thấy bàn phím ở dưới cùng, ô sửa và nút xác nhận ở ngay phía trên, còn một phần hội thoại vẫn nhìn thấy. [Ảnh Messenger của Meta](https://about.fb.com/wp-content/uploads/2023/12/01_Edit-a-Message.jpg) | Dùng vị trí tương tự cho vùng soạn và nút **Gửi** khi bàn phím mở. Phần màn hình còn lại dành cho các tin đã gửi. |
| **Codex Desktop** | Ảnh người dùng gửi cho thấy vùng soạn nằm dưới nội dung hội thoại. Tài liệu OpenAI mô tả việc đưa chữ nhận dạng vào vùng soạn để người dùng đọc và sửa trước khi gửi. [Ảnh Codex](ui_ux_20261107/assets/codex_conversation_user_reference.png) · [Tài liệu nhập bằng giọng nói](https://learn.chatgpt.com/docs/prompting#use-voice-dictation) | Giữ câu vừa nhận dạng trong vùng soạn để hai người đọc lại. **Gửi** đưa câu vào hội thoại. |
| **DeepSeek Harness (DSH)** | Tài liệu trên nhánh `master` mô tả vùng hội thoại cuộn phía trên vùng soạn. Trên điện thoại và máy tính bảng, người dùng chạm ô nhập để mở bàn phím. Nếu ô nhập đang có con trỏ và trở về rỗng sau khi gửi thành công, DSH đóng bàn phím. [Vùng hội thoại](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-chat/README.md#scroll-ownership) · [Vùng soạn và bàn phím](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-conversation/README.md) | Dùng vùng hội thoại có thể cuộn và tự đóng bàn phím sau khi **Gửi** thành công. |
| **LearnHarness `0.5.0`** | Bài kiểm thử xác nhận thao tác gõ chỉ <strong style="color:#087789;">cập nhật vùng soạn và trạng thái nút gửi</strong>. Bài kiểm thử cũng kiểm tra trường hợp ghép chữ nhận dạng vào bản nháp trước khi gửi. [Mã kiểm thử](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/tests/chat-input-performance.test.tsx#L818) | Khi sửa chữ, giới hạn phần giao diện cần cập nhật ở vùng soạn và trạng thái nút **Gửi**. |

## Quyết định cho PBL6 V1

<strong style="color:#087A47;">Đã chốt bố cục khi mở bàn phím.</strong> Bàn phím ảo nằm dưới cùng. Vùng soạn và nút **Gửi** luôn thấy được ngay phía trên bàn phím. Vùng hội thoại có thể cuộn và dùng phần chiều cao còn lại. Số tin nhìn thấy phụ thuộc vào chiều cao đó và độ dài từng tin.

Khi chữ nhận dạng xuất hiện, bàn phím vẫn đóng. Người dùng chạm vùng soạn để mở bàn phím, dùng **Backspace** hoặc gõ để sửa rồi bấm **Gửi**. <strong style="color:#087A47;">Bàn phím tự đóng sau khi gửi thành công.</strong> Khi triển khai, phần cần cập nhật theo từng phím là vùng soạn và trạng thái nút **Gửi**. [Đặc tả UI/UX](../STT_PRODUCT_UI_UX.md) · [Khung Bàn phím mở](ui_ux_20261107/assets/wireframe-ban-phim-ao.png)

Nếu vùng soạn đã có chữ, PBL6 chèn kết quả nhận dạng tại **vị trí con trỏ**, giữa phần chữ trước và sau con trỏ.

Tin vừa gửi dùng cùng kiểu và cỡ chữ với các tin khác trong hội thoại. <strong style="color:#087A47;">Sau khi gửi thành công, vùng hội thoại tự cuộn đến tin vừa gửi.</strong> Hành vi này tham khảo cách DSH đưa người dùng về cuối danh sách khi gửi. [Tài liệu cuộn hội thoại DSH](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-chat/README.md#scroll-ownership)

<strong style="color:#946200;">Chưa đo độ trễ trên Pi 4.</strong> Bảng dựa trên ảnh, tài liệu và mã kiểm thử của các ứng dụng tham chiếu. Khi có bản chạy trên Pi 4, kiểm tra thời gian từ lúc chạm tới lúc bàn phím hiện và độ trễ khi gõ tiếng Việt trong một hội thoại dài. [Hướng dẫn thử trên NH2067](../HUONG_DAN_NH2067_PI4.md#23-thử-hình-ảnh-chạm-và-bàn-phím)

## Khi nhận dạng giọng nói thất bại

Đối chiếu mã các bản Windows đã cài ngày 10/11/2026.

- **DSH `0.2.1-rc.5`** hiện lý do ngay trong thanh thu. Nút mic ở trạng thái này bắt đầu thu một đoạn mới. Mã nằm trong `dsh/node_modules/@deepseek-ai/dsh-experimental-client-ui-voice-input/lib/client.js` bên trong `app.asar`. [Tài liệu nhập bằng giọng nói của DSH](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/voice-input.md)
- **Codex Desktop `26.1103.4239.0`** có thông báo nổi khi nhận dạng lỗi, trong đó có thông báo kiểm tra kết nối. Mã xử lý nằm trong `webview/assets/async/476181.b9a1c6297e.js` và `webview/assets/async/314290.21d21cdcbd.js` bên trong `app.asar`.
- **LearnHarness `0.5.0`** có trường hợp hiện lỗi mất kết nối ngay trên nút **Dictate**. Lần chạm tiếp theo xóa nhãn lỗi và bắt đầu lượt thu mới. [Mã kết nối](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/components/dictation.tsx#L420) · [Mã nút Dictate](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/components/dictation.tsx#L694)

<strong style="color:#087A47;">PBL6 V1 quay lại biểu tượng mic khi nhận dạng đoạn vừa thu thất bại.</strong> Giao diện giữ chữ đang soạn và chỉ hiện lại mic. Người dùng chạm mic để bắt đầu một lượt thu mới. [Đặc tả UI/UX](../STT_PRODUCT_UI_UX.md)
