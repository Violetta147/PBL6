# STT — bàn giao sau P1 và chốt BOM

Cập nhật 07/11/2026. Dự án giữ tại `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`. **Ưu tiên phiên tiếp theo: thảo luận UI/UX sản phẩm đa phương thức cùng các lựa chọn BOM và lập kế hoạch mua sắm tại Đà Nẵng. Chưa tự triển khai P2/batch hoặc đặt hàng.**

## 1. Đọc theo thứ tự

**Bản phác V1 đã cập nhật nút mic.** Nút ở vị trí trước đây của **Chọn file**, với các khung minh họa dừng thu, chờ nhận dạng và báo lỗi. Dùng bản phác làm tham chiếu khi triển khai. Quy tắc vị trí và trạng thái mic đã được người dùng chốt.

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
- Chưa có thu micro Pi/Record/Stop, điều khiển qua LAN, bản cài Windows, kiểm chứng Linux ARM64, cảm ứng/kiosk khởi động trên Pi, V2/V3 hoặc IoT/OTA hoàn chỉnh.
- Luồng V1 còn phải hoàn thiện: chọn nguồn/device path trên Pi → Record → Stop dừng capture → Deepgram → transcript cuối hoặc lỗi rõ ràng; dùng đường một file của P1 để kiểm tra tích hợp khi cần. Batch chạy trong bộ thí nghiệm. Không tự dùng micro của browser laptop. V2 mới đưa audio lên trong khi thu (hiện kết quả cuối); V3 mới hiện chữ tạm cập nhật rồi chốt chữ cuối.

Khi cần mở lại trên laptop, PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6\stt-app'
npm run desktop
```

Dependencies và build đã có trên máy. Ứng dụng có thể vẫn đang chạy; không mở thêm backend cùng cổng 3100. Nếu bản web riêng đang chạy, dừng đúng terminal của nó trước. Không tắt hàng loạt Node/Electron. Không đọc/chia sẻ key trong Settings để làm bàn giao.

## 3. Công việc phiên tiếp theo: UI/UX, chốt BOM và kế hoạch đi mua

**Yêu cầu sản phẩm mới cần bàn:** giao tiếp giữa hai người bằng ký hiệu, giọng nói và chữ, có TTS và Settings. Giao diện P1 chưa được duyệt làm sản phẩm cuối. Đọc [STT_PRODUCT_UI_UX.md](STT_PRODUCT_UI_UX.md) trước khi chốt màn/giá đỡ: cách hai người nhìn và dùng màn ảnh hưởng BOM. Tham khảo tinh thần Codex/LearnHarness/messenger và bố cục ảnh người dùng gửi; không lấy bảng màu ảnh làm mặc định. Chưa triển khai lại UI hoặc thêm sign-to-text/TTS; giữ các mốc V1/V2/V3 STT. Người dùng muốn tiếp tục thảo luận ở phiên mới.

**Dùng `STT_BOM.md` làm BOM duy nhất để chốt.** Bản trước thay và bản highlight nguyên gốc được giữ bên ngoài repository tại `C:\Users\LAPTOP T&T\Downloads\PBL6_BOM_BACKUP_20261107_9t707jsm`.

Sản phẩm cuối dùng cảm ứng và Electron kiosk. Nhóm tích hợp HDMI + USB touch trước, rồi xét DSI sau khi HDMI ổn định. **Phiếu Điện tử Nguyễn Hiền lúc 17:25 ngày 07/11/2026 ghi đã mua 1 màn NH2067, 7 inch, 1024 × 600 (1.090.000 VNĐ) và 1 cáp micro-HDMI sang HDMI (75.000 VNĐ). Tổng tiền hàng là 1.165.000 VNĐ.** Cần kiểm tra USB touch, nguồn và phụ kiện trong hộp. Loa, micro thay thế, AEC và powered hub phụ thuộc nhu cầu thực tế.

Bản highlight gốc có thêm các mức tiền nháp. BOM chính phân biệt chúng với giá niêm yết. Khảo sát DSI ngày 06/11 được giữ để tham khảo. Cần xác nhận tổng ngân sách, khoảng cách thử và cách cấp nguồn theo bộ NH2067 thực tế.

**Lượt thử màn ngày 07/11/2026:** người dùng báo NH2067 kết nối thành công với Pi 4 và nhận chạm, cảm giác hơi khác điện thoại. Bước tiếp theo là xác nhận độ phân giải đang dùng và thử vị trí chạm ở vài điểm. Dùng [bản phác bàn phím mở](reports/ui_ux_20261107/assets/wireframe-ban-phim-ao.png) để đối chiếu vùng đọc, vùng sửa chữ và nút Gửi khi thử kiosk.

## 4. Giữ công việc nghiên cứu và triển khai còn lại

- **N02 đã có quy trình đo thống nhất, còn chờ kết quả so sánh trên Pi.** RTF Whisper CLI cũ gồm khởi động/nạp model từng WAV, khác phạm vi RTF gọi nhận dạng của Zipformer. Giữ số cũ theo đúng phạm vi đo. Dùng N02 trước khi so sánh tốc độ hoặc chọn bộ nhận dạng chạy tại máy dựa trên tốc độ. V1 Deepgram có thể tiếp tục song song.
- Giữ B01–B04, prediction, dữ liệu và scorer. Không chạy model/benchmark từ bàn giao này.
- Nếu người dùng tiếp tục phần mềm: hoàn thiện luồng thu và dừng trên Pi, sửa và gửi chữ, mở lại hội thoại để gửi tiếp, rồi thử nhận dạng lỗi và thu lại. Hoàn thành V1 trước V2 rồi V3. Deepgram là provider đang dùng; không khôi phục Google STT vào phạm vi chủ động.
- Khi cần Pi: kiểm tra phiên truy cập hiện tại, đưa từng bước với lệnh, nơi chạy, kết quả mong đợi và đầu ra cần gửi lại; không giả định Pi đã nhận bản mã mới.

## 5. Git và bảo toàn thay đổi

Nhánh hiện tại `master`; kiểm tra `git status --short` và `git log -3 --oneline` trước khi sửa. Có nhiều chỉnh sửa tài liệu và file chưa theo dõi của người dùng; giữ nguyên, kể cả trạng thái xóa `marp_slides_tutorial.zip`. Không reset/clean hoặc gộp chúng vào commit nhiệm vụ mới. Bản BOM cũ đã được sao lưu trước lần ghi đè được người dùng yêu cầu.

Mỗi thay đổi hoàn chỉnh phải có tài liệu/kiểm thử liên quan, chạy kiểm tra phù hợp và commit theo AGENTS.md. Chốt BOM chỉ cần kiểm tra tài liệu; không chạy lại ASR/test ứng dụng nếu không đổi mã. Mốc 05/11 là kế hoạch cũ đã qua; chưa có hạn mới được người dùng xác nhận.
