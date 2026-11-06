# STT V1 — mốc P1: Settings và một file

Ứng dụng nằm trong repository PBL6 hiện tại, dùng React/TypeScript/Tailwind CSS, Next.js/Node.js và Electron. Mốc này xây đường **nhập key tại máy → chọn một file → Deepgram `language=vi` → chữ cuối hoặc lỗi**. Chưa phải V1 hoàn chỉnh: thu micro Pi, batch và triển khai Pi/kiosk thực tế còn ở các bước tiếp theo. V2/V3 chưa triển khai.

Đọc [báo cáo P1 và hướng dẫn thử API thật](../reports/stt_v1_p1_20261107/BAO_CAO.md) trước khi quyết định bước tiếp theo.

## Khởi động trên Windows

Yêu cầu Node.js từ 22.12 trở lên; môi trường phát triển đã có Node 22.22.2. Trong PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6\stt-app'
npm ci
npm run build
npm run desktop
```

Launcher đã sửa lỗi ẩn cửa sổ Electron trên Windows: Electron phải được mở với `windowsHide: false`, còn backend vẫn chạy ẩn. Bản P1 chưa có bộ cài hoặc shortcut desktop.

`desktop` khởi động backend tại `http://127.0.0.1:3100`, chờ backend sẵn sàng rồi mở Electron. Đóng cửa sổ desktop sẽ dừng backend do launcher tạo. Nếu cổng đang có tiến trình khác, launcher từ chối mở để tránh điều khiển nhầm backend. Nếu đã cài dependencies và build xong, chỉ cần `npm run desktop`.

