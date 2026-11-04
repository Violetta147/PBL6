# Thiết bị giao tiếp để bàn — Anatomy 02

Bản mới ngày29/10/2026. Mở index.html bằng Chrome/Edge, không cần Internet hoặc cài thêm phần mềm. Thư mục độc lập với device_3d trước đó.

## Cách xem
- Kéo ngang để xoay360°, dùng thanh Phóng to để xem chi tiết.
- Lắp ráp / Mở vỏ / Tách cụm; thanh tách điều khiển mức mở.
- Bấm trực tiếp lên cụm hoặc tên trong danh sách. Xem riêng tự đưa cụm vào giữa.
- Phía người ký / Phía đối thoại đổi hướng. Phím trái/phải xoay, E tách, Home đặt lại.
- Sáng/Tối đổi chủ đề. Lưu hình SVG xuất góc đang xem dạng vector.
- Tab Cách giao tiếp giải thích camera → preprocessing → SPOTER → xác nhận → loa và micro → ASR → màn. Có công thức attention và ablation của Minh.
- Tab Thông số & giới hạn mô tả các giả định và phần chưa kiểm chứng.

## File chính
- index.html, index-dark.html: hình học3D được chiếu lại bằng SVG khi xoay;121 khối,12 cụm.
- preview.png, exploded.png: ảnh toàn trang; exploded.svg: hình vector tư thế tách.
- specification.json: thông số và giả định bố trí.
- DESIGN.md: concept trước khi dựng. VALIDATION.md: kết quả kiểm tra gồm các phép chưa đạt.
- model.mjs, live.js, page.html, style.css, build.mjs: nguồn chỉnh sửa; vendor/: anatomy và giấy phépMIT; checks/: ảnh/log kiểm tra.

## Những lựa chọn giữ đúng
Vỏ liền; màn cảm ứng7inch dự kiến; màn/camera hướng người ký, loa hướng người đối thoại. Camera AioneusUSB1080p và microSD32GB theo trao đổi gốc; Pi4B8GB theo B04. NH2067 mô tả1024×600 và17×10cm, chưa có CAD/lỗ gá/chiều dày. Loa, mic, nguồn chưa chốt, hình đại diện. ESP32/quạt/pin/cảm biến không tự thêm vào cấu hình mặc định.

Vỏ mới khoảng220×145×216mm, màn đứng; khác đề xuất màn nghiêng12° của bản trước. Kích thước cơ khí là ước lượng. Khe gió là đồ họa trên mặt, chưa mô phỏng thông gió. Vít là chi tiết mặt, không có ren. Chưa định tuyến dây do thiếu model và khoảng hở. Không có file chế tạoSTL/STEP hoặc sơ đồ điện.

## Dựng lại
Node22: npm run build; npm test. node qa-browser.cjs dùng Playwright của môi trường hiện tại, có thể đặt PLAYWRIGHT_PACKAGE và CHROME_PATH. npm run serve mở127.0.0.1:8767. Nhấp đúpHTML vẫn dùng được.

Đọc VALIDATION.md trước khi suy luận cơ khí. Đây là bản bố trí/trình diễn, chưa có chứng nhận audit anatomy đầy đủ hoặc kiểm chứng phần cứng.

## Vai trò trong dự án

Bản phác thảo dùng để hình dung sản phẩm cuối; chưa cần đưa vào các mốc xây dựng ứng dụng STT. Chỉ dùng lại khi chọn ngoại vi và thiết kế bố trí/vỏ.
