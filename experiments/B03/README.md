# B03 — So sánh ba model

Đã chạy `B03_Qwen_Colab_GPU.ipynb` trên Colab A100-SXM4-40GB: Qwen hoàn tất 100/100 dev, WER_ws 9,7605%, CER 6,2771%. Lần chạy `qwen_gpu_20261010_023946` giữ nguyên trên Drive; bản prediction và metadata được sao lưu vào `results/`. [DEMO.md](DEMO.md) có bảng ba model và năm câu để nghe/đối chiếu. Không cần chạy lại Qwen để xem bảng này.

Mở `B03_STT.ipynb` trên Colab GPU. Notebook chạy B01/B02 nếu chưa có output, thêm Qwen3-ASR-0.6B, rồi lập bảng ba model cùng 100 dev. Backend Qwen là Transformers, không vLLM/aligner. Kết quả từng mẫu và bảng tổng hợp ở `results/`.

Qwen chỉ chạy GPU; runner không cho chạy CPU hoặc tự chuyển sang CPU. Lần CPU trước đã dừng và được giữ trong `attempts/cancelled_cpu/` với 6/100 prediction, không tham gia bảng so sánh.

Ô nghe cuối notebook tự import pandas và Audio/display, nên không cần chạy ô tổng hợp trước để có các import này. Nếu kernel đã khởi động lại, chạy ô đọc Drive với `RUN_NAME` của lần đã lưu để khôi phục ROOT/RUN_DIR; sau đó chạy ô nghe, không cần chạy lại Qwen.

Transcript trong ô nghe được in nguyên văn theo từng nhãn/model, tránh pandas rút gọn chuỗi dài thành `...`. Khi đổi phần hiển thị, chỉ chạy lại ô nghe; không cần chạy inference.

Nghe lại 3–5 lỗi và đọc ba prediction trước khi viết kết luận. Trong bảng đã đo, Whisper/Zipformer chạy CPU laptop và Qwen chạy GPU Colab; không xếp tốc độ như cùng phần cứng. Không mở test để chọn model. Zipformer là ứng viên thử Pi trước, Qwen giữ làm đối chiếu; chưa có số đo Pi để chốt cấu hình.

Đã đủ self dev20 và hai baseline CPU ngày 13/10. Mở notebook riêng `B03_Self_dev20_Qwen_GPU.ipynb` tại thư mục Drive `STT_B01_B03`, chọn GPU, chạy các ô theo thứ tự. Notebook đọc `self_dev20_package.zip` (20 WAV chính, runner/scorer và hai baseline đã đo); chỉ chạy thêm Qwen rồi chấm ba model. Giữ `RUN_NAME = 'self_dev20_qwen_v1'`; bấm lại ô không tạo tên ngẫu nhiên khác, lần hoàn tất không chạy inference lại. Output vào `runs/self_dev20_qwen_v1` trên Drive. Không dùng notebook FLEURS cũ cho bộ tự thu và không ghi đè kết quả FLEURS. Notebook mới đã kiểm tra compile/bootstrap và test local; chưa xác nhận chạy inference Colab. Sau khi Qwen xong, gửi tên lần chạy để kiểm tra độc lập.
