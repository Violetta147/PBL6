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

### Cổng Touch, hàng chân hàn và nguồn ngoài

Nhóm có sẵn **một adapter 5 V – 3 A dành cho Pi 4**. Dùng adapter đó cấp điện cho Pi, rồi nối USB từ Pi đến cổng **Touch** của màn để cấp điện và truyền dữ liệu chạm như trong bài thử ban đầu. [BOM PBL6](STT_BOM.md)

Ảnh bo Rev4.1 của Nguyễn Hiền cho thấy **cổng micro‑USB Touch** và dãy **`5V`, `DN`, `DP`, `GND`** cạnh cổng. Dãy này là hàng chân hàn đưa nguồn và dữ liệu USB ra ngoài. Hãng nêu có thể dùng các chân này để tích hợp nguồn ngoài. <strong style="color:#946200;">Tránh cấp đồng thời 5 V từ Pi qua USB và từ adapter ngoài vào bo</strong> khi chưa xác minh cách tách hai đường nguồn trên đúng revision. Nếu bo thực tế có hai cổng cắm USB vật lý, chụp rộng mặt sau để thấy cả hai cổng và nhãn trước khi chọn cách nối. [Ảnh mặt sau bo](https://www.dientunguyenhien.vn/public/images/lcd_7inch_1.jpg) · [Mô tả phần cứng Waveshare](https://www.waveshare.com/7inch-HDMI-LCD-C.htm) · [Raspberry Pi về cấp ngược nguồn qua USB](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#back-powering)

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

## 5. Thử thêm mic, loa và camera

Gắn ngoại vi vào máy thực hiện thao tác tương ứng. Với cấu hình kiosk chạy trên Pi, dùng **màn NH2067 và webcam Aioneus có mic tích hợp** để thử thu âm trước. Nếu xử lý ký hiệu trên laptop, camera phục vụ ký hiệu có thể gắn laptop. Pi chỉ cần nhận văn bản khi hai luồng được tích hợp. [Thiết bị hiện có trong BOM](STT_BOM.md) · [Luồng thu âm Pi trong đặc tả](STT_SYSTEM_SPEC.md)

| Thiết bị | Khi cần dùng |
| --- | --- |
| **Webcam Aioneus / mic** | Cắm webcam vào Pi để dùng mic tích hợp khi thử STT. Thử mic USB riêng nếu mic hiện có chưa đáp ứng. |
| **Tai nghe hoặc loa** | Cắm tai nghe 3,5 mm đang có để thử phát. Để hai người cùng nghe, có thể dùng loa chủ động có nguồn riêng và ngõ AUX 3,5 mm. Nếu loa lấy điện từ USB của Pi, tính loa vào tổng tải USB. |
| **Camera cho ký hiệu** | Gắn vào máy chạy nhận dạng ký hiệu. Bài thử STT và TTS chỉ cần thu, phát âm thanh và văn bản. |

[Thông số phần cứng Pi 4](https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-product-brief.pdf) · [Cách chọn đầu ra âm thanh](https://www.raspberrypi.com/documentation/computers/configuration.html#change-audio-output)

1. Thử **Pi + màn**, rồi gắn **webcam Aioneus** và kiểm tra chạm trong lúc thu thử. Thêm thiết bị phát ở lượt sau để dễ xác định thiết bị nào gây gián đoạn nếu có.
2. Khi bản ứng dụng trên Pi sẵn sàng, chạy một lượt **thu → nhận dạng → gửi → phát**, đồng thời kiểm tra màn có chớp, chạm có ngắt quãng và âm thanh có mất kết nối không.
3. Mở **Terminal trên Pi** và chạy lệnh dưới đây trước và sau lượt thử. Ghi lại cả hai kết quả và danh sách thiết bị đang cắm.

```bash
vcgencmd get_throttled
```

`throttled=0x0` nghĩa là lệnh không báo cờ cảnh báo tại thời điểm kiểm tra. Cờ `0x1` cho biết Pi đang phát hiện sụt áp, cờ `0x10000` cho biết đã từng phát hiện sụt áp. Các cờ có thể xuất hiện cùng nhau. Lệnh này theo dõi tình trạng Pi, còn màn và ngoại vi cần được kiểm tra bằng thao tác thực tế. Nếu nguồn hoặc cổng USB không đáp ứng khi chạy đúng bộ thiết bị, cân nhắc **hub USB có adapter riêng** để cấp điện cho ngoại vi vẫn cần truyền dữ liệu với Pi. [Giải nghĩa các cờ trên Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled) · [Giới hạn USB và khuyến nghị về hub](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#typical-power-requirements)

## Tình trạng thử của PBL6

<strong style="color:#087A47;">Đã thử kết nối và có phản hồi chạm</strong> theo báo cáo người dùng ngày **07/11/2026**. Cảm giác chạm hơi khác điện thoại. <strong style="color:#946200;">Cần kiểm tra tiếp</strong> độ phân giải đang chạy, vị trí chạm và bàn phím ảo trong ứng dụng. [Ghi nhận trong BOM](STT_BOM.md)
