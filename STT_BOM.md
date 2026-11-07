# 📋 BOM Tổng Thể Cho Thiết Bị Giao Tiếp (Speech-to-Text)

> **Cập nhật 08/11/2026.** Đồng bộ cấu hình NH2067 đã thử, các phép thử còn chờ và hạng mục mua sắm có điều kiện.<br/>
> **Nguyên tắc tài chính:** BOM dùng chung cho các mốc phát triển. Chi phí đã mua lấy từ chứng từ. Các mẫu còn khảo sát dùng giá niêm yết có ngày kiểm tra. Tận dụng phần cứng đang đáp ứng yêu cầu.

---

> [!IMPORTANT]
> **BOM chính của dự án.** Phiếu bán hàng Điện tử Nguyễn Hiền lúc **17:25 ngày 07/11/2026** ghi **1 màn NH2067, 7 inch, 1024 × 600** và **1 cáp micro-HDMI sang HDMI**, tổng tiền hàng **1.165.000 VNĐ**. Người dùng đã thử kết nối với Pi 4 và xác nhận màn hoạt động, có nhận thao tác chạm. P1 mới có Settings, một file và Electron trên Windows. Capture Pi, batch và kiosk phần cứng chưa hoàn thành. Xem [bàn giao](START_NEXT_CHAT_STT.md) và [báo cáo P1](reports/stt_v1_p1_20261107/BAO_CAO.md).

> **Giá đỡ là phụ kiện.** Hai người có thể cùng nhìn màn khi ngồi cạnh hoặc chếch nhau và xoay cả thiết bị để đổi hướng nhìn. Khi chọn kiểu lắp, đối chiếu kích thước, lỗ bắt vít và chỗ ra dây trên NH2067 thực tế. [Bản phác hội thoại 1024 × 600](reports/ui_ux_20261107/assets/wireframe-hoi-thoai-1024x600.pen)

## 🎯 Tổng Hợp Tình Trạng Ngân Sách Theo 2 Giai Đoạn

| Giai đoạn triển khai | Dự toán chi phí | Trạng thái thiết bị | Mục tiêu kỹ thuật & Chiến lược phần cứng |
| :--- | :---: | :---: | :--- |
| **Giai đoạn 1: Mốc kiểm thử ban đầu (V1)** | <strong style="background-color:#DDF7E9;color:#0B6B45;padding:3px 8px;border-radius:4px;font-size:1.05em;">Chưa xác định cần mua mới</strong> | <span style="color:#087A47;font-weight:700;">TẬN DỤNG PHẦN CỨNG ĐÃ CÓ</span> | P1 đã thử nhận dạng một file qua Deepgram và mở desktop trên laptop. Thu từ mic webcam trong ứng dụng và điều khiển qua LAN còn chờ tích hợp. Chi phí API và mạng được tính riêng. |
| **Giai đoạn 2: Đóng gói Kiosk độc lập** | <strong style="background-color:#FFF3C4;color:#6E4900;padding:3px 8px;border-radius:4px;font-size:1.05em;">Chưa chốt tổng dự toán</strong> | <span style="color:#2457B4;font-weight:700;">DỰ TRÙ MUA SẮM</span> | **Ưu tiên màn cảm ứng HDMI + USB** cho tích hợp đầu tiên; khung vỏ Kiosk + Electron app toàn màn hình. DSI chỉ là bước nâng cấp sau. |

### 🔍 Chi tiết phân bổ dự toán Giai đoạn 2 (Kiosk độc lập)

