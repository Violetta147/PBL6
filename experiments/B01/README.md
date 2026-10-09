# B01 — Chạy baseline

Mở `B01_STT.ipynb`: upload gói dữ liệu, cài runtime, chạy 10 câu pilot bằng Whisper-base đa ngôn ngữ, phát một audio và đối chiếu nhãn/prediction. Lưu `results/whisper_pilot.jsonl` và `results/whisper_pilot.run.json`.

Demo 3–5 phút: audio → bản chép lời → một lỗi cụ thể → WER tính tay. Pi đã biết: Pi 4B 8GB, Pi OS 13 Trixie aarch64. Micro và màn hình chưa xác nhận. Notebook chưa chạy không được tính là hoàn tất baseline.

[DEMO.md](DEMO.md) đã có ví dụ từ output thật của lần chạy CLI local; kiểm tra audio bằng tai vẫn cần người thực hiện. JSONL và run metadata ở `results/` là bằng chứng inference, không phụ thuộc việc notebook Colab đã chạy hay chưa.
