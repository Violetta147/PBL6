# Hướng dẫn sử dụng màn hình NH2067 với Raspberry Pi 4

**Dành cho nhóm PBL6 · 07/11/2026**

Nếu bo màn khớp với ảnh mặt sau của Nguyễn Hiền, chỉ cần hai dây giữa Pi và màn. <strong style="color:#087789;">HDMI đưa hình lên màn</strong>. <strong style="color:#087789;">Micro‑USB Touch vừa cấp nguồn 5 V cho màn vừa truyền dữ liệu chạm về Pi</strong>. Pi 4 vẫn dùng adapter USB‑C của Pi. [Ảnh mặt sau từ Nguyễn Hiền](https://www.dientunguyenhien.vn/public/images/lcd_7inch_1.jpg) · [Hướng dẫn cổng của Waveshare](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29#Interface_Introduction)

## 1. Nhận đúng màn và chuẩn bị dây

Trang Nguyễn Hiền dùng mã bán hàng **NH2067** và mô tả màn cảm ứng HDMI **7 inch, 1024 × 600**. Ảnh mặt sau trên trang cho thấy bo in **Waveshare 7inch HDMI LCD (C), Rev4.1**, với cổng **Display**, cổng **Touch** và công tắc **Backlight**. <strong style="color:#946200;">Đối chiếu chữ in trên bo đang dùng</strong> trước khi áp dụng hướng dẫn cổng bên dưới. Phiên bản của bo thực tế cần xác nhận trên thiết bị. [Trang NH2067](https://www.dientunguyenhien.vn/show/2067) · [Ảnh mặt sau](https://www.dientunguyenhien.vn/public/images/lcd_7inch_1.jpg)

| Dây cần dùng | Cắm ở Pi 4 | Cắm ở màn | Công dụng |
| --- | --- | --- | --- |
| **Micro‑HDMI → HDMI** đã mua cùng màn | Cổng micro‑HDMI, ưu tiên cổng **HDMI0** khi thử một màn | HDMI cỡ chuẩn, nhãn **Display** | Hình ảnh |
| **USB‑A → micro‑USB có truyền dữ liệu** | Cổng USB‑A | Cổng micro‑USB, nhãn **Touch** | Nguồn 5 V và dữ liệu cảm ứng |
| **Adapter USB‑C của Pi 4** | Cổng nguồn USB‑C | — | Cấp nguồn cho Pi và thiết bị USB đang nối |

[Cổng và nguồn Raspberry Pi 4](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply) · [Kết nối màn 7inch HDMI LCD (C)](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29#Hardware_Connection)

## 2. Kết nối và bật màn

1. Nếu Pi đang chạy, tắt máy qua menu hệ điều hành, chờ tắt hẳn rồi ngắt adapter của Pi.
2. Nối **USB‑A từ Pi** đến cổng **Touch** trên màn. Dùng dây có truyền dữ liệu để thử cả cảm ứng.
3. Nối **micro‑HDMI từ Pi** đến cổng **Display** trên màn. Gạt **Backlight** sang **ON** nếu bo có công tắc như ảnh.
4. Cắm lại adapter USB‑C của Pi và chờ hệ điều hành khởi động. Kiểm tra lần lượt **lên hình**, sau đó **chạm một lần vào một nút** trên desktop.

Nếu màn lên hình và nhận chạm ổn định với cách nối này, có thể dùng nguồn từ USB của Pi. Waveshare công bố mức tiêu thụ màn khoảng **2,5 W** ở **5 V**. Raspberry Pi công bố giới hạn **1,2 A tổng cho các thiết bị USB** trên Pi 4 Model B. Khi lắp thêm webcam, loa USB hoặc thiết bị khác, thử lại với đúng bộ ngoại vi sẽ dùng. [Thông số Waveshare](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29#Specification) · [Yêu cầu nguồn Raspberry Pi](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#typical-power-requirements)

## 3. Kiểm tra độ phân giải, cảm ứng và bàn phím

**Hình ảnh.** Trên **Raspberry Pi OS Trixie Desktop**, mở **Preferences → Control Centre → Screens**, chọn đúng màn HDMI và đọc mục **Resolution**. Nếu hệ thống đang dùng **1024 × 600**, giữ thiết lập đó. Nếu đang dùng chế độ khác và danh sách có **1024 × 600**, chọn chế độ này, bấm **Apply** và xác nhận khi hình hiển thị đúng. Nếu chế độ không xuất hiện, ghi lại tên ngõ HDMI và những độ phân giải đang có để kiểm tra tiếp. [Cài đặt màn hình Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/configuration.html#configure-display-settings)

**Cảm ứng.** Thử chạm một lần vào vài nút ở các vị trí cách xa nhau trên desktop. Ghi lại nút có phản hồi ngay, phải chạm lại hay bị lệch. Sau đó thử cuộn một trang dài. Ghi riêng lỗi chạm và lỗi cuộn để biết khác biệt so với điện thoại nằm ở thao tác nào.

**Bàn phím ảo.** Trên desktop, mở trình soạn thảo hoặc ô nhập của trình duyệt, chạm vào ô, gõ thử **“Tôi muốn hỏi giờ làm việc.”** và dùng phím **Xóa / Backspace**. Nếu bàn phím chưa tự hiện và thanh tác vụ có biểu tượng bàn phím, dùng biểu tượng đó để mở thủ công. Khi có bản kiosk, thử lại trong composer để kiểm tra bàn phím hiện khi chạm vùng soạn, gõ được tiếng Việt và nút **Gửi** còn trong tầm chạm. [Cấu hình bàn phím ảo của Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/configuration.html#configure-onscreen-keyboard) · [Bản phác PBL6 khi bàn phím mở](reports/ui_ux_20261107/assets/wireframe-ban-phim-ao.png)

## 4. Xử lý nhanh khi gặp lỗi

| Hiện tượng | Kiểm tra trước |
| --- | --- |
| Màn tối khi Pi đã khởi động | Kiểm tra dây USB đang vào cổng **Touch** và công tắc **Backlight** ở **ON**. |
| Đèn nền sáng nhưng chưa có hình | Kiểm tra hai đầu HDMI. Thử khởi động với một màn cắm sẵn vào **HDMI0**. |
| Có hình nhưng chưa nhận chạm | Đổi sang dây USB‑A → micro‑USB đã biết có truyền dữ liệu và thử chạm lại. |
| Chạm lệch hoặc điều khiển nhầm màn | Thử với riêng NH2067, để hướng màn **Normal** và chạm lại ở vài vị trí. Ghi rõ nếu chỉ lệch sau khi xoay hoặc khi gắn màn thứ hai. |
| Màn chớp hoặc chạm ngắt quãng khi cắm thêm ngoại vi | Thử lại với màn và Pi trước, rồi thêm từng ngoại vi để xem lỗi xuất hiện khi cắm thiết bị nào. Kiểm tra nguồn Pi và dây USB trước khi chọn cách cấp nguồn khác. |

Nếu đã có hình nhưng cảm ứng vẫn lỗi, mở **Terminal trên Pi** bằng chuột hoặc bàn phím vật lý và chạy:

```bash
cat /etc/os-release
lsusb
```

Gửi lại tên và phiên bản hệ điều hành, đầu ra `lsusb`, cổng đang cắm và mô tả lỗi chạm. `lsusb` cho biết thiết bị nào được Pi nhận qua USB. Tên thiết bị có thể khác nhau theo bo. Việc thiết bị xuất hiện trong danh sách chỉ xác nhận Pi nhận được kết nối USB; vẫn cần thử chạm để kiểm tra thao tác.

## Tình trạng thử của PBL6

<strong style="color:#087A47;">Đã thử kết nối và có phản hồi chạm</strong> theo báo cáo người dùng ngày **07/11/2026**. Cảm giác chạm hơi khác điện thoại. <strong style="color:#946200;">Cần kiểm tra tiếp</strong> độ phân giải đang chạy, vị trí chạm và bàn phím ảo trong ứng dụng. [Ghi nhận trong BOM](STT_BOM.md)
