# Hướng dẫn sử dụng màn hình NH2067 với Raspberry Pi 4

**PBL6 · 07/11/2026**

Tài liệu này hướng dẫn nối màn với Pi 4, thử hình ảnh và cảm ứng, rồi kiểm tra lại khi thêm mic hoặc loa. Với bộ đang hoạt động, dùng **cáp HDMI cho hình ảnh**, **một dây USB cho cổng Touch đã thử** và **adapter 5 V – 3 A sẵn có cho Pi**. [BOM PBL6](STT_BOM.md)

## 1. Nhận diện đúng bo và chuẩn bị dây

Trang Nguyễn Hiền dùng mã bán hàng **NH2067** cho màn cảm ứng HDMI 7 inch, **1024 × 600**. Ảnh của bo nhóm đang dùng cho thấy dòng **7inch HDMI Display**, **1024 × 600 Pixel**, **USB Touch** và hai cổng cùng ghi **Touch**. Một cổng gần công tắc ON/OFF, cổng kia gần HDMI. [Trang NH2067](https://www.dientunguyenhien.vn/show/2067)

Theo thông tin nhóm đọc từ tem hộp, màn là **IPS 7 inch, HDMI, 1024 × 600, cảm ứng điện dung 5 điểm**. Do tem bị rách ở đoạn cuối, mã sản phẩm trên hộp (SKU) <strong style="background-color:#FFF3C4;color:#6E4900;padding:1px 4px;border-radius:3px;">được đọc tạm</strong> là `MP17032`. Lần tra cứu theo mã này và cách đọc `MPI7032` (nếu ký tự sau `MP` là chữ `I`) chưa tìm được tài liệu màn hình tương ứng. Để xác nhận mã bo và phiên bản mạch, đối chiếu chữ in trực tiếp trên bo hoặc hỏi nhà bán theo lô NH2067.

Ảnh trên trang bán minh họa **Waveshare 7inch HDMI LCD (C) Rev4.1**, có một cổng micro‑USB và một hàng chân hàn. Mẫu tham chiếu **LCDWiki MPI7002** khớp với thông số trên tem và có bố trí hai cổng Touch tương tự bo của nhóm. Tài liệu MPI7002 mô tả mỗi cổng của mẫu đó đều dùng được cho nguồn và dữ liệu chạm, mỗi lần chỉ cần một cổng. <strong style="background-color:#FFF3C4;color:#6E4900;padding:1px 4px;border-radius:3px;">Cần xác minh</strong> mã bo thực tế và cách hai cổng chia sẻ đường 5 V. [Ảnh trên trang bán](https://www.dientunguyenhien.vn/public/images/lcd_7inch_1.jpg) · [Tài liệu Waveshare](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29#Interface_Introduction) · [Tài liệu MPI7002, trang 7](https://www.lcdwiki.com/res/MPI7002/7inch_MPI7002_datasheet.pdf#page=7)

**Bảng 1.** Dây cần dùng khi nối trực tiếp Pi 4 với màn.

| Dây | Đầu ở Pi 4 | Đầu còn lại | Công dụng |
| --- | --- | --- | --- |
| **Micro‑HDMI → HDMI** | Micro‑HDMI, ưu tiên **HDMI0** khi thử một màn | Cổng HDMI trên màn | Đưa hình từ Pi lên màn |
| **USB‑A → micro‑USB có dữ liệu** | USB‑A | Một cổng **Touch** đã thử | Nguồn qua USB và dữ liệu cảm ứng |
| **Adapter 5 V – 3 A** | Cổng nguồn **USB‑C** | Ổ điện | Cấp điện cho Pi |

Dây sạc chỉ có đường nguồn có thể làm màn sáng, nhưng cần dây USB <strong style="background-color:#DFF8FC;color:#075A67;padding:1px 4px;border-radius:3px;">có truyền dữ liệu</strong> để Pi nhận thao tác chạm. [Cổng và nguồn Raspberry Pi 4](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply)

## 2. Kết nối và kiểm tra

### 2.1. Cắm trực tiếp với adapter sẵn có

1. Nếu Pi đang chạy, tắt qua menu hệ điều hành, chờ tắt hẳn rồi ngắt adapter.
2. Nối **micro‑HDMI trên Pi** với **HDMI trên màn**. Nối **USB‑A trên Pi** với **cổng Touch đã thử** trên màn. <strong style="background-color:#FFF3C4;color:#6E4900;padding:1px 4px;border-radius:3px;">Để trống cổng Touch kia.</strong>
3. Đặt công tắc màn ở **ON**, cắm lại adapter của Pi và chờ vào desktop. Kiểm tra lên hình, rồi chạm một lần vào một nút.

<strong style="background-color:#FDE7E7;color:#A71F31;padding:1px 4px;border-radius:3px;">Cách đấu cần tránh</strong> Cắm USB từ Pi vào một cổng Touch rồi cắm củ sạc vào cổng Touch thứ hai. Nếu hai cổng dùng chung đường 5 V, cách đấu đó nối hai nguồn song song. Điện áp không cộng thành 10 V, nhưng dòng điện có thể chạy ngược qua USB về Pi và bỏ qua mạch bảo vệ nguồn. [Giải thích cấp ngược nguồn của Raspberry Pi](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#back-powering)

### 2.2. Dùng hub có nguồn riêng nếu cần

Khi bộ ngoại vi thực tế vượt khả năng cấp nguồn USB của Pi, có thể dùng hub USB có adapter riêng. Chọn hub có truyền dữ liệu và có thiết kế tránh cấp điện ngược về Pi. <strong style="background-color:#DFF8FC;color:#075A67;padding:1px 4px;border-radius:3px;">Adapter của hub cắm vào cổng nguồn của hub.</strong> Hình 1 cho thấy Pi và hub dùng hai adapter riêng, còn màn dùng một cổng Touch. [Nguồn và thiết bị USB trên Pi](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#typical-power-requirements)

```mermaid
flowchart LR
    AP["Adapter 5 V – 3 A của Pi"] -->|"Nguồn USB-C"| P["Raspberry Pi 4"]
    AH["Adapter của hub"] -->|"Cổng nguồn của hub"| H["Hub USB có nguồn riêng"]
    P <-->|"USB · dữ liệu"| H
    H -->|"Một dây USB · nguồn 5 V và dữ liệu chạm"| M["NH2067 · một cổng Touch"]
    P -->|"HDMI · hình ảnh"| M
    classDef power fill:#FFF3C4,stroke:#946200,color:#6E4900,font-weight:bold;
    classDef device fill:#DFF8FC,stroke:#087789,color:#075A67,font-weight:bold;
    class AP,AH power;
    class P,H,M device;
```

**Hình 1.** Sơ đồ đề xuất khi dùng hub có nguồn riêng. Mũi tên USB từ hub đến màn chỉ hướng cấp điện. Dữ liệu chạm đi từ màn qua hub về Pi trên cùng dây USB. HDMI vẫn nối thẳng từ Pi đến màn.

Để chuyển cách nối, tắt Pi và ngắt nguồn Pi lẫn hub. Chuyển đầu USB của dây màn từ Pi sang **cổng USB thiết bị trên hub**, rồi nối dây USB của hub về Pi. Cắm adapter của Pi và adapter đúng loại của hub vào cổng nguồn tương ứng, sau đó thử lên hình và chạm. Củ sạc cắm trực tiếp vào Touch chỉ cấp điện. Để cảm ứng điều khiển Pi, dây Touch cần có đường dữ liệu về Pi.

### 2.3. Thử hình ảnh, chạm và bàn phím

1. **Độ phân giải.** Trên **Raspberry Pi OS Trixie Desktop**, vào **Preferences → Control Centre → Screens** và đọc **Resolution** của màn HDMI. Nếu đang ở **1024 × 600**, giữ thiết lập đó. Nếu danh sách có mức này nhưng Pi đang dùng mức khác, chọn <strong style="background-color:#DFF8FC;color:#075A67;padding:1px 4px;border-radius:3px;">1024 × 600</strong>, bấm **Apply** rồi xác nhận nếu hình hiển thị đúng. Nếu mức này không xuất hiện, ghi lại tên ngõ HDMI và các chế độ hiện có. [Cài đặt màn hình Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/configuration.html#configure-display-settings)
2. **Cảm ứng.** Chạm một lần vào vài nút ở các vị trí cách xa nhau. Ghi lại nút phản hồi ngay, cần chạm lại hay bị lệch. Mở một trang dài trong Chromium, <strong style="background-color:#DFF8FC;color:#075A67;padding:1px 4px;border-radius:3px;">vuốt một ngón ngay giữa nội dung</strong> và ghi lại trang có cuộn hay chỉ kéo được khi đặt ngón lên thanh cuộn.

   Nếu chỉ kéo được thanh cuộn hoặc phải chạm hai lần để mở thư mục, vào **Preferences → Control Centre → Screens**, mở menu của màn HDMI rồi xem <strong style="background-color:#DFF8FC;color:#075A67;padding:1px 4px;border-radius:3px;">Touchscreen → Mode</strong>. Trong chế độ **Mouse Emulation** (giả lập chuột), chạm rồi rê ngón tay tương đương giữ nút chuột trái rồi kéo. Nếu đang bật chế độ này, thử chọn **Multitouch** và vuốt lại trên cùng trang trong Chromium. Sau khi đổi, thử lại cả thao tác mở thư mục vì chạm đúp có thể hoạt động khác. [Hai chế độ cảm ứng trên Raspberry Pi OS](https://www.raspberrypi.com/news/a-new-raspberry-pi-os-release/#improved-touchscreen-support)

3. **Bàn phím ảo.** Chạm ô nhập trên desktop, gõ thử **“Tôi muốn hỏi giờ làm việc.”** rồi dùng **Xóa / Backspace**. Nếu bàn phím chưa hiện và thanh tác vụ có biểu tượng bàn phím, dùng biểu tượng đó để mở. Khi có bản kiosk, thử lại trong vùng soạn để xác nhận gõ dấu tiếng Việt, nhìn thấy câu đang sửa và chạm được **Gửi** khi bàn phím mở. [Cài đặt bàn phím ảo](https://www.raspberrypi.com/documentation/computers/configuration.html#configure-onscreen-keyboard) · [Bản phác PBL6 khi mở bàn phím](reports/ui_ux_20261107/assets/wireframe-ban-phim-ao.png)

### 2.4. Thử thêm thiết bị và kiểm tra nguồn

Với kiosk trên Pi, thử **Pi + màn** trước, sau đó thêm **webcam Aioneus** và dùng mic tích hợp để thu thử. Dùng tai nghe 3,5 mm đang có để thử phát, rồi thêm loa ở lượt sau. Nếu loa lấy điện từ USB của Pi, tính loa vào tải USB. Loa chủ động có nguồn riêng và ngõ AUX có thể nhận âm thanh qua jack 3,5 mm. Camera nhận dạng ký hiệu gắn vào máy chạy nhận dạng, chẳng hạn laptop. Khi hai dự án được tích hợp, Pi nhận văn bản để hiển thị hoặc đọc. [BOM thiết bị](STT_BOM.md) · [Đặc tả thu âm trên Pi](STT_SYSTEM_SPEC.md) · [Chọn đầu ra âm thanh](https://www.raspberrypi.com/documentation/computers/configuration.html#change-audio-output)

Pi 4 Model B có giới hạn <strong style="background-color:#FFF3C4;color:#6E4900;padding:1px 4px;border-radius:3px;">1,2 A tổng cho thiết bị USB</strong>. Mức **2,5 W ở 5 V** là thông số của mẫu Waveshare tham chiếu. Dòng của bo hai cổng chưa được đo. Khi ứng dụng trên Pi sẵn sàng, thử một lượt **thu → nhận dạng → gửi → phát** với bộ ngoại vi dự định dùng. Quan sát màn có chớp, cảm ứng có ngắt quãng và âm thanh có mất kết nối hay không. [Giới hạn nguồn USB của Pi](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#typical-power-requirements) · [Thông số mẫu Waveshare](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29#Specification)

Mở **Terminal trên Pi** và chạy lệnh sau trước và sau lượt thử:

```bash
vcgencmd get_throttled
```

Ghi lại hai kết quả và thiết bị đang cắm. `throttled=0x0` nghĩa là không có cờ cảnh báo trong kết quả đọc. Cờ `0x1` báo Pi <strong style="background-color:#FFF3C4;color:#6E4900;padding:1px 4px;border-radius:3px;">đang phát hiện sụt áp</strong>, còn `0x10000` báo đã từng phát hiện sụt áp. Các cờ có thể xuất hiện cùng nhau. Lệnh theo dõi tình trạng Pi. Vẫn cần kiểm tra màn và ngoại vi bằng thao tác thực tế. [Giải nghĩa cờ trên Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled)

### 2.5. Xử lý khi gặp lỗi

**Bảng 2.** Kiểm tra đầu tiên theo triệu chứng.

| Hiện tượng | Kiểm tra trước |
| --- | --- |
| Màn tối khi Pi đã khởi động | Kiểm tra dây USB vào cổng Touch đã thử và công tắc màn ở **ON**. |
| Đèn nền sáng nhưng chưa có hình | Kiểm tra hai đầu HDMI. Thử khởi động với một màn cắm sẵn ở **HDMI0**. |
| Có hình nhưng chưa nhận chạm | Thử dây **USB‑A → micro‑USB có truyền dữ liệu**. |
| Chạm lệch hoặc điều khiển nhầm màn | Thử với riêng NH2067 ở hướng **Normal**. Ghi rõ nếu chỉ lệch khi xoay hoặc gắn thêm màn. |
| Màn chớp hoặc chạm ngắt quãng khi thêm ngoại vi | Thử lại với Pi và màn trước. <strong style="background-color:#DFF8FC;color:#075A67;padding:1px 4px;border-radius:3px;">Thêm từng thiết bị</strong>, kiểm tra nguồn Pi và dây USB khi lỗi xuất hiện. |

Nếu đã có hình mà cảm ứng vẫn lỗi, mở **Terminal trên Pi** bằng chuột hoặc bàn phím vật lý và chạy:

```bash
cat /etc/os-release
lsusb
```

Gửi lại phiên bản hệ điều hành, đầu ra `lsusb`, cổng Touch đang cắm và triệu chứng. `lsusb` cho biết Pi nhận thiết bị nào qua USB. Đối chiếu thêm phản hồi khi chạm để kiểm tra điều khiển thực tế.

## 3. Kết quả thử trên Pi 4

<strong style="background-color:#DDF7E9;color:#0B6B45;padding:1px 4px;border-radius:3px;">Đã thử</strong> Theo báo cáo của người dùng ngày **07/11/2026**, màn <strong style="background-color:#DDF7E9;color:#0B6B45;padding:1px 4px;border-radius:3px;">lên hình và nhận chạm</strong> khi kết nối với Pi 4. Người dùng ghi nhận chỉ cuộn được khi đặt ngón lên thanh cuộn rồi kéo, và phải chạm hai lần để mở ứng dụng hoặc thư mục đã thử. [Ghi nhận kết nối trong BOM](STT_BOM.md)

<strong style="background-color:#FFF3C4;color:#6E4900;padding:1px 4px;border-radius:3px;">Cần xác minh</strong> Ghi lại độ phân giải đầu ra thực tế, cổng Touch đang dùng và độ chính xác của vị trí chạm. Kiểm tra chế độ cảm ứng hiện tại và ghi kết quả vuốt giữa trang trong Chromium nếu thử chuyển sang **Multitouch**. Khi thử trong kiosk, ghi thêm kết quả bàn phím ảo tiếng Việt và thao tác **Gửi**. Sơ đồ hub ở Hình 1 là phương án lắp nếu cần, chưa có kết quả thử trên bộ thiết bị của nhóm.
