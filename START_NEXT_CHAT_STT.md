# PBL6 STT — bàn giao để duyệt luồng hội thoại

## Điểm tiếp tục hiện tại · 13/11/2026

**Giai đoạn 1 & Giai đoạn 2 đã hoàn thành 100% với 92 tests đạt (Green). Đang thực hiện Giai đoạn 3.**
- **Giai đoạn 1 (Backend Storage & APIs):** Xây dựng module lưu trữ JSON nguyên tử (atomic write, queue Promise chống race condition), 13 API endpoints cho hội thoại, tin nhắn, cài đặt, và thu âm. 92/92 unit & integration tests pass trong 5.7s.
- **Giai đoạn 2 (Giao diện 1024×600 & Trình soạn thảo Smart Latch):** Hoàn thiện giao diện Light theme tối ưu màn hình cảm ứng 7 inch, vùng soạn thảo thông minh (Smart Latch: bấm Gửi khi đang thu sẽ tự ngắt, đợi chữ và gửi đúng 1 lần), chỉnh sửa tiêu đề tại chỗ (inline editable title), hiển thị danh sách tin nhắn.
- **Giai đoạn 3 (Đang triển khai):** Tích hợp thu âm micro đa nền tảng (Windows qua WASAPI, Pi qua PipeWire) bằng chuẩn Web Audio API phía client; phân quyền Electron (`permission === 'media'`) trên `127.0.0.1`; Bảng Lịch sử trượt 360px; Màn Cài đặt toàn diện với modal cảnh báo thay đổi chưa lưu.
- **Dọn dẹp:** Đã xóa bỏ hoàn toàn trang và route tạm `/file-upload` để giữ dự án sạch sẽ. Không sử dụng mô hình laptop điều khiển Pi qua LAN; sản phẩm hoạt động độc lập trên Pi (kiosk) hoặc Windows.

### Bàn giao trước đó

Cập nhật 08/11/2026. Dự án giữ tại `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`. **Phiên tiếp theo tiếp tục thảo luận từng bước. Bắt đầu bằng một lượt thu giọng nói, sửa chữ và gửi tin trên bản phác 1024 × 600.** Việc triển khai phần mềm, thử nghiệm trên Pi và mua sắm được thực hiện theo yêu cầu riêng của người dùng.

## 1. Đọc theo thứ tự

**Bản phác V1 đặt nút mic ngay bên trái Gửi.** Các khung dừng thu, chờ nhận dạng và báo lỗi dùng chung vị trí nút. Dùng bản phác làm tham chiếu khi triển khai.

**Bấm Gửi khi đang thu** sẽ dừng mic, đợi chữ rồi gửi toàn bộ bản nháp đã ghép. Bấm **Gửi** khi đang chờ thì đợi cùng lượt nhận dạng. Nếu nhận dạng lỗi, bỏ yêu cầu gửi và giữ bản nháp. [Khảo sát và quyết định V1](reports/NGHIEN_CUU_GUI_KHI_DANG_THU.md)

1. [AGENTS.md](AGENTS.md). Đọc quy tắc làm việc, kiểm thử và commit. Kiểm tra Git status trước khi sửa.
2. [STT_PRODUCT_UI_UX.md](STT_PRODUCT_UI_UX.md). Đọc mục 1–3 để nắm phạm vi, cách dùng vùng soạn, luồng mic và các quy tắc Lịch sử đã chốt. Dùng mục 5–6 để duyệt kịch bản phiên mới.
3. [Bản phác Pencil 1024 × 600](reports/ui_ux_20261107/assets/wireframe-hoi-thoai-1024x600.pen). Xem ba khung Trao đổi, Mở lịch sử và Bàn phím mở. Đối chiếu vùng soạn, mic, nút Gửi và chỗ đọc tin khi bàn phím hiện.
4. [STT_BOM.md](STT_BOM.md) và [HUONG_DAN_NH2067_PI4.md](HUONG_DAN_NH2067_PI4.md). Đọc cấu hình màn đã dùng và mục kết quả thử để tách bằng chứng thực tế khỏi phụ kiện và phép thử còn chờ.
5. [STT_SHIFT_HANDOFF.md](STT_SHIFT_HANDOFF.md) và [báo cáo P1](reports/stt_v1_p1_20261107/BAO_CAO.md). Đọc phần `Implementation checkpoint` và mục 3 của báo cáo khi cần xác nhận phạm vi phần mềm, kiểm thử trên Windows hoặc kết quả dùng thử một file.

Dùng bàn giao và bằng chứng trong repo để tiếp tục. Chỉ tra một đoạn chat cũ khi cần làm rõ một quyết định cụ thể. Đọc `STT_SYSTEM_SPEC.md`, `STT_PLAN_1_WEEK.md`, `stt-app/README.md` và `experiments/inventory_20261102/README.md` khi quay lại triển khai hoặc đánh giá STT.

## 2. Tiến trình triển khai V1 (Cập nhật 13/11/2026)

**Giai đoạn 1 & 2 đã hoàn thành và đạt 92/92 test trên Windows. Giai đoạn 3 đang thực hiện.**

