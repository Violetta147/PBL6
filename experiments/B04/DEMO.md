# Demo B04 — WAV → chữ trên Pi

Mở SSH vào Pi và vào `/home/pi/PBL6_STT_B04_20261013`. Kết nối mạng dùng để điều khiển SSH; Zipformer nhận dạng cục bộ bằng model đã có, không gửi audio tới dịch vụ ASR.

Chạy một WAV đã chốt bằng lệnh sau. Tên output có thời gian để giữ các lần demo riêng; không cần chạy lại cả 20 câu hoặc biên dịch runtime.

```bash
cd /home/pi/PBL6_STT_B04_20261013
DEMO_RUN="experiments/B04/results/demo_$(date +%Y%m%d_%H%M%S).jsonl"
.venv/bin/python experiments/run_asr.py --model zipformer --manifest experiments/B04/smoke.csv --output "$DEMO_RUN" --device cpu --threads 2
.venv/bin/python -c 'import json,sys; r=json.loads(open(sys.argv[1]).readline()); print("Reference:",r["reference"]); print("Prediction:",r["prediction"]); print("Inference (s):",r["elapsed_s"])' "$DEMO_RUN"
```

Trong khoảng ba phút: nói mục tiêu là chọn ASR có sẵn cho Pi; chạy câu trên và đọc reference/prediction; mở bảng kết quả hai lượt 20 câu tại `results/zipformer_summary.csv`. Giải thích RTF inference khoảng 0,12 là khoảng 10,3 giây xử lý cho 84,2 giây audio, còn nạp model khoảng 3,74 giây được đo riêng. RAM cực đại khoảng 199 MiB. Chỉ sai một đơn vị “gốc/góc” trong dev20.

Đây là demo nhận dạng WAV trên Pi. Chưa có kết quả micro, chia đoạn lời nói hoặc hiển thị kính; các phần đó thuộc B05. Không gọi thời gian inference một WAV là độ trễ phụ đề từ lúc người dùng nói. Kết quả 20 câu một người đọc chỉ giúp chọn ứng viên, không chứng minh chất lượng chung đã đạt.

Đọc phần đối chiếu Whisper và giới hạn phạm vi đo trong README trước khi so tốc độ. Không cần chạy Whisper trong buổi trình bày nếu đã có output lưu. Người thực hiện vẫn cần tự tập và trình bày với thầy; tài liệu demo không phải bằng chứng đã demo.
