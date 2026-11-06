# STT — bàn giao sau P1 và chốt BOM

Cập nhật 07/11/2026. Dự án giữ tại `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`. **Ưu tiên phiên tiếp theo: thảo luận UI/UX sản phẩm đa phương thức cùng các lựa chọn BOM và lập kế hoạch mua sắm tại Đà Nẵng. Chưa tự triển khai P2/batch hoặc đặt hàng.**

## 1. Đọc theo thứ tự

1. `AGENTS.md`: quy tắc kiểm thử, tài liệu và commit.
2. `STT_BOM.md`: BOM chính, đã thay bằng bố cục highlight người dùng đưa và hiệu chỉnh các nội dung chưa có căn cứ. Không dùng một bản `_HIGHLIGHTED` khác làm nguồn quyết định song song.
3. [STT_PRODUCT_UI_UX.md](STT_PRODUCT_UI_UX.md): yêu cầu giao tiếp đa phương thức giữa hai người; ba tham chiếu Codex/LearnHarness/Deepseek Harness, cơ chế conversation/session và nhận định sơ bộ “harness bao quanh model”; ảnh tham khảo và các quyết định UI/UX chưa chốt.
4. `reports/stt_v1_p1_20261107/BAO_CAO.md`: báo cáo triển khai, hai lượt dùng thử và lỗi desktop đã sửa.
5. `STT_SHIFT_HANDOFF.md`: trạng thái công việc và nhiệm vụ tiếp theo.
6. Khi cần chi tiết phần mềm/nghiên cứu: `STT_SYSTEM_SPEC.md`, `STT_PLAN_1_WEEK.md`, `stt-app/README.md`, `experiments/inventory_20261102/README.md`.

Không cần đọc lại toàn bộ chat/log phiên cũ. Người dùng đã yêu cầu tránh việc đó để tiết kiệm context; dùng các tài liệu và bằng chứng hiện có, chỉ tra lịch sử nếu người dùng yêu cầu hoặc có điểm thật sự chưa thể giải quyết từ nguồn hiện tại.

## 2. P1 đã làm đến đâu?

**P1 đã triển khai và đã có bằng chứng sử dụng thực tế ở phạm vi một file. Toàn bộ V1 chưa hoàn thành.**

- Mã tại `stt-app`, phiên bản 0.1.0. Stack đã chốt: React + TypeScript + Tailwind CSS, Next.js/Node.js và Electron.
- Settings nhập/xóa key tại máy, giữ key trên backend; nhận một WAV/MP3/FLAC tối đa 20 MiB; gọi Deepgram `language=vi`; hiện chữ cuối/lỗi; xuất .txt và sao chép.
- Production build, TypeScript, 20 backend tests và 8 Chrome/HTTP/Electron tests đã đạt trên Windows. Đây là kết quả đã chạy ở P1, không phải yêu cầu chạy lại mặc định cho phiên chốt BOM.
- Người dùng đã gửi hai lượt Nova-3/vi trên Chrome: `studio_M1.wav` và `phone_F1.wav`, có ảnh và .txt. Chi tiết trong `user_trial_studio_M1.json`, `user_trial_phone_F1.json` cùng thư mục báo cáo. phone_F1 có cụm “nước sệt”, người dùng nghĩ là “nước sạch”; reference chưa xác nhận, chưa quy nguyên nhân cho vùng miền và chưa chấm WER/CER.
- Lỗi không thấy cửa sổ desktop sau `npm run desktop` đã sửa: tiến trình Electron dùng `windowsHide: false`, backend vẫn chạy ẩn. Kiểm thử hồi quy xác nhận launcher production tạo cửa sổ có tiêu đề. Commit mã P1 ban đầu `e99ccaa9`, sửa desktop và lưu hai lượt thử `9041d6e2`.
- Chưa có batch, thu micro Pi/Record/Stop, điều khiển qua LAN, bản cài Windows, kiểm chứng Linux ARM64, cảm ứng/kiosk khởi động trên Pi, V2/V3 hoặc IoT/OTA hoàn chỉnh.
- Luồng V1 còn phải hoàn thiện: chọn nguồn/device path trên Pi → Record → Stop dừng capture → Deepgram → transcript cuối hoặc lỗi rõ ràng; hỗ trợ một file và batch. Không tự dùng micro của browser laptop. V2 mới đưa audio lên trong khi thu (hiện kết quả cuối); V3 mới hiện chữ tạm cập nhật rồi chốt chữ cuối.

