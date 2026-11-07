# Hướng dẫn sử dụng màn hình NH2067 với Raspberry Pi 4

**Dành cho nhóm PBL6 · 07/11/2026**

<strong style="color:#087789;">HDMI đưa hình lên màn</strong>. Dùng lại dây USB và cổng **Touch** mà người dùng đã thử nhận chạm với Pi 4. <strong style="color:#946200;">Bo thực tế có hai cổng vật lý cùng ghi Touch</strong>. Vai trò cấp nguồn và dữ liệu của từng cổng cần xác minh trước khi đổi cách nối. Pi 4 dùng adapter USB‑C của Pi.

## 1. Nhận đúng màn và chuẩn bị dây

Trang Nguyễn Hiền dùng mã bán hàng **NH2067** và mô tả màn cảm ứng HDMI **7 inch, 1024 × 600**. Ảnh của **bo thực tế** do người dùng gửi cho thấy dòng **7inch HDMI Display**, **1024 × 600 Pixel** và **USB Touch**. Hai cổng nhỏ đều ghi **Touch**, một cổng gần công tắc ON/OFF và một cổng gần HDMI. [Trang NH2067](https://www.dientunguyenhien.vn/show/2067)

Ảnh mặt sau **trên trang bán** minh họa bo **Waveshare 7inch HDMI LCD (C), Rev4.1**, có một cổng micro‑USB và một hàng chân hàn. Bố trí khác với bo thực tế trong ảnh người dùng gửi. Dùng tài liệu Waveshare để tham khảo mẫu Rev4.1 trong ảnh bán hàng. [Ảnh mặt sau trên trang bán](https://www.dientunguyenhien.vn/public/images/lcd_7inch_1.jpg) · [Hướng dẫn cổng của Waveshare](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29#Interface_Introduction)

| Dây cần dùng | Cắm ở Pi 4 | Cắm ở màn | Công dụng |
| --- | --- | --- | --- |
| **Micro‑HDMI → HDMI** đã mua cùng màn | Cổng micro‑HDMI, ưu tiên cổng **HDMI0** khi thử một màn | HDMI cỡ chuẩn | Hình ảnh |
| **USB‑A → micro‑USB có truyền dữ liệu** | Cổng USB‑A | Cổng **Touch** đã thử hoạt động | Dữ liệu cảm ứng. Có thể đồng thời cấp nguồn cho màn tùy theo cách đấu trên bo. |
| **Adapter USB‑C của Pi 4** | Cổng nguồn USB‑C | — | Cấp nguồn cho Pi và thiết bị USB đang nối |

[Cổng và nguồn Raspberry Pi 4](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply) · [Kết nối màn 7inch HDMI LCD (C)](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29#Hardware_Connection)

## 2. Kết nối và bật màn

1. Nếu Pi đang chạy, tắt máy qua menu hệ điều hành, chờ tắt hẳn rồi ngắt adapter của Pi.
2. Nối **USB‑A từ Pi** đến đúng cổng **Touch** đã thử nhận chạm. Dùng dây có truyền dữ liệu.
3. Nối **micro‑HDMI từ Pi** đến cổng **HDMI** trên màn. Đặt công tắc của màn ở **ON**.
4. Cắm lại adapter USB‑C của Pi và chờ hệ điều hành khởi động. Kiểm tra lần lượt **lên hình**, sau đó **chạm một lần vào một nút** trên desktop.

Nếu màn lên hình và nhận chạm ổn định khi giữa Pi và màn chỉ có dây HDMI và một dây USB, có thể tiếp tục dùng cách nối đó. Mức **2,5 W ở 5 V** là thông số cho mẫu **Waveshare** tham chiếu. Dòng tiêu thụ của bo hai cổng chưa được đo. Raspberry Pi công bố giới hạn **1,2 A tổng cho các thiết bị USB** trên Pi 4 Model B. Khi lắp thêm webcam, loa USB hoặc thiết bị khác, thử lại với đúng bộ ngoại vi sẽ dùng. [Thông số Waveshare](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29#Specification) · [Yêu cầu nguồn Raspberry Pi](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#typical-power-requirements)

### Hai cổng Touch và nguồn ngoài

**Cách đang dùng.** Adapter **5 V – 3 A** sẵn có cấp điện cho Pi 4. Nối **một dây USB dữ liệu** từ Pi đến cổng Touch đã thử. Dây này vừa cấp điện cho màn vừa đưa tín hiệu chạm về Pi. Để trống cổng Touch còn lại. [BOM PBL6](STT_BOM.md)

Tài liệu **LCDWiki MPI7002** cho thấy bố trí cổng tương tự và mô tả hai cổng của mẫu đó có cùng chức năng nguồn và dữ liệu. Nhóm chưa xác nhận bo thực tế có đúng mã này hoặc hai đường 5 V được đấu thế nào. [Tài liệu MPI7002, trang 7](https://www.lcdwiki.com/res/MPI7002/7inch_MPI7002_datasheet.pdf#page=7)

**Nếu sau này cần giảm tải USB cho Pi.** Dùng **hub USB có nguồn riêng**, tức bộ chia có adapter cấp điện cho thiết bị cắm vào hub. Chọn hub truyền được dữ liệu và không cấp ngược nguồn qua dây nối về Pi. Dùng đúng adapter theo thông số của hub. [Raspberry Pi về nguồn USB](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#typical-power-requirements) · [Raspberry Pi về cấp ngược nguồn](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#back-powering)

```text
Adapter 5 V – 3 A của nhóm → cổng nguồn USB-C của Pi 4
Adapter của hub            → cổng nguồn riêng của hub
Pi 4 ↔ USB ↔ hub ↔ một dây USB ↔ cổng Touch đã thử trên màn
Pi 4 → cáp HDMI → cổng HDMI trên màn
```

**Adapter của hub cắm vào hub.** Dây nối từ hub đến màn mang cả nguồn 5 V từ hub và dữ liệu cảm ứng. Hai phần dùng các đường dây khác nhau trong cùng cáp USB. Khi đổi cách nối, tắt Pi qua hệ điều hành và ngắt nguồn Pi, hub. Chuyển đầu USB của dây màn đang cắm vào Pi sang một cổng USB thiết bị trên hub, rồi nối dây USB của hub về Pi. Sau khi nối xong, cấp nguồn và thử lên hình, chạm.

<strong style="color:#946200;">Chỉ cắm một cổng Touch trên màn.</strong> Tránh cắm USB từ Pi vào một cổng rồi cắm củ sạc vào cổng Touch thứ hai. Nếu hai cổng chung đường 5 V, hai nguồn sẽ nối song song. Vấn đề cần tránh là dòng điện có thể chạy ngược về Pi, dù điện áp hai nguồn không cộng thành 10 V. Củ sạc cắm riêng vào màn cũng chỉ cấp điện. Pi cần đường dữ liệu USB để nhận cảm ứng. [Giải thích về cấp ngược nguồn](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#back-powering)

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
