# Chuẩn bị 20 câu dev thật

Chưa có bản ghi tự thu được xác nhận. Không thay bằng TTS hoặc lấy audio FLEURS rồi gọi là tự thu.

Đọc 20 câu trong `self_dev_template.csv`. Có thể dùng ứng dụng ghi âm đang có trên điện thoại hoặc micro laptop/tai nghe; chưa cần mua thiết bị. Không mặc định điện thoại tốt hơn laptop: khoảng cách, hướng micro, tiếng ồn và xử lý âm thanh của ứng dụng đều ảnh hưởng. Micro tai nghe gần miệng thuận tiện cho bản thu rõ, nhưng không đại diện cho kính thu tiếng người đối diện ở xa. Xem [hướng dẫn đặt micro của Shure](https://service.shure.com/articles/en_US/Knowledge/critical-distance-and-microphone-placement).

Bắt đầu bằng hai tệp, đọc câu 01 và 02 trong phòng yên, đặt điện thoại cách miệng khoảng 30 cm nếu dùng điện thoại. Đây là khoảng cách khởi đầu cho phiên thu, không phải phép mô phỏng kính đã được xác nhận. Nói tự nhiên, để một khoảng nghỉ ngắn trước/sau câu, nghe lại xem có rõ và bị cắt đầu/cuối không. Đặt tên `self_01` và `self_02`, giữ đuôi thực tế `.m4a`, `.mp3` hoặc `.wav`. Đưa bản gốc lên thư mục Drive `Seventh Semester/PBL6/STT_B01_B03/self_recorded/raw` và báo trong chat. Thư mục này là đích đề xuất, không phải xác nhận đã có file. Codex kiểm tra định dạng và chuẩn bị bản WAV trước khi thu tiếp đủ 20 câu; hai tệp đầu vẫn thuộc bộ 20.

Không cần tự chuyển định dạng hoặc đổi đuôi file thành WAV. Đầu vào chạy model cuối cùng phải là `data/self_recorded/dev/self_01.wav` đến `self_20.wav`, mono 16kHz PCM16; Codex sẽ chuẩn bị bản chuyển đổi và kiểm tra khi nhận được audio. Giữ bản thu gốc. Đọc tự nhiên, không cần đọc giống văn bản tuyệt đối: nhãn cuối phải phản ánh lời thực sự nói, kể cả nói nhầm/lặp từ.

Ghi mã người nói, phiên thu, điều kiện thực tế (10 câu yên, 10 câu một điều kiện ồn khi thuận tiện). Có sự đồng ý của người được thu; nghe lại từng tệp, chỉnh reference theo audio rồi mới điền `consent=yes` và `label_verified=yes`. Không mặc định nhãn đúng chỉ vì có câu gợi ý. Không cần đưa tên thật vào metadata.

Dùng một thiết bị và cấu hình thu ổn định cho bộ 20; cả ba model phải nhận cùng các tệp đã chuẩn hóa. Chưa cần thí nghiệm so nhiều micro. Ghi tên thiết bị/ứng dụng, khoảng cách và tiếng ồn thực tế. Hai nhóm yên/ồn dùng câu khác nhau nên điểm theo nhóm chỉ mô tả, không chứng minh tác động riêng của tiếng ồn. Nếu chưa có điều kiện thu ồn, báo đúng điều kiện đã thu thay vì gán nhãn ồn cho đủ số.

Giữ phiên/người của test tách biệt trước khi chỉnh cấu hình; test sẽ thu ở giai đoạn sau. Nếu chỉ có một người thì tách phiên và báo giới hạn người nói. Sau khi có WAV và metadata thật: `python experiments/import_self.py --metadata experiments/B02/self_dev_template.csv`. Lệnh kiểm tra đủ 20 WAV và tạo `experiments/manifests/self_dev20.csv`; chạy ba model và lập bảng tự thu riêng.
