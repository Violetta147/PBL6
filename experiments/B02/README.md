# B02 — Hai model, cùng cách chấm

Mở `B02_STT.ipynb`, chạy Whisper-base và Zipformer-30M ONNX INT8 trên cùng 100 dev. Các run, `summary.csv` và `comparison.csv` ở `results/`. Scorer giữ dấu tiếng Việt, dùng WER_ws và CER; lỗi inference vẫn nằm trong mẫu số.

Demo: chọn cùng một ID, nghe audio, đối chiếu hai prediction và bảng toàn tập. Phần tự thu đã có 20 câu chính được người thực hiện nghe xác nhận nhãn: 2 phòng ngủ/18 cà phê. `self_dev20_metadata.csv` là metadata thật, `self_dev_template.csv` chỉ là câu gợi ý. Hai baseline chạy đủ 20/20 CPU, WER_ws Whisper 27,6243%, Zipformer 0,5525%; bảng/metadata/kiểm tra ở `results/self_dev20/`, ghi chú tại `notes.txt`. Bộ bốn đối chiếu cũ ở `results/self_dev_pairs4/` giữ riêng. Qwen self dev20 cũng đã hoàn tất; bảng ba model ở B03/results/self_dev20. Test chưa mở.

[DEMO.md](DEMO.md) ghi bảng dev đã đo trên CPU laptop và ba mẫu lỗi để nghe. Đây là so sánh cấu hình đã ghi trong metadata; không suy từ bảng FLEURS rằng Zipformer luôn tốt hơn trên mọi môi trường.
