# BOM tổng thể cho thiết bị giao tiếp

Ngày 02/11/2026. Đây là một BOM dùng chung cho các mốc phát triển. Chưa có đơn đặt hàng mới. Không lấy giá trong trao đổi cũ làm giá hiện tại.

| Hạng mục | Số lượng / trạng thái | Vai trò và điều kiện dùng/mua |
|---|---|---|
| Raspberry Pi 4B rev 1.5, RAM 8 GB | 1, đã có | Máy biên; Trixie aarch64 theo thông tin người dùng. Cần phiên truy cập hiện tại trước triển khai. |
| microSD 32 GB | 1, đã có | Lưu OS, runtime và cấu hình. Kiểm tra dung lượng thực trên Pi trước cài. |
| Adapter DC 5 V–3 A | 1, đã có | Cấp riêng cho Pi; nhãn không chứng minh ổn định dưới mọi tải. Kiểm tra nguồn/nhiệt khi chạy cấu hình thực tế. |
| Webcam Aioneus USB 1080p, có đầu thu Camera | 1, đã thử thu/phát | Dùng micro hiện có trước. Lệnh ALSA và người dùng đã xác nhận nghe lại được bản thu trong trao đổi. Không cần mua micro chỉ vì tài liệu cũ ghi chưa có. |
| Laptop và mạng nội bộ | Đã có | Phát triển và mở giao diện web của Pi. Google/Deepgram cần Internet khi dùng cloud. Chưa xác minh mạng hiện tại. |
| Tai nghe 3,5 mm | 1, đã thử phát trên Pi | Phát triển và thử TTS. Không thay loa khi cần cho người đối diện nghe hoặc thử vọng âm. |
| Màn hình ngoài | Đã có, chưa rõ cổng/cáp | Có thể tận dụng sau. Mốc đầu dùng màn hình laptop; không mua touchscreen để chặn việc bắt đầu. |
| ESP32 DevKit V1, nút/LED/điện trở/dây/breadboard | Có trong kho nhóm, kiểm tra theo nhu cầu | Nhánh firmware riêng; chưa có xác nhận bài nút/LED/Serial đã chạy. Không cần để STT đầu tiên hoạt động. |
| STM32/ESP8266/UNO và dụng cụ trong bảng kho | Có thể tận dụng, tình trạng chưa xác minh | Không gán ghi chú cá nhân của đồng đội thành ý kiến người dùng. Không mua board mới khi chưa có nhiệm vụ. |
| Quạt hai dây | Đã có, chưa rõ định mức | Kiểm tra điện áp/dòng và bố trí trước dùng. Không suy là quạt PWM. |
| Loa chủ động AUX hoặc USB audio | Chưa xác nhận có sẵn | Cần cho thử hội thoại qua loa. Tận dụng/mượn trước; nếu mua, xác minh đầu vào âm thanh, nguồn, phụ kiện và ngày nhận. LF-804 chỉ là ứng viên cũ, không có bằng chứng AEC trong hồ sơ. |
| Micro USB thay thế | Chờ kiểm chứng nhu cầu | Chỉ mua nếu webcam không đáp ứng bài thu thực tế. Chưa chốt model/giá hoặc yêu cầu micro đắt tiền. |
| Bộ mic–loa có AEC hoặc AEC phần mềm | Đánh giá sau | Thử khi âm thanh loa lọt vào micro gây vấn đề. Phải kiểm tra cả lúc người nói và loa cùng hoạt động. Chưa chọn giải pháp hoặc mua riêng. |
| Touchscreen chính | Giai đoạn thiết bị độc lập | Chưa chốt kích thước/model. Dùng laptop trước theo quyết định cuối. |
| micro-HDMI -> HDMI | 1 đường hình ảnh nếu dùng màn HDMI | Kiểm tra cáp/adapter sẵn có và bộ phụ kiện trước mua. Không dùng để đưa desktop Pi lên laptop qua VNC/web. |
| Cáp USB touch + nguồn màn | Theo đúng model màn | Là các đường riêng với HDMI. Không giả định Pi cấp đủ nguồn cho màn. |
| Powered USB hub | Chờ kiểm tra tải/cổng | Chỉ thêm nếu thiếu cổng hoặc nguồn ngoại vi không đáp ứng. |
| HC-SR04 / VL53L1X | Cảm biến mở rộng | HC-SR04 có trong danh sách kho; chưa chọn cho sản phẩm. Chưa cần mua VL53L1X. |
| Pin/UPS, đo nguồn, vỏ | Giai đoạn sau | Chọn sau khi biết công suất, thời gian dự phòng và bố trí cơ khí. |

**Đợt đầu: chưa xác định món bắt buộc phải mua mới để bắt đầu STT.** Có thể làm kiểm thử phần mềm và thu bằng webcam đã có. Thử vọng âm thực tế còn phụ thuộc loa; không ghi là đã đạt chỉ từ bản thu webcam hoặc tai nghe.

Ưu tiên khảo sát mua trực tiếp tại Đà Nẵng (Nguyễn Hiền, SPIDER, BKM) hoặc Shopee khi phát sinh món cần mua. Chưa xác minh giá, tồn kho, bộ phụ kiện hay thời gian giao trong lượt này. Mức trần mua bổ sung chưa được cung cấp. Không đưa thời gian giao hàng chưa xác nhận vào lịch bắt buộc.

Nguồn tồn kho và xác nhận thu/phát: `C:\Users\LAPTOP T&T\Downloads\iot-communication-support-system.md`, đặc biệt phần bàn giao cuối. Hướng dẫn nguồn Pi: https://www.raspberrypi.com/documentation/computers/getting-started.html . Tài liệu hãng ghi nguồn Pi 4 là 5 V–3 A; vẫn phải kiểm tra nguồn thực tế khi có tải.
