# Anatomy v2 — concept và danh mục trước khi dựng
Ngày 29/10/2026. Một thiết bị giao tiếp để bàn vỏ liền; tháo tấm vỏ và kéo các khay ra để giải thích vai trò linh kiện. Các cụm tách theo trục, toàn thiết bị xoay quanh trục đứng.

Mức Hero, một chủ thể 3D. Bản mới độc lập với reports/device_3d. Màn 7 inch dự kiến, camera cùng phía người ký; loa và micro phía đối thoại. Các lựa chọn này đã được người dùng trả lời; không hỏi lại.

## Danh mục dự kiến (trên 100 khối có mục đích)
- Đế: 4 chân cao su, 4 đệm chân, tấm đế, gờ đỡ trái/phải, 4 chân gá khay.
- Vỏ: 2 hông, nắp trên, 4 thanh mặt trước quanh cửa màn, 4 thanh mặt sau quanh loa, gân/khe thoáng; vít biểu diễn bằng chi tiết trên mặt.
- Hiển thị: thân LCD 170×100 mm (NH2067 mô tả), lớp cảm ứng, viền cửa; chiều dày/gá chỉ ước lượng.
- Camera: chân gá, khớp đỡ, thân 72×30×28 mm ước lượng, vành ống kính, kính, chỉ báo, hai miếng mặt trước.
- Tính toán: khay, 4 trụ, PCB Pi4B85×56, CPU, RAM, chip USB, Ethernet, 2 cụm USB, GPIO và 40 chân, 2 microHDMI, USB-C, jack audio, khe microSD và thẻ 32GB. Vị trí chi tiết là giản lược, không dùng chế tạo.
- Âm thanh: khung loa, nam châm, màng nón, vành, lưới; mic và vỏ đầu thu; bo ampli, IC, tụ và đầu nối. Đều là đại diện chưa chốt.
- Nguồn: khay, vùng bo DC, đầu DC, 3 đầu phân phối, linh kiện đại diện; adapter ngoài vỏ, không có nguồn AC trong mô hình.

## Quy ước
Đơn vị mm; x ngang, y hướng người ký, z lên. Đế220×145mm; chiều cao mới216mm là ước lượng. Màn đứng trong bản này (thay đề xuất nghiêng12° của v1), để minh họa mặt và cửa tháo rõ ràng; chưa có thiết kế công thái học chốt. Khe gió/vít/PCB không phải CAD sản phẩm. Không dựng dây mềm nối giữa hai cụm đang tách; mô tả USB/HDMI/audio/DC trong bảng kết nối. Không đưa ESP32/quạt/pin/cảm biến thành cấu hình mặc định.

## Nguồn kiểm tra lại
Graph nodes/chains/sources → src_d9fcd3d718fa → note tổng kết SPOTER 27/10 ở SLR; src_038a26911ea8/src_656d18e1bd0c → báo cáo/note STT ở PBL6. Chat gốc xác nhận AioneusUSB1080p và microSD32GB; bảng loa/màn là lựa chọn bạn của người dùng đề xuất, chưa phải BOM đã mua.
