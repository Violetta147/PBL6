# Khảo Sát Thiết Kế Phần Cứng & Vỏ Kiosk (Trao Đổi Với Khoa Hà)

---

## 1. Liên Kết Tham Khảo & Sưu Tầm Mua Sắm

- **Phụ kiện Shopee:** [Shopee Product 83038628/26071808056](https://shopee.vn/product/83038628/26071808056?gads_t_sig=gqRjZGVrxHCFomtpsTE0MjUxOnRzc19zZGtfa2V5omt20QACpGFsZ2_SAAAAZKNkZWvAomN0xEAAAAAMc1TPTF0zl9lUk9doKYfbtNkYCBZaTm6dQ6q3WJIrnGYlyLtpSCE1-D6jy2YmlKEe_b7zxJZfI6lpwZ6fqmNpcGhlcnRleHTEbAAAAAybyLhF2uWEaRZTCPG9ZHD0agy5akSsMXxLTyqmZNXXxdCqd971_0jq-nMNV1kBIaeoGgTnhNYCDvs1pLXYQbPOqK-osBQYOJVfx7EyCS_X4rHeSmSZeSTMm-YC_pAd48A8njP_YyPEAA&gad_source=1&gad_campaignid=23034094465&gbraid=0AAAAADPpQE6kLRX3o37YiOotGuWgU82B5&gclid=Cj0KCQiAh9vXBhDKARIsAMooYhd0IQAW6cXcpnIRtX_W9kL3qAoNIRXosQZQQCiZpkyYM8tQuIJC7H4aAnlIEALw_wcB)
- **Nền tảng thiết kế phần cứng AI (Blueprint.io):** [https://www.blueprint.io/](https://www.blueprint.io/) *(Hỗ trợ dựng sơ đồ nối dây, danh mục BOM và trực quan hóa mô hình)*
- **Mẫu vỏ màn hình 7 inch Chợ Trời Hà Nội (Mica):** [https://chotroihn.vn/vo-man-hinh-7-inch](https://chotroihn.vn/vo-man-hinh-7-inch?srsltid=AYCX9vLHQADE3g99gVYuXtgUrWqS1aRW0Fldu0vJ-P5sVpbJRANZb1EJ)
- **Mẫu vỏ màn hình 7 inch Waveshare (Bicolor Case):** [https://www.waveshare.com/product/displays/bicolor-case-for-7inch-lcd.htm](https://www.waveshare.com/product/displays/bicolor-case-for-7inch-lcd.htm)
- **Thông số màn hình 7 inch (Điện Tử Nguyễn Hiền):** [https://dientunguyenhien.vn/show/2067](https://dientunguyenhien.vn/show/2067)

---

## 2. Thư Mục Lưu Trữ Hình Ảnh Tham Chiếu (Assets)

Toàn bộ ảnh đã được trích xuất và lưu trữ tại thư mục:  
👉 [assets/hardware_khoa_ha/](file:///C:/Users/LAPTOP%20T&T/VIOLETTA/Documents/ChatGPT/PBL6/assets/hardware_khoa_ha)

### Các hình ảnh tham chiếu chính:
- [Vỏ 3D Waveshare 2 màu có chân đế chỉnh góc](file:///C:/Users/LAPTOP%20T&T/VIOLETTA/Documents/ChatGPT/PBL6/assets/hardware_khoa_ha/case_waveshare_bicolor_3d.jpg) (`case_waveshare_bicolor_3d.jpg`)
- [Vỏ mica đen trắng bắt lưng Raspberry Pi 4](file:///C:/Users/LAPTOP%20T&T/VIOLETTA/Documents/ChatGPT/PBL6/assets/hardware_khoa_ha/case_chotroihn_acrylic_rear.jpg) (`case_chotroihn_acrylic_rear.jpg`)
- 17 ảnh chụp đoạn chat Zalo trao đổi trực tiếp giữa bạn và Khoa Hà (`2aoborco...1.jpg` đến `...17.jpg`).

---

## 3. Tóm Tắt Chi Tiết Đoạn Trao Đổi Với Hà Minh Khoa & Thịnh

### A. Yêu cầu thiết kế vỏ hộp Kiosk
- **Mục tiêu:** Tạo vỏ bảo vệ để đặt máy trên bàn (Kiosk giao tiếp cảm ứng).
- **Linh kiện đặt bên trong vỏ hộp:**
  1. Mặt trước: Màn hình cảm ứng 7 inch (độ phân giải 1024 × 600, link Điện Tử Nguyễn Hiền).
  2. Bên trong ruột hộp: Bo mạch chính **Raspberry Pi 4 Model B**.
  3. Hệ thống âm thanh: **Loa** phát âm thanh (dùng cho phản hồi giọng nói/TTS).
  4. Mạch nguồn, chiết áp và dây cáp nối HDMI / USB Touch.
- **Kích thước ước tính ban đầu:**
  - Chiều ngang: khoảng **20 cm**.
  - Chiều cao: khoảng **14 – 15 cm**.
  - Độ dày: Đủ chứa vừa Raspberry Pi 4 kèm tản nhiệt và củ loa.

### B. Thách thức kỹ thuật thiết kế
- **Khoa phân tích:** Nếu chỉ vẽ một chiếc hộp kín thì rất dễ. Nhưng để **dễ tháo/lắp** khi cần sửa chữa, cắm rút cáp, fix linh kiện bên trong thì cấu trúc ngàm, rãnh trượt hoặc ốc vít bắt nắp phải thiết kế kỹ lưỡng.
- Cần có kích thước chính xác của màn hình, vị trí các cổng cắm (HDMI, Type-C nguồn, USB) để chừa khe hở chuẩn xác.

### C. Thời gian và Chi phí In 3D
- **Thời gian in:** Khoa lưu ý in 3D mất khá nhiều thời gian.
  - Bản in thử nhanh (nét in thô 0.28mm, rỗng ruột để test form dáng): Mất **6 đến 7 tiếng**.
  - Bản in chuẩn hoàn thiện (mịn, độ cứng vững cao): Có thể mất gần **1 ngày**.
- **Chi phí dự tính:**
  - Mẫu in test: Khoảng **150.000 VNĐ** hoặc thấp hơn tùy vào lượng nhựa tiêu hao.

### D. Phương án vỏ thử nghiệm (Cân nhắc lựa chọn)
1. **Phương án 1 (Chính thức):** In 3D (nhựa PLA/PETG) theo file thiết kế riêng của nhóm (Khoa hỗ trợ vẽ và in).
2. **Phương án 2 (Thử nghiệm nhanh / Dự phòng):** Cắt ghép bằng **bìa các-tông (Cardboard prototyping)** để kiểm tra kích thước lắp ráp linh kiện thực tế trước khi bấm in 3D thật (tiết kiệm thời gian và chi phí).
3. **Phương án 3 (Mua vỏ có sẵn):** Sử dụng vỏ Mica 7 inch (Chợ Trời HN) hoặc vỏ Waveshare 7 inch có chân đế.
