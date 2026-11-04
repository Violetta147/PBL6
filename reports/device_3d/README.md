# Mô hình bố trí 3D — thiết bị hỗ trợ giao tiếp để bàn

Ngày: **28/10/2026**. Phạm vi: mô hình bố trí và trình diễn, theo câu trả lời của người dùng trong chat. Kích thước chưa có được phép ước lượng và phải ghi rõ. Đây chưa phải CAD để chế tạo hoặc kiểm chứng độ bền, nhiệt, âm học hay nguồn điện.

## Xem mô hình

1. Mở **`index.html`** bằng Chrome hoặc Edge. Có thể mở bằng cách nhấp đúp; thư viện đã đóng gói trong file, không cần Internet hoặc cài Node để xem.
2. Kéo để xoay, cuộn/pinch để zoom. Chọn **Mặt trước** (người ký hiệu), **Mặt sau** (người đối thoại) hoặc **Góc gốc**.
3. **Lắp ráp** xem hình dáng vỏ; **Bên trong** bỏ các tấm vỏ; **Tách cụm** và thanh trượt đưa các cụm ra ngoài để nhìn bố trí.
4. Nhấp một cụm hoặc chọn trong danh sách để đọc tên, trạng thái, thông số riêng. **Xem riêng** cô lập cụm; **Ẩn bộ phận** là thao tác có thể đảo ngược.
5. ESP32 và quạt tắt mặc định, có thể bật để xem phương án. Pin và cảm biến khoảng cách không được tự thêm vào bản mặc định.
6. **Xuất GLB đang xem** giữ trạng thái bố trí/ẩn hiện hiện tại. **Lưu ảnh PNG** lưu riêng góc nhìn 3D.

Nếu thiết bị không hỗ trợ WebGL, có thể xem ảnh `preview.png`, đọc `specification.json`, hoặc mở GLB trong phần mềm 3D hỗ trợ glTF.

## Các file bàn giao

- `index.html`: bản xem tương tác độc lập, không tải tài nguyên từ mạng.
- `pbl6-device-assembled.glb`: mô hình lắp ráp mặc định, giữ tên và metadata từng cụm.
- `pbl6-device-exploded.glb`: bố trí tách cụm. Dây được bỏ trong tư thế này; không biểu diễn dây bị kéo giãn.
- `specification.json`: thông số và giả định của từng cụm.
- `preview.png`: ảnh toàn trang của bản xem desktop.
- `VALIDATION.md`: các phép kiểm tra và giới hạn.
- `THIRD_PARTY_LICENSES.txt`: giấy phép thư viện được đóng gói.

GLB dùng **mét**, thông qua hệ số `.001` ở nút gốc; tọa độ mô hình nguồn dùng **mm**. File mặc định không chứa ESP32/quạt. Muốn xuất chúng, bật trong bản xem và dùng nút xuất. glTF không có trạng thái ẩn giống bản xem, vì vậy cụm đang ẩn được bỏ khi xuất, thay vì khẳng định chúng vẫn có thể bật lại từ file GLB.

## Các lựa chọn đã nhận

| Nội dung | Quyết định |
|---|---|
| Mục đích | Bố trí và trình diễn; cho phép kích thước ước lượng |
| Vỏ | Vỏ liền, các tấm tháo phục vụ quan sát/bảo trì |
| Màn | Một màn cảm ứng 7 inch, phương án dự kiến |
| Hướng | Màn/camera về phía người ký hiệu; loa về phía người đối thoại |
| Loa, micro, nguồn, quạt và MCU | Chưa chốt model hoặc tích hợp |

Vỏ đề xuất khoảng **220 × 145 × 207 mm**, gồm camera, màn nghiêng **12°**. Đây là số bố trí do bản mô hình chọn, không phải kích thước đã đo hoặc đã chốt trong đồ án. Chuyển động tách cụm là exploded view để quan sát, không chứng minh một quy trình tháo lắp không va chạm.

## Cơ sở linh kiện và hình học

| Cụm | Nguồn hoặc giả định |
|---|---|
| Pi 4B 8 GB | PCB khoảng 85 × 56 mm theo Raspberry Pi; đầu nối/chip dựng đơn giản, không phải CAD chính thức |
| microSD 32 GB | Có trong trao đổi gốc; hình học dùng kích thước danh nghĩa |
| Màn dự kiến | Trang NH2067 ghi 7 inch, 1024×600, 17×10 cm. Chiều dày 10 mm, vùng ảnh 153,5 × 90 mm và gá lắp là ước lượng. Chưa xác minh bản vẽ kỹ thuật, khoảng hở đầu nối, phụ kiện và biến thể cảm ứng |
| Webcam Aioneus USB 1080p | Tên từ trao đổi gốc; khối 72 × 30 × 28 mm là mô phỏng vì thiếu mã model/kích thước. Không suy ra có micro hoặc góc nhìn bao nhiêu |
| Loa + ampli | Hình học đại diện Ø50 mm và bo ampli; chưa chọn sản phẩm. Không coi đây là bản vẽ của Loyfun 804 |
| Thu âm | Cụm đại diện theo nhu cầu STT; chưa chọn USB mic, mic webcam hoặc AEC. Vị trí phía người đối thoại là đề xuất bố trí |
| Nguồn | Chỉ vùng đầu vào DC/phân phối. Adapter AC/DC đặt ngoài vỏ; chưa chọn điện áp từng nhánh, dòng tổng hoặc bo cụ thể. Không thêm mạch nguồn AC trần bên trong |
| ESP32 | Vị trí tùy chọn, 52 × 28 mm ước lượng; biến thể DevKit V1 chưa rõ; tắt mặc định |
| Quạt | Vị trí tùy chọn 40 × 40 × 10 mm ước lượng. Không xác nhận quạt hai dây trong kho có kích thước này; tắt mặc định |

## Phát triển lại

Trong thư mục này, dùng Node 22 hoặc tương đương:

```powershell
npm ci
npm run build
npm test
node qa-browser.mjs
```

`qa-browser.mjs` dùng Playwright từ runtime Codex và Edge có sẵn. Có thể đặt `PLAYWRIGHT_PACKAGE` đến package Playwright khác, `BROWSER_CHANNEL=chrome` để đổi trình duyệt. Script kiểm tra UI bằng WebGL, xuất hai GLB, kiểm tra header/metadata/đơn vị và chụp ảnh desktop/mobile. Không gọi model ML hoặc phần cứng.

`npm run serve` chỉ mở máy chủ trên **127.0.0.1:8766**, phục vụ bản xem trong panel trình duyệt nếu cần. Mở file HTML trực tiếp vẫn là cách xem độc lập.

## Vai trò trong dự án

Đây là bản phác thảo hình dáng và bố trí cho sản phẩm cuối. Không phải yêu cầu triển khai hay bằng chứng hoàn thành ứng dụng STT. Chỉ cần dùng lại khi chốt ngoại vi, vị trí micro/màn hình và thiết kế vỏ.
