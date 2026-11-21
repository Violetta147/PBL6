# Kế hoạch deploy STT V1 lên Raspberry Pi 4

Mục tiêu là chạy **Pi 4 và màn cảm ứng NH2067** độc lập. Sau khi khởi động, ứng dụng mở toàn màn hình và cho phép **thu giọng tiếng Việt → dừng → sửa bản chép lời → gửi → mở lại trong Lịch sử**. Backend chạy trên Pi tại `127.0.0.1:3100`. Cần Internet khi gửi bản thu đến Deepgram.

Màn NH2067 đã lên hình và nhận chạm qua HDMI và USB trong lần thử thiết bị. Bản STT `8855f3cc` đã có launcher Electron, thu micro và đóng gói. Cần xác nhận luồng thu, gửi và tự mở kiosk trên Pi thật. Dùng commit này làm mốc thử có thể tái lập. [Bàn giao STT](../STT_SHIFT_HANDOFF.md) · [Hướng dẫn màn hình](../HUONG_DAN_NH2067_PI4.md) · [Cấu hình ứng dụng](package.json)

## 1. Kiểm tra môi trường trên Pi

Kết nối SSH từ máy tính vào Pi bằng tài khoản đang chạy Raspberry Pi OS Desktop trên màn NH2067. Chạy các lệnh chỉ đọc sau. `Session: tty` mô tả phiên lệnh hiện tại qua SSH. Kiểm tra phiên đồ hoạ riêng ở bước 2.

```bash
uname -m
getconf LONG_BIT
grep '^PRETTY_NAME=' /etc/os-release
printf 'Session: %s\n' "${XDG_SESSION_TYPE:-unknown}"
ps -C labwc -o comm=
command -v node
command -v npm
node -p 'process.version + " " + process.arch'
npm --version
git --version
df -h "$HOME"
wpctl status
```

