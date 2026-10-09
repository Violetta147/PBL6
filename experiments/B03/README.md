# B03 — So sánh ba model

Mở `B03_STT.ipynb` trên Colab GPU. Notebook chạy B01/B02 nếu chưa có output, thêm Qwen3-ASR-0.6B, rồi lập bảng ba model cùng 100 dev. Backend Qwen là Transformers, không vLLM/aligner. Kết quả từng mẫu và bảng tổng hợp ở `results/`.

Nghe lại 3–5 lỗi và đọc ba prediction trước khi viết kết luận. Zipformer CPU và Whisper/Qwen GPU phục vụ so chất lượng; không xếp tốc độ như cùng phần cứng. Chưa có 20 WAV tự thu thì bảng môi trường thực tế còn thiếu. Không mở test để chọn model, không tuyên bố model mới mặc định thắng.
