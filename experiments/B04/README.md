# B04 — Kết quả đo trên Raspberry Pi 4

B01–B03 đã có kết quả thật trên laptop/Colab. Ngày 13/10 đã chạy Zipformer ONNX INT8 trên Pi 4B 8 GB, aarch64/Python 3.13.5, hai lượt cùng self dev20. Kết quả ở `results/zipformer_summary.csv`; raw từng lượt có JSONL, metadata, log GNU time, sensor và verification. Đối chiếu Whisper-base smoke và tiny dự phòng đã hoàn tất. Chọn Zipformer cho demo WAV và thử B05; chưa cần micro hoặc kính để hoàn thành B04.

Trước khi chuyển sang Pi, phát câu 20 self dev trong B03/DEMO.md và đọc reference/prediction. Nhãn là “Kết quả trên máy tính chưa phải kết quả trên kính.”, Qwen nhận hai lần “cách quả” thay “kết quả”. Đối chiếu audio để giải thích đây là lỗi nội dung; không gọi là lỗi chữ hoa/thường. Người thực hiện đã xác nhận nhãn audio, nhưng chưa xác nhận nghe riêng lỗi prediction Qwen này.

Tập demo khoảng 3 phút: giới thiệu mục tiêu chọn model cho Pi và dữ liệu đã dùng; mở bảng FLEURS dev100 rồi bảng self dev20 riêng; phát một mẫu và chỉ khác biệt thật; kết thúc bằng bảng Pi ở cuối tài liệu và giới hạn của phép đo WAV. Có thể thêm câu 14 self dev: Zipformer sai “gốc/góc” trong khi Qwen khớp sau chuẩn hóa. Dùng output đã lưu, không cần chạy model lại trên lớp. Chưa ghi nhận đã trình bày với thầy.

Pi đã kết nối SSH và xác nhận Pi 4B 8 GB, aarch64, Raspberry Pi OS 13/Python 3.13.5. Thư mục làm việc là `/home/pi/PBL6_STT_B04_20261013`. [DEMO.md](DEMO.md) có lệnh chạy một WAV để tập trình bày; không cần chạy lại toàn bộ benchmark.

Gói chuẩn bị `B04_Pi4_self_dev20.zip` nằm trong thư mục STT_B01_B03 trên ổ Drive G: chứa đúng 20 WAV chính, manifest đã xác nhận, runner/scorer/audit/summary hiện có và bốn file model Zipformer đã dùng trên laptop. Không có audio test, Qwen weights hoặc môi trường Python laptop; không cần tải lại checkpoint Zipformer nếu giải nén đúng cấu trúc. Receipt `experiments/B04/package_receipt.json` lưu hash từng file. Đồng bộ cloud cần xác nhận riêng.

Quy trình đã thực hiện cho Zipformer: kiểm tra hash và giải nén gói vào thư mục riêng trên Pi; tạo venv, cài runtime; thử một WAV rồi chạy đúng 20 WAV qua hai lượt với hai luồng CPU. Mỗi lượt giữ JSONL, metadata và log riêng. Ghi thời gian nạp model, thời gian inference/RTF, RAM và nhiệt trước/sau. RTF là thời gian xử lý chia thời lượng audio; RAM cực đại cả tiến trình phải ghi rõ có bao gồm nạp model. Không gộp hai lượt thành 40 câu độc lập hoặc coi replay WAV là hội thoại liên tục.

