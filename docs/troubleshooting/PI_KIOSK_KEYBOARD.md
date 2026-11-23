# Pi: Lỗi bàn phím ảo & kẹt tab đăng nhập Firefox Kiosk

Ghi nhận ngày **23/11/2026** trên nhánh **`codex/gloss-sentence-flow`** (chưa commit/merge).

---

## 1. Bấm nút bàn phím ảo nhưng bàn phím không hiện (`--fullscreen-kiosk`)

### Triệu chứng & Nguyên nhân
- Khi chạm nút mở bàn phím ảo hoặc chạm ô nhập trên màn hình 7 inch, `POST /api/osk` vẫn gọi thành công D-Bus `sm.puri.OSK0.SetVisible(true)`, nhưng trên màn hình không thấy `squeekboard`.
- **Nguyên nhân:** `activate.sh` / `rollback.sh` truyền `--fullscreen-kiosk` cho `pi_start.sh` (tức chạy `firefox --kiosk`). Trên Wayland compositor **`labwc`** (`labwc` issue #2926), cửa sổ fullscreen được xếp lớp đè lên trên `squeekboard`, đồng thời gây bất tiện cho cửa sổ phụ khi đăng nhập OAuth.

### Cách khắc phục
- Luôn chạy `pi_start.sh` với **`--windowed`** (tức `--new-window`, là mặc định của `pi_start.sh`), kết hợp `userChrome.css` ẩn `#TabsToolbar, #nav-bar, #PersonalToolbar` + `xulstore.json` (`sizemode: maximized`) để giữ giao diện sạch toàn màn hình mà không bị `labwc` đè lên `squeekboard`.
- Đã chuyển `--fullscreen-kiosk` → `--windowed` trong `slr-app/MVP/outputs/deploy_20261123_ui/activate.sh` và `rollback.sh`, đồng thời thêm cảnh báo vào `slr-m2/deployment/m2/pi_start.sh`.

### Hiệu chỉnh khoảng trống màn dọc (`stt-app/app/page.tsx`)
- Khi mở `squeekboard` ở bố cục dọc (`768×1024`), nếu `labwc` đã co chiều cao cửa sổ Firefox (`~988px` → `~680px`), logic cũ chỉ kiểm tra `vh <= 420` (vốn viết cho màn ngang `1024×600`) nên vẫn trừ thêm `210px` qua `maxHeight`.
- Đã cập nhật `computeOskCeiling` trong `stt-app/app/page.tsx` để so với chiều cao gốc trước khi mở bàn phím (`baseVh - vh >= 120`): nhận diện việc compositor đã thu nhỏ viewport ở cả màn ngang lẫn màn dọc.

---

## 2. Đóng tab đăng nhập ChatGPT OAuth làm tắt luôn app PBL6

### Triệu chứng & Nguyên nhân
- Bấm **Cài đặt → Ký hiệu → ChatGPT → Kết nối** hoặc link **Quản lý hạn mức** mở trang OpenAI bằng `window.open(...)` không có cờ popup → Firefox mở thành **tab thứ 2 trong cùng cửa sổ** với PBL6.
- Do `userChrome.css` đã ẩn `#TabsToolbar` (thanh tab) và `#nav-bar`, khi đăng nhập xong người dùng không thấy tab PBL6 để chuyển lại; bấm nút đóng `X` trên góc cửa sổ sẽ **đóng cả Firefox (cùng app PBL6 đang mở)**.
- *(Lưu ý: token kết nối được lưu ở backend `pbl6-ui.service` tại `~/.config/pbl6-stt/chatgpt-connections.json`, nên đóng Firefox không làm mất kết nối đã lưu — chỉ cần mở lại trình duyệt tới `http://127.0.0.1:3100/`.)*

### Cách khắc phục đã triển khai trong code (chờ đẩy lên Pi)
1. **`stt-app/src/components/SentenceServiceSettings.tsx`:** Mở link đăng nhập và link usage với cờ `popup=yes,width=640,height=760` để tách thành cửa sổ popup riêng (giữ nguyên cửa sổ app PBL6 phía sau), đồng thời tự đóng popup khi `readStatus` báo đã kết nối xong hoặc khi bấm hủy.
2. **`stt-app/src/server/chatgptConnection.ts`:** Callback `http://127.0.0.1:<port>/auth/callback` trả về trang HTML có nút lớn **"Quay lại ứng dụng PBL6"** và tự gọi `window.close()` khi hoàn tất (fallback điều hướng về `http://127.0.0.1:3100/` nếu bị mở trong tab đơn).
3. **`slr-m2/deployment/m2/pi_start.sh`:** Thêm cấu hình profile Firefox (`browser.link.open_newwindow = 3`, `browser.link.open_newwindow.restriction = 2`, `dom.allow_scripts_to_close_windows = true`) để cho phép popup độc lập và cho phép callback tự đóng cửa sổ popup.

---

## 3. Lệnh kiểm tra nhanh trên Pi qua SSH

```bash
# 1. Xác nhận Firefox chạy --new-window (KHÔNG có --kiosk) và squeekboard đang chạy
pgrep -af 'firefox|squeekboard'

# 2. Mở/tắt và kiểm tra trạng thái Squeekboard trực tiếp qua API & D-Bus
export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus WAYLAND_DISPLAY=wayland-0
curl -fsS -X POST http://127.0.0.1:3100/api/osk -H 'Origin: http://127.0.0.1:3100' -H 'Host: 127.0.0.1:3100' -H 'Content-Type: application/json' -d '{"visible":true}'
busctl --user get-property sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0 Visible
grim ~/keyboard-check-open.png
curl -fsS -X POST http://127.0.0.1:3100/api/osk -H 'Origin: http://127.0.0.1:3100' -H 'Host: 127.0.0.1:3100' -H 'Content-Type: application/json' -d '{"visible":false}'
```

*(Ghi chú kiểm chứng ngày 23/11 lúc 13:12–13:13: đã triển khai gói `deploy_20261123_ui` build ID `hvpA651UTl_VT3EnzgcAf` lên Pi `192.168.1.8` ở chế độ `--windowed`. Sau khi ngắt SSH: `pbl6-ui.service` `active`, `:3100` và `:8765` đều OK với `ws_clients=1`, `display-before.sha256` cả 3 file cấu hình màn hình/cảm ứng khớp nguyên vẹn, tài khoản ChatGPT đã kết nối vẫn được giữ trên Pi, và ảnh chụp `grim` (`keyboard-windowed-closed.png`, `keyboard-windowed-open.png`) xác nhận `squeekboard` mở/tắt sạch trên màn dọc không đè giao diện và không còn khoảng trống `210px`. Trên Windows trước đó đã qua `npm run typecheck`, `27/27` unit tests, `npm run build`, `npm run curate:server`.)*
