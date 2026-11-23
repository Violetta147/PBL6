# Pi: màn hình xoay dọc nhưng cảm ứng sai hướng

Ghi nhận và kiểm tra ngày **23/11/2026**, trên Pi `192.168.1.8`, tài khoản `pi`.

File hướng dẫn được tạo trong checkout **`codex/gloss-sentence-flow`** của phiên làm việc này. Chưa commit, không sửa nhánh `perf/streaming-onnx`.

## Triệu chứng và cách đã khắc phục

Theo người dùng: màn hình HDMI 7 inch đã xoay dọc nhưng cảm ứng USB chưa khớp hướng; kéo trái có thể thành kéo phải. HDMI và cảm ứng USB là hai thiết bị riêng.

Các bước người dùng đã thực hiện thành công:

1. Mở **Screen Configuration** trên Pi.
2. Chuột phải **HDMI-A-1 → Touchscreen**.
3. Chọn **wch.cn USB2IIC_CTP_CONTROL** đang được Pi nhận diện.
4. Bấm **Apply**.
5. Trong hộp đếm ngược, bấm **OK trực tiếp trên màn hình 7 inch**. Theo lần gặp này, chuột VNC bị đơ trong khoảng đếm ngược 10 giây, nên không dùng VNC để xác nhận.
6. Nếu màn hình bị freeze sau khi xác nhận nhưng SSH vẫn vào được, lưu/dừng công việc cần thiết rồi reboot Pi qua SSH.
7. Sau khi Pi khởi động lại, kiểm tra chạm/kéo theo cả hai trục. Người dùng xác nhận cảm ứng đã bình thường và cấu hình còn được giữ.

Chỉ reboot khi cần thoát trạng thái freeze hoặc nạp lại phiên desktop. Trong lần kiểm tra này, file cấu hình đã được ghi lúc 11:24:20, trước lần boot 11:32:09; vì vậy không nên hiểu reboot là thao tác duy nhất làm cấu hình được lưu.

### Reboot khi thực sự bị freeze

Chạy từ PowerShell trên laptop, sau khi đã lưu công việc:

```powershell
ssh -t pi@192.168.1.8 'sudo reboot'
```

Lệnh này **khởi động lại Pi**, không phải lệnh kiểm tra. Trong lượt audit, agent không chạy lệnh reboot hoặc Apply.

## Điểm tìm thấy thêm: tên thiết bị thay đổi theo USB

Đối chiếu cấu hình hiện tại với các file `.bak` cho thấy trước lần Apply vừa rồi **đã có map vào HDMI-A-1**, nhưng tên thiết bị đầy đủ khác nhau:

| Mục | Trước, trong bản sao `.bak` | Hiện tại |
|---|---|---|
| `deviceName` | `wch.cn USB2IIC_CTP_CONTROL (USB 1-1.3)` | `wch.cn USB2IIC_CTP_CONTROL (USB 1-1.2)` |
| `mapToOutput` | `HDMI-A-1` | `HDMI-A-1` |
| `mouseEmulation` | `no` | `no` |

**Suy luận từ cấu hình:** map cũ có thể không còn khớp thiết bị sau khi tên/đường USB thay đổi. Chưa có log trước lỗi để chứng minh chính xác sự kiện nào làm tên USB đổi.

Nếu tái phát, đặc biệt sau khi thay cổng USB hoặc hub, chọn lại đúng thiết bị đang xuất hiện trong Screen Configuration; đừng mặc định chuỗi `(USB 1-1.2)` luôn đúng trên mọi lần cắm.

## Những file OS được ghi trong lần Apply

Đọc qua SSH và so sánh bản sao tại chỗ:

| File trên Pi | Kết quả kiểm tra |
|---|---|
| `/home/pi/.config/labwc/rc.xml` | Sửa 11:24:20; dòng touch đổi USB `1-1.3` → `1-1.2` |
| `/home/pi/.config/labwc/rcgreeter.xml` | Sửa 11:24:20; dòng touch tương ứng cũng đổi USB `1-1.3` → `1-1.2` |
| `/home/pi/.config/kanshi/config` | Ghi lúc 11:24:20; nội dung hiện tại giống `config.bak` |
| `/home/pi/.config/labwc/rc.bak` | Bản sao ngay trước `rc.xml` mới; ghi cùng thời điểm |
| `/home/pi/.config/labwc/rcgreeter.bak` | Bản sao ngay trước `rcgreeter.xml` mới; ghi cùng thời điểm |
| `/home/pi/.config/kanshi/config.bak` | Bản sao cấu hình output; ghi cùng thời điểm |

Đây là các file đã xác minh trong hai thư mục cấu hình, không phải khẳng định đã theo dõi mọi lần ghi file trên toàn bộ OS. Cấu hình `~/.config/labwc/environment` vẫn có thời gian sửa 06/10/2026.

### Cấu hình touch hiện tại, để đối chiếu

```xml
<?xml version="1.0"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <touch deviceName="wch.cn USB2IIC_CTP_CONTROL (USB 1-1.2)" mapToOutput="HDMI-A-1" mouseEmulation="no"/>
</openbox_config>
```

