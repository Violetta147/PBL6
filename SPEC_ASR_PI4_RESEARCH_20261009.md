# Đặc tả lean: thử nghiệm ASR tiếng Việt trên Pi 4

Phiên bản 2.0 — 09/10/2026. Một người phụ trách STT, bảy tuần, một buổi demo mỗi tuần. Phạm vi được rút gọn theo yêu cầu học tập, thử nghiệm và đánh giá.

Đọc tài liệu này để biết mục tiêu/cách đo; làm theo [kế hoạch 7 buổi](PLAN_DEMO_STT_7_BUOI.md) để thực hiện. [Ghi chú khái niệm](REVIEW_CONCEPTS_20261009.md) giải thích các điểm dễ nhầm.

## 1. Mục tiêu cần giải quyết

**Tìm một mô hình STT tiếng Việt có sẵn phù hợp với Pi 4, bằng cách so sánh chất lượng phiên âm, tốc độ và RAM, rồi thử thu âm thành chữ.** Kết quả phục vụ hướng phụ đề kính thông minh; SLR vẫn là phần đóng góp riêng cần ưu tiên nguồn lực.

Ba câu hỏi: trên cùng audio, các model khác nhau thế nào; model nhỏ nào phù hợp Pi hơn; khi thu bằng micro, tiếng ồn/khoảng cách/chia đoạn gây lỗi gì? Đầu ra là bảng so sánh, vài lỗi có audio/nhãn/output và một demo cơ bản.

Dùng trọng số pretrained; **baseline đủ tốt thì giữ**. Không cần training hoặc cải tiến thuật toán để hoàn thành STT. Tính mới ở phần này là khảo sát lựa chọn hiện nay, gồm model năm 2026, và kết quả thử nghiệm do nhóm tự tạo; không tuyên bố phát minh ASR mới.

Phần bắt buộc dừng ở thu âm → STT → chữ trên terminal/màn hình đang có. Kính thật và kết nối SLR làm sau nếu đã sẵn sàng. App điện thoại, dịch vụ nhiều người, phụ đề tạm, nhận diện người nói và thiết kế kính không nằm trong phần STT này.

## 2. Dùng tài nguyên đang có

| Tài nguyên | Vai trò |
|---|---|
| Pi 4B 8 GB, Raspberry Pi OS 13 Trixie, aarch64 | Chạy model nhỏ trên CPU, đo tốc độ/RAM và thử micro |
| Laptop i5-7200U, RAM 12 GB, Intel HD Graphics 620 | Quản lý mã, xem kết quả, chuẩn bị demo và điều khiển Pi |
| Colab Pro, 250 credits theo thông tin người thực hiện | So sánh model; dùng GPU thực tế được cấp, A100 khi có |
| Drive 5 TB, home server HDD 1 TB | Lưu dữ liệu/kết quả và bản sao quan trọng |
| Micro USB và màn hình đang có | Thu câu nói và hiện chữ; kiểm tra/mượn micro sớm nếu thiếu |

