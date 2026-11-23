# Thử tạo câu trên app — 23/11/2026

**Trạng thái:** mục tiêu có thời hạn cũ đã được người dùng xóa, không khôi phục. Người dùng sau đó yêu cầu ưu tiên chạy được tạo câu và ngày 23/11 đã cho phép triển khai lên Pi. Đã triển khai source code OAuth ChatGPT và adapter Responses theo tài liệu OpenAI; đã kích hoạt bản build trên Pi thành công. Chưa đăng nhập hoặc xác nhận kết quả với LLM thật. Chưa commit/merge.

- Mục tiêu: nhận chuỗi gloss thật trên app, chỉnh/xóa từ chưa rõ, tạo câu bằng LLM thật, kiểm tra/sửa câu và gửi vào hội thoại. Không thay mô hình hoặc ngưỡng nhận dạng.
- Nhánh: `codex/gloss-sentence-flow`, từ `cd6d0917`. Giữ nguyên mọi thay đổi có sẵn. Chưa merge main, chưa commit.
- Đầu vào: SLR WebSocket hiện có, gloss đã chọn/bỏ, cấu hình LLM phía server. Không gửi video hoặc landmark cho LLM.
- Đầu ra: câu gợi ý tách khỏi gloss nguồn; người dùng xác nhận trước khi lưu; phản hồi cũ không được ghi đè chuỗi mới; lỗi giữ bản nháp.
- File được phép sửa: `stt-app/app/page.tsx`, API route tạo câu/kết nối ChatGPT, `src/server/signSentence.ts`, `src/server/chatgptConnection.ts`, contracts/storage/handlers liên quan, component thẻ ký, lib trạng thái câu, nhãn nút, kiểm thử liên quan. Không sửa frozen bundle, checkpoint hoặc ngưỡng. Không triển khai demo chính thức hoặc commit nếu chưa được duyệt riêng.
- Kiểm chứng: `npm run typecheck`, `npm run build`, kiểm thử endpoint/model/storage, UI bằng Playwright ở 1024×600; cuối cùng thử app với nhà cung cấp thật và nguồn gloss thật. Mock chỉ kiểm chứng luồng, không chứng minh đạt mục tiêu thực tế.
- Bước cần người dùng: đăng nhập và cấp quyền ChatGPT trên trình duyệt Pi rồi chọn model. Thiết kế đã đủ để thực thi; không yêu cầu API key đối với ChatGPT subscription. API key là lựa chọn độc lập nếu dùng nhánh API.

## Kết quả chạy

Đã qua typecheck/build; cảnh báo truy vết cấu hình động đã xử lý. Bộ test logic trạng thái và tạo câu 15/15 qua bằng dịch vụ HTTP mô phỏng; kiểm tra hồi quy Python trước đó 12/12 qua. 7 kiểm thử UI liên quan header, camera/trạng thái, nút Đọc và responsive qua. Chưa kiểm thử toàn bộ UI mới, model thật hoặc loa/camera thật trên Pi. Không đánh dấu đạt chỉ vì build hoặc test mock qua.


## Triển khai được duyệt ngày 23/11

- Đã thêm mã OAuth độc lập từ tài liệu OpenAI: callback loopback trên Pi; PKCE/state/nonce, xác minh chữ ký ID token với JWKS và iss/aud/exp/sub, kiểm tra quyền dùng gói ChatGPT; token server-side, lưu nguyên tử với quyền 0600 trên Linux; làm mới token có tuần tự hóa. Không đọc/sao chép token LearnHarness hoặc Codex.
- Danh mục model lấy từ tài khoản; gọi Responses API store=false/stream=true và chỉ nhận thành công khi có response.completed. Câu chưa hoàn tất/lỗi/hết hạn mức không được đưa thành kết quả. Chuyển/ngắt tài khoản hủy yêu cầu đang chạy; đổi provider/model trên UI vô hiệu hóa câu gợi ý cũ, giữ gloss nguồn.
- Màn nhà cung cấp rút về API KEY + Thêm nhà cung cấp, SUBSCRIPTION ChatGPT + tài khoản/Quản lý, model của kết nối. Ngang menu trái 190px, dọc tab trên như thiết kế đã duyệt. Chỉ quản lý kết nối trên trình duyệt local của Pi; chưa thực hiện hệ thống đăng nhập/tài khoản PBL6 và phân quyền hoàn chỉnh.
- Kiểm chứng: build và TypeScript qua; 18 bài kiểm thử Node qua (gồm OAuth/Responses và HTTP provider mô phỏng); 9 bài Playwright qua (có chỉnh gloss, tạo/sửa câu và gửi); 16 bài Python pipeline/server/camera qua. Một bài camera smart-gating bị lỗi timing trong lần chạy đồng thời với build, sau đó chạy riêng và chạy lại bộ 16 bài đều qua; không sửa ngưỡng hoặc test đó để che lỗi.
- Artifact: outputs/deploy_20261123_ui/ gồm ui.tar, manifest.sha256, runtime/pipeline.py + server.py, activate.sh, rollback.sh. Build ID oxuZGM-_1c6507kxKpiqg. Pi stage /home/pi/PBL6/.deploy-20261123-gloss-sentence có backup UI/config/data/runtime trước chuyển đổi. Không đẩy checkpoint hoặc ghi đè cấu hình STT từ laptop.
- Laptop Vision Backend chạy tại 192.168.1.14:8767, không nạp fallback classifier; đã kiểm tra Pi gọi health được. Pi giữ pi-split, threshold fallback=0, utterance-rest=4.0.
- Quyết định triển khai không được hiểu là duyệt commit/merge. Nhánh vẫn codex/gloss-sentence-flow.


