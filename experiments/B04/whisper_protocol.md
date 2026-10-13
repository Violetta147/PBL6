# Đối chiếu Whisper.cpp trên Pi

Đăng ký trước khi chạy smoke: dùng whisper.cpp v1.9.5, commit `d1be6fde11ac6e0407606b4e42fe72d34add8037`, model base đa ngôn ngữ GGML từ `ggerganov/whisper.cpp`, revision `5359861c739e955e79d9a303bcbc70fb988958b1`. Ép tiếng Việt, CPU hai luồng, greedy, temperature 0, không fallback nhiệt độ, không context văn bản từ câu trước. Không huấn luyện hoặc sửa nhãn.

Smoke dùng câu self dev01 để kiểm tra CLI. Nếu wall time / thời lượng WAV > 1, thử tiny đa ngôn ngữ dự phòng, giữ nguyên kết quả base. Sau đó đo hai lượt cùng self dev20 cho cấu hình lựa chọn; không coi smoke là một tập đánh giá mới. Tiny là checkpoint khác, phải có tên riêng và không thay điểm Whisper-base đã đo laptop.

Mỗi WAV mở một tiến trình CLI mới để dùng runtime có sẵn. Thời gian đo gồm nạp model, đọc WAV, nhận dạng và ghi text; ghi là process wall RTF, không gọi là inference RTF. GNU time đo peak RSS từng tiến trình; báo cáo giá trị lớn nhất của lượt. Zipformer có inference time riêng và wall time toàn lượt; không so trực tiếp hai phạm vi đo rồi kết luận tỷ lệ tăng tốc. OS file cache có thể ấm. B04 chỉ nhận dạng tệp, chưa đo phụ đề micro.

Lưu text/log/time từng WAV, JSONL chấm cùng scorer, hash checkpoint/binary/code/manifest, sensor trước/sau và xác minh độc lập JiWER. Không ghi đè run, giữ kết quả lỗi nếu có. Thử base được phép kết thúc ở smoke nếu quá chậm theo tiêu chí trên, thay vì bắt buộc chạy 40 lần nạp base.