Khi cần mở lại trên laptop, PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6\stt-app'
npm run desktop
```

Dependencies và build đã có trên máy. Ứng dụng có thể vẫn đang chạy; không mở thêm backend cùng cổng 3100. Nếu bản web riêng đang chạy, dừng đúng terminal của nó trước. Không tắt hàng loạt Node/Electron. Không đọc/chia sẻ key trong Settings để làm bàn giao.

## 3. Công việc phiên tiếp theo: UI/UX, chốt BOM và kế hoạch đi mua

**Yêu cầu sản phẩm mới cần bàn:** giao tiếp giữa hai người bằng ký hiệu, giọng nói và chữ, có TTS và Settings. Giao diện P1 chưa được duyệt làm sản phẩm cuối. Đọc [STT_PRODUCT_UI_UX.md](STT_PRODUCT_UI_UX.md) trước khi chốt màn/giá đỡ: cách hai người nhìn và dùng màn ảnh hưởng BOM. Tham khảo tinh thần Codex/LearnHarness/messenger và bố cục ảnh người dùng gửi; không lấy bảng màu ảnh làm mặc định. Chưa triển khai lại UI hoặc thêm sign-to-text/TTS; giữ các mốc V1/V2/V3 STT. Người dùng muốn tiếp tục thảo luận ở phiên mới.

**Dùng `STT_BOM.md` làm BOM duy nhất để chốt.** Bản trước thay và bản highlight nguyên gốc được giữ bên ngoài repository tại `C:\Users\LAPTOP T&T\Downloads\PBL6_BOM_BACKUP_20261107_9t707jsm`.

Đã chốt: sản phẩm cuối có cảm ứng + Electron kiosk; tích hợp HDMI + USB touch trước, DSI chỉ là phương án nâng cấp sau khi HDMI ổn định. Chưa chốt: kích thước/model màn HDMI, đầu/chiều dài cáp, nguồn, vỏ/giá đỡ, nhà bán, tổng giá và ngày nhận. Loa, micro thay thế, AEC và powered hub phụ thuộc nhu cầu thực tế, không tự thành danh sách mua bắt buộc.

Bản highlight gốc có thêm các mức tiền nháp. BOM chính đã phân biệt chúng với báo giá; không dùng giá ứng viên DSI để dự toán màn HDMI. Giá/tồn kho DSI là thông tin khảo sát ngày 06/11, cần kiểm tra lại khi mua. Không mặc định màn 7 inch, khoảng cách 1–2 m, tổng ngân sách 2–2,5 triệu, toàn bộ thiết bị đã có đủ hoặc nguồn màn luôn phải đi riêng.

**Khảo sát màn bổ sung ngày 07/11:** BOM đã có Nguyễn Hiền NH2067 (trang hiển thị 1.090.000 VNĐ) và Tuyết Nga (820.000 VNĐ), đều 7 inch HDMI 1024×600. Chưa xác minh đúng đường USB touch/nguồn/phụ kiện và tổng VAT/ship/bảo hành; chưa chốt mua. Shop Shopee là nguồn đồ cũ người dùng báo chỉ còn DSI, công cụ chưa đọc được trang. BOM cũng đã giải thích SPI và lý do chưa ưu tiên làm màn chính. Không coi tên HDMI là bằng chứng touch qua USB.

Trình bày các ứng viên cụ thể trong một bảng so sánh: tương thích Pi 4/OS, kích thước/độ phân giải, đường touch, nguồn, phụ kiện, giá có VAT/ship, bảo hành, tồn kho và cách/ngày nhận có nguồn. Ưu tiên Đà Nẵng (Nguyễn Hiền/SPIDER/BKM) hoặc nhà bán giao được về Đà Nẵng. Người dùng chưa chốt ngân sách, không yêu cầu rẻ nhất; cho xem so sánh trước khi yêu cầu quyết định. Lập danh sách tận dụng/mượn/mua có điều kiện và lịch đi mua sau khi người dùng chọn. Không đặt hàng hoặc liên hệ người khác nếu chưa được yêu cầu.

## 4. Giữ công việc nghiên cứu và triển khai còn lại

- **N02 chưa hoàn thành**, không chặn V1 Deepgram. RTF Whisper CLI cũ gồm khởi động/nạp model từng WAV, khác phạm vi RTF gọi nhận dạng của Zipformer. Không lấy tỷ số đó để kết luận tăng tốc. Hoàn thành phép đo thống nhất trước so sánh tốc độ hoặc chọn local engine dựa trên tốc độ.
- Giữ B01–B04, prediction, dữ liệu và scorer. Không chạy model/benchmark từ bàn giao này.
- Nếu người dùng tiếp tục phần mềm: bước tiếp theo dự kiến là batch, rồi capture Pi/Record/Stop để hoàn thiện V1. Hoàn thành V1 trước V2 rồi V3. Deepgram là provider đang dùng; không khôi phục Google STT vào phạm vi chủ động.
- Khi cần Pi: kiểm tra phiên truy cập hiện tại, đưa từng bước với lệnh, nơi chạy, kết quả mong đợi và đầu ra cần gửi lại; không giả định Pi đã nhận bản mã mới.

## 5. Git và bảo toàn thay đổi

Nhánh hiện tại `master`; kiểm tra `git status --short` và `git log -3 --oneline` trước khi sửa. Có nhiều chỉnh sửa tài liệu và file chưa theo dõi của người dùng; giữ nguyên, kể cả trạng thái xóa `marp_slides_tutorial.zip`. Không reset/clean hoặc gộp chúng vào commit nhiệm vụ mới. Bản BOM cũ đã được sao lưu trước lần ghi đè được người dùng yêu cầu.

Mỗi thay đổi hoàn chỉnh phải có tài liệu/kiểm thử liên quan, chạy kiểm tra phù hợp và commit theo AGENTS.md. Chốt BOM chỉ cần kiểm tra tài liệu; không chạy lại ASR/test ứng dụng nếu không đổi mã. Mốc 05/11 là kế hoạch cũ đã qua; chưa có hạn mới được người dùng xác nhận.
