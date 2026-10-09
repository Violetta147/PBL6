# B02 — Hai model, cùng cách chấm

Mở `B02_STT.ipynb`, chạy Whisper-base và Zipformer-30M ONNX INT8 trên cùng 100 dev. Các run, `summary.csv` và `comparison.csv` ở `results/`. Scorer giữ dấu tiếng Việt, dùng WER_ws và CER; lỗi inference vẫn nằm trong mẫu số.

Demo: chọn cùng một ID, nghe audio, đối chiếu hai prediction và bảng toàn tập. Phần tự thu cần tiếng nói thật theo `THU_AM.md`; mẫu metadata là hướng dẫn thu, chưa phải dữ liệu đã đo.
