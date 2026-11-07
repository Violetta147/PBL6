# Khảo sát nút Đọc to trong các ứng dụng harness

**PBL6 · 07/11/2026 · Tạm hoãn.** Phần này lưu các quan sát để tham khảo khi nhóm quay lại thiết kế **Text-to-Speech (TTS)**. Giải pháp tạo và phát giọng của PBL6 sẽ được chọn riêng cho Raspberry Pi và phải hoạt động độc lập với gói đăng ký ChatGPT.

## Kết quả khảo sát

| Ứng dụng | Điều đã xác nhận |
| --- | --- |
| **Codex Desktop** | Ảnh tham chiếu và mã bản cài cho thấy icon **Đọc to** dưới phản hồi đã hoàn tất. Nút đọc đúng phản hồi được chọn, hiện trạng thái tải và đổi thành **Dừng đọc** khi phát. Chọn đọc phản hồi khác dừng lượt phát hiện tại. Mã phía ứng dụng cho thấy yêu cầu tạo âm thanh được gửi tới dịch vụ của ChatGPT. Mô hình giọng cụ thể chưa được xác định qua mã đã rà. |
| **DeepSeek Harness `0.2.1-rc.5`** | Trong bản cài đã rà, tính năng giọng nói xác nhận được là **thu giọng thành chữ**. Plugin bên thứ ba `dsh-plugin-speech` là ví dụ về cách bổ sung nút phát/dừng dưới từng phản hồi. Plugin nhận văn bản ở máy chủ và truyền âm thanh về giao diện. [Tài liệu Voice Input của DSH](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/voice-input.md) · [Mã và tài liệu plugin](https://github.com/NakamuraIA/dsh-plugin-speech#what-it-does) |
| **LearnHarness `0.5.0`** | **Dictate** thu âm từ mic và đưa chữ nhận dạng bằng Deepgram vào vùng soạn. Trong phần mã giao diện đã rà, chưa thấy nút đọc to từng tin. [Tài liệu Dictation của LearnHarness](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/docs/getting-started.md#dictation) |

## Tham chiếu cho PBL6

Giữ ảnh Codex làm tham chiếu cho **icon loa đi theo từng tin nhắn**. Trong PBL6, **Gửi** và **Đọc to** là hai thao tác riêng. Vị trí nút loa, nội dung được đọc và cách tạo giọng sẽ được chốt khi nhóm quay lại phần TTS. [Tài liệu UI/UX PBL6](../STT_PRODUCT_UI_UX.md)