- Mã tại `stt-app`, phiên bản 0.1.0. Stack đã chốt: React + TypeScript + Tailwind CSS, Next.js/Node.js và Electron.
- **Giai đoạn 1 (Backend Storage & APIs):** Đã hoàn thành lưu trữ JSON nguyên tử, chống race condition, 13 API endpoints, mock recorder cho test suite, 92 tests passing.
- **Giai đoạn 2 (UI Composer & Smart Latch):** Đã hoàn thành giao diện 1024×600, vùng soạn thảo thông minh Smart Latch, đổi tên hội thoại tại chỗ, cuộn tin nhắn.
- **Giai đoạn 3 (Web Audio Micro & Lịch sử/Cài đặt):** Chuyển dịch sang thu âm Web Audio API đa nền tảng (WASAPI trên Windows, PipeWire trên Pi) mã hóa WAV 16kHz Mono phía client; tích hợp Drawer Lịch sử 360px và Cài đặt.
- **Làm sạch dự án:** Route tạm `/file-upload` đã được xóa sạch. Sản phẩm hoạt động độc lập (standalone kiosk trên Pi hoặc cửa sổ desktop trên Windows), không dùng mô hình điều khiển qua LAN.
- V2 gửi âm thanh trong lúc thu và hiện chữ cuối. V3 bổ sung chữ tạm cập nhật trong khi nói.

