# Chuẩn bị 20 câu dev thật

Chưa có bản ghi tự thu được xác nhận. Không thay bằng TTS hoặc lấy audio FLEURS rồi gọi là tự thu.

Đọc 20 câu trong `self_dev_template.csv`, thu từng tệp `data/self_recorded/dev/self_01.wav` đến `self_20.wav`. Có thể dùng phần mềm thu âm đang có. Lưu mono 16kHz PCM16; nếu thu 48kHz, resample thực sự bằng công cụ có sẵn. Giữ bản thu gốc. Đọc tự nhiên, không cần đọc giống văn bản tuyệt đối: nhãn cuối phải phản ánh lời thực sự nói, kể cả nói nhầm/lặp từ.

Ghi mã người nói, phiên thu, điều kiện thực tế (10 câu yên, 10 câu một điều kiện ồn khi thuận tiện). Có sự đồng ý của người được thu; nghe lại từng tệp, chỉnh reference theo audio rồi mới điền `consent=yes` và `label_verified=yes`. Không mặc định nhãn đúng chỉ vì có câu gợi ý. Không cần đưa tên thật vào metadata.

Giữ phiên/người của test tách biệt trước khi chỉnh cấu hình; test sẽ thu ở giai đoạn sau. Nếu chỉ có một người thì tách phiên và báo giới hạn người nói. Sau khi có WAV và metadata thật: `python experiments/import_self.py --metadata experiments/B02/self_dev_template.csv`. Lệnh kiểm tra đủ 20 WAV và tạo `experiments/manifests/self_dev20.csv`; chạy ba model và lập bảng tự thu riêng.
