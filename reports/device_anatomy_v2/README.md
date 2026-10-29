# Thiết bị giao tiếp để bàn — Anatomy 02

Bản mới ngày29/10/2026. Mở index.html bằng Chrome/Edge, không cần Internet hoặc cài thêm phần mềm. Thư mục độc lập với device_3d trước đó.

## Cách xem
- Kéo ngang để xoay360°, dùng thanh Phóng to để xem chi tiết.
- Lắp ráp / Mở vỏ / Tách cụm; thanh tách điều khiển mức mở.
- Bấm trực tiếp lên cụm hoặc tên trong danh sách. Xem riêng tự đưa cụm vào giữa.
- Phía người ký / Phía đối thoại đổi hướng. Phím trái/phải xoay, E tách, Home đặt lại.
- Sáng/Tối đổi chủ đề. Lưu hình SVG xuất góc đang xem dạng vector.
- Tab Cách giao tiếp giải thích camera → preprocessing → SPOTER → xác nhận → loa và micro → ASR → màn. Có công thức attention và ablation của Minh.
- Tab Căn cứ & giới hạn ghi nguồn và trạng thái quyết định.

## File chính
- index.html, index-dark.html: hình học3D được chiếu lại bằng SVG khi xoay;121 khối,12 cụm.
- preview.png, exploded.png: ảnh toàn trang; exploded.svg: hình vector tư thế tách.
- specification.json: thông số/giả định; graph-evidence.json: trích graph và nguồn.
- DESIGN.md: concept trước khi dựng. VALIDATION.md: kết quả kiểm tra gồm các phép chưa đạt.
- model.mjs, live.js, page.html, style.css, build.mjs: nguồn chỉnh sửa; vendor/: anatomy và giấy phépMIT; checks/: ảnh/log kiểm tra.

## Những lựa chọn giữ đúng
Vỏ liền; màn cảm ứng7inch dự kiến; màn/camera hướng người ký, loa hướng người đối thoại. Camera AioneusUSB1080p và microSD32GB theo trao đổi gốc; Pi4B8GB theo B04. NH2067 mô tả1024×600 và17×10cm, chưa có CAD/lỗ gá/chiều dày. Loa, mic, nguồn chưa chốt, hình đại diện. ESP32/quạt/pin/cảm biến không tự thêm vào cấu hình mặc định.

Vỏ mới khoảng220×145×216mm, màn đứng; khác đề xuất màn nghiêng12° của bản trước. Kích thước cơ khí là ước lượng. Khe gió là đồ họa trên mặt, chưa mô phỏng thông gió. Vít là chi tiết mặt, không có ren. Chưa định tuyến dây do thiếu model và khoảng hở. Không có file chế tạoSTL/STEP hoặc sơ đồ điện.

## Nguồn đọc lại
- LearnHarness/data/graph/nodes.jsonl, chains.jsonl, sources.json trong AppData/Roaming.
- Chat gốc chat_mvoydjut_49dd56bb: cảm ứng, Aioneus, microSD, ứng viên màn/loa; không coi kho linh kiện là BOM.
- PBL6/reports/DEMO_BUOI_01_04.md và noteSTT liên kết graph: Zipformer trên Pi với WAV; không suy ra live hoàn thiện.
- SLR/minh_read/TOM_TAT_SPOTER_AUGMENTATION_ERROR_ANALYSIS_CSLR.md(27/10): preprocessing, bốn lượt ablation, input64×128, chiếu128→108, encoder/decoder6+6,400 lớp từ đơn.
- NH2067: https://www.dientunguyenhien.vn/show/2067 ; Pi: https://www.raspberrypi.com/documentation/computers/sbcs.html . Kích thước tham khảo từ lần kiểm tra28/10 ở bản trước.

## Dựng lại
Node22: npm run build; npm test. node qa-browser.cjs dùng Playwright của môi trường hiện tại, có thể đặt PLAYWRIGHT_PACKAGE và CHROME_PATH. npm run serve mở127.0.0.1:8767. Nhấp đúpHTML vẫn dùng được.

Đọc VALIDATION.md trước khi suy luận cơ khí. Đây là bản bố trí/trình diễn, chưa có chứng nhận audit anatomy đầy đủ hoặc kiểm chứng phần cứng.
