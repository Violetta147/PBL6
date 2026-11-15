# [CHƯA CHỐT - BẢN NHÁP LƯU TRỮ] HƯỚNG DẪN TRIỂN KHAI RASPBERRY PI 4 & QUẢN TRỊ TELEMETRY

> [!WARNING]
> **Trạng thái tài liệu: CHƯA CHỐT (Bản nháp ghi chú tạm thời để quay lại làm sau).**
>
> Toàn bộ nội dung về Telemetry (tắt cloud telemetry, script đo nhiệt độ/sụt áp cục bộ) và cấu hình triển khai Raspberry Pi 4 (HDMI 1024×600, âm thanh, autostart kiosk) dưới đây chỉ là **ghi chú tham khảo sơ bộ**, chưa được Quân phê duyệt hay chốt thiết kế.
>
> Khi quay lại giai đoạn Pi 4 & Telemetry, cần rà soát và chốt lại từng quyết định trước khi triển khai thực tế.

Tài liệu này tổng hợp ghi chú tham khảo về cấu hình hệ thống và các bước dự kiến triển khai ứng dụng Kiosk (STT App & tích hợp SLR sau này) lên thiết bị nhúng **Raspberry Pi 4 Model B**, kèm theo ghi chú về **Telemetry** (Đo lường & Giám sát hệ thống).

---