### Kết quả kích hoạt trên Pi

- activate.sh trả DEPLOY_OK, build ID oxuZGM-_1c6507kxKpiqg. UI :3100 và SLR :8765 đều health OK; Firefox kiosk đã mở.
- Kiểm tra SHA-256 ba file labwc/rc.xml, labwc/rcgreeter.xml, kanshi/config sau khởi động: đều OK, không thay cấu hình cảm ứng.
- M2 dùng ONNX, pi-split, fallback threshold 0, thời gian nghỉ 4.0; Vision laptop 192.168.1.14:8767 reachable.
- ChatGPT API trạng thái trả accounts=[], pending=false: chưa đăng nhập tài khoản thật. Cần người dùng Continue with ChatGPT trên Pi và chọn model rồi mới thử LLM thật. Không ghi API key hoặc token vào báo cáo.
- Bản cũ và cấu hình/dữ liệu nằm trong /home/pi/PBL6/.deploy-20261123-gloss-sentence/previous-*. Hoàn tác bằng bash /home/pi/PBL6/.deploy-20261123-gloss-sentence/rollback.sh. Rollback chưa được chạy vì bản mới health OK.


### Lỗi phát hiện khi chụp màn hình sau triển khai

Health ban đầu OK nhưng lần kiểm tra sau thấy cổng UI 3100 đã đóng, Firefox hiển thị Unable to connect; SLR vẫn chạy. Không có log OOM/segfault, Pi còn khoảng 6.5 GiB khả dụng. Chưa xác nhận được nguyên nhân kết thúc tiến trình Node từ log nên không kết luận lỗi do thiếu RAM hoặc source OAuth.

Đã sửa đúng phần khởi chạy UI trong slr-m2/deployment/m2/pi_start.sh: dùng transient user service pbl6-ui.service, Type=exec, Restart=on-failure, chạy tách khỏi SSH; stop_services dừng unit trước khi dọn cổng. Giữ nhánh nohup khi máy không có user systemd. Giữ nguyên các chỉnh sửa VNC đã có, chế độ nhận dạng và ngưỡng. Bản launcher trước sửa được lưu trong stage/previous-runtime/pi_start.sh; launcher mới trong stage/runtime/pi_start.sh. Rollback UI dừng unit trước, khôi phục UI/pipeline/server; giữ launcher giám sát mới để tránh tái xuất hiện lỗi khởi chạy.

Đã chạy bash -n trên launcher mới ngay tại Pi, khởi động lại thành công. Cần kiểm tra tiếp sau khi ngắt SSH và xem screenshot mới; không chỉ dựa health đầu tiên.


Kiểm tra sau sửa launcher và ngắt SSH: 12:32:03 (Asia/Saigon), UI health vẫn OK, pbl6-ui.service ActiveState=active, MainPID=8694, NRestarts=0. Manifest toàn bộ gói/runtime/launcher/scripts đều khớp; bash -n activate.sh/rollback.sh qua. Kiểm tra origin lạ bị 403, thao tác local không hợp lệ trả 409 (đã vào đúng handler), không khởi tạo OAuth hoặc gọi model. STT settings và dữ liệu hội thoại đối chiếu backup đều không đổi. Screenshot thực tế: outputs/deploy_20261123_ui/pi-screen-current.png. Chưa đăng nhập ChatGPT thật; vẫn chờ thao tác đăng nhập/chọn model của người dùng.

### Cập nhật sửa lỗi Kiosk OSK & Popup đăng nhập OAuth — 23/11 (sau 12:40)