Đây là trích cấu hình đã đọc, **không phải lệnh ghi đè toàn bộ rc.xml**. Máy khác có thể có thêm phím tắt hoặc cấu hình riêng cần giữ.

### Cấu hình màn hình hiện tại

`~/.config/kanshi/config`:

```text
profile {
                output HDMI-A-1 enable scale 1.000000 mode 1024x768@60.004 position 0,0 transform 270
}
```

`wlr-randr` xác nhận HDMI-A-1 bật, mode hiện tại **1024×768**, transform **270**, scale **1**. Mode ưu tiên mà output báo là **1024×600**. Sau khi xoay, vùng logic của mode hiện tại tương ứng 768×1024, không phải 600×1024.

Agent chỉ ghi nhận, **không đổi độ phân giải hoặc góc xoay**. Nếu sau này kiểm thử UI 600×1024, cần đối chiếu lại mode thật trước khi kết luận bố cục có lỗi.

## Kiểm tra an toàn qua SSH

Các lệnh `cat`, `stat`, `wlr-randr` không kèm tùy chọn thay output chỉ đọc cấu hình/trạng thái. Không cần `ssh -t` cho thao tác chỉ đọc này.

Mở một phiên SSH từ PowerShell trên laptop:

```powershell
ssh pi@192.168.1.8
```

Sau khi đã vào shell của Pi, chạy:

```bash
stat ~/.config/labwc/rc.xml ~/.config/labwc/rcgreeter.xml ~/.config/kanshi/config
cat ~/.config/labwc/rc.xml
cat ~/.config/kanshi/config
WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000 wlr-randr
```

Khi đọc, dùng `~/.config/...` thay vì `\~/.config/...`: dấu gạch chéo ngược có thể làm shell coi `~` là ký tự thường, không mở rộng thành thư mục home. Không cắt `wlr-randr` còn 20 dòng nếu cần xem `Transform`/`Scale`, vì hai dòng này có thể nằm phía dưới.

Trong audit đã chạy các lệnh đọc tương đương với lệnh người dùng nêu, đồng thời đọc hết output để thấy transform và mode hiện tại.

## Kết quả kiểm tra mã nguồn và nhánh Git

### Laptop

- Nhánh checkout: `codex/gloss-sentence-flow`.
- Sau `git fetch origin`, nhánh local `perf/streaming-onnx` và `origin/perf/streaming-onnx` đều ở **`cd6d091730e0394b819610df6506c8f4dfbd4325`**, ahead/behind **0/0**.
- Reflog perf vẫn ghi lần cập nhật cuối là pull fast-forward ngày 22/11/2026 lúc 18:30:38 +07:00. Không có commit/merge mới trên perf trong quá trình sửa cảm ứng.
- Checkout hiện có thay đổi chưa commit từ công việc thiết kế và thử tạo câu trước đó, gồm Pencil/tài liệu, `pipeline.py`, `server.py`, các file `stt-app`, cùng các thay đổi có sẵn như VNC trong `pi_start.sh` và thí nghiệm segmentation. Không coi chúng là thay đổi do Screen Configuration tạo ra.
- File chưa commit không thuộc riêng một commit của nhánh nào; chuyển nhánh trong cùng checkout có thể mang theo chúng. Agent không chuyển nhánh trong audit.

### Pi

- `/home/pi/PBL6` là thư mục triển khai **không có `.git`**, nên không thể dùng `git status` tại đó để xác nhận một branch Pi.
- Đã so SHA-256 sáu file đang triển khai với bản stage giữ từ 22/11 tại `/home/pi/PBL6/.deploy-20261122-cd6d0917/runtime/`: **cả 6 khớp**.
- Các file: `classifier.py`, `pipeline.py`, `remote_clients.py`, `server.py`, `vision_backend.py`, `pi_start.sh`. Thời gian sửa của chúng vẫn 22/11/2026 khoảng 19:04.
- Năm file Python trên cũng khớp nội dung commit perf `cd6d0917`. `pi_start.sh` khớp bản stage đã giữ chỉnh sửa VNC có sẵn, không khớp nguyên xi commit perf vì chỉnh sửa VNC đó chưa commit từ trước.
- Đây là bằng chứng cho sáu file runtime đã kiểm tra; không phải so hash toàn bộ ứng dụng Next/Electron hoặc toàn bộ filesystem Pi.

**Kết luận audit:** xác minh được thay đổi cấu hình OS phục vụ ánh xạ cảm ứng; không thấy thay đổi mới của nhánh perf hoặc sáu file runtime SLR trên Pi do lần thao tác này. Không có mốc snapshot đầy đủ trước sự cố để khẳng định mọi file trên máy đều không đổi.

## Kiểm chứng file hướng dẫn

- Nội dung dựa trên đầu ra SSH, Git và báo cáo thao tác trực tiếp của người dùng; agent chưa trực tiếp chạm lại màn hình 7 inch.
- Chạy `git diff --check` và kiểm tra file đang nằm trong checkout `codex/gloss-sentence-flow`.
- Không chứa mật khẩu SSH, token hoặc API key. Chưa commit/push, chưa thay cấu hình màn hình/cảm ứng trong lượt audit.
