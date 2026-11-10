# Khảo sát cách giữ âm thanh trong một lượt nhận dạng

**PBL6 · 10/11/2026.** Đối chiếu luồng thu giọng nói để nhập chữ của LearnHarness, Codex Desktop và DeepSeek Harness. Phần PBL6 tập trung vào lượt thu bằng mic trên Pi, sau đó bấm dừng để nhận dạng.

## Kết quả đối chiếu

| Ứng dụng | Âm thanh đi qua đâu | Cách giữ âm thanh |
| --- | --- | --- |
| **LearnHarness `0.5.0`** | `AudioWorklet` tạo từng khung PCM và gửi thẳng từ giao diện đến Deepgram qua WebSocket trong lúc thu. Chữ được gom và đưa vào ô soạn khi lượt thu kết thúc. | Khung chưa gửi trong lúc mở hoặc nối lại kết nối nằm trong mảng `ArrayBuffer` có giới hạn. Khi kết nối mở, app gửi hàng đợi rồi xóa mảng. Luồng này không tạo tệp thu. [Mã hàng đợi](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/components/dictation.tsx#L280-L357) · [Mã thu và gửi](https://github.com/amosblomqvist/learnharness/blob/v0.5.0/components/dictation.tsx#L445-L465) |
| **Codex Desktop `26.1103.4239.0` trên Windows** | Ô soạn dùng `MediaRecorder` gom các phần âm thanh thành `Blob`. Mã có nhánh lưu bản ghi riêng cho tính năng đọc chính tả. | Khi nhánh này chạy, app ghi từng phần `.chunk` và thông tin bản ghi vào thư mục `dictation-history`. App có thể đọc các phần lại để xử lý hoặc tải bản ghi. Đây là cơ chế giữ bản ghi có điều kiện. Mã tĩnh chưa cho biết nhánh đó sẽ chạy trong cấu hình và tài khoản nào khi thử thực tế. |
| **DeepSeek Harness `0.2.1-rc.5`** | Giao diện gom các `Blob` trong lúc thu. Khi dừng, app ghép, giải mã và chuyển sang WAV, rồi chuyển dữ liệu WAV mã hóa base64 tới tiến trình xử lý. | Bộ SenseVoice tích hợp đọc mẫu âm thanh từ dữ liệu nhận được và đưa mảng `Float32Array` vào bộ nhận dạng. Mã đã rà xử lý qua bộ đệm và không tạo tệp thu. Tài liệu DSH ghi nhận kết quả vào bản nháp, còn thao tác gửi mới tạo nội dung hội thoại. [Mã gom âm thanh](https://github.com/deepseek-ai/deepseek-harness/blob/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159/packages/experimental/client-ui-voice-input/src/client/audio.ts#L143-L159) · [Mã nhận dạng](https://github.com/deepseek-ai/deepseek-harness/blob/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159/packages/experimental/speech-to-text-sensevoice/src/inference.ts#L55-L88) · [Tài liệu Voice Input](https://github.com/deepseek-ai/deepseek-harness/blob/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159/docs/subsystems/voice-input.md#browser-and-host-ownership) |

**Cách đối chiếu.** LearnHarness được kiểm tra ở mã nguồn gắn thẻ `v0.5.0`. Với Codex, đọc trực tiếp `app.asar` của bản Windows đã cài. Mã thu và lưu nằm trong `webview/assets/async/202026.1f4062c12e.js`, `webview/assets/async/886697.0ee704d200.js` và `.vite/build/early-bootstrap-199-e3316cddb4ea6a6b.js`. Với DSH, bản cài `0.2.1-rc.5` có cùng đường xử lý nêu trên trong `dsh-experimental-client-ui-voice-input/lib/client.js` và `dsh-experimental-speech-to-text-sensevoice/lib/worker.js`. Các liên kết DSH trỏ đến một commit công khai cố định để đọc đoạn tương ứng. Khảo sát dựa trên mã và tài liệu. Việc thử bằng mic, gọi dịch vụ và đo tài nguyên trên Pi vẫn chưa thực hiện.

**SenseVoiceSmall** là mô hình chuyển giọng nói thành chữ của FunAudioLLM. DSH dùng bản ONNX và chạy nhận dạng bằng CPU của máy chạy phần xử lý. Bản mô hình công bố liệt kê tiếng Quan Thoại, Quảng Đông, Anh, Nhật và Hàn. Tiếng Việt chưa nằm trong danh sách đó. [Mô hình SenseVoiceSmall](https://huggingface.co/FunAudioLLM/SenseVoiceSmall) · [Cách DSH tích hợp](https://github.com/deepseek-ai/deepseek-harness/blob/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159/packages/experimental/speech-to-text-sensevoice/README.md)

## Áp dụng cho PBL6 V1

<strong style="color:#087A47;">Lịch sử lưu các hội thoại.</strong> Mỗi hội thoại gồm tên và các tin đã gửi. Hội thoại xuất hiện trong Lịch sử từ lần gửi thành công đầu tiên. Người dùng có thể mở lại, đọc các tin trước và gửi tiếp. [Quy tắc Lịch sử](../STT_PRODUCT_UI_UX.md#quy-tắc-lịch-sử-đã-chốt)

<strong style="color:#B22563;">Đề xuất dùng một tệp WAV tạm trên Pi cho mỗi lượt thu bằng mic.</strong> Ghi dần âm thanh vào thư mục tạm của ứng dụng. Khi bấm dừng, đóng tệp rồi dùng tệp làm đầu vào nhận dạng. Xóa tệp khi lượt thu kết thúc, kể cả khi nhận dạng thất bại hoặc bị hủy. Khi khởi động, ứng dụng dọn các tệp thu của chính nó còn sót từ lần chạy trước. Theo phương án này, bản thu tạm chỉ phục vụ nhận dạng và kết quả chữ vẫn đi vào ô soạn để người dùng đọc, sửa rồi gửi.

**Dung lượng tham khảo.** WAV mono 16 kHz, 16 bit chứa khoảng **1,92 MB dữ liệu âm thanh mỗi phút**, chưa tính phần đầu tệp. Đây là phép tính theo định dạng ví dụ. Ghi dần vào tệp giúp giai đoạn thu không phải giữ toàn bộ bản ghi trong RAM nếu thư mục tạm nằm trên ổ lưu trữ. Đường nhận dạng một file hiện có đọc toàn bộ nội dung vào RAM khi gửi. Vì vậy mức RAM và độ trễ của toàn lượt vẫn cần kiểm tra trên Pi. [Mã đọc file của PBL6](../stt-app/src/server/audio.ts#L20) · [Mã gửi dữ liệu cho Deepgram](../stt-app/src/server/deepgram.ts#L7)

### Số tệp, tải ghi và tốc độ nói

**Một lượt thu có thể gồm nhiều khối âm thanh nhưng chỉ cần một tệp WAV.** Pi nối từng khối vào cùng tệp trong lúc thu. Với đường V1 gửi cả đoạn sau khi dừng, chia cùng lượng dữ liệu ra nhiều tệp sẽ thêm thao tác tạo và dọn tệp. Nếu cần ghép lại để gửi, việc ghép cũng tốn thêm thao tác. Các tệp `.chunk` trong Codex thuộc cơ chế lưu và đọc lại bản ghi. Chưa có phép đo chứng minh cách đó giúp nhận dạng nhanh hơn.

**Tải ghi ở cấu hình ví dụ là 32 kB/s.** Mỗi giây có 16.000 mẫu, mỗi mẫu 2 byte. Một bản sao dữ liệu âm thanh chiếm khoảng **0,32 MB cho 10 giây**, **0,96 MB cho 30 giây** và **1,92 MB cho 60 giây**. Nếu có hai bản sao đầy đủ cùng tồn tại trong RAM thì một lượt 60 giây chiếm **3,84 MB** dữ liệu âm thanh. Con số này chưa gồm bộ đệm hệ điều hành hoặc phần còn lại của ứng dụng. Có thể chủ động giữ một tệp mẫu để nghe lại khi kiểm thử. Đây là thao tác kiểm thử riêng với việc giữ tệp đến khi nhận dạng xong.

**Tốc độ nói giúp chọn kịch bản thử.** Ruan và cộng sự đo khoảng **153 từ/phút** khi nhập tin nhắn ngắn bằng giọng nói tiếng Anh trong phòng thí nghiệm. Pellegrino và cộng sự báo cáo khoảng **5,22 âm tiết/giây** cho tiếng Việt trong khảo sát đọc thành tiếng. Một từ tiếng Việt có thể gồm nhiều âm tiết. Các số này là mốc tham khảo cho từng bài nghiên cứu. Độ dài lượt thu PBL6 nên được tính từ lúc bắt đầu đến khi dừng, gồm cả khoảng ngập ngừng. Các mốc **10, 30 và 60 giây** là ví dụ để kiểm tra, chưa phải phân bố thời lượng sử dụng thực tế hay giới hạn thu. [Nghiên cứu nhập tin nhắn của Ruan và cộng sự](https://arxiv.org/abs/1608.07323) · [Nghiên cứu tốc độ nói của Pellegrino và cộng sự](https://www.ddl.cnrs.fr/fulltext/pellegrino/Pellegrino_2011_Language.pdf)

**Khi kiểm tra Pi**, lấy mốc RAM của phần xử lý khi chưa thu và theo dõi đỉnh RAM suốt lượt. Ghi riêng đoạn từ khi phần xử lý bắt đầu đọc hoặc chuẩn bị âm thanh đến khi nhận phản hồi Deepgram. Khâu này có thể giữ cả tệp và các bản sao phục vụ yêu cầu mạng cùng lúc, trong khi khâu thu chỉ cần giữ các khối đang xử lý. Đo riêng độ trễ từ chạm nút dừng đến khi thấy chữ trong ô soạn. Nếu cần so RAM với tệp tạm, dùng cùng âm thanh, thiết bị và đường nhận dạng. [Hạng mục kiểm tra V1](../STT_PLAN_1_WEEK.md#approved-version-order)

## Thiết kế tăng dần từ V1 đến V3

| Mốc | Cách xử lý âm thanh | Khi nào chữ xuất hiện trong ô soạn |
| --- | --- | --- |
| **V1** | Phương án đề xuất là ghi từng phần vào WAV tạm trên Pi. Dừng thu rồi nhận dạng cả đoạn. | Chèn chữ cuối một lần sau khi dừng. |
| **V2** | Dùng lại nguồn mic. Chuyển từng khung âm thanh đến bộ nhận dạng ngay trong lúc thu, qua hàng đợi có giới hạn. Hàng đợi giữ các khung đang chờ gửi. | Sau khi dừng, đợi kết quả cuối rồi chèn một lần như V1. |
| **V3** | Dùng lại luồng truyền âm thanh và cách kết thúc lượt của V2. Nhận thêm kết quả tạm từ bộ nhận dạng hỗ trợ. | Chèn chữ tạm đầu tiên tại con trỏ, cập nhật đoạn đó tại chỗ, rồi chuyển thành chữ thường khi kết quả cuối về. |

**Mục đích của V1** là kiểm tra trọn một lượt trên Pi, từ chọn và thu đúng mic đến dừng, nhận chữ cuối từ Deepgram và hiển thị kết quả hoặc lỗi. Nhận dạng sau khi dừng cho phép kiểm tra thu âm và gọi nhận dạng theo thứ tự. Trong phương án tệp tạm, khối âm thanh đi qua bộ đệm RAM ngắn rồi được ghi vào WAV. WAV giữ các khối đã thu đến lúc gửi cả đoạn.

**V2 dùng lại đầu thu của V1.** Cùng nguồn mic và các khối âm thanh, nhưng đầu nhận khối chuyển từ bộ ghi WAV sang hàng đợi gửi qua mạng. Khi mạng chậm, RAM giữ các khối đang chờ trong giới hạn của hàng đợi. Vì Deepgram nhận âm thanh trong lúc thu, đường V2 không cần ghi song song một WAV đầy đủ. Đường V1 vẫn dùng được riêng. V3 dùng lại đường truyền của V2 và bổ sung chữ tạm.

**Dùng chung qua ba mốc.** Giữ cách chọn mic, vòng đời của lượt thu, vùng soạn, vị trí báo lỗi và thao tác **Gửi**. Tách dữ liệu âm thanh của lượt thu khỏi dữ liệu hội thoại. Kiểm tra từng mốc trước khi tiến lên. [Thứ tự và tiêu chí từng mốc](../STT_PLAN_1_WEEK.md#approved-version-order) · [Quy tắc chèn chữ](../STT_PRODUCT_UI_UX.md#2-thu-sửa-và-gửi-trong-vùng-soạn-chung)
