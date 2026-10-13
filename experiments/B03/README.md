# B03 — So sánh ba model

Đã chạy `B03_Qwen_Colab_GPU.ipynb` trên Colab A100-SXM4-40GB: Qwen hoàn tất 100/100 dev, WER_ws 9,7605%, CER 6,2771%. Lần chạy `qwen_gpu_20261010_023946` giữ nguyên trên Drive; bản prediction và metadata được sao lưu vào `results/`. [DEMO.md](DEMO.md) có bảng ba model và năm câu để nghe/đối chiếu. Không cần chạy lại Qwen để xem bảng này.

Mở `B03_STT.ipynb` trên Colab GPU. Notebook chạy B01/B02 nếu chưa có output, thêm Qwen3-ASR-0.6B, rồi lập bảng ba model cùng 100 dev. Backend Qwen là Transformers, không vLLM/aligner. Kết quả từng mẫu và bảng tổng hợp ở `results/`.

Qwen chỉ chạy GPU; runner không cho chạy CPU hoặc tự chuyển sang CPU. Lần CPU trước đã dừng và được giữ trong `attempts/cancelled_cpu/` với 6/100 prediction, không tham gia bảng so sánh.

Ô nghe cuối notebook tự import pandas và Audio/display, nên không cần chạy ô tổng hợp trước để có các import này. Nếu kernel đã khởi động lại, chạy ô đọc Drive với `RUN_NAME` của lần đã lưu để khôi phục ROOT/RUN_DIR; sau đó chạy ô nghe, không cần chạy lại Qwen.

Transcript trong ô nghe được in nguyên văn theo từng nhãn/model, tránh pandas rút gọn chuỗi dài thành `...`. Khi đổi phần hiển thị, chỉ chạy lại ô nghe; không cần chạy inference.

Nghe lại 3–5 lỗi và đọc ba prediction trước khi viết kết luận. Trong bảng đã đo, Whisper/Zipformer chạy CPU laptop và Qwen chạy GPU Colab; không xếp tốc độ như cùng phần cứng. Không mở test để chọn model. Zipformer là ứng viên thử Pi trước, Qwen giữ làm đối chiếu; chưa có số đo Pi để chốt cấu hình.

Ngày 13/10, người thực hiện đã chạy Qwen self dev20 trên A100-SXM4-40GB, bfloat16, đủ 20/20. Run `self_dev20_qwen_v1` và input SHA-256 khớp gói; runner/scorer/manifest hash khớp, hai baseline giữ nguyên, JiWER độc lập khớp và bảng sinh lại local trùng Colab về nội dung. Kết quả ba model tại `results/self_dev20/`, nguồn/hash tại `source.json`; xem `DEMO.md` để trình bày.

Self dev20: WER_ws Whisper 27,6243%, Zipformer 0,5525%, Qwen 1,1050%; CER 17,7924%, 0,1647%, 1,3180%. Qwen chỉ sai hai đơn vị ở câu 20, 19 câu còn lại khớp sau chuẩn hóa. Còn cần người trình bày nghe câu lỗi Qwen trước khi mô tả phân tích bằng nghe. Tập nhỏ một người đọc, 2 phòng ngủ/18 cà phê, chưa thay đánh giá test/Pi.

Không cần chạy lại Qwen để xem output đã lưu. Giữ notebook riêng `B03_Self_dev20_Qwen_GPU.ipynb` và `RUN_NAME = 'self_dev20_qwen_v1'`. Khi kernel mới, chạy ô mở Drive để khôi phục ROOT/RUN_DIR rồi ô nghe cuối; có thể dùng CPU để đọc/nghe kết quả, không chạy ô inference trên CPU. Nếu chạy từ đầu, ô GPU và runner vẫn chặn Qwen CPU. Bấm lại ô inference với cùng gói/cấu hình nhận biết lần đã hoàn tất, không suy diễn việc sinh summary là một lần inference mới.
