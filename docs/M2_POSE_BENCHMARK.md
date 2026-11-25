# Đo độ trễ pose trên M2 qua LAN

Chạy trên nhánh `latency-optimization`. Bài đo lấy dữ liệu từ đường camera thật với một ô chờ pose và mục tiêu thu 25 FPS. Chế độ đo bật trên Pi. Laptop chạy Vision Backend bằng lệnh thông thường và trả các mốc đo khi Pi yêu cầu.

## Chép bản đo sang Pi

Khi Pi đã có checkout M2 tương ứng tại `~/PBL6`, có thể chép các file đã sửa trực tiếp từ Mac. Thay `<IP_PI>` bằng địa chỉ của Pi và đổi user SSH nếu cần. Nếu dùng máy khác làm Vision Backend, cập nhật `classifier.py`, `pose_wire.py` và `vision_backend.py` trên máy đó.

```bash
cd /Users/vohoangminh/PBL6/PBL6_Revamped/deployment/pbl6-vsl-gloss-sentence-flow
PI_SSH='pi@<IP_PI>'
scp slr-m2/deployment/m2/{classifier.py,pipeline.py,pose_metrics.py,pose_wire.py,remote_clients.py,server.py,vision_backend.py,pi_start.sh} \
  "${PI_SSH}:PBL6/slr-m2/deployment/m2/"
```

## Chạy Vision Backend trên laptop

Từ thư mục repo đã có bản cập nhật, dùng môi trường Python của M2. Với Windows PowerShell:

```powershell
cd slr-m2
python -m deployment.m2.vision_backend --host 0.0.0.0 --port 8767 --no-fallback-classifier
```

Nếu laptop là Mac đang dùng lại môi trường M1 trong workspace và đứng tại thư mục repo:

```bash
cd slr-m2
../../m1/.venv-m1/bin/python -m deployment.m2.vision_backend \
  --host 0.0.0.0 --port 8767 --no-fallback-classifier
```

## Chạy SLR Edge trên Pi

Cập nhật cùng bản mã trên cả hai máy. Đường pose mặc định dùng WebSocket nhị phân với đúng một frame đang chờ phản hồi. Đổi sang `--pose-transport http` trên Pi để chạy đối chứng HTTP ở cùng cấu hình JPEG. Đứng tại Pi, thay `<IP_LAPTOP>` bằng địa chỉ LAN của laptop.

```bash
cd ~/PBL6/slr-m2
LAPTOP_IP='<IP_LAPTOP>'
curl -fsS "http://$LAPTOP_IP:8767/api/vision/health"
~/pbl6-venv/bin/python -m deployment.m2.server \
  --host 0.0.0.0 --port 8765 --inference-mode pi-split \
  --vision-backend-url "http://$LAPTOP_IP:8767" \
  --fallback-threshold 0 --pose-transport websocket --measure-pose
```

Để đo có tải Firefox và giao diện thật, nếu bộ UI đã được cài, dùng lệnh khởi động kiosk thay cho lệnh chạy Edge trực tiếp.

```bash
bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh '<IP_LAPTOP>' --pose-transport websocket --measure-pose
```

## Thu một lượt ký

Dùng nút bắt đầu và dừng trên kiosk, hoặc mở terminal thứ hai trên Pi rồi chạy các lệnh dưới đây. Ký cùng một chuỗi trong khoảng 30–60 giây khi so sánh các lần chạy. Thay chỉ số camera nếu cần.

```bash
EDGE=http://127.0.0.1:8765
curl -fsS -X POST "$EDGE/api/session/start" \
  -H 'Content-Type: application/json' -d '{"camera_index":0}'

# Ký trước camera. Khi kết thúc, chạy các lệnh bên dưới.
curl -fsS -X POST "$EDGE/api/session/stop" >/dev/null
curl -fsS "$EDGE/api/metrics/pose" | python3 -m json.tool
curl -fsS "$EDGE/api/metrics/pose?include_frames=1" -o m2-pose-timing.json
```

Tải báo cáo trước khi mở phiên mới. Phiên camera mới tạo bộ đếm mới. Endpoint cũng có thể đọc trong lúc ký. Replay video dùng đường capture khác và không có báo cáo này.

## Đọc báo cáo

| Trường | Ý nghĩa |
| --- | --- |
| `counts` | Frame đọc thành công và nhận vào FIFO (`captured`), frame lấy ra (`dequeued`), request đã bắt đầu gửi và đã ghi nhận kết quả hoặc lỗi (`sent`), phản hồi pose hợp lệ (`pose_replies`), và lỗi xử lý (`pose_errors`). `discarded_at_stop` là frame còn chờ khi bấm Stop. |
| `dropped_before_send` | Số frame chờ bị thay bằng frame mới trước khi gửi. `fifo_peak_pending` là số frame chờ cao nhất. |
| `fifo_ms`, `encode_ms`, `pose_roundtrip_ms`, `frame_age_ms` | Từ đọc frame tới lấy khỏi FIFO, mã hóa JPEG, thời gian gửi JPEG và nhận pose hai chiều, và từ đọc frame tới nhận xong phản hồi HTTP. |
| `laptop_decode_ms`, `laptop_worker_wait_ms`, `laptop_mediapipe_lock_wait_ms`, `laptop_mediapipe_ms` | Giải mã JPEG, chờ luồng xử lý, chờ khóa MediaPipe, và thời gian chạy Pose/Hands. Khi chạy đồng thời, Pose/Hands tính thời gian thực trôi qua. |
| `laptop_handler_ms` | Thời gian trong HTTP handler phía laptop đến lúc chuẩn bị trả kết quả, gồm cả đọc thân request và chạy vision. Các số đo chặng con nằm trong tổng này. |

Percentile tính theo các frame thành công trong tối đa 15.000 mẫu gần nhất. Bộ đếm vẫn tính cả phiên. Với `include_frames=1`, báo cáo JSON chứa mẫu theo `seq`, gồm cả các request lỗi. Các mốc `captured_at`, `send_at`, `response_at` dùng đồng hồ Pi và có đơn vị ms kể từ khi bắt đầu đo. Thời gian backend là các khoảng đo trên đồng hồ laptop. So sánh `pose_roundtrip_ms` giữa hai giá trị `pose_transport`. `websocket_connect_ms` ghi riêng các lần bắt tay. `frame_age_ms` vẫn gồm thời gian kết nối nếu phải mở socket mới. Chênh lệch giữa thời gian hai chiều và thời gian handler gồm cả truyền dữ liệu và chi phí giao thức ngoài handler. Phần camera và driver trước lúc Pi đọc được ảnh nằm ngoài phép đo.