- Mốc dự kiến là `aarch64`, userspace **64 bit**, Node.js **22.12 trở lên** và `process.arch=arm64`. Nếu Node thiếu hoặc sai kiến trúc, dùng bước 1.1. [Tải Node.js](https://nodejs.org/en/download)
- Trong **Control Centre → Screens**, kiểm tra độ phân giải đang dùng là **1024 × 600**, rồi chạm thử bốn góc. Cắm micro USB đang dùng và tìm tên thiết bị trong mục **Sources** của `wpctl status`. Nếu thiếu nguồn thu, kiểm tra danh sách đầu vào trong phần âm thanh của hệ điều hành trước khi thử STT.
- Gửi kết quả môi trường, tên micro và độ phân giải đang hiện. Nếu một lệnh lỗi, gửi nguyên văn lỗi. Bỏ thông tin nhận dạng máy khi chép đầu ra.

### 1.1. Cài Node.js nếu Terminal chưa có

Có thể cài và build từ phiên `tty`. Bản Node.js Linux ARM64 được cài riêng cho STT trong thư mục của tài khoản trên Pi. Khối lệnh kiểm tra SHA-256 trước khi giải nén. [Bảng SHA-256 chính thức của dòng Node 22](https://nodejs.org/download/release/latest-v22.x/SHASUMS256.txt)

```bash
(
  set -e
  cd "$(mktemp -d)"
  source_url=https://nodejs.org/download/release/latest-v22.x
  curl -fsSLO "$source_url/SHASUMS256.txt"
  archive=$(awk '$2 ~ /^node-v22\.[0-9]+\.[0-9]+-linux-arm64\.tar\.xz$/ { print $2 }' SHASUMS256.txt)
  test -n "$archive"
  curl -fsSLO "$source_url/$archive"
  grep -F "  $archive" SHASUMS256.txt | sha256sum -c -
  mkdir -p "$HOME/.local/opt/pbl6-node22"
  tar -xJf "$archive" -C "$HOME/.local/opt/pbl6-node22" --strip-components=1
)
```

Khi dòng kiểm tra hiện `OK`, chạy tiếp trong phiên SSH. Lặp lại dòng `export` trong phiên SSH mới nếu cần gọi `node` hoặc `npm` trực tiếp.

```bash
export PATH="$HOME/.local/opt/pbl6-node22/bin:$PATH"
node -p 'process.version + " " + process.arch'
npm --version
```

Kết quả cần có `v22.… arm64` và phiên bản npm. Nếu `Audio → Sources` từng trống, cắm micro USB hoặc webcam USB có micro vào Pi rồi chạy lại `wpctl status`. Phần build có thể làm trước khi micro sẵn sàng.

## 2. Build và mở ứng dụng dạng cửa sổ

Chạy qua SSH bằng tài khoản sử dụng màn cảm ứng. Dùng thư mục mới `~/pbl6-pi`. Nếu đã có checkout dùng cho lần thử này, vào checkout đó, xem `git status --short` và kiểm tra commit trước khi tiếp tục.

```bash
git clone https://github.com/Violetta147/PBL6.git "$HOME/pbl6-pi"
cd "$HOME/pbl6-pi"
git switch --detach 8855f3cc9847546d3c14785e7615df9a9cbe6d04
git rev-parse --short HEAD
cd stt-app
npm ci
npm run build
npm run typecheck
```

Chạy từng lệnh theo thứ tự và dừng ở lệnh đầu tiên báo lỗi. Nếu `npm ci` đã xong nhưng build báo chỉ nạp được SWC WebAssembly và Turbopack dừng, thử lại với Webpack trong checkout hiện có. Log lần đầu trên Pi cho thấy SWC ARM64 glibc chưa được cài dù lockfile có khai báo. Nguyên nhân gói bị bỏ qua vẫn cần xác minh. [Nền tảng hỗ trợ của Turbopack](https://nextjs.org/docs/app/api-reference/turbopack#supported-platforms)

Nếu build Webpack của commit `8855f3cc` biên dịch xong nhưng báo `TS2344` cho `RouteContext`, áp dụng bản sửa kiểu trong checkout thử. Next.js yêu cầu `params` của route động là `Promise`. Các handler đã chờ kết quả của Promise khi chạy.

```bash
(
  set -e
  cd "$HOME/pbl6-pi/stt-app"
  sed -i 's/^type RouteContext<T> = { params: Promise<T> | T };$/type RouteContext<T> = { params: Promise<T> };/' src/server/handlers.ts
  grep -Fx 'type RouteContext<T> = { params: Promise<T> };' src/server/handlers.ts
)
```

Sau khi thấy dòng `RouteContext` đã sửa, chạy lại build.

```bash
(
  set -e
  export PATH="$HOME/.local/opt/pbl6-node22/bin:$PATH"
  cd "$HOME/pbl6-pi/stt-app"
  npm run build -- --webpack
  npm run typecheck
)
```

Khi build đạt, đọc thông tin phiên đồ hoạ từ cùng kết nối SSH.

```bash
systemctl --user show-environment | grep -E '^(WAYLAND_DISPLAY|DISPLAY|XDG_RUNTIME_DIR)='
find "/run/user/$(id -u)" -maxdepth 1 -type s -name 'wayland-*' -printf '%f\n'
```

Nếu `WAYLAND_DISPLAY` trong môi trường systemd khớp tên socket đang chạy, mở Electron bằng service tạm của tài khoản. Cửa sổ sẽ mở trên Pi. Nếu biến thiếu, socket không khớp hoặc có nhiều phiên đồ hoạ, gửi đầu ra trước khi chọn phiên hiển thị. [Tài liệu systemd-run](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html)

```bash
node_bin="$HOME/.local/opt/pbl6-node22/bin"
systemd-run --user --unit=pbl6-stt-trial --property=Type=exec \
  --working-directory="$HOME/pbl6-pi/stt-app" \
  --setenv="PATH=$node_bin:$PATH" \
  "$node_bin/npm" run desktop
```

Sau khi thấy cửa sổ trên NH2067, kiểm tra backend qua SSH.

```bash
curl -fsS http://127.0.0.1:3100/api/health
```

Kết quả cần có HTTP 200 và trường `"application":"pbl6-stt"`. Nếu báo cổng 3100 đã dùng, dừng đúng phiên STT đang chiếm cổng trước khi thử lại. Xem log bằng `journalctl --user -u pbl6-stt-trial -n 60 --no-pager`. Dừng bản thử bằng `systemctl --user stop pbl6-stt-trial`. [Launcher](scripts/desktop.mjs) · [Endpoint kiểm tra](app/api/health/route.ts)

**Kết quả trên Pi:** Build Webpack và typecheck đã chạy qua sau khi sửa kiểu route. Service `pbl6-stt-trial` đã mở cửa sổ Electron trên NH2067. Lần gọi đầu diễn ra trước khi backend lắng nghe, lần thử lại trả JSON đúng ứng dụng. Trường `piCapture:false` đang được viết cố định trong endpoint và không đo trạng thái micro. Mốc tiếp theo là xác nhận nguồn thu thật trong PipeWire.

## 3. Nghiệm thu V1 trên màn cảm ứng

**Đã xác minh đường nhận dạng file trên Pi.** Backend chạy qua SSH nhận một file WAV thu sẵn từ laptop và trả `completed` với Deepgram Nova-3, ngôn ngữ `vi`. Audio dài 3,86 giây và yêu cầu Deepgram mất khoảng 2,33 giây theo trường `requestMs`. Lượt này xác minh đường truyền file và dịch vụ nhận dạng. Lượt thu bằng nút micro, gửi tin và mở lại trong Lịch sử còn cần thử trên màn cảm ứng.

**Ảnh từ NH2067:** bản chạy dạng cửa sổ hiển thị được tin đã lưu, hội thoại trong Lịch sử và bàn phím hệ thống. Mép dưới cửa sổ bị khuất, còn bàn phím che vùng soạn khi mở. Ảnh chưa xác nhận nguồn nhập của tin. Bản vá thử giới hạn kích thước cửa sổ theo vùng màn hình và dùng trạng thái `Visible` của Squeekboard qua D-Bus để dành chỗ bên dưới bố cục. Với màn 600 px, bản thử dành 252 px khi bàn phím phủ lên cửa sổ. Cần xác nhận phần chừa trên thiết bị thật.

Trong lần kiểm tra, PipeWire chỉ thấy đầu ra tai nghe 3,5 mm và chưa thấy nguồn thu. Khi có micro USB hoặc webcam USB có micro, kiểm tra mục `Audio → Sources` bằng `wpctl status`. Nếu service thử file `pbl6-stt-file-test` đang chạy, dừng bằng `systemctl --user stop pbl6-stt-file-test` để trả cổng 3100 trước khi mở lại Electron theo bước 2.

| Lượt thử | Thao tác và kết quả cần thấy |
| --- | --- |
| Thu và gửi | Mở **Cài đặt**, lưu key Deepgram tại Pi, rồi chọn micro. Nói một câu tiếng Việt khoảng 10 giây. Nhấn nút vuông để dừng. Chữ vào ô soạn để sửa bằng bàn phím tiếng Việt. Nhấn **Gửi**, mở **Lịch sử** và tìm lại đúng tin. |
| Gửi khi đang thu | Nhấn **Gửi** trong khi thu một câu mới. Ứng dụng dừng thu, chờ bản chép lời và gửi đúng một lần khi có kết quả. |
| Lỗi và thử lại | Giữ một dòng chữ trong ô soạn rồi kiểm tra trường hợp mất mạng hoặc ngắt micro. Ghi lại phản hồi thực tế. Cần giữ được bản nháp và huỷ yêu cầu gửi đang chờ khi nhận dạng thất bại. Sau khi khôi phục kết nối, thu lại thành công. |
| Mở lại | Đóng và mở lại ứng dụng. Kiểm tra lựa chọn micro, lịch sử và khả năng gửi tiếp trong hội thoại cũ. |

Ghi commit, tên micro, câu nói dự kiến, chữ trả về và trạng thái gửi cho từng lượt. Ghi số giây từ lúc dừng đến lúc có chữ nếu cần so sánh sau này. Nhập API key trực tiếp trên Pi. Khi gửi bằng chứng, chỉ gửi đầu ra đã bỏ key và dữ liệu riêng tư. [Luồng V1 đã duyệt](../STT_PRODUCT_UI_UX.md)

## 4. Mở kiosk và thử sau khi khởi động lại

Sau khi các lượt trên đạt, dừng service thử qua SSH. Chạy lại lệnh mở Electron ở bước 2 và đổi `run desktop` thành `run desktop:kiosk`.

Khi kiểm tra riêng lỗi bố cục, mở thẳng bản thử bằng `desktop:kiosk` và kiểm tra thanh tác vụ biến mất, ô soạn, mic và **Gửi** đều nằm trong khung. Mở bàn phím hệ thống và thử sửa một câu. Nếu bàn phím vẫn che vùng nhập, giữ nó mở rồi chạy `busctl --user get-property sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0 Visible` qua SSH. Ghi kết quả và ảnh chụp. Kiosk tự mở sau khi đăng nhập là mốc tiếp theo sau khi bản mở thủ công đạt.

Thử lại một lượt thu, sửa, gửi bằng cảm ứng ở 1024 × 600. Dừng bản thử từ SSH khi cần thoát toàn màn hình. Sau khi kiosk mở qua SSH ổn định, mới cấu hình tự mở trong phiên Desktop. Nếu phiên xác nhận đang chạy **labwc**, thêm launcher vào cấu hình autostart của đúng tài khoản chạy kiosk. Sao lưu cấu hình hiện có, giữ các mục hệ thống và dùng đường dẫn Node/npm đã xác minh trong bước 1. Chốt lệnh autostart sau khi đã có đầu ra từ Pi, vì môi trường đăng nhập có thể khác phiên SSH. [Hướng dẫn kiosk của Raspberry Pi](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/) · [Cơ chế autostart của labwc](https://labwc.github.io/labwc-config.5.html)

Chỉ ghi **đạt deploy** sau khi reboot lên đúng ứng dụng, backend trả kết quả kiểm tra, và màn cảm ứng thu, sửa, gửi rồi mở lại được tin vừa gửi. Nếu tự mở lỗi, khôi phục cấu hình autostart đã sao lưu và mở thủ công từ SSH. Khi nâng bản, giữ một checkout đã chạy ổn và sao lưu thư mục cấu hình cùng dữ liệu hội thoại ngoài repo trước khi thử bản mới. [Đường dẫn cấu hình](src/server/settings.ts) · [Đường dẫn lưu hội thoại](src/server/storage.ts)

Đóng gói thành thư mục chạy Linux ARM64 là bước tiếp theo nếu cần bàn giao bản cài. Repo có lệnh `npm run pack`. Cần chạy và thử gói trên Pi trước khi dùng cho autostart. [Kiến trúc Linux ARM64 trong electron-builder](https://www.electron.build/v26/docs/architecture/)