* **1. Màn hình và cáp hình ảnh đã mua tại Điện tử Nguyễn Hiền.** Tổng tiền hàng theo phiếu là **1.165.000 VNĐ**.
  * **Màn NH2067 (1 cái)** giá **1.090.000 VNĐ**. Đã thử lên hình và nhận chạm trên Pi 4. Mã bo thực tế và phụ kiện trong hộp còn cần đối chiếu.
  * **Cáp micro-HDMI sang HDMI (1 sợi)** giá **75.000 VNĐ**. Đã dùng để nối hình ảnh giữa Pi 4 và màn.
  * **Cấu hình đã thử.** Cáp HDMI mang hình ảnh. Một dây USB dữ liệu nối với một cổng **Touch** để cấp điện cho màn và đưa tín hiệu chạm về Pi. Adapter 5 V – 3 A sẵn có cấp điện cho Pi. [Hướng dẫn NH2067](HUONG_DAN_NH2067_PI4.md)
  * *Tham khảo ứng viên DSI (nâng cấp sau; giá khảo sát 06/11/2026, chưa kiểm tra lại lúc mua):*
    * **Cytron: Raspberry Pi Touch Display 2 (7")** — <strong style="background-color:#E7F0FF;color:#1B4494;padding:1px 5px;border-radius:3px;">2.052.000 VNĐ</strong> *(Đã gồm VAT, kèm cáp DSI 15-15 pin & dây nguồn).*
    * **Raspberrypi.vn: Waveshare DSI 7" (1024×600, kèm case)** — <strong style="background-color:#E7F0FF;color:#1B4494;padding:1px 5px;border-radius:3px;">1.900.000 VNĐ</strong> *(Chưa VAT & ship, kèm sẵn vỏ case).*
* **2. Phụ kiện & âm thanh dự phòng (nếu phát sinh):** Ước tính nháp trong bản highlight: <span style="color:#946200;font-weight:700;">200.000 – 400.000 VNĐ, chưa xác minh và chưa chốt</span>
  * *Bộ dây kết nối.* Dùng cáp micro-HDMI sang HDMI và dây USB dữ liệu đã thử. Chiều dài dây và cách bố trí trong vỏ còn để chọn.
  * *Loa chủ động AUX / USB audio.* Tạm hoãn khảo sát. Khi cần thử người đối diện nghe rõ hoặc kiểm tra vọng âm, ưu tiên tận dụng hoặc mượn.
  * *Hub USB có nguồn riêng.* Chỉ xét sau khi kiểm tra tải thực tế với các ngoại vi. Cách nối an toàn được ghi trong [hướng dẫn NH2067](HUONG_DAN_NH2067_PI4.md).

---

## 🗺️ Lộ Trình Phát Triển & Kiến Trúc Kết Nối

```mermaid
flowchart TD
    subgraph V1["Giai đoạn V1: tận dụng phần cứng sẵn có"]
        direction LR
        Pi4["Raspberry Pi 4B<br/>(8GB RAM, Trixie aarch64)"]
        CamMic["Webcam Aioneus USB<br/>(Micro thu âm có sẵn)"]
        LaptopScreen["Laptop cá nhân<br/>(Electron / Web STT; chưa tích hợp LAN)"]
        Headphone["Tai nghe 3,5 mm<br/>(Đã thử đầu ra âm thanh)"]
        Pi4 --- CamMic
        Pi4 ---|"Kết nối mạng dự kiến; P1 chưa tích hợp"| LaptopScreen
        Pi4 --- Headphone
    end

    subgraph Phase2["Giai đoạn 2: Tích hợp Kiosk — Ưu tiên HDMI + USB (Chưa chốt tổng dự toán)"]
        direction LR
        Pi4_Kiosk["Raspberry Pi 4B"]
        ScreenHDMI["NH2067 · 7 inch · 1024×600<br/>Đã thử lên hình và nhận chạm"]
        microHDMI["Cáp micro-HDMI → HDMI<br/>(Kênh hình ảnh)"]
        usbTouch["Một dây USB dữ liệu<br/>(Nguồn màn và dữ liệu chạm)"]
        pwrPi["Adapter 5 V – 3 A<br/>(Nguồn Pi sẵn có)"]
        speaker["Loa ngoài AUX/USB<br/>(Để sau)"]

        Pi4_Kiosk ==>|"Xuất hình"| microHDMI ==> ScreenHDMI
        Pi4_Kiosk --- usbTouch --- ScreenHDMI
        pwrPi ==>|"Cấp điện"| Pi4_Kiosk
        Pi4_Kiosk -.-> speaker
    end

    subgraph Upgrade["Phương án nâng cấp sau: Giao tiếp DSI"]
        direction LR
        DSI_Screen["Màn hình DSI 7 inch<br/>(Touch Display 2 / Waveshare)"]
        DSI_Ribbon["Cáp Ribbon DSI 15-15 pin<br/>(Gọn gàng trong thân vỏ)"]
        DSI_Ribbon --- DSI_Screen
    end

    V1 ==>|"Đạt chuẩn STT phần mềm trên Laptop"| Phase2
    Phase2 -.->|"Chỉ nâng cấp khi HDMI + USB đã ổn định"| Upgrade

    classDef passNode fill:#DDF7E9,stroke:#25865B,color:#0B6B45,stroke-width:2px,font-weight:bold;
    classDef primaryNode fill:#E7F0FF,stroke:#2457B4,color:#1B4494,stroke-width:2px,font-weight:bold;
    classDef optNode fill:#F0E9FF,stroke:#713DB0,color:#4D3375,stroke-width:2px,stroke-dasharray: 5 5;
    classDef warnNode fill:#FFF3C4,stroke:#B58105,color:#6E4900,stroke-width:2px,font-weight:bold;

    class Pi4,CamMic,LaptopScreen,Headphone,pwrPi passNode;
    class Pi4_Kiosk,ScreenHDMI,microHDMI,usbTouch primaryNode;
    class DSI_Screen,DSI_Ribbon optNode;
    class speaker warnNode;
```

---

## 🔌 HDMI + USB: Phương Án Tích Hợp Màn Hình Đầu Tiên

> [!IMPORTANT]
> **Quyết định cốt lõi:** <span style="color:#087A47;font-weight:700;">Sau kiểm thử phần mềm trên laptop, ưu tiên màn cảm ứng HDMI + USB trên Pi 4. DSI chỉ là khả năng nâng cấp sau khi phương án này đã chạy ổn định.</span><br/>
> Đã chốt hướng kết nối cho bước tích hợp đầu tiên; việc dùng laptop trước nhằm đảm bảo tính sẵn sàng của pipeline STT, không có nghĩa bỏ màn cảm ứng của sản phẩm Kiosk cuối.

### Bảng 1. Bộ linh kiện cần xác định cho phương án HDMI + USB *(Dự kiến cho 1 thiết bị)*

| Hạng mục | Số lượng | Công dụng và trạng thái kỹ thuật |
| :--- | :---: | :--- |
| **Màn hình cảm ứng HDMI — Nguyễn Hiền NH2067** | <span style="background-color:#E7F0FF;color:#1B4494;padding:2px 6px;border-radius:3px;font-weight:700;">1 cái</span> | Đã thử lên hình và nhận chạm trên Pi 4 theo báo cáo của người dùng. Cần kiểm tra độ chính xác vị trí chạm khi dùng giao diện. |
| **Cáp micro-HDMI sang HDMI** | <span style="background-color:#E7F0FF;color:#1B4494;padding:2px 6px;border-radius:3px;font-weight:700;">1 sợi</span> | **Truyền hình ảnh.** Đã mua theo phiếu. |
| **Cáp USB dữ liệu từ Pi tới cổng Touch** | <span style="background-color:#E7F0FF;color:#1B4494;padding:2px 6px;border-radius:3px;font-weight:700;">1 sợi</span> | Dây USB-A sang micro-USB nối Pi với một cổng **Touch** trên màn. Dây mang nguồn cấp màn và dữ liệu chạm. Cảm ứng cần dây có đường dữ liệu. |
| **Adapter nguồn Pi 5 V – 3 A** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">1 bộ sẵn có</span> | Đã dùng trong cấu hình Pi và màn. Tổng tải khi bổ sung webcam hoặc thiết bị khác còn cần thử. |

#### 🔄 Luồng kết nối chuẩn:
* **Hiển thị hình ảnh:** `Pi 4` $\rightarrow$ `micro-HDMI sang HDMI` $\rightarrow$ `Màn hình`.
* **Cảm ứng và nguồn màn.** Dùng một dây USB dữ liệu giữa Pi và một cổng Touch đã thử. Để trống cổng Touch còn lại khi thử cấu hình này.
* **Kiểm tra còn lại.** Đo độ phân giải đang dùng, thử chạm đúng vị trí, thử vuốt và đối chiếu bàn phím ảo khi chạy kiosk. [Hướng dẫn NH2067](HUONG_DAN_NH2067_PI4.md)

---

## 🛒 Ứng viên HDMI do người dùng bổ sung — kiểm tra trang ngày 07/11/2026

**Người dùng đã mua NH2067.** Bảng giữ kết quả khảo sát các mẫu để tham khảo. Chi phí thực tế của màn và cáp ghi ở mục dự toán.

| Nguồn / ứng viên | Giá và thông tin trang | Điểm thuận lợi | Còn thiếu để quyết định |
| :--- | :--- | :--- | :--- |
| **[Điện tử Nguyễn Hiền — NH2067](https://www.dientunguyenhien.vn/show/2067)** | **1.090.000 VNĐ**; 7 inch, 1024×600; trang và ảnh người dùng gửi hiển thị tồn 7 khi khảo sát 07/11/2026 | **Đã mua, đã thử lên hình và nhận chạm.** Phiếu bán hàng ghi cùng giá cho màn. | Mã bo và phiên bản mạch thực tế, phụ kiện trong hộp, độ phân giải đầu ra đang dùng và nghiệm thu kiosk. |
| **[Điện tử Tuyết Nga — màn điện dung 7 inch HDMI Raspberry Pi](https://dientutuyetnga.com/products/man-hinh-cam-ung-dien-dung-7-inch-hdmi-raspberry-pi)** | **820.000 VNĐ**; 1024×600; mô tả hỗ trợ Pi 3/4 | Giá niêm yết thấp hơn NH2067 **270.000 VNĐ** | Nhà bán ở TP.HCM; cần phí/ngày giao Đà Nẵng, tồn kho, VAT, bảo hành, mã board, USB touch/nguồn/cáp. Trang tự lưu ý tồn kho có thể chưa cập nhật; mô tả khác nhau về số điểm chạm theo OS, cần thử đúng OS. |
| **[Viện Máy Tính — Waveshare 7inch HDMI LCD (C)](https://vienmaytinh.com/products/man-hinh-waveshare-7-inch-hdmi-capacitive-touch-screen-lcd-c)** | **625.000 VNĐ** giá online, chưa gồm công thay. Trang ghi IPS 7 inch 1024×600, HDMI, USB touch điện dung và nguồn 5 V | [Waveshare](https://www.waveshare.com/7inch-HDMI-LCD-C.htm) ghi mã **11199** cho mẫu này. [Tài liệu hãng về cổng](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29) ghi HDMI chuẩn cho hình và micro-USB dùng chung cho touch và nguồn | Shop ghi micro-USB hoặc USB-C, kèm cáp HDMI, cáp USB và chân đế acrylic. Xác nhận mã/revision và ảnh cổng của hàng thực, cáp/đầu chuyển micro-HDMI cho Pi 4, đủ chân đế, cách cấp nguồn và dòng yêu cầu. Hỏi giá có VAT, phí/ngày giao Đà Nẵng, tồn kho và đổi trả |
| **[Điện tử Á Châu — LCD HDMI 7 inch 1024×600](https://dientuachau.com/lcd-hdmi-7-inch-1024-x-600)** | **630.000 VNĐ**. Trang ghi ngõ HDMI và điện áp hoạt động 5–12 V DC. Ô loại cảm ứng để trống | Có thể khảo sát như mẫu HDMI để đối chiếu hình ảnh | Cần xác nhận có tấm cảm ứng và USB data hay chỉ có LCD. Hỏi mã board, điện áp đúng của bộ hàng, đầu nguồn, phụ kiện, tồn kho, VAT, giao Đà Nẵng và bảo hành |
| **[Shopee — bộ số hóa cảm ứng USB nhiều kích cỡ](https://shopee.vn/product/1382786553/24637236048?extraParams=%7B%22display_model_id%22%3A207890570047%2C%22model_selection_logic%22%3A3%7D)** | Tiêu đề trong link nêu bộ số hóa/điều khiển cảm ứng điện dung USB, nhiều kích cỡ. Chưa đọc được trang để xác nhận biến thể hoặc giá | Có thể khảo sát riêng như linh kiện cảm ứng nếu cần | Hỏi biến thể được chọn có kèm LCD và bo HDMI hay chỉ gồm kính touch và bo USB. Nếu chỉ có touch, xác nhận kích thước kính và khả năng ghép với panel trước khi so giá với màn trọn bộ |
| **[Shop Shopee tuandinh241 — link người dùng gửi](https://shopee.vn/tuandinh241?categoryId=100644&entryPoint=ShopByPDP&itemId=42836315614)** | **Người dùng báo:** đồ cũ, hết HDMI, chỉ còn DSI; chưa có giá/model xác minh | Có thể khảo sát thêm cho phương án DSI về sau | Công cụ không mở được trang; chưa tự xác minh biến thể, giá, tình trạng panel/touch, dây kèm, tương thích, bảo hành và giao hàng. Không xếp vào hàng HDMI còn sẵn. |

**Lượt thử NH2067 trên Pi 4 ngày 07/11/2026.** Màn lên hình và nhận chạm. Người dùng phải đặt ngón lên thanh cuộn mới kéo được và phải chạm hai lần để mở ứng dụng hoặc thư mục đã thử. Chế độ cảm ứng hiện tại và kết quả sau khi đổi chế độ vẫn cần xác minh. [Kết quả thử trong hướng dẫn](HUONG_DAN_NH2067_PI4.md)

**Việc tiếp theo khi có thể thử Pi.** Kiểm tra độ phân giải và độ chính xác vị trí chạm. Bài thử vuốt trong Chromium đang tạm hoãn. Khi thử kiosk, đối chiếu thêm cách gõ tiếng Việt và chạm **Gửi** lúc mở bàn phím ảo.

**Nội dung để người dùng hỏi nhà bán khi muốn chốt:**

1. Mã model, hãng và revision board; ảnh rõ mặt sau/các cổng và tài liệu đúng model.
2. Cảm ứng điện dung hay điện trở? Dữ liệu chạm đi bằng **USB, GPIO/SPI hay I2C**? Nếu USB, cổng nào là data touch, cổng nào chỉ cấp nguồn?
3. Đã chạy Pi 4 và OS/kernel nào? Có cần driver/overlay không? Cho thử chạm, kéo, xoay màn và bàn phím ảo trên OS đang dùng được không?
4. Nguồn bao nhiêu V/A, cấp riêng hay dùng chung đường touch? Bộ kèm dây gì, đầu HDMI phía màn là loại nào? Cần cáp micro-HDMI phía Pi 4.
5. Giá đủ VAT, cáp/nguồn, vỏ/giá đỡ nếu cần, phí và ngày nhận; chính sách bảo hành/đổi khi touch không chạy đúng cấu hình đã thống nhất.

Nhóm cần thử wireframe hội thoại, chữ và bàn phím ảo ở **1024×600** trước khi chốt màn 7 inch; mức giá mới không tự chốt kích thước. Chưa liên hệ nhà bán hoặc đặt hàng từ cập nhật tài liệu này.

## 🔎 Vì sao SPI chưa được ưu tiên làm màn chính?

**SPI (Serial Peripheral Interface)** là bus nối tiếp dùng cho ngoại vi, trong đó có màn hình, qua các chân GPIO trên Pi; xem [tài liệu Raspberry Pi](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio-pin-inputs-outputs-and-communication-protocols). Nó là một phương án có thật; phần so sánh trước chưa giải thích lý do không đưa vào nhánh ưu tiên.

[Hướng dẫn chọn màn của Waveshare](https://www.waveshare.com/rpi_lcd_selection_guide) mô tả nhóm SPI của họ có lợi thế giá, nhưng hạn chế độ phân giải/tần số cập nhật và cần chú ý tương thích hệ thống. Đây là nhận xét về các dòng màn được liệt kê, không phải định luật cho mọi màn SPI.

**Đánh giá cho sản phẩm này:** màn chính cần hội thoại cuộn, chữ dễ đọc, bàn phím ảo và có thể có preview camera; vì vậy ưu tiên đường hiển thị phù hợp giao diện desktop trước. Một màn SPI nhỏ, độ phân giải thấp có thể làm chật bố cục và hạn chế cập nhật hình. Driver/overlay và khả năng xuất giao diện Electron trên đúng OS cũng cần kiểm chứng theo model. Chưa benchmark màn SPI trên Pi của nhóm; không gán một mức FPS chung hoặc khẳng định SPI không chạy được Electron.

**Giao tiếp hình ảnh và giao tiếp cảm ứng là hai thông tin khác nhau.** Ví dụ [Waveshare 3.5 inch RPi LCD (F)](https://www.waveshare.com/wiki/3.5inch_RPi_LCD_%28F%29) dùng SPI cho hình và I2C cho cảm ứng điện dung. Do đó màn SPI không đồng nghĩa luôn cảm ứng điện trở; màn ghi HDMI cũng chưa chứng minh touch qua USB.

**Hướng hiện tại:** giữ HDMI + USB touch là mục tiêu tích hợp đầu tiên; DSI là khả năng sau khi HDMI ổn định. SPI có thể xét cho màn trạng thái phụ/giao diện đơn giản, hoặc khi có model cụ thể chứng minh đáp ứng màn chính; chưa thêm một món phải mua hay thay thứ tự tích hợp.

---

## 📦 Danh Mục Thiết Bị Chi Tiết (BOM Toàn Diện)

| Hạng mục phần cứng | Số lượng / Trạng thái | Chi phí phần cứng bổ sung | Vai trò và điều kiện sử dụng / mua sắm |
| :--- | :---: | :---: | :--- |
| **Raspberry Pi 4B rev 1.5, RAM 8 GB** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">1, ĐÃ CÓ</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | Máy biên xử lý chính; Trixie aarch64 theo thông tin người dùng; cần kiểm tra bản phân phối/kernel/firmware thực tế. Cần phiên truy cập kiểm tra trước khi triển khai sâu. |
| **Thẻ nhớ microSD 32 GB** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">1, ĐÃ CÓ</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | Lưu hệ điều hành (OS), môi trường runtime và cấu hình. Kiểm tra dung lượng trống thực tế trước khi cài đặt. |
| **Bộ nguồn Adapter DC 5 V – 3 A** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">1, ĐÃ CÓ</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | Cấp nguồn riêng cho Pi; nhãn 3A chưa chứng minh không sụt áp dưới mọi tải ngoại vi. Cần kiểm tra nhiệt độ và điện áp khi chạy tải đầy đủ. |
| **Webcam Aioneus USB 1080p (tích hợp mic)** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">1, ĐÃ THỬ THU/PHÁT</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | <span style="color:#087A47;font-weight:700;">Dùng micro hiện có trước.</span> Lệnh ALSA và người dùng đã xác nhận nghe lại được bản thu; đây chưa phải kiểm chứng chất lượng STT ở khoảng cách sử dụng. Không mua micro mới khi chưa có nhu cầu thực tế. |
| **Laptop & mạng nội bộ** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">ĐÃ CÓ SẴN</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | Môi trường lập trình, build code và mở giao diện Web STT của Pi. Deepgram cần Internet; P1 chưa có điều khiển Pi qua LAN. |
| **Tai nghe Jack 3,5 mm** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">1, ĐÃ THỬ PHÁT</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | Dùng phát triển và test âm thanh Text-to-Speech (TTS). Không thay thế loa ngoài khi cần kiểm thử giao tiếp thực tế hoặc đo tiếng vọng. |
| **Màn hình ngoài hiện có** | <span style="background-color:#F0E9FF;color:#4D3375;padding:2px 6px;border-radius:3px;font-weight:700;">ĐÃ CÓ TRONG KHO</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | Chưa rõ chuẩn cổng/cáp. <span style="color:#087789;font-weight:700;">Mốc V1 tận dụng màn hình laptop qua Web</span>; không mua touchscreen làm tắc nghẽn tiến độ. |
| **ESP32 DevKit V1, nút/LED/điện trở/dây/testboard** | <span style="background-color:#F0E9FF;color:#4D3375;padding:2px 6px;border-radius:3px;font-weight:700;">CÓ TRONG KHO NHÓM</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | Nhánh firmware phụ trợ; chưa có xác nhận bài nút/LED/Serial đã chạy. Không bắt buộc cho luồng STT ban đầu. |
| **STM32 / ESP8266 / UNO & dụng cụ kho** | <span style="background-color:#F0E9FF;color:#4D3375;padding:2px 6px;border-radius:3px;font-weight:700;">CÓ THỂ TẬN DỤNG</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | Thiết bị dự phòng trong kho, không mua thêm board mới khi chưa có nhiệm vụ cụ thể. |
| **Quạt tản nhiệt 2 dây** | <span style="background-color:#F0E9FF;color:#4D3375;padding:2px 6px;border-radius:3px;font-weight:700;">ĐÃ CÓ SẴN</span> | <span style="color:#087A47;font-weight:700;">0 VNĐ</span> | Kiểm tra định mức điện áp/dòng và vị trí tản nhiệt trước khi cắm chân GPIO. Không tự suy là quạt điều tốc PWM. |
| **Loa chủ động AUX hoặc USB Audio** | <span style="background-color:#FFF3C4;color:#6E4900;padding:2px 6px;border-radius:3px;font-weight:700;">TẠM HOÃN KHẢO SÁT</span> | <span style="color:#946200;font-weight:700;">Nháp ~150k–250k, chưa xác minh</span> | Dùng cho bài thử nghe ở vị trí người đối diện khi quay lại TTS. Ưu tiên mượn hoặc tận dụng. Nếu cần mua, xác minh cổng kết nối, công suất và nguồn nuôi. |
| **Micro USB thay thế** | <span style="background-color:#FFF3C4;color:#6E4900;padding:2px 6px;border-radius:3px;font-weight:700;">CHỜ KIỂM CHỨNG</span> | <span style="color:#946200;font-weight:700;">Chưa phát sinh</span> | <span style="color:#C52236;font-weight:700;">Chỉ mua nếu mic webcam không đáp ứng</span> bài test nhận dạng giọng nói thực tế (thu gần như sử dụng tại bàn, ghi khoảng cách đo thực tế; ưu tiên giọng Đà Nẵng). |
| **Mạch Mic–Loa tích hợp AEC (chống vọng)** | <span style="background-color:#FFF3C4;color:#6E4900;padding:2px 6px;border-radius:3px;font-weight:700;">ĐÁNH GIÁ SAU</span> | <span style="color:#946200;font-weight:700;">Chưa phát sinh</span> | Đánh giá sau khi thử nghiệm loa ngoài bị lọt tiếng vào mic gây vòng lặp vọng âm. So sánh phương án phần mềm/phần cứng khi có nhu cầu thực tế; chưa chốt giải pháp AEC. |
| **Màn cảm ứng Nguyễn Hiền NH2067** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">1 CÁI · ĐÃ MUA</span> | **1.090.000 VNĐ** theo phiếu | Màn 7 inch, 1024 × 600. Đã lên hình và nhận chạm. Mã bo và phụ kiện kèm còn cần đối chiếu. |
| **Cáp micro-HDMI sang HDMI** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">1 SỢI · ĐÃ MUA</span> | **75.000 VNĐ** theo phiếu | Đã dùng để truyền hình từ Pi 4 tới màn. |
| **Dây USB dữ liệu cho Touch** | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">1 SỢI · ĐÃ DÙNG</span> | <span style="color:#946200;font-weight:700;">Dự trù cũ ~50k–100k cho dây và nguồn, chưa xác minh</span> | Một dây mang cả điện cấp màn và dữ liệu chạm. Chiều dài dây khi lắp vỏ còn để chọn. |
| **Bộ chia cổng USB có nguồn (Powered USB Hub)** | <span style="background-color:#FFF3C4;color:#6E4900;padding:2px 6px;border-radius:3px;font-weight:700;">CHỜ ĐO TẢI THỰC TẾ</span> | <span style="color:#946200;font-weight:700;">Nháp ~150k; chưa xác minh</span> | Chỉ thêm nếu thiếu cổng hoặc nguồn ngoại vi từ Pi không đáp ứng (tránh sụt áp khi cắm đồng thời webcam + mic + touch + loa). |

> [!NOTE]
> **Đợt đầu:** <span style="color:#087A47;font-weight:700;">Chưa xác định món bắt buộc phải mua mới để bắt đầu STT.</span> Có thể làm kiểm thử phần mềm và thu bằng webcam đã có. Thử vọng âm thực tế còn phụ thuộc loa; <span style="color:#C52236;font-weight:700;">không ghi là đã đạt chỉ từ bản thu webcam hoặc tai nghe.</span>

---

## 🖥️ Màn Hình Cảm Ứng Và Chế Độ Kiosk — 06/11/2026

* **Hình thái thiết bị:** <span style="color:#087789;font-weight:700;">Sản phẩm cuối dùng màn hình cảm ứng và chế độ Kiosk.</span> Khi bật thiết bị, Pi tự mở giao diện STT toàn màn hình; người dùng thao tác trực tiếp bằng chạm.
* **Chiến lược tích hợp.** Tiếp tục dùng laptop để phát triển và kiểm thử V1 trước. **Đã chọn NH2067, 7 inch, 1024 × 600 cho tích hợp đầu tiên.** Dùng cấu hình HDMI và một cổng Touch đã thử khi chuyển sang nghiệm thu cảm ứng và kiosk trên Pi.
* **Phần mềm màn hình cảm ứng (Chốt 07/11/2026):**
  * Ứng dụng dùng <span style="color:#713DB0;font-weight:700;">React + TypeScript + Tailwind CSS, Next.js / Node.js và Electron</span>.
  * Trên thiết bị cuối, Pi chạy backend và Electron mở giao diện STT ở kiosk mode. Tiếp tục dùng laptop cho phát triển/kiểm thử ban đầu; **ổn định HDMI + USB touch trước DSI**.
  * Lượt thử màn ban đầu đã nhận chạm trên Pi 4. Kiểm tra bàn phím ảo, thao tác trong ứng dụng và khởi động Electron kiosk với bản Linux ARM64 ở bước tích hợp.

---

## 🔬 DSI Là Phương Án Nâng Cấp Sau HDMI + USB — Khảo Sát 06/11/2026

> [!WARNING]
> **Thứ tự ưu tiên:** <span style="color:#946200;font-weight:700;">Ổn định HDMI + USB cảm ứng trước; chỉ cân nhắc DSI sau đó.</span> Đây là thứ tự tích hợp đã được xác nhận, chưa phải báo cáo HDMI đã chạy ổn định hay quyết định mua màn DSI. Tiếp tục kiểm thử V1 trên laptop trước bước tích hợp màn thiết bị.

**Khảo sát nhà cung cấp DSI ngày 06/11/2026:** giá/tồn kho dưới đây là ảnh chụp trạng thái website của lượt khảo sát cũ, chưa kiểm tra lại lúc mua. Có cơ sở đặt giao Đà Nẵng; chưa xác nhận bán trực tiếp tại Nguyễn Hiền/SPIDER/BKM.

| Ứng viên DSI cho Pi 4 | Giá hiển thị | Trạng thái trên trang và điểm cần kiểm tra |
| :--- | :---: | :--- |
| **[Cytron: Raspberry Pi Touch Display 2, 7 inch](https://www.cytrontech.vn/p-raspberry-pi-7-inch-touch-screen-display-2)** | <strong style="background-color:#E7F0FF;color:#1B4494;padding:2px 6px;border-radius:4px;">2.052.000 VNĐ</strong><br/>*(Đã gồm VAT)* | Trang ghi 5 sản phẩm; nêu hỗ trợ Pi 4, kèm cáp DSI 15–15 chân và dây nguồn. Kiểm tra đúng biến thể 7 inch, phụ kiện và phí giao tại thời điểm đặt. |
| **[Raspberrypi.vn: Waveshare DSI 7 inch (1024×600, MPN 20430, kèm case)](https://raspberrypi.vn/san-pham/man-hinh-cam-ung-dien-dung-7inch-ips-ket-noi-dsi-do-phan-giai-1024x600)** | <strong style="background-color:#E7F0FF;color:#1B4494;padding:2px 6px;border-radius:4px;">1.900.000 VNĐ</strong><br/>*(Chưa VAT & ship)* | Trang ghi còn hàng, hỗ trợ Pi 4; case dành cho Pi 4. Cần xác nhận đủ dây và cấu hình đúng model/OS; đây không phải Touch Display 2. |

*Cytron công bố [giao toàn quốc](https://www.cytrontech.vn/delivery-information), nhưng trang chính sách cập nhật 2023 và thông tin kho chưa nhất quán. Không xem địa chỉ kho là điểm mua trực tiếp tại Đà Nẵng hoặc cam kết ngày giao.*

**Công sức chuyển đổi DSI (đánh giá chưa đo).** Giữ ứng dụng web, backend và luồng STT độc lập với cổng màn. Khi đổi dây, nguồn hoặc vỏ, kiểm tra lại hiển thị, vị trí chạm, bàn phím ảo và kiosk. Dự kiến thấp–vừa với Touch Display 2 7 inch trên Raspberry Pi OS được hỗ trợ. Cần xác minh tương thích với Trixie aarch64 và số dây cho hình ảnh, cảm ứng và nguồn theo từng model. Giữ cấu hình HDMI đã đạt để quay lại.

### 🛠️ Điều kiện nghiệm thu chuyển đổi sang DSI:
1. **Lưu bản cấu hình HDMI đã đạt chuẩn** trước khi chuyển.
2. Thử khởi động nguội vào kiosk thành công.
3. Hình ảnh và chữ dễ đọc. Điểm chạm khớp với vị trí điều khiển trên giao diện.
4. Thao tác Record / Stop và Settings mượt mà bằng chạm; nhập liệu tốt bằng bàn phím ảo.
5. Một phiên hội thoại STT chạy thực tế đạt yêu cầu và bộ nguồn chịu tải tốt.
*Chỉ nhận cấu hình DSI khi toàn bộ các bước trên đạt; luôn giữ đường lùi (fallback) về cấu hình HDMI.*

---

## ⚖️ Ma Trận So Sánh Các Phương Án Phần Cứng & Khuyến Nghị

| Phương án | Lợi ích | Hạn chế / Việc phải thử | Chi phí bổ sung hiện biết | Khuyến nghị hành động |
| :--- | :--- | :--- | :---: | :--- |
| **1. Webcam đang có + Màn hình laptop** | Thu âm đã thử trên Pi; bắt đầu được ngay. | Chưa đo chất lượng giọng miền Trung tại khoảng cách sử dụng thực tế. | <strong style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:4px;">0 đồng mua thêm</strong> | <span style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:3px;font-weight:700;">DÙNG TRƯỚC (V1)</span> |
| **2. Micro USB riêng + Laptop** | Có thể chọn vị trí và hướng thu thuận tiện hơn. | Phải chọn model, thử Linux, chất lượng và ngày nhận; không mặc định tốt hơn webcam. | <span style="color:#946200;font-weight:700;">Chưa chọn model / giá</span> | Chỉ xét nếu phép thu bằng webcam cho thấy vấn đề. |
| **3. Mic–loa tích hợp AEC** | Có thể giảm công việc định tuyến tham chiếu loa khi cần chống vọng. | Cần thử đúng Pi/OS; quảng cáo lọc ồn không chứng minh AEC; chưa có nhu cầu mua đã xác nhận. | <span style="color:#946200;font-weight:700;">Chưa có báo giá kiểm tra</span> | Để sau thử vọng âm. |
| **4. Loa riêng để thử + Micro hiện có** | Kiểm tra tình huống loa phát trong lúc thu âm. | Tùy bố trí có thể thu lẫn tiếng loa; chưa phải giải pháp AEC hoàn chỉnh. | <strong style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:4px;">0 đồng (nếu mượn)</strong><br/>hoặc mức nháp ~150k–200k chưa xác minh | Tận dụng khi đến bài thử playback. |
| **5. NH2067 và bộ cáp/nguồn** | Đã lên hình và nhận chạm trên Pi 4. Dùng cho bước tích hợp kiosk. | Kiểm tra vuốt, bàn phím ảo, khởi động Electron kiosk và tải nguồn khi lắp thêm ngoại vi. | <strong style="background-color:#DDF7E9;color:#0B6B45;padding:2px 6px;border-radius:4px;">1.165.000 VNĐ cho màn và cáp HDMI theo phiếu</strong> | <span style="background-color:#E7F0FF;color:#1B4494;padding:2px 6px;border-radius:3px;font-weight:700;">PHƯƠNG ÁN TÍCH HỢP ĐẦU TIÊN</span> *(DSI xem xét sau)* |

---

## ✅ Các Mục Cần Chốt Ở Phiên Mua Sắm Tiếp Theo

| Quyết định | Trạng thái / cách chốt |
| :--- | :--- |
| Kích thước và model màn cảm ứng HDMI | Đã chọn NH2067, 7 inch, 1024 × 600. Đã lên hình và nhận chạm trên Pi 4. Cần xác minh mã bo và thử khả năng đọc, chạm trong kiosk. |
| Đầu cáp HDMI/USB, chiều dài và phụ kiện kèm | Đã dùng micro-HDMI sang HDMI và USB-A sang micro-USB có dữ liệu. Chiều dài khi lắp vỏ và phụ kiện kèm còn cần đối chiếu. |
| Nguồn màn và tổng tải Pi + ngoại vi | Cấu hình Pi và màn đã chạy với adapter 5 V – 3 A cho Pi và một dây USB cho màn. Tổng tải với các ngoại vi còn cần kiểm tra. |
| Vỏ/giá đỡ và chỗ cho dây, quạt | Giá đỡ là phụ kiện. Kiểu vỏ, cách lắp và chỗ cho dây còn để chọn. |
| Loa và bài thử phát âm thanh | Tai nghe 3,5 mm đã phát được trên Pi. Khảo sát loa ngoài để sau. Bài thử qua loa laptop đang chờ trong [kế hoạch RealVNC](reports/KE_HOACH_THU_AM_THANH_REALVNC.md). |
| Nhà bán và chi phí đã mua | Điện tử Nguyễn Hiền. Phiếu ngày 07/11/2026 lúc 17:25 ghi tổng tiền hàng **1.165.000 VNĐ** cho màn và cáp. |
| DSI, micro thay thế, AEC và powered hub | Giữ là phương án có điều kiện; DSI chỉ xét sau HDMI ổn định. Không tự thêm vào đơn mua bắt buộc. |

**Chi phí đã ghi nhận theo phiếu là 1.165.000 VNĐ cho màn và cáp hình ảnh.** Dự toán toàn bộ kiosk còn phụ thuộc vào phụ kiện, nguồn, giá đỡ và các khoản phát sinh thực tế. Các mức nháp trong bản highlight gốc dùng để tham khảo. Các mẫu còn khảo sát ghi theo giá niêm yết.

## 📌 Ghi Chú Mua Sắm & Logistics

* **Quan điểm ngân sách:** Người dùng muốn xem so sánh trước, chưa chốt số tiền và không bắt buộc chọn cấu hình rẻ nhất. <span style="color:#087789;font-weight:700;">Đánh giá giá trị và thời gian nhận trước khi yêu cầu quyết định mua.</span> Không tự hiểu việc chưa có trần ngân sách là quyền chi tiêu không giới hạn.
* **Địa bàn mua sắm:** Ưu tiên khảo sát mua trực tiếp tại **Đà Nẵng** (*Nguyễn Hiền, SPIDER, BKM*) hoặc **Shopee** khi phát sinh món cần mua thực tế.
* **Nguồn tham chiếu:**
  * File tồn kho & xác nhận thu/phát: `C:\Users\LAPTOP T&T\Downloads\iot-communication-support-system.md`
  * Tài liệu nguồn Raspberry Pi 4 (5V – 3A): https://www.raspberrypi.com/documentation/computers/getting-started.html
  * Tài liệu Touch Display 2: https://www.raspberrypi.com/documentation/accessories/touch-display-2.html
  * Wiki Waveshare: https://www.waveshare.com/wiki/7inch_DSI_LCD_%28C%29
