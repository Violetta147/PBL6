# Demo B03 — Ba model trên cùng 100 câu dev

Qwen đã chạy trên Colab A100-SXM4-40GB, Transformers bfloat16, batch 1, ngôn ngữ Vietnamese; không huấn luyện. Lần chạy `qwen_gpu_20261010_023946` được giữ trên Drive. Hai baseline là kết quả CPU laptop đã đo, được dùng lại nguyên vẹn. Prediction và metadata Qwen được sao lưu tại `results/`; bảng sinh lại local trùng summary Colab.

| Checkpoint/runtime đã đo | Thiết bị | WER_ws | CER | Hoàn tất |
|---|---|---:|---:|---:|
| Whisper-base đa ngôn ngữ, openai-whisper | CPU laptop | 49,3743% | 33,9208% | 100/100 |
| Zipformer-30M, sherpa-onnx offline ONNX INT8 | CPU laptop | 7,5080% | 5,3494% | 100/100 |
| Qwen3-ASR-0.6B, qwen-asr Transformers | A100 Colab | 9,7605% | 6,2771% | 100/100 |

Cùng 2.797 đơn vị reference và 9.702 ký tự; giữ dấu/chữ số, cùng chuẩn hóa và WAV. Đã kiểm tra ID, audio/reference hash, signature mã/manifest và chấm lại bằng JiWER. Bằng chứng ở [verification.json](../verification.json), [source.json](results/source.json) và [comparison.csv](results/comparison.csv). `false_captions_per_minute` trống vì tập này chưa đo audio không có lời nói.

Zipformer có tỷ lệ lỗi thấp nhất trong lần đo này. Qwen cao hơn Zipformer 2,2524 điểm phần trăm WER_ws, nhưng lỗi thấp hơn ở 18 câu; Zipformer thấp hơn ở 46 câu, bằng ở 36 câu. Thống kê theo câu chỉ mô tả số lỗi, không phải kiểm định thống kê. Một số ví dụ cho thấy Qwen giữ số viết bằng chữ số và tên riêng tốt hơn. Không thay scorer sau khi xem kết quả; khác biệt `25` và `hai mươi lăm` vẫn tính là lỗi theo quy tắc hiện tại.

## Năm câu để nghe và đối chiếu

Nhận xét dưới đây dựa trên text đã lưu. Người trình bày cần phát WAV và kiểm tra trước khi nói đã phân tích bằng nghe. Mở `comparison.csv`, tìm đúng ID để xem đầy đủ cả ba prediction.

| WAV/ID | Whisper WER_ws | Zipformer WER_ws | Qwen WER_ws | Điều cần xem/nghe |
|---|---:|---:|---:|---|
| [15936085030676963416](../../data/derived/stt_b01_b03/dev/15936085030676963416.wav) | 34,48% | 34,48% | 5,17% | Ngày tháng, Louis XVI và tên người; Qwen có 3 lỗi so với 20 của mỗi baseline. Reference `Versaille` khác output `Versailles`; kiểm tra nhãn/audio trước khi nhận xét, giữ nguyên nhãn trong bảng hiện tại. |
| [39175139941883407](../../data/derived/stt_b01_b03/dev/39175139941883407.wav) | 54,84% | 35,48% | 0,00% | Qwen khớp reference có `19.500 km²` và `14`; Zipformer viết số/đơn vị bằng chữ, tạo 11 lỗi theo scorer hiện tại. Điểm này phản ánh cả cách viết số. |
| [4767212356465567922](../../data/derived/stt_b01_b03/dev/4767212356465567922.wav) | 60,87% | 21,74% | 43,48% | Qwen có `nói chín` thay `nổi tiếng`, cùng lỗi tên riêng và cụm khác; Zipformer có 5 lỗi, Qwen 10. Model mới vẫn có câu kém hơn. |
| [14301804876253465717](../../data/derived/stt_b01_b03/dev/14301804876253465717.wav) | 68,52% | 25,93% | 37,04% | Tên vận động viên, `trượt tuyết`, `về đích` và Super-G đều khó; Qwen viết `13/14` trong khi nhãn viết `mười ba/mười bốn`. Cần tách lỗi nhận âm và khác cách viết. |
| [12943089570068506915](../../data/derived/stt_b01_b03/dev/12943089570068506915.wav) | 63,64% | 39,39% | 36,36% | `108`, `56`, tên món ăn và Baba Shyam; cả ba còn lỗi. Qwen tốt hơn Zipformer một lỗi theo khoảng trắng ở câu này. |

## Trình bày trong 3–5 phút

Mở bảng ba model, nói rõ tập dev100 và thiết bị. Phát một câu Qwen tốt hơn và một câu Zipformer tốt hơn, hiện ba transcript cùng reference. Giải thích khác cách viết số và một lỗi nhận âm. Kết thúc bằng quyết định thử Zipformer ONNX INT8 trên Pi trước, giữ Qwen trên Colab làm đối chiếu.

Đây là ứng viên cho bước đo Pi, chưa phải cấu hình kính đã chốt. [Model card Zipformer](https://huggingface.co/hynt/Zipformer-30M-RNNT-6000h) liệt kê FLEURS trong dữ liệu huấn luyện; kết quả này chưa chứng minh khả năng tổng quát trên môi trường mới. Còn thiếu 20 câu tự thu và xác nhận nghe lỗi. Giữ test đóng; chưa cần fine-tune hoặc thêm model trước khi bổ sung dữ liệu thực tế và số đo Pi.
