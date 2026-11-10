# Khảo sát nút Gửi trong lúc thu và chờ nhận dạng

**PBL6 · 10/11/2026.** Đối chiếu hai thời điểm người dùng có thể bấm **Gửi** trong vùng soạn. Thời điểm thứ nhất là khi mic còn thu. Thời điểm thứ hai là khi mic đã dừng và chữ chưa về.

## Kết quả đối chiếu

| Ứng dụng | Bấm Gửi khi đang thu | Bấm Gửi khi đang chờ chữ |
| --- | --- | --- |
| **DeepSeek Harness `0.2.1-rc.5`** | Thanh thu có nút **Dừng** riêng. Thao tác **Gửi** vẫn xử lý bản nháp theo điều kiện gửi thông thường. | **Gửi** không đợi kết quả nhận dạng. Khi có chữ, app thử chèn vào vị trí đã lưu. Nếu vị trí đó hết hiệu lực, app giữ chữ để người dùng bấm **Chèn**. [Mã chèn chữ](https://github.com/deepseek-ai/deepseek-harness/blob/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159/packages/experimental/client-ui-voice-input/src/client/VoiceInput.tsx#L107-L134) · [Kiểm thử Dừng và Gửi](https://github.com/deepseek-ai/deepseek-harness/blob/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159/packages/experimental/client-ui-voice-input/tests/voice-input.client.spec.tsx#L49-L60) |
| **LearnHarness `0.5.0`** | **Gửi** dừng thu và đợi lượt nhận dạng kết thúc. App ghép chữ nhận được vào bản nháp trước khi đọc bản nháp để gửi. | Nếu đã dừng thu, **Gửi** đợi cùng lượt đó. Mã gửi đọc lại bản nháp mới nhất sau khi chờ. [Mã nút Gửi](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/components/chat.tsx#L1202-L1232) · [Mã dừng và chờ](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/components/dictation.tsx#L499-L546) |
| **Codex Desktop Windows `26.1103.7773.0`** | **Gửi** yêu cầu dừng thu, đợi chữ rồi gửi. Nút dừng mic có đường riêng để đưa chữ vào ô soạn. | Nếu người dùng đã dừng mic để chèn chữ, **Gửi** có thể đổi lượt đang chờ sang chèn rồi gửi. Khi đã nhận yêu cầu gửi, nút hiện trạng thái chờ và khóa lần bấm tiếp theo. |
| **Antigravity App Windows `2.29.0`** | Trong chế độ hiện chữ trực tiếp, **Gửi** dừng thu, đợi nhận dạng hoàn tất rồi gửi. Nút có chú thích *Stop Recording and Send*. | **Gửi** có thể đợi lượt nhận dạng đang hoàn tất rồi gửi. App hiện trạng thái đang gửi sau khi nhận yêu cầu. [Tài liệu nhập giọng nói của Google](https://antigravity.google/docs/features#voice-transcription) |

<strong style="color:#946200;">Phạm vi kiểm chứng.</strong> Đối chiếu mã và tài liệu. Chưa thử các thao tác bằng mic thật. DSH được đối chiếu giữa bản cài và mã công khai cố định ở các liên kết trên. Codex được kiểm tra trong `app.asar`, ở `webview/assets/async/309406.8bbeca04ca.js` và `webview/assets/async/202026.1f4062c12e.js`. Antigravity được kiểm tra trong `main.js` của `resources/bin/language_server.exe` trên bản cài App. Antigravity IDE cũ có đường gửi tệp âm thanh riêng. [Khảo sát Antigravity trước đó](NGHIEN_CUU_COMPOSER_ANTIGRAVITY.md)

## Quyết định cho PBL6 V1

<strong style="color:#087A47;">Bấm Gửi trong lúc thu sẽ dừng thu, đợi nhận dạng rồi tự gửi câu hoàn chỉnh.</strong> Nếu người dùng đã bấm hình vuông và chữ chưa về, bấm **Gửi** yêu cầu gửi sau khi cùng lượt nhận dạng đó kết thúc. Khi chữ về, app chèn theo vị trí con trỏ đã chốt, rồi gửi toàn bộ bản nháp đã ghép đúng một lần. Bản nháp vẫn nhận chỉnh sửa và di chuyển con trỏ trong lúc chờ.

**Bấm hình vuông để dừng và xem lại chữ.** Nếu người dùng chỉ bấm hình vuông, kết quả vào ô soạn để đọc và sửa. Khi muốn đưa câu vào hội thoại, người dùng bấm **Gửi**.

**Phản hồi sau khi bấm Gửi.** PBL6 giữ chữ **Gửi**, làm mờ và tạm khóa nút trong lúc chờ chữ. Vòng xoay vẫn ở nút mic. Nếu chỉ dừng bằng hình vuông, nút **Gửi** còn bấm được.

**Khi nhận dạng lỗi**, app bỏ yêu cầu gửi đang chờ, giữ bản nháp và hiện báo lỗi ở vị trí chung cạnh mic. Khi nhận dạng thành công nhưng gửi tin lỗi, app giữ bản nháp đã ghép để người dùng xử lý theo quy tắc gửi lỗi hiện có. [Đặc tả vùng soạn và tiêu chí duyệt](../STT_PRODUCT_UI_UX.md#2-thu-sửa-và-gửi-trong-vùng-soạn-chung)

**Khi nhận dạng xong mà không có chữ**, PBL6 dùng trạng thái `completed_empty` đã có từ P1. Nút mic trở lại, bản nháp được giữ, yêu cầu tự gửi bị bỏ và **Gửi** trở về trạng thái theo nội dung ô soạn. Mic trở lại là phản hồi của giao diện cho trường hợp này. [Mã trả kết quả của P1](../stt-app/src/server/deepgram.ts#L31-L36)

**Khi chuyển hội thoại**, PBL6 hủy lượt đang thu hoặc đang chờ chữ, kể cả khi đã bấm **Gửi**. Kết quả đến sau bị bỏ qua. Chỉ mở bảng **Lịch sử** để xem danh sách thì lượt thu vẫn tiếp tục. Mã LearnHarness hủy lượt thu khi rời màn hình và vô hiệu hóa các thao tác đang chờ. [Mã LearnHarness](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/components/dictation.tsx#L564-L571)
