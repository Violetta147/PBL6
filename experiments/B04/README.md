# B04 — Bắt đầu đo trên Raspberry Pi 4

B01–B03 đã có kết quả thật trên laptop/Colab. Chưa có số đo Pi. Bắt đầu bằng Zipformer ONNX INT8 đã đo; sau khi chạy được mới tiếp tục phần đối chiếu Whisper theo kế hoạch. Chưa cần micro hoặc kính để làm bước nhận dạng WAV này.

Trước khi chuyển sang Pi, phát câu 20 self dev trong B03/DEMO.md và đọc reference/prediction. Nhãn là “Kết quả trên máy tính chưa phải kết quả trên kính.”, Qwen nhận hai lần “cách quả” thay “kết quả”. Đối chiếu audio để giải thích đây là lỗi nội dung; không gọi là lỗi chữ hoa/thường. Người thực hiện đã xác nhận nhãn audio, nhưng chưa xác nhận nghe riêng lỗi prediction Qwen này.

Tập demo khoảng 3 phút: giới thiệu mục tiêu chọn model cho Pi và dữ liệu đã dùng; mở bảng FLEURS dev100 rồi bảng self dev20 riêng; phát một mẫu và chỉ khác biệt thật; kết thúc rằng Zipformer là ứng viên thử Pi, chưa có bằng chứng tốc độ/RAM trên Pi. Có thể thêm câu 14 self dev: Zipformer sai “gốc/góc” trong khi Qwen khớp sau chuẩn hóa. Dùng output đã lưu, không cần chạy model lại trên lớp. Chưa ghi nhận đã trình bày với thầy.

Việc cần làm ngay trên Pi: mở Terminal trực tiếp hoặc SSH vào Pi rồi chạy block chỉ đọc sau. Đây là lệnh Linux trên Pi, không phải PowerShell laptop:

```bash
hostname
hostname -I
uname -m
python3 --version
free -h
vcgencmd measure_temp
```

Gửi output và cho biết đang dùng Terminal trực tiếp hay SSH. Nếu SSH, cung cấp tên người dùng kết nối; không gửi mật khẩu trong chat. Các thông tin này dùng xác nhận kiến trúc/Python/RAM/nhiệt và chọn cách chuyển gói, không tự coi Pi đã chạy ASR.

Gói chuẩn bị `B04_Pi4_self_dev20.zip` nằm trong thư mục STT_B01_B03 trên ổ Drive G: chứa đúng 20 WAV chính, manifest đã xác nhận, runner/scorer/audit/summary hiện có và bốn file model Zipformer đã dùng trên laptop. Không có audio test, Qwen weights hoặc môi trường Python laptop; không cần tải lại checkpoint Zipformer nếu giải nén đúng cấu trúc. Receipt `experiments/B04/package_receipt.json` lưu hash từng file. Đồng bộ cloud cần xác nhận riêng.

Sau khi xác nhận kết nối/Python: chuyển và giải nén gói vào thư mục riêng trên Pi; tạo venv, cài runtime phù hợp; thử một WAV để kiểm tra luồng rồi chạy đúng 20 WAV qua hai lượt với hai luồng CPU. Mỗi lượt giữ JSONL, metadata và log riêng. Ghi thời gian nạp model, thời gian inference/RTF, RAM và nhiệt trước/sau. RTF là thời gian xử lý chia thời lượng audio; RAM cực đại cả tiến trình phải ghi rõ có bao gồm nạp model. Không gộp hai lượt thành 40 câu độc lập hoặc coi replay WAV là hội thoại liên tục.

Kết quả chỉ được thêm vào bảng Pi khi có output thật từ Pi. Hiện mới chuẩn bị gói và hướng dẫn, chưa cài runtime hoặc đo inference trên Pi. [sherpa-onnx 1.13.8](https://pypi.org/project/sherpa-onnx/1.13.8/) có bản Linux ARM64/CPython 3.13; vẫn phải kiểm tra môi trường Pi thực tế. [Checkpoint Zipformer](https://huggingface.co/hynt/Zipformer-30M-RNNT-6000h) giữ nguyên nguồn và hash so với lần đo laptop.