Pi dùng CPU; laptop nêu trên không có GPU CUDA. C2 chạy trên Colab không có nghĩa phải chuyển nó lên Pi. Colab phục vụ thí nghiệm tệp, không làm máy chủ phụ đề. Lưu output ra Drive trước khi ngắt phiên và sao lưu kết quả chính; không cần phục hồi thêm corpus lớn. [Colab FAQ](https://research.google.com/colaboratory/faq.html), [Pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/).

## 3. Ba model để so sánh

| Mã | Model/gói | Vai trò |
|---|---|---|
| C0 | `openai/whisper-base`, bản đa ngôn ngữ | Baseline trên Colab; thử Pi bằng whisper.cpp |
| C1 | `hynt/Zipformer-30M-RNNT-6000h`, gói `sherpa-onnx-zipformer-vi-30M-int8-2026-02-09` | Model nhỏ chuyên tiếng Việt, ưu tiên thử CPU Pi |
| C2 | `Qwen/Qwen3-ASR-0.6B` | Model ASR năm 2026 để đối chiếu trên Colab |

So sánh các checkpoint/runtime thực tế này; không kết luận riêng kiến trúc nào luôn tốt hơn. Dùng frontend và tokenizer của tác giả. Whisper chọn bản đa ngôn ngữ, nhiệm vụ phiên âm tiếng Việt; C1 dùng gói ONNX INT8 đã có; C2 bắt đầu bằng backend Transformers. Gói C1 là offline, có thể kết hợp VAD khi thu micro, không mặc định streaming nguyên sinh.

Nguồn thực hành: [Whisper](https://github.com/openai/whisper), [whisper.cpp](https://github.com/ggml-org/whisper.cpp), [Zipformer](https://huggingface.co/hynt/Zipformer-30M-RNNT-6000h), [gói sherpa-onnx tiếng Việt](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/zipformer-transducer-models.html), [Qwen3-ASR](https://huggingface.co/Qwen/Qwen3-ASR-0.6B).

Nếu C0 quá chậm trên Pi, thử Whisper-tiny đa ngôn ngữ. Nếu C2 không chạy được sau khoảng một ngày sửa môi trường, có thể thay bằng [PhoASR-whisper-small](https://huggingface.co/Qualcomm-AI-Research/PhoASR-whisper-small), ghi lý do và chốt trước đánh giá cuối. Không bắt buộc thử cả hai dự phòng. Ghi nguồn, phiên bản và giấy phép; không cần tự lượng tử hóa hoặc phân phối lại trọng số.

## 4. Dữ liệu vừa đủ

**FLEURS `vi_vn`:** dùng 5–10 mẫu train kiểm tra luồng; chọn cố định **100 mẫu dev và 200 mẫu test**, dùng seed 42 và lưu ID trước chạy. Không lựa câu dễ sau khi xem output. Giữ split chính thức. Chạy toàn bộ dev/test là mở rộng nếu còn thời gian; bảng phải ghi rõ subset 100/200, không gọi là điểm toàn bộ FLEURS/XTREME-S.

Nguồn hiện có ở revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`: train 2.994, dev 361, test 857 bản ghi. Có 4 dòng train và 6 dòng test chỉ gồm 6 cột TSV; đọc theo cấu trúc từng dòng, không bỏ chúng. Có thể lấy transcript nguyên bản ở trường thứ ba nhất quán rồi chuẩn hóa để chấm. [Nguồn FLEURS](https://huggingface.co/datasets/google/fleurs); archive và cách khôi phục ở [README](README.md).

**Audio tự thu:** khoảng **50–70 câu**, gồm 20 câu dev và 30–50 câu test, thêm khoảng 2 phút không có lời nói. Thử câu thường, số/phủ định, phòng yên và một điều kiện ồn có ghi nhận. Mời thêm 1–2 người khi thuận tiện; không cần chiến dịch thu dữ liệu lớn.

Chia trước khi chỉnh model/VAD, ưu tiên người nói khác giữa dev/test. Nếu chỉ có cùng người, tách phiên và nêu chưa kiểm tra khả năng tổng quát sang người mới. Các đoạn cùng phiên/bản biến đổi của cùng audio đi chung split. Xin đồng ý ghi âm, dùng mã người nói và nghe kiểm tra transcript; nhãn máy chưa kiểm tra không dùng làm chuẩn.

Metadata đủ dùng: ID, đường dẫn, split, người/phiên, điều kiện và transcript. Với FLEURS, dùng split + tên WAV làm ID mẫu để gắn output đúng file. Giữ raw; chuyển audio ra bản dẫn xuất; không bỏ câu ồn hợp lệ vì nhận sai. VietSuperSpeech có nhãn từ Zipformer nên không dùng làm nhãn chuẩn chính để xếp hạng chính Zipformer.

Benchmark công khai có thể từng xuất hiện trong dữ liệu pretrained; C1 có liệt kê FLEURS. Test chưa dùng chọn cấu hình của nhóm không đồng nghĩa model chắc chắn chưa thấy. Audio tự thu bổ sung bằng chứng về môi trường của đề tài, với giới hạn tập nhỏ.

## 5. Pipeline và phần mã tối thiểu

```text
WAV hoặc micro → đọc/thu audio → frontend của checkpoint → model → text
                                                               ↓
                                                   bảng đo / hiện chữ
```

Bắt đầu bằng WAV mono 16 kHz, PCM 16 bit khi runtime yêu cầu. Stereo cần kiểm tra kênh; 48 kHz phải resample thật, không chỉ sửa header. Dùng đúng processor/tokenizer, giữ dấu tiếng Việt. Không thêm MFCC, F0, PCA hoặc scaler vào model pretrained.

Khi chạy tệp được, thử ví dụ micro + VAD sẵn có trong runtime. VAD đóng đoạn, model phiên âm rồi hiện **final**. Chưa cần partial hoặc thuật toán xếp lịch mới. Nếu chưa theo kịp nói liên tục, dùng nhận từng lượt nói làm demo và báo giới hạn.

Mã gồm một notebook so sánh, một script/CLI Pi và vài hàm đọc dữ liệu/chuẩn hóa/chấm điểm dùng chung. Tách module khi thật sự lặp hoặc khó đọc; không dựng framework, nhiều tầng backend hoặc giao thức caption riêng.

Mỗi lượt chạy lưu output CSV/JSONL, bảng tổng hợp và ghi chú môi trường. Output gồm ID, model, split, reference, prediction, thời lượng, thời gian xử lý và status. Ghi checkpoint/runtime phiên bản nào, thiết bị và cờ giải mã nào để chạy lại được.

## 6. Đánh giá đơn giản nhưng đúng

**WER_ws/CER:** dùng một hàm chuẩn hóa cho cả nhãn và output: Unicode NFC, chữ thường, thay dấu câu bằng khoảng trắng, gộp khoảng trắng. Giữ dấu và chữ số; “ma” khác “má”, “25” vẫn khác “hai mươi lăm”. Không tạo từ điển sửa chữ từ test.

`WER_ws = (thay thế + xóa + chèn) / số đơn vị reference`. Tách bằng khoảng trắng, thường gần mức âm tiết tiếng Việt; không gọi là từ đã phân đoạn. CER dùng Unicode code point sau NFC, bỏ khoảng trắng. Điểm toàn tập là tổng lỗi chia tổng độ dài reference. [JiWER](https://jitsi.github.io/jiwer/), [bài học đánh giá ASR](https://huggingface.co/learn/audio-course/chapter5/evaluation).

Nhãn rỗng không chia cho 0: với audio không có lời nói, báo số lần tạo chữ sai mỗi phút. Inference lỗi/timeout giữ status; với audio/nhãn hợp lệ nhưng không có output, chấm dự đoán rỗng và báo tỷ lệ hoàn tất. Không chỉ báo điểm trên các mẫu thành công.

**Tốc độ/RAM trên Pi:** chọn **20 tệp dev cố định**, chạy **hai lượt** cho C0/C1. Báo median và min–max thời gian/RTF, RAM quan sát được, nhiệt trước/sau. `RTF = thời gian xử lý / thời lượng audio`. Tách nạp model nếu công cụ cho phép; nếu CLI nạp lại mỗi tệp, ghi wall time gồm nạp, không gọi là warm inference. Giữ cùng audio/điều kiện, ghi số luồng/runtime. Không xếp thời gian GPU Colab và CPU Pi như cùng môi trường.

**Micro:** thử 5–10 phút với câu ngắn, khoảng nghỉ, câu nối nhanh và ồn. Ghi chữ có theo kịp không, mất/lặp chữ, RAM/nhiệt và khoảng chờ. Với 10 câu có mốc kết thúc xác định được, đo từ hết lời nói đến khi final hiện; nếu đo từ VAD hoặc bấm giờ, ghi đúng cách đo và độ chính xác. Không cần đồng bộ đồng hồ nhiều thiết bị hoặc đo năng lượng.

Nếu chấm phiên liên tục, ghép toàn bộ final và so với toàn bộ reference; lời VAD bỏ sót vẫn tính lỗi xóa. RTF trên WAV không tự chứng minh micro theo kịp. Không cần bootstrap/khoảng tin cậy để hoàn thành; báo số mẫu và giới hạn là bắt buộc.

## 7. Thứ tự thử nghiệm và điểm dừng

| Mã | Làm gì | Đầu ra |
|---|---|---|
| T1 | C0 trên 5–10 mẫu pilot, kiểm tra audio/scorer | Audio → text và điểm tính đúng |
| T2 | C0/C1/C2 trên 100 FLEURS dev và 20 câu tự thu dev | Bảng dev, ví dụ lỗi, cấu hình cần thử Pi |
| T3 | C0/C1 trên Pi, 20 tệp dev × 2 lượt | Bảng tốc độ/RAM, ứng viên demo |
| T4 | Micro + VAD + ứng viên Pi, dùng dev | Chữ final, lỗi do model/thu/chia đoạn |
| T5 | Sau chốt cấu hình, chấm 200 FLEURS test và 30–50 câu tự thu test; xác nhận bản chọn trên Pi | Bảng cuối và giới hạn |

Chọn/chỉnh trên dev. Trước T5, chốt ID, checkpoint/runtime, scoring và chia đoạn. Phân tích test để báo cáo được; dùng nó sửa tiếp phải nói rõ test tham gia phát triển. Không cần hồ sơ đăng ký thí nghiệm phức tạp.

Nếu GGML/Pi khác HF/Colab, ghi backend riêng và kiểm tra chất lượng bản thực sự chọn trên Pi. Nếu tiny là cấu hình cuối, chấm cùng dữ liệu/quy tắc. Thử micro cuối bằng audio test hoặc một phiên mới với config đã chốt; không cần stress test ba lượt.

**Dừng tối ưu khi có demo cơ bản và bảng đủ để giải thích lựa chọn.** Nếu còn yếu, thử tối đa một thay đổi đơn giản trên dev: model nhỏ hơn, mức thu, VAD hoặc số luồng. Không mở training vì điểm chưa đẹp. Các ngưỡng WER/độ trễ cứng trong bản trước không còn là tiêu chí nghiệm thu.

## 8. Điều kiện hoàn thành

- Có kết quả ba ứng viên, hoặc lý do thay thế/không chạy được được ghi rõ.
- Bảng đo có dữ liệu/scoring rõ, output từng mẫu và ví dụ lỗi được nghe kiểm tra.
- Có thử model nhỏ trên Pi và demo thu âm → chữ; nói đúng mức liên tục hoặc từng lượt.
- Có báo cáo ngắn về chất lượng, tốc độ, RAM, lỗi và lựa chọn cuối.

Có thể kết luận baseline đủ dùng, model mới tốt hơn nhưng chỉ để đối chiếu trên Colab, hoặc Pi chưa theo kịp hội thoại này. Kết luận có phạm vi/bằng chứng là kết quả học tập đáng giá, không phải chứng minh một model luôn tốt nhất.

## 9. Bảng kết quả và báo cáo

Bảng chất lượng gồm model/backend, corpus/split, số mẫu hoàn tất/tổng, WER_ws, CER và thiết bị. Bảng Pi thêm thời gian/RTF, RAM và nhiệt. Ô chưa đo ghi `chưa đo`; không lấy số model card điền vào kết quả nhóm.

Báo cáo khoảng 4–6 trang, điều chỉnh theo yêu cầu học phần: bài toán; model/dữ liệu; cách đo; kết quả; lỗi và lựa chọn. Có 3–5 ví dụ như số, phủ định, giọng địa phương, cắt đầu câu hoặc chữ lặp. Vài bảng/hình từ dữ liệu thật là đủ; không cần dashboard/báo cáo từng stage.

## 10. Bắt đầu thực hiện

Làm B01 trong [kế hoạch](PLAN_DEMO_STT_7_BUOI.md): một audio → C0 → lưu text → kiểm tra WER bằng tay. Học waveform, sample rate, frontend và evaluation đúng lúc cần từ [khóa Audio Hugging Face](https://huggingface.co/learn/audio-course/chapter0/introduction).

Năm stage/35 bước ML là kiến thức tham chiếu, không còn là checklist phải triển khai. Kính thật, SLR interface, partial, thống kê suy luận và model mở rộng làm sau phần cốt lõi. Mỗi tuần ưu tiên một kết quả thử nghiệm để demo theo lịch đã chốt.
