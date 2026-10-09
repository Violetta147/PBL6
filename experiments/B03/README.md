# B03 — So sánh ba model

Lựa chọn chạy tiếp: `B03_Qwen_Colab_GPU.ipynb` trên Drive đọc lại hai baseline đã đo, chỉ chạy Qwen GPU và lưu kết quả trực tiếp vào Drive. Chọn GPU trước khi chạy; khi cần tiếp tục lần ngắt, điền `RUN_NAME` cũ. Notebook chưa chạy nên chưa có điểm Qwen.

Mở `B03_STT.ipynb` trên Colab GPU. Notebook chạy B01/B02 nếu chưa có output, thêm Qwen3-ASR-0.6B, rồi lập bảng ba model cùng 100 dev. Backend Qwen là Transformers, không vLLM/aligner. Kết quả từng mẫu và bảng tổng hợp ở `results/`.

Qwen chỉ chạy GPU; runner không cho chạy CPU hoặc tự chuyển sang CPU. Lần CPU trước đã dừng và được giữ trong `attempts/cancelled_cpu/` với 6/100 prediction, không tham gia bảng so sánh.

Nghe lại 3–5 lỗi và đọc ba prediction trước khi viết kết luận. Zipformer CPU và Whisper/Qwen GPU phục vụ so chất lượng; không xếp tốc độ như cùng phần cứng. Chưa có 20 WAV tự thu thì bảng môi trường thực tế còn thiếu. Không mở test để chọn model, không tuyên bố model mới mặc định thắng.
