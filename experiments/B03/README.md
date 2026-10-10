# B03 — So sánh ba model

Đã chạy `B03_Qwen_Colab_GPU.ipynb` trên Colab A100-SXM4-40GB: Qwen hoàn tất 100/100 dev, WER_ws 9,7605%, CER 6,2771%. Lần chạy `qwen_gpu_20261010_023946` giữ nguyên trên Drive; bản prediction và metadata được sao lưu vào `results/`. [DEMO.md](DEMO.md) có bảng ba model và năm câu để nghe/đối chiếu. Không cần chạy lại Qwen để xem bảng này.

Mở `B03_STT.ipynb` trên Colab GPU. Notebook chạy B01/B02 nếu chưa có output, thêm Qwen3-ASR-0.6B, rồi lập bảng ba model cùng 100 dev. Backend Qwen là Transformers, không vLLM/aligner. Kết quả từng mẫu và bảng tổng hợp ở `results/`.

Qwen chỉ chạy GPU; runner không cho chạy CPU hoặc tự chuyển sang CPU. Lần CPU trước đã dừng và được giữ trong `attempts/cancelled_cpu/` với 6/100 prediction, không tham gia bảng so sánh.

Ô nghe cuối notebook tự import pandas và Audio/display, nên không cần chạy ô tổng hợp trước để có các import này. Nếu kernel đã khởi động lại, chạy ô đọc Drive với `RUN_NAME` của lần đã lưu để khôi phục ROOT/RUN_DIR; sau đó chạy ô nghe, không cần chạy lại Qwen.

Nghe lại 3–5 lỗi và đọc ba prediction trước khi viết kết luận. Trong bảng đã đo, Whisper/Zipformer chạy CPU laptop và Qwen chạy GPU Colab; không xếp tốc độ như cùng phần cứng. Chưa có 20 WAV tự thu thì bảng môi trường thực tế còn thiếu. Không mở test để chọn model. Zipformer là ứng viên thử Pi trước, Qwen giữ làm đối chiếu; chưa có số đo Pi để chốt cấu hình.
