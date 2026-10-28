# Kiểm tra mô hình bố trí thiết bị

Ngày kiểm tra: **28/10/2026**. Phạm vi: file HTML, hình học mô hình, tương tác trình duyệt và xuất GLB. Không chạy lại thí nghiệm ML hoặc kiểm tra phần cứng.

## Kiểm tra tự động

`npm test`: **4/4 bài đạt**.

1. Giữ đúng quyết định người dùng; ID cụm không trùng; mỗi cụm có trạng thái/thông số/nguồn hợp lệ; không tự thêm pin hoặc cảm biến.
2. Cả 14 cụm có hình học 3D hữu hạn ở các mức tách 0%, 25%, 50%, 75%, 100%.
3. ESP32 và quạt tắt mặc định; PCB Pi giữ kích thước 85 × 56 mm; bao ngoài không vượt số bố trí ước lượng được báo cáo.
4. Màn/camera ở phía người ký hiệu; loa/thu âm ở phía đối thoại.

Kiểm thử Edge headless/WebGL bằng `node qa-browser.mjs`: **đạt**.

- Mở trực tiếp `file:///…/index.html`, không cần máy chủ hoặc mạng.
- Chuyển giữa lắp ráp, tách cụm, bên trong; đo trạng thái hiển thị thực tế.
- Cô lập Pi, trả lại toàn bộ, bật/tắt ESP32 và quạt.
- Chọn lens camera bằng tọa độ click trên canvas, xác nhận chọn đúng cụm `camera`.
- Không có lỗi JavaScript trong lần kiểm thử hoàn tất; không có request HTTP/HTTPS để tải thư viện hoặc tài nguyên.
- Kiểm tra desktop 1440 px và điện thoại 390 px. Ở 390 px, `scrollWidth = innerWidth = 390`.
- Có kiểm tra bổ sung ở 320 px trong lần rà giao diện cuối; xem `verification.json`.

## Kiểm tra file GLB

Hai file đã được xuất từ mô hình trong trình duyệt và kiểm tra cấu trúc binary:

| File | Kích thước | Nodes | Meshes | Textures |
|---|---:|---:|---:|---:|
| `pbl6-device-assembled.glb` | 1.938.612 byte | 158 | 143 | 1 |
| `pbl6-device-exploded.glb` | 1.872.596 byte | 152 | 138 | 1 |

- GLB magic/version hợp lệ, glTF 2.0.
- Các cụm `pi`, `display` và tên hierarchy được giữ.
- Ma trận ở nút gốc có hệ số `.001`, chuyển tọa độ mm sang mét. Thông tin nguồn, giới hạn và tư thế xuất nằm trong `extras`.
- ESP32/quạt không có trong bản mặc định; dây bỏ ở file tách cụm.
- Texture màn hình được đóng trong GLB.

## Rà soát hình ảnh

Đã mở và xem ảnh desktop lắp ráp, tách cụm, bên trong, mặt sau và ảnh điện thoại. Đã sửa khe chuyển tiếp của mặt trước, góc nhìn bên trong, vị trí Pi trong exploded view và nhãn chọn trên màn nhỏ. Bản xem chỉ vẽ lại khi trạng thái/góc nhìn thay đổi, giảm tải khi đứng yên.

## Giới hạn

- Không phải kiểm tra dung sai cơ khí, độ hở cáp hoặc một đường tháo lắp không va chạm. Tách cụm là công cụ nhìn bố trí.
- Vỏ, gá, chiều dày màn, phần webcam, loa, micro, nguồn và quạt chủ yếu là hình học ước lượng, đã gắn nhãn.
- Chưa mô phỏng tải điện, nhiệt, âm học, khả năng khử vọng, góc nhìn camera, khoảng cách ra dấu hoặc khả năng chạm thực tế.
- Không chứng minh thiết bị tích hợp chạy nhận dạng liên tục hoặc đạt độ trễ sản phẩm.
- Bộ kiểm tra binary/hierarchy không thay thế chứng nhận glTF đầy đủ hoặc kiểm tra bằng mọi phần mềm CAD/3D. Bản HTML/WebGL là bản xem đã trực tiếp kiểm thử.