Để dùng trình duyệt thay Electron, chạy `npm start` rồi mở [ứng dụng cục bộ](http://127.0.0.1:3100). Dừng bằng Ctrl+C tại terminal. Không chạy `npm start` và `npm run desktop` đồng thời trên cùng cổng. Phát triển bằng `npm run dev` hoặc `npm run desktop:dev`. `desktop:kiosk` mở cửa sổ kiosk sau khi đã build; đây chưa phải cấu hình tự khởi động hệ điều hành hay chứng nhận kiosk trên Pi.

## Dùng thử một file và API thật

1. Mở **Cài đặt**. Nhập Deepgram API key vào ô mật khẩu; giữ `Nova-3` và `Tiếng Việt · vi`, hoặc chọn `Nova-2` nếu muốn thử riêng cấu hình đó. Nhấn **Lưu cấu hình**. Không gửi key qua chat.
2. Thông báo lưu thành công chỉ chứng minh đã lưu cấu hình, chưa kiểm chứng quyền API. Key đã lưu không được tải ngược về ô nhập. Để trống key khi lưu các mục khác sẽ giữ key cũ; nút **Xóa key đã lưu** mới xóa nó.
3. Mở **Nhận dạng file**, chọn một WAV, MP3 hoặc FLAC không trống, tối đa 20 MiB. Nên bắt đầu bằng bản thu ngắn đã nghe lại và được phép gửi cloud.
4. Nhấn **Nhận dạng file**. Lúc này audio mới được gửi đến Deepgram qua Internet. Ứng dụng chờ kết quả cuối hoặc hiện lỗi; không tự gọi lại để tránh gửi trùng khi kết quả chưa rõ.
5. Khi có kết quả, kiểm tra chữ, rồi dùng **Lưu .txt** hoặc **Sao chép**. File không có transcript được hiển thị rõ; không tạo chữ thay cho phản hồi rỗng. Kết quả trước vẫn được giữ khi yêu cầu sau lỗi, kèm đúng tên file của nó.
6. Gửi lại **mã commit/phiên bản, định dạng file, model, kết quả thành công hay nguyên văn thông báo lỗi và nhận xét về chữ**. Không gửi key hoặc file cấu hình. Thời gian “Yêu cầu Deepgram” gồm đường yêu cầu/đáp ứng client và dịch vụ; không dùng làm RTF nhận dạng local hoặc kết luận chất lượng model.

## Cấu hình và dữ liệu

- Mặc định Windows: `%LOCALAPPDATA%\PBL6-STT\settings.json`; Linux: `${XDG_CONFIG_HOME:-~/.config}/pbl6-stt/settings.json`. `PBL6_STT_CONFIG_DIR` cho phép chọn thư mục riêng, dùng trong kiểm thử.
- Key được lưu **chưa mã hóa** ngoài repository. Trên POSIX, ứng dụng yêu cầu quyền thư mục `0700` và file `0600`; trên Windows phụ thuộc quyền tài khoản/thư mục. Không commit hoặc chia sẻ file này. Chưa triển khai kho bí mật mã hóa.
- Audio tải lên được xử lý trong bộ nhớ, không ghi vào thư mục thí nghiệm. Transcript ở bộ nhớ giao diện cho đến khi tải .txt; tải lại/đóng ứng dụng sẽ mất kết quả chưa xuất. Chưa có lịch sử phiên bền vững.
- `PBL6_STT_PORT` cho phép chọn cổng desktop khác trong khoảng 1024–65535; mặc định 3100. `PBL6_STT_DESKTOP_DATA_DIR` chọn profile Electron riêng khi kiểm thử, độc lập với thư mục Settings.
- Backend chỉ bind loopback và các API chặn Origin khác. Mốc này **chưa mở LAN**, chưa có xác thực để laptop điều khiển Pi qua mạng. Không đổi hostname bind để tự công bố dịch vụ.
- Không gọi `getUserMedia`; camera/micro trình duyệt bị tắt. Không có tự chuyển nguồn thu sang laptop. Bộ kiểm tra file chỉ xác minh phần mở đầu của WAV/MP3/FLAC; Deepgram vẫn có thể từ chối file hỏng bên trong.
- Mỗi backend nhận tối đa một yêu cầu nhận dạng tại một thời điểm. Key/model/timeout được chụp tại đầu yêu cầu, thay đổi Settings chỉ áp dụng cho yêu cầu tiếp theo.

## Kiểm thử

```powershell
npm test
npm run build
npm run typecheck
npm run test:ui
```

Backend tests dùng thư mục tạm và transport mô phỏng, không gọi Deepgram. UI tests cần Google Chrome đã cài, dùng production server riêng cổng 3111 và thư mục cấu hình `.local/ui-test-config`. Có thể đặt `PBL6_STT_TEST_BROWSER=msedge` nếu dùng Edge. Kiểm thử giao diện có các phản hồi mô phỏng; test Electron mở UI thật trên máy chạy test. Các kết quả ấy không chứng minh API thật, nhận dạng tiếng Việt, Linux ARM64, cảm ứng, hoặc micro Pi đã đạt.

## Bước tiếp theo

Sau khi xem báo cáo P1 và thử API thật: hoàn thiện batch, sau đó capture Pi/Record/Stop và các kiểm thử tích hợp còn thiếu. Trước thao tác Pi phải có lệnh, nơi chạy và đầu ra cần gửi lại. Giữ nguyên B01–B04. N02 vẫn chưa hoàn thành; nó không chặn V1 Deepgram, nhưng cần hoàn thành trước so sánh tốc độ hoặc chọn local engine dựa trên tốc độ.

## Tài liệu API đã đối chiếu

- [Deepgram: model và ngôn ngữ](https://developers.deepgram.com/docs/models-languages-overview), [nhận dạng audio đã ghi](https://developers.deepgram.com/reference/speech-to-text/listen-pre-recorded).
- [Next.js Route Handlers](https://nextjs.org/docs/app/api-reference/file-conventions/route), [Tailwind CSS với Next.js](https://tailwindcss.com/docs/installation/framework-guides/nextjs).
- [Electron: BrowserWindow](https://www.electronjs.org/docs/latest/api/browser-window).
