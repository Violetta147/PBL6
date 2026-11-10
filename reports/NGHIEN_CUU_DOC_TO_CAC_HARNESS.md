# Khảo sát nút Đọc to trong các ứng dụng harness

**PBL6 · Cập nhật 10/11/2026.** Phần này lưu các quan sát phục vụ thiết kế **Đọc to (TTS)**. Giải pháp tạo và phát giọng của PBL6 sẽ được chọn riêng cho Raspberry Pi và phải hoạt động độc lập với gói đăng ký ChatGPT.

## Kết quả khảo sát

| Ứng dụng | Điều đã xác nhận |
| --- | --- |
| **Codex Desktop** | Ảnh tham chiếu và mã bản cài cho thấy icon **Đọc to** dưới phản hồi đã hoàn tất. Nút đọc đúng phản hồi được chọn, hiện trạng thái tải và đổi thành **Dừng đọc** khi phát. Chọn đọc phản hồi khác dừng lượt phát hiện tại. Mã phía ứng dụng cho thấy yêu cầu tạo âm thanh được gửi tới dịch vụ của ChatGPT. Mô hình giọng cụ thể chưa được xác định qua mã đã rà. |
| **DeepSeek Harness `0.2.1-rc.5`** | Trong bản cài đã rà, tính năng giọng nói xác nhận được là **thu giọng thành chữ**. Plugin bên thứ ba `dsh-plugin-speech` là ví dụ về cách bổ sung nút phát/dừng dưới từng phản hồi. Plugin nhận văn bản ở máy chủ và truyền âm thanh về giao diện. [Tài liệu Voice Input của DSH](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/voice-input.md) · [Mã và tài liệu plugin](https://github.com/NakamuraIA/dsh-plugin-speech#what-it-does) |
| **LearnHarness `0.5.0`** | **Dictate** thu âm từ mic và đưa chữ nhận dạng bằng Deepgram vào vùng soạn. Trong phần mã giao diện đã rà, chưa thấy nút đọc to từng tin. [Tài liệu Dictation của LearnHarness](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/docs/getting-started.md#dictation) |

## Tham chiếu cho PBL6

**Kiểm tra lại Codex Desktop trên Windows.** Ba ảnh người dùng gửi cho thấy nút loa, vòng xoay khi tải và hình vuông khi đang phát. Mã trong bản cài `26.1103.7773.0` (`resources/app.asar`, `webview/assets/async/708390.17710d5ff1.js`, mô-đun `DM5G`) cho thấy nút truyền mã của tin vừa chọn cho bộ phát. Nếu đang có lượt của tin khác, bộ phát dừng âm thanh và hủy xử lý của lượt cũ trước khi đưa tin mới vào trạng thái chờ. Mã cũng kiểm tra lượt còn hiệu lực trước khi phát, nên kết quả cũ về muộn không phát trở lại. Kết luận dựa trên đọc mã và ảnh tham chiếu. Chưa thử phát âm thanh A rồi chuyển sang B trên ứng dụng.

**Đã chốt cho PBL6.** **Gửi** và **Đọc to** là hai thao tác riêng. Chỉ đọc từng tin đã gửi. Khi đang đọc tin A mà người dùng chạm loa ở tin B, dừng A ngay và chuyển sang B. Dùng ba trạng thái của Codex làm tham chiếu khi duyệt giao diện nút. [Tài liệu UI/UX PBL6](../STT_PRODUCT_UI_UX.md)
