# Demo B02: cùng dữ liệu, cùng cách chấm

Hai model đã chạy đủ 100/100 câu FLEURS dev trên CPU laptop. Cùng 2.797 đơn vị reference và 9.702 ký tự, cùng WAV dẫn xuất PCM16 mono16kHz, cùng chuẩn hóa NFC/chữ thường/dấu câu; dấu tiếng Việt và chữ số giữ nguyên.

| Model/runtime | WER_ws | CER | Hoàn tất |
|---|---:|---:|---:|
| Whisper-base, openai-whisper, CPU | 49,3743% | 33,9208% | 100/100 |
| Zipformer-30M, sherpa-onnx offline INT8, CPU | 7,5080% | 5,3494% | 100/100 |

Các điểm được tính lại độc lập bằng JiWER trong [verification.json](../verification.json). Bảng này là subset nội bộ, không phải toàn bộ FLEURS hay điểm XTREME-S chính thức. C1 liệt kê FLEURS trong nguồn huấn luyện; cần dữ liệu tự thu để bổ sung bằng chứng môi trường mới. Giữ nguyên quy tắc chấm sau khi thấy output.

## Ba mẫu để nghe và giải thích

Các nhận xét dưới đây dựa trên text đã lưu; cần phát audio và kiểm tra trước khi trình bày như phân tích đã nghe. Prediction đầy đủ nằm trong [comparison.csv](results/comparison.csv), không cắt chữ khi tính điểm.

1. [4446382519192965870.wav](../../data/derived/stt_b01_b03/dev/4446382519192965870.wav): câu về Kruger National Park và các địa danh. Whisper lặp `page` nhiều lần; WER_ws 284,6154%, Zipformer 35,8974%. WER có thể vượt 100% do lỗi chèn; đây không phải phép chia sai. Cả hai còn lỗi tên riêng. Khi hiển thị có thể rút gọn đoạn lặp, nhưng bảng chấm dùng nguyên prediction.
2. [15936085030676963416.wav](../../data/derived/stt_b01_b03/dev/15936085030676963416.wav): ngày tháng, số năm, tên người và tên cung điện. Hai model cùng WER_ws 34,4828% nhưng lỗi khác nhau. Zipformer viết nhiều số bằng chữ trong khi reference có chữ số; scorer hiện hành vẫn tính khác. Cùng điểm không đồng nghĩa cùng transcript hoặc cùng lỗi.
3. [12943089570068506915.wav](../../data/derived/stt_b01_b03/dev/12943089570068506915.wav): `108`, `56`, tên món ăn và tên người. Whisper WER_ws 63,6364%, Zipformer 39,3939%. Dùng mẫu này để giải thích lỗi số/tên riêng và giới hạn của bộ chấm chưa chuẩn hóa số theo nghĩa.

Demo 3–5 phút: mở summary → chọn một ID chung → nghe WAV → đối chiếu hai transcript → giải thích một lỗi và giới hạn tập dữ liệu. Chưa cần làm UI. Phần 20 câu tự thu còn thiếu; [THU_AM.md](THU_AM.md) chỉ dẫn chuẩn bị, không phải dữ liệu đã thu.