## MỤC LỤC
1. [Quản trị Telemetry: Nguyên lý & Cấu hình](#1-quản-trị-telemetry-nguyên-lý--cấu-hình)
   - 1.1. Vô hiệu hóa Next.js / 3rd-party Telemetry
   - 1.2. Thiết lập Giám sát Đo đạc Phần cứng Cục bộ (Local Hardware Telemetry)
2. [Khảo sát Phần cứng & Màn hình 7 Inch (1024x600)](#2-khảo-sát-phần-cứng--màn-hình-7-inch-1024x600)
3. [Chuẩn bị Hệ điều hành Raspberry Pi OS (64-bit)](#3-chuẩn-bị-hệ-điều-hành-raspberry-pi-os-64-bit)
4. [Cấu hình Màn hình Cảm ứng & Âm thanh](#4-cấu-hình-màn-hình-cảm-ứng--âm-thanh)
   - 4.1. Hiển thị HDMI 1024x600 & USB Touchscreen
   - 4.2. Cấu hình Microphone & Loa (ALSA / PipeWire)
5. [Cài đặt Môi trường Runtime & Ứng dụng](#5-cài-đặt-môi-trường-runtime--ứng-dụng)
6. [Thiết lập Tự động Chạy Kiosk Toàn Màn hình (Autostart / Systemd)](#6-thiết-lập-tự-động-chạy-kiosk-toàn-màn-hình-autostart--systemd)
7. [Bảng Kiểm Tra Sự Cố (Troubleshooting Checklist)](#7-bảng-kiểm-tra-sự-cố-troubleshooting-checklist)

---

## 1. Quản trị Telemetry: Nguyên lý & Cấu hình

### 1.1. Vô hiệu hóa Next.js / 3rd-party Telemetry

Trong các thiết bị chuyên dụng (Kiosk / Embedded Device) như trạm giao tiếp hỗ trợ người điếc, việc đảm bảo **tính độc lập mạng**, **bảo mật dữ liệu riêng tư** và **tiết kiệm băng thông/CPU** là ưu tiên hàng đầu.

#### Tại sao phải tắt telemetry mặc định?
- **Ngăn chặn rò rỉ siêu dữ liệu (Metadata Leaks):** Next.js mặc định gửi các sự kiện thu thập ẩn danh (anonymous usage events) về Vercel. Thiết bị hỗ trợ người khuyết tật có thể hoạt động trong mạng nội bộ bệnh viện, trường học hoặc môi trường không có kết nối Internet liên tục.
- **Tránh timeout hoặc nghẽn tài nguyên:** Khi không có mạng, các luồng telemetry cố gắng kết nối ngầm có thể gây nghẽn DNS hoặc lãng phí chu kỳ xử lý của CPU ARM.

#### Cấu hình trong hệ thống:
1. **Biến môi trường hệ thống:**
   Đảm bảo biến môi trường sau luôn có hiệu lực:
   ```bash
   export NEXT_TELEMETRY_DISABLED=1
   ```
2. **Khai báo trong Standalone Server / Systemd:**
   Trong file dịch vụ systemd (mục 6), ta đặt:
   ```ini
   Environment="NEXT_TELEMETRY_DISABLED=1"
   Environment="NODE_ENV=production"
   ```

---

### 1.2. Thiết lập Giám sát Đo đạc Phần cứng Cục bộ (Local Hardware Telemetry)

Thay vì gửi dữ liệu ra đám mây, thiết bị kiosk cần **Telemetry cục bộ** để bảo vệ phần cứng (chống quá nhiệt, sụt áp) và đảm bảo trải nghiệm người dùng luôn mượt mà.

#### Các chỉ số quan trọng cần đo đạc:
1. **Nhiệt độ SoC Broadcom BCM2711:**
   - Lệnh đọc: `vcgencmd measure_temp`
   - Ngưỡng an toàn: `< 70°C`. Nếu vượt `80°C`, CPU sẽ tự hạ xung (thermal throttling), làm giảm tốc độ nhận diện STT/SLR.
2. **Trạng thái Throttling & Sụt điện áp (Undervoltage):**
   - Lệnh đọc: `vcgencmd get_throttled`
   - Giải mã bit quan trọng:
     - `0x50000`: Đã từng bị throttling vì nhiệt độ.
     - `0x50005`: Đang hoặc đã từng bị sụt nguồn (undervoltage). Cần đổi nguồn 5V/3A chuẩn Type-C.
3. **Mức sử dụng RAM & Bộ nhớ Swap:**
   - Lệnh: `free -m` (Đặc biệt quan trọng khi chạy đồng thời luồng Whisper STT cục bộ và MediaPipe/PyTorch SLR).

#### Kịch bản Mini-Telemetry Script (`pi-telemetry.sh`):
```bash
#!/bin/bash
# Đo đạc thông số Pi định kỳ và ghi log cục bộ
TEMP=$(vcgencmd measure_temp | egrep -o '[0-9]*\.[0-9]*')
THROTTLED=$(vcgencmd get_throttled)
MEM_AVAIL=$(free -m | awk '/^Mem:/{print $7}')
DATE=$(date "+%Y-%m-%d %H:%M:%S")

echo "[$DATE] Temp: ${TEMP}°C | Throttled: $THROTTLED | FreeRAM: ${MEM_AVAIL}MB" >> /var/log/kiosk-hardware.log
```

---

## 2. Khảo sát Phần cứng & Màn hình 7 Inch (1024x600)

Hệ thống thiết bị sử dụng:
1. **Board mạch chủ:** Raspberry Pi 4 Model B (Khuyến nghị 4GB hoặc 8GB RAM).
2. **Màn hình hiển thị:** Waveshare 7 inch Capacitive Touch LCD (hoặc tương đương từ Chợ Trời HN).
   - Độ phân giải gốc: **1024 x 600 pixels**.
   - Cổng giao tiếp hiển thị: **HDMI**.
   - Cổng giao tiếp cảm ứng: **Micro-USB Touch** (nhận dạng như thiết bị HID chuẩn chuột/cảm ứng đa điểm, không cần driver riêng trên Linux kernel hiện đại).
3. **Vỏ bảo vệ & Giá đỡ:** Vỏ mica đen trắng hoặc bìa các-tông mẫu kiểm thử ban đầu, nghiêng góc ~45° hoặc 60° phục vụ góc nhìn đứng/ngồi tại quầy giao dịch.
4. **Phụ kiện ngoại vi:**
   - Micro thu âm USB Gooseneck hoặc Omnidirectional USB Mic có lọc ồn phần cứng.
   - Nguồn điện: Bộ chuyển đổi USB-C chuẩn 5V - 3A / 3.5A ổn định.

---

## 3. Chuẩn bị Hệ điều hành Raspberry Pi OS (64-bit)

- Tải **Raspberry Pi Imager** từ trang chủ.
- Chọn OS: **Raspberry Pi OS (64-bit)** (dựa trên Debian 12 Bookworm, có Desktop). Phiên bản 64-bit là bắt buộc để hỗ trợ các thư viện AI, Electron hiện đại và tối ưu hiệu năng nhân ARM Cortex-A72.
- Trong cài đặt nâng cao của Pi Imager:
  - Bật SSH.
  - Thiết lập user/password (vd: `pi` / `pbl6kiosk`).
  - Cấu hình Wi-Fi kết nối nội bộ.

---

## 4. Cấu hình Màn hình Cảm ứng & Âm thanh

### 4.1. Hiển thị HDMI 1024x600 & USB Touchscreen

Màn hình 1024x600 đôi khi bị Raspberry Pi nhận nhầm thành 720p hoặc 1080p nội suy dẫn đến chữ bị mờ. Ta ép độ phân giải chuẩn trong cấu hình khởi động:

1. Chỉnh sửa file cấu hình boot:
   ```bash
   sudo nano /boot/firmware/config.txt
   # (Trên một số bản OS cũ là /boot/config.txt)
   ```
2. Thêm hoặc cập nhật các dòng sau:
   ```ini
   # Ép độ phân giải HDMI 1024x600 60Hz (DMT mode 87)
   hdmi_force_hotplug=1
   hdmi_group=2
   hdmi_mode=87
   hdmi_cvt 1024 600 60 6 0 0 0
   hdmi_drive=1
   ```
3. Lưu lại (`Ctrl+O`, `Enter`, `Ctrl+X`) và khởi động lại (`sudo reboot`).

### 4.2. Cấu hình Microphone & Loa (ALSA / PipeWire)

1. **Kiểm tra thiết bị thu âm:**
   ```bash
   arecord -l
   ```
   Ghi lại số Card và Device (ví dụ: `card 1: Device [USB PnP Audio Device], device 0`).
2. **Kiểm tra mức âm lượng Micro:**
   ```bash
   alsamixer
   ```
   Nhấn `F6` chọn card USB Mic, tăng âm lượng mic lên mức 85-90% (tránh đẩy lên 100% gây vỡ âm méo tiếng khi chuyển thành văn bản).
3. **Cấp quyền truy cập microphone cho người dùng thông thường:**
   ```bash
   sudo usermod -aG audio,video pi
   ```

---

## 5. Cài đặt Môi trường Runtime & Ứng dụng

1. **Cài đặt Node.js 20 LTS:**
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
   sudo apt-get install -y nodejs git
   ```
2. **Cài đặt các gói phụ trợ cho Electron & Kiosk:**
   ```bash
   sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxcomposite1 \
     libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 unclutter
   ```
3. **Chuyển giao mã nguồn ứng dụng:**
   - Đặt thư mục ứng dụng tại `/home/pi/stt-touchscreen-app`.
   - Chạy build hoặc giải nén gói standalone.

---

## 6. Thiết lập Tự động Chạy Kiosk Toàn Màn hình (Autostart / Systemd)

Có hai phương án cấu hình: chạy dịch vụ nền qua Systemd và tự động mở giao diện Electron khi màn hình đăng nhập.

### Phương án: Chạy qua Desktop Autostart (Khuyên dùng cho Electron GUI)

1. Tạo thư mục autostart:
   ```bash
   mkdir -p ~/.config/autostart
   nano ~/.config/autostart/kiosk.desktop
   ```
2. Nhập nội dung:
   ```ini
   [Desktop Entry]
   Type=Application
   Name=STT Kiosk
   Exec=/home/pi/stt-touchscreen-app/start-kiosk.sh
   Hidden=false
   X-GNOME-Autostart-enabled=true
   ```

3. Tạo script điều khiển `/home/pi/stt-touchscreen-app/start-kiosk.sh`:
   ```bash
   #!/bin/bash
   # 1. Ẩn con trỏ chuột khi không chạm màn hình
   unclutter -idle 0.5 -root &

   # 2. Tắt chế độ ngủ màn hình (Screensaver / DPMS)
   xset s noblank
   xset s off
   xset -dpms

   # 3. Đặt biến môi trường cấm telemetry
   export NEXT_TELEMETRY_DISABLED=1
   export NODE_ENV=production

   # 4. Khởi chạy ứng dụng với cờ kiosk
   cd /home/pi/stt-touchscreen-app
   npm run start -- --kiosk
   ```
4. Cấp quyền thực thi:
   ```bash
   chmod +x /home/pi/stt-touchscreen-app/start-kiosk.sh
   ```

---

## 7. Bảng Kiểm Tra Sự Cố (Troubleshooting Checklist)

| Hiện tượng | Nguyên nhân phổ biến | Cách khắc phục |
| :--- | :--- | :--- |
| **Màn hình hiển thị viền đen hoặc chữ bị vỡ hạt** | Pi chưa nạp đúng timing 1024x600 của LCD | Kiểm tra lại `hdmi_cvt 1024 600 60 6 0 0 0` trong `/boot/firmware/config.txt`. |
| **Chạm cảm ứng bị ngược trục X/Y** | Cảm ứng chưa được map đúng hướng xoay màn hình | Cài đặt `xinput-calibrator` hoặc thêm file cấu hình `99-calibration.conf` trong `/etc/X11/xorg.conf.d/`. |
| **STT không thu được âm thanh** | Quyền Chromium/Electron microphone bị chặn hoặc sai Default Device | Kiểm tra cờ quyền trong Electron `permissionRequestHandler`, test bằng `arecord -d 5 test.wav`. |
| **App chạy chậm hoặc bị giật sau 15 phút** | SoC Pi 4 bị quá nhiệt (>80°C) dẫn đến thermal throttling | Bổ sung quạt tản nhiệt mini 5V/30mm vào vỏ case Waveshare và theo dõi bằng `vcgencmd measure_temp`. |
| **Biểu tượng tia sét vàng ở góc trên** | Nguồn cấp không đủ công suất (<5V 3A) | Thay cáp sạc và củ sạc chuẩn 5V 3A chuyên dụng cho Raspberry Pi 4. |