Kết quả chỉ được thêm vào bảng Pi khi có output thật từ Pi. [sherpa-onnx 1.13.8](https://pypi.org/project/sherpa-onnx/1.13.8/) và các gói numpy 2.4.3/soundfile 0.14.0/jiwer 4.0.0 đã cài trong venv riêng trên Pi; thêm GNU time để đo RAM và CMake để biên dịch runtime whisper.cpp có sẵn, không nâng cấp Python hệ thống. [Checkpoint Zipformer](https://huggingface.co/hynt/Zipformer-30M-RNNT-6000h) giữ nguyên nguồn và hash so với lần đo laptop.

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

Hai tên trên đã có kết quả; script từ chối ghi đè. Để lặp lại có chủ đích, chọn tên mới và giữ cấu hình/manifest. Sau bổ sung adapter Whisper, bốn test đo/CLI đạt trên Pi; 22 test toàn bộ đạt local. Raw và archive xuất từ Pi đã kiểm tra hash/chấm lại độc lập trên laptop, không suy số đo Pi từ kết quả Colab.

## Đối chiếu Whisper.cpp

[Quy trình đã đặt trước](whisper_protocol.md): dùng Whisper-base đa ngôn ngữ qua whisper.cpp v1.9.5, tiếng Việt, CPU hai luồng. Smoke câu dev01 đúng nội dung nhưng mất 20,869 s cho WAV 5,355 s, wall RTF 3,8973, peak RSS 237,59 MiB. Vì wall RTF > 1, chuyển sang tiny dự phòng và giữ output base trong `results/whisper_base_smoke`; không có điểm chất lượng base trên đủ 20 câu Pi.

Tiny smoke mất 8,737 s, wall RTF 1,6316 và sai nội dung. Tiny là checkpoint khác với Whisper-base trên laptop. Không sao chép điểm base laptop sang bảng tiny/Pi. Model GGML tải từ repository tác giả `ggerganov/whisper.cpp`, revision ghim trong metadata; binary/model/code/manifest đều có SHA-256.

Phép đo CLI mở tiến trình mới cho mỗi WAV: wall time gồm nạp model, đọc WAV, nhận dạng và ghi text. Do đó không lấy wall RTF của Whisper chia cho inference RTF của Zipformer để tuyên bố mức tăng tốc. Peak RSS là giá trị lớn nhất của các tiến trình CLI trong lượt, gồm nạp model; thời gian nạp không được trừ khỏi wall. Raw có text, log, GNU time từng WAV và JSONL để chấm cùng scorer.

Pi chưa có micro, người thực hiện xác nhận ngày 13/10. B04 demo WAV độc lập với việc mua/mượn micro. B05 có thể bắt đầu bằng replay theo thời gian thực qua VAD/ASR và ghi rõ là replay; phần thu giọng nói trực tiếp còn chờ thiết bị.

| Tiny, cùng self dev20 | WER_ws | CER | Tổng wall | Wall RTF | Peak RSS | Nhiệt trước → sau |
|---|---:|---:|---:|---:|---:|---|
| r1 | 41,9889% | 26,3591% | 172,807 s | 2,0533 | 147,48 MiB | 37,9 → 48,7°C |
| r2 | 41,9889% | 26,3591% | 171,309 s | 2,0355 | 147,46 MiB | 39,4 → 49,6°C |

Hai lượt đủ 20/20, cùng 76 lỗi / 181 đơn vị và 160 lỗi / 607 ký tự; prediction cả 20 câu giống nhau giữa hai lượt. `throttled=0x0` trước/sau. Median wall mỗi WAV 8,57/8,44 s. Bảng tại `results/whisper_summary.csv`, raw tại `whisper_tiny_r1/` và `whisper_tiny_r2/`; JiWER, audio hash, timing và peak RSS đã kiểm tra lại trên laptop sau tải từ Pi. Smoke giữ riêng, không trộn vào 20 câu.

**Lựa chọn B04:** Zipformer ONNX INT8, CPU hai luồng. Trên self dev20 đã đo, chất lượng tốt hơn tiny và thời gian inference thấp hơn thời lượng audio; RAM khoảng 199 MiB phù hợp Pi 8 GB. Whisper-base nhận đúng câu smoke nhưng chậm theo tiêu chí đã đặt trước; tiny giảm wall time nhưng chất lượng/tốc độ chưa phù hợp cấu hình thử này. Không suy rằng mọi cấu hình Whisper đều kém hoặc Zipformer đã đạt chất lượng dùng thực tế. Giữ nguyên model cho B05, chưa có lý do huấn luyện lại từ các kết quả này.

Để lặp riêng Whisper có chủ đích, trong workspace Pi đã chuẩn bị dùng `--run-name` mới; các tên đã đo sẽ bị từ chối ghi đè:

```bash
.venv/bin/python experiments/B04/run_whisper_cpp_pi.py --run-name whisper_tiny_new --checkpoint tiny
```

Runtime upstream giữ nguyên tag/commit; lệnh cấu hình/biên dịch và CLI help lưu tại `results/whisper_configure.log`, `whisper_build.log`, `whisper_CMakeCache.txt`, `whisper_cli_help.txt`. Metadata từng run lưu tham số CLI và nguồn/hash model để đối chiếu. Đây chỉ là biên dịch phần mềm có sẵn, không xây dựng hay huấn luyện model mới.