Khi cần mở lại trên laptop, PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6\stt-app'
npm run desktop
```

Dependencies và build đã có trên máy. Ứng dụng có thể vẫn đang chạy; không mở thêm backend cùng cổng 3100. Nếu bản web riêng đang chạy, dừng đúng terminal của nó trước. Không tắt hàng loạt Node/Electron. Không đọc/chia sẻ key trong Settings để làm bàn giao.

## 3. Quyết định thiết kế đã chốt

- **Phạm vi.** Hai người dùng chung một màn hình và một vùng soạn. Ai cũng có thể nhập. Người dùng tự chọn cách đặt, cầm hoặc xoay thiết bị để xem, tương tự khi đưa màn hình điện thoại cho người khác đọc. Giá đỡ là phụ kiện. PBL6 phụ trách STT, TTS và Settings. Chữ để đọc có thể đến từ luồng khác, kể cả dự án nhận dạng ký hiệu. Phần nhận dạng ký hiệu và camera phục vụ nhận dạng nằm ngoài luồng STT đang duyệt. [Khảo sát vùng soạn và tình huống dùng một màn hình](reports/NGHIEN_CUU_COMPOSER_ANTIGRAVITY.md)
- **Thu, sửa và gửi.** Chạm mic một lần để bắt đầu thu, chạm lần nữa để dừng. Trong lúc nhận dạng, giao diện hiện vòng chờ. Chữ nhận được vào vùng soạn để đọc lại và sửa. Người dùng cũng có thể gõ trực tiếp. Chỉ mở bàn phím ảo khi chạm vùng soạn, dùng Backspace trên bàn phím để xóa chữ. Bấm **Gửi** mới đưa câu vào hội thoại.
- **Lịch sử.** Mở ứng dụng vào hội thoại mới. Trong Lịch sử có nút **+ Hội thoại mới**. Hội thoại được lưu từ lần gửi thành công đầu tiên và mở lại được sau khi tắt ứng dụng. Người dùng có thể soạn và gửi tiếp trong hội thoại đã mở lại. Sắp theo thời điểm gửi thành công tin gần nhất, theo quy tắc **Last updated** của DeepSeek Harness. Xem lại, đổi tên và đọc to giữ nguyên vị trí. Trong **Settings**, mục **Xóa lịch sử** cho chọn hội thoại, rồi bấm **Delete** để xóa ngay các mục đã chọn.
- **TTS.** **Đọc to** và **Gửi** là hai thao tác riêng. Vị trí nút, phần chữ được đọc và giải pháp tạo giọng đang tạm hoãn. Giao diện Codex là tham chiếu, còn TTS của PBL6 phải hoạt động độc lập với gói đăng ký ChatGPT. [Khảo sát Đọc to](reports/NGHIEN_CUU_DOC_TO_CAC_HARNESS.md)

**Tên và cách đổi tên hội thoại.** Dùng tin đầu tiên được gửi thành công để tạo tên theo LearnHarness, rút gọn câu dài ở ranh giới từ. Chạm tiêu đề của hội thoại đang mở để sửa tên tại chỗ. Khi dùng chuột, nhấn chuột phải vào mục trong **Lịch sử** rồi chọn **Đổi tên**. ID hội thoại tách với tên hiển thị.

**Bản nháp.** V1 giữ chữ chưa gửi trong vùng soạn của hội thoại đang mở theo LearnHarness. Chuyển hội thoại hoặc đóng ứng dụng sẽ bỏ bản nháp. Nếu gửi lỗi khi hội thoại vẫn mở, ứng dụng giữ chữ để sửa hoặc thử gửi lại. [Khảo sát cách giữ bản nháp](reports/NGHIEN_CUU_BAN_NHAP_HOI_THOAI.md)

**Còn để duyệt.** Màu sắc, các mục Settings còn lại, cách xử lý audio thô, tệp tạm và định dạng lưu. Phần nghiên cứu Codex, LearnHarness và DeepSeek Harness dùng để tham khảo hành vi. Cordis và kiến trúc plugin vẫn là chủ đề thảo luận. Chỉ đọc [bản so sánh Cordis](comparision_everything_is_a_plugin.md) và [ghi chú Everything is a Plugin](everything_is_a_plugin_cordis.md) khi quay lại câu hỏi kiến trúc.

## 4. Phần cứng đã thử và việc để sau

**Dùng `STT_BOM.md` làm BOM chính.** Phiếu Điện tử Nguyễn Hiền lúc 17:25 ngày 07/11/2026 ghi màn NH2067 7 inch 1024 × 600 giá **1.090.000 VNĐ** và cáp micro-HDMI sang HDMI giá **75.000 VNĐ**, tổng **1.165.000 VNĐ**. Bản BOM trước khi thay và bản highlight nguyên gốc được giữ tại `C:\Users\LAPTOP T&T\Downloads\PBL6_BOM_BACKUP_20261107_9t707jsm`.

Màn đã lên hình và nhận chạm với Pi 4. HDMI truyền hình ảnh. Một dây USB dữ liệu nối từ Pi đến cổng Touch đã thử mang cả nguồn và dữ liệu chạm. Pi dùng adapter **5 V – 3 A** sẵn có. Bo thực tế có hai cổng Touch, mã bo vẫn cần xác minh. Đầu ra tai nghe 3,5 mm đã thử nghe được. Mic tích hợp trên webcam Aioneus đã thử thu âm, chất lượng nhận dạng ở khoảng cách sử dụng còn cần đo.

Giữ ưu tiên HDMI và USB touch cho tích hợp đầu tiên. Bài thử vuốt trong Chromium được tạm hoãn. Độ phân giải đang dùng, vị trí chạm, bàn phím tiếng Việt và kiosk trên Pi vẫn cần kiểm tra. Loa ngoài, hub có nguồn và DSI là các hạng mục xem xét khi có nhu cầu thực tế. Bài thử RealVNC chờ ở [kế hoạch riêng](reports/KE_HOACH_THU_AM_THANH_REALVNC.md).

## 5. Việc tiếp theo và thứ tự triển khai hiện có

Dùng bản phác Trao đổi và Bàn phím mở để đi qua một lượt STT. Xem người dùng nhận ra trạng thái đang thu, đang nhận dạng và lúc chữ vào vùng soạn thế nào. Sau đó kiểm tra họ có sửa chữ, bấm **Gửi** và tìm lại tin trong **Lịch sử** được hay không. Đây là kịch bản duyệt giao diện. Khi người dùng sẵn sàng thử Pi, dùng mục 2.3 của hướng dẫn NH2067 cho bài chạm và bàn phím thật.

- **N02 đã có quy trình đo thống nhất, còn chờ kết quả so sánh trên Pi.** RTF Whisper CLI cũ gồm khởi động/nạp model từng WAV, khác phạm vi RTF gọi nhận dạng của Zipformer. Giữ số cũ theo đúng phạm vi đo. Dùng N02 trước khi so sánh tốc độ hoặc chọn bộ nhận dạng chạy tại máy dựa trên tốc độ. V1 Deepgram có thể tiếp tục song song.
- Giữ B01–B04, prediction, dữ liệu và scorer. Không chạy model/benchmark từ bàn giao này.
- Khi tiếp tục phần mềm, hoàn thiện luồng thu và dừng trên Pi, sửa và gửi chữ, mở lại hội thoại để gửi tiếp, rồi thử nhận dạng lỗi và thu lại. Hoàn thành V1 trước V2 và V3. Deepgram là dịch vụ STT đang dùng. [Tiêu chí V1](STT_PLAN_1_WEEK.md#approved-version-order)
- Khi cần thử Pi, kiểm tra phiên truy cập và bản mã hiện có. Ghi từng lệnh, nơi chạy, kết quả mong đợi và đầu ra cần gửi lại.

## 6. Git và bảo toàn thay đổi

Nhánh hiện tại `master`; kiểm tra `git status --short` và `git log -3 --oneline` trước khi sửa. Có nhiều chỉnh sửa tài liệu và file chưa theo dõi của người dùng; giữ nguyên, kể cả trạng thái xóa `marp_slides_tutorial.zip`. Không reset/clean hoặc gộp chúng vào commit nhiệm vụ mới. Bản BOM cũ đã được sao lưu trước lần ghi đè được người dùng yêu cầu.

Mỗi thay đổi hoàn chỉnh phải có tài liệu/kiểm thử liên quan, chạy kiểm tra phù hợp và commit theo AGENTS.md. Chốt BOM chỉ cần kiểm tra tài liệu; không chạy lại ASR/test ứng dụng nếu không đổi mã. Mốc 05/11 là kế hoạch cũ đã qua; chưa có hạn mới được người dùng xác nhận.
