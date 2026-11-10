# Khảo sát cách giữ âm thanh trong một lượt nhận dạng

**PBL6 · 10/11/2026.** Đối chiếu luồng thu giọng nói để nhập chữ của LearnHarness, Codex Desktop và DeepSeek Harness. Phần PBL6 tập trung vào lượt thu bằng mic trên Pi, sau đó bấm dừng để nhận dạng.

## Kết quả đối chiếu

| Ứng dụng | Âm thanh đi qua đâu | Cách giữ âm thanh |
| --- | --- | --- |
| **LearnHarness `0.5.0`** | `AudioWorklet` tạo từng khung PCM và gửi thẳng từ giao diện đến Deepgram qua WebSocket trong lúc thu. Chữ được gom và đưa vào ô soạn khi lượt thu kết thúc. | Khung chưa gửi trong lúc mở hoặc nối lại kết nối nằm trong mảng `ArrayBuffer` có giới hạn. Khi kết nối mở, app gửi hàng đợi rồi xóa mảng. Luồng này không tạo tệp thu. [Mã hàng đợi](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/components/dictation.tsx#L280-L357) · [Mã thu và gửi](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/components/dictation.tsx#L445-L465) |
| **Codex Desktop `26.1103.4239.0` trên Windows** | Ô soạn dùng `MediaRecorder` gom các phần âm thanh thành `Blob`. Mã có nhánh lưu bản ghi riêng cho tính năng đọc chính tả. | Khi nhánh này chạy, app ghi từng phần `.chunk` và thông tin bản ghi vào thư mục `dictation-history`. App có thể đọc các phần lại để xử lý hoặc tải bản ghi. Đây là cơ chế giữ bản ghi có điều kiện. Mã tĩnh chưa cho biết nhánh đó sẽ chạy trong cấu hình và tài khoản nào khi thử thực tế. |
| **DeepSeek Harness `0.2.1-rc.5`** | Giao diện gom các `Blob` trong lúc thu. Khi dừng, app ghép, giải mã và chuyển sang WAV, rồi chuyển dữ liệu WAV mã hóa base64 tới tiến trình xử lý. | Bộ SenseVoice tích hợp đọc mẫu âm thanh từ dữ liệu nhận được và đưa mảng `Float32Array` vào bộ nhận dạng. Mã đã rà xử lý qua bộ đệm và không tạo tệp thu. Tài liệu DSH ghi nhận kết quả vào bản nháp, còn thao tác gửi mới tạo nội dung hội thoại. [Mã gom âm thanh](https://github.com/deepseek-ai/deepseek-harness/blob/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159/packages/experimental/client-ui-voice-input/src/client/audio.ts#L143-L159) · [Mã nhận dạng](https://github.com/deepseek-ai/deepseek-harness/blob/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159/packages/experimental/speech-to-text-sensevoice/src/inference.ts#L55-L88) · [Tài liệu Voice Input](https://github.com/deepseek-ai/deepseek-harness/blob/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159/docs/subsystems/voice-input.md#browser-and-host-ownership) |

**Cách đối chiếu.** LearnHarness được kiểm tra ở mã nguồn gắn thẻ `v0.5.0`. Với Codex, đọc trực tiếp `app.asar` của bản Windows đã cài. Mã thu và lưu nằm trong `webview/assets/async/202026.1f4062c12e.js`, `webview/assets/async/886697.0ee704d200.js` và `.vite/build/early-bootstrap-199-e3316cddb4ea6a6b.js`. Với DSH, bản cài `0.2.1-rc.5` có cùng đường xử lý nêu trên trong `dsh-experimental-client-ui-voice-input/lib/client.js` và `dsh-experimental-speech-to-text-sensevoice/lib/worker.js`. Các liên kết DSH trỏ đến một commit công khai cố định để đọc đoạn tương ứng. Khảo sát dựa trên mã và tài liệu. Việc thử bằng mic, gọi dịch vụ và đo tài nguyên trên Pi vẫn chưa thực hiện.

## Áp dụng cho PBL6 V1

<strong style="color:#087A47;">Lịch sử lưu các hội thoại.</strong> Mỗi hội thoại gồm tên và các tin đã gửi. Hội thoại xuất hiện trong Lịch sử từ lần gửi thành công đầu tiên. Người dùng có thể mở lại, đọc các tin trước và gửi tiếp. [Quy tắc Lịch sử](../STT_PRODUCT_UI_UX.md#quy-tắc-lịch-sử-đã-chốt)

<strong style="color:#B22563;">Đề xuất dùng một tệp WAV tạm trên Pi cho mỗi lượt thu bằng mic.</strong> Ghi dần âm thanh vào thư mục tạm của ứng dụng. Khi bấm dừng, đóng tệp rồi dùng tệp làm đầu vào nhận dạng. Xóa tệp khi lượt thu kết thúc, kể cả khi nhận dạng thất bại hoặc bị hủy. Khi khởi động, ứng dụng dọn các tệp thu của chính nó còn sót từ lần chạy trước. Theo phương án này, bản thu tạm chỉ phục vụ nhận dạng và kết quả chữ vẫn đi vào ô soạn để người dùng đọc, sửa rồi gửi.

**Dung lượng tham khảo.** WAV mono 16 kHz, 16 bit chứa khoảng **1,92 MB dữ liệu âm thanh mỗi phút**, chưa tính phần đầu tệp. Đây là phép tính theo định dạng ví dụ. Ghi dần vào tệp giúp giai đoạn thu không phải giữ toàn bộ bản ghi trong RAM nếu thư mục tạm nằm trên ổ lưu trữ. Đường nhận dạng một file hiện có đọc toàn bộ nội dung vào RAM khi gửi. Vì vậy mức RAM và độ trễ của toàn lượt vẫn cần kiểm tra trên Pi. [Mã đọc file của PBL6](../stt-app/src/server/audio.ts#L20) · [Mã gửi dữ liệu cho Deepgram](../stt-app/src/server/deepgram.ts#L7)

## Thiết kế tăng dần từ V1 đến V3

| Mốc | Cách xử lý âm thanh | Khi nào chữ xuất hiện trong ô soạn |
| --- | --- | --- |
| **V1** | Phương án đề xuất là ghi từng phần vào WAV tạm trên Pi. Dừng thu rồi nhận dạng cả đoạn. | Chèn chữ cuối một lần sau khi dừng. |
| **V2** | Dùng lại nguồn mic. Chuyển từng khung âm thanh đến bộ nhận dạng ngay trong lúc thu, qua hàng đợi có giới hạn. Hàng đợi giữ các khung đang chờ gửi. | Sau khi dừng, đợi kết quả cuối rồi chèn một lần như V1. |
| **V3** | Dùng lại luồng truyền âm thanh và cách kết thúc lượt của V2. Nhận thêm kết quả tạm từ bộ nhận dạng hỗ trợ. | Chèn chữ tạm đầu tiên tại con trỏ, cập nhật đoạn đó tại chỗ, rồi chuyển thành chữ thường khi kết quả cuối về. |

**Dùng chung qua ba mốc.** Giữ cách chọn mic, vòng đời của lượt thu, vùng soạn, vị trí báo lỗi và thao tác **Gửi**. Tách dữ liệu âm thanh của lượt thu khỏi dữ liệu hội thoại. Tệp WAV tạm phục vụ đường nhận dạng cả đoạn của V1. V2 và V3 có thể truyền theo khung mà không cần ghi một bản WAV đầy đủ song song. Kiểm tra từng mốc trước khi tiến lên và giữ các chế độ trước còn dùng được. [Thứ tự và tiêu chí từng mốc](../STT_PLAN_1_WEEK.md#approved-version-order) · [Quy tắc chèn chữ](../STT_PRODUCT_UI_UX.md#2-thu-sửa-và-gửi-trong-vùng-soạn-chung)
