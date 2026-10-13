# B04 — Bắt đầu đo trên Raspberry Pi 4

B01–B03 đã có kết quả thật trên laptop/Colab. Ngày 13/10 đã chạy Zipformer ONNX INT8 trên Pi 4B 8 GB, aarch64/Python 3.13.5, hai lượt cùng self dev20. Kết quả ở `results/zipformer_summary.csv`; raw từng lượt có JSONL, metadata, log GNU time, sensor và verification. Phần đối chiếu Whisper đang tiếp tục; chưa cần micro hoặc kính để làm bước nhận dạng WAV này.

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

Kết quả chỉ được thêm vào bảng Pi khi có output thật từ Pi. [sherpa-onnx 1.13.8](https://pypi.org/project/sherpa-onnx/1.13.8/) và các gói numpy 2.4.3/soundfile 0.14.0/jiwer 4.0.0 đã cài trong venv riêng trên Pi; chỉ thêm GNU time để đo RAM, không nâng cấp Python hệ thống. [Checkpoint Zipformer](https://huggingface.co/hynt/Zipformer-30M-RNNT-6000h) giữ nguyên nguồn và hash so với lần đo laptop.

## Kết quả Zipformer thực tế

| Lượt | Audio | Tổng inference | RTF tổng | RAM cực đại | Nạp model | Nhiệt trước → sau |
|---|---:|---:|---:|---:|---:|---|
| r1 | 84,160 s | 10,278 s | 0,1221 | 199,06 MiB | 3,742 s | 36,0 → 45,2°C |
| r2 | 84,160 s | 10,226 s | 0,1215 | 198,32 MiB | 3,735 s | 36,5 → 45,2°C |

Mỗi lượt 20/20, WER_ws 0,5525%, CER 0,1647%; toàn bộ prediction giống laptop. Median inference mỗi WAV khoảng 0,51 s (min–max khoảng 0,40–0,67 s). `throttled=0x0` trước/sau cả hai lượt. Cùng 20 câu đo hai lần, không phải tập 40 câu độc lập. Chỉ sai “gốc/góc” câu 14.

Inference trong JSONL đo riêng hàm model, không gồm nạp model/đọc WAV; wall time toàn tiến trình khoảng 14,6 s/lượt. RAM là peak RSS toàn tiến trình runner, bao gồm nạp model/thư viện. OS file cache có thể đã ấm sau smoke/lượt trước; mỗi lượt tạo tiến trình/model mới. Số liệu tệp chưa phải độ trễ phụ đề micro hoặc khả năng streaming nguyên sinh.

Trên Pi, thư mục thí nghiệm `/home/pi/PBL6_STT_B04_20261013`; sau khi giải nén gói và bổ sung script đo đã kiểm tra, lệnh dùng là:

```bash
.venv/bin/python experiments/B04/run_zipformer_pi.py --run-name zipformer_r1
.venv/bin/python experiments/B04/run_zipformer_pi.py --run-name zipformer_r2
```

Hai tên trên đã có kết quả; script từ chối ghi đè. Để lặp lại có chủ đích, chọn tên mới và giữ cấu hình/manifest. Ba test tính RTF/RAM đạt trên Pi; 21 test toàn bộ đạt local. Raw và archive xuất từ Pi đã kiểm tra hash/chấm lại độc lập trên laptop, không suy số đo Pi từ kết quả Colab.