- **Sửa launcher `--fullscreen-kiosk` → `--windowed`:** Đã bỏ `--fullscreen-kiosk` khỏi `outputs/deploy_20261123_ui/activate.sh` và `rollback.sh`, thêm chú thích cảnh báo `labwc #2926` vào `slr-m2/deployment/m2/pi_start.sh`.
- **Sửa kẹt tab OAuth Firefox & chiều cao bàn phím màn dọc:**
  - `stt-app/src/components/SentenceServiceSettings.tsx`: mở đăng nhập ChatGPT và link hạn mức bằng cửa sổ `popup=yes,width=640,height=760` để không đè cùng cửa sổ đã ẩn thanh tab của PBL6; tự đóng popup khi hết `pending` hoặc bấm hủy.
  - `stt-app/src/server/chatgptConnection.ts`: callback trả HTML tiếng Việt có nút **"Quay lại ứng dụng PBL6"** và tự gọi `window.close()` khi kết nối thành công (fallback điều hướng về `http://127.0.0.1:3100/`).
  - `slr-m2/deployment/m2/pi_start.sh`: thêm `browser.link.open_newwindow=3`, `browser.link.open_newwindow.restriction=2`, `dom.allow_scripts_to_close_windows=true` trong `user.js`.
  - `stt-app/app/page.tsx`: cập nhật `computeOskCeiling` so với `baseViewportHeightRef` (`baseVh - vh >= 120`) để không trừ trùng `210px` trên màn dọc khi `labwc` tự co viewport.
- **Kiểm chứng cục bộ (Windows):** `npm run typecheck` OK; `node --import tsx --test tests/chatgpt-connection.test.ts tests/sign-sentence.test.ts tests/routes.test.ts tests/slr-integration.test.ts` **27/27 PASS**; `npm run build` & `npm run curate:server` OK (build ID mới **`hvpA651UTl_VT3EnzgcAf`**); đã đóng gói lại `outputs/deploy_20261123_ui/ui.tar`, `build-id.txt`, `runtime/pi_start.sh`, `manifest.sha256` và ghi `docs/troubleshooting/PI_KIOSK_KEYBOARD.md`.
- **Trạng thái Pi (xác minh thực tế 23/11 13:12–13:13):** Đã nạp key SSH lên Pi `192.168.1.8` và triển khai thành công build `hvpA651UTl_VT3EnzgcAf` kèm `pi_start.sh` `--windowed`. Kiểm chứng trực tiếp sau khi ngắt SSH: `pbl6-ui.service` `active`, `BUILD_ID=hvpA651UTl_VT3EnzgcAf`, `:8765` `ws_clients=1`, `display-before.sha256` cả 3 file cảm ứng/xoay khớp 100%, `/api/osk` bật/tắt `squeekboard` qua D-Bus (`Visible: b true` → `b false`) với 2 ảnh `grim` thực tế ([keyboard-windowed-closed.png](../outputs/deploy_20261123_ui/keyboard-windowed-closed.png), [keyboard-windowed-open.png](../outputs/deploy_20261123_ui/keyboard-windowed-open.png)) hiển thị bàn phím sạch khớp khít không khoảng trống dưới composer, và tài khoản ChatGPT đã kết nối trước đó vẫn được giữ nguyên (`account_count=1`, `model=""` — người dùng chỉ cần vào **Cài đặt → Ký hiệu** chọn model và thử ký thật tạo câu). Chưa thử bấm luồng popup OAuth lại và chưa thử tạo câu LLM thật end-to-end trên Pi.
- **Cập nhật UX & ổn định kết nối Vision (23/11 13:41):** Triển khai build `ucY6PlkNulAS7oY_WPW4f` + `pipeline.py` (3 frame lỗi liên tiếp mới báo + tự xóa lỗi qua `error_cleared`/`status`) + `remote_clients.py` (`timeout=4.0s`) sau khi qua 35/35 test Python + 27/27 test Node. Đưa vùng hội thoại lên trên ở cả bố cục dọc để thẻ `ĐANG KÝ TRỰC TIẾP` áp sát composer; hiển thị ngay model đã lưu (`gpt-6-astra`) khi mở Settings và thêm nhãn `✓ Tự động lưu` ở tab Ký hiệu; ảnh `grim` live ([pi-screen-layout-v2.png](../outputs/deploy_20261123_ui/pi-screen-layout-v2.png)) xác nhận camera `15.3 FPS` / `pose 9.5 FPS` sạch lỗi đỏ và đúng bố cục.
- **Sửa tụt `0.5 FPS` & chốt bàn giao (23/11 14:12):** Đặt `MAX_PENDING_POSE_FRAMES = 1` và gỡ `wait_for` chặn `cap.read()` trong `slr-m2/deployment/m2/pipeline.py` (giữ nguyên `640px`/`q=75` ở `remote_clients.py`); 35/35 test Python OK (`test_m2_split.py` đã cập nhật); đo live trên Pi đạt **`capture_fps: 15.3`**, **`pose_fps: 10.3`**, `last_error: null`. Toàn bộ tổng hợp bàn giao cho người làm tiếp nằm ở `docs/HANDOFF_GLOSS_SENTENCE_20261123.md`.
