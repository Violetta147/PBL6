# Demo B03 — Ba model trên cùng 100 câu dev

Qwen đã chạy trên Colab A100-SXM4-40GB, Transformers bfloat16, batch 1, ngôn ngữ Vietnamese; không huấn luyện. Lần chạy `qwen_gpu_20261010_023946` được giữ trên Drive. Hai baseline là kết quả CPU laptop đã đo, được dùng lại nguyên vẹn. Prediction và metadata Qwen được sao lưu tại `results/`; bảng sinh lại local trùng summary Colab.

| Checkpoint/runtime đã đo                     | Thiết bị   |   WER_ws |      CER | Hoàn tất |
| -------------------------------------------- | ---------- | -------: | -------: | -------: |
| Whisper-base đa ngôn ngữ, openai-whisper     | CPU laptop | 49,3743% | 33,9208% |  100/100 |
| Zipformer-30M, sherpa-onnx offline ONNX INT8 | CPU laptop |  7,5080% |  5,3494% |  100/100 |
| Qwen3-ASR-0.6B, qwen-asr Transformers        | A100 Colab |  9,7605% |  6,2771% |  100/100 |

Cùng 2.797 đơn vị reference và 9.702 ký tự; giữ dấu/chữ số, cùng chuẩn hóa và WAV. Đã kiểm tra ID, audio/reference hash, signature mã/manifest và chấm lại bằng [^1]JiWER. Bằng chứng ở [verification.json](../verification.json), [source.json](results/source.json) và [comparison.csv](results/comparison.csv). `false_captions_per_minute` trống vì tập này chưa đo audio không có lời nói.

Zipformer có tỷ lệ lỗi thấp nhất trong lần đo này. Qwen cao hơn Zipformer 2,2524 điểm phần trăm WER_ws, nhưng lỗi thấp hơn ở 18 câu; Zipformer thấp hơn ở 46 câu, bằng ở 36 câu. Thống kê theo câu chỉ mô tả số lỗi, không phải kiểm định thống kê. Một số ví dụ cho thấy Qwen giữ số viết bằng chữ số và tên riêng tốt hơn. Không thay scorer sau khi xem kết quả; khác biệt `25` và `hai mươi lăm` vẫn tính là lỗi theo quy tắc hiện tại.

## Năm câu để nghe và đối chiếu

Nhận xét dưới đây dựa trên text đã lưu. Người trình bày cần phát WAV và kiểm tra trước khi nói đã phân tích bằng nghe. Mở `comparison.csv`, tìm đúng ID để xem đầy đủ cả ba prediction.

| WAV/ID | Whisper WER_ws | Zipformer WER_ws | Qwen WER_ws | Điều cần xem/nghe |
|---|---:|---:|---:|---|
| [15936085030676963416](../../data/derived/stt_b01_b03/dev/15936085030676963416.wav) | 34,48% | 34,48% | 5,17% | Ngày tháng, Louis XVI và tên người; Qwen có 3 lỗi so với 20 của mỗi baseline. Reference `Versaille` khác output `Versailles`; kiểm tra nhãn/audio trước khi nhận xét, giữ nguyên nhãn trong bảng hiện tại. |
| [39175139941883407](../../data/derived/stt_b01_b03/dev/39175139941883407.wav) | 54,84% | 35,48% | 0,00% | Qwen khớp reference có `19.500 km²` và `14`; Zipformer viết số/đơn vị bằng chữ, tạo 11 lỗi theo scorer hiện tại. Điểm này phản ánh cả cách viết số. |
| [4767212356465567922](../../data/derived/stt_b01_b03/dev/4767212356465567922.wav) | 60,87% | 21,74% | 43,48% | Qwen có `nói chín` thay `nổi tiếng`, cùng lỗi tên riêng và cụm khác; Zipformer có 5 lỗi, Qwen 10. Model mới vẫn có câu kém hơn. |
| [14301804876253465717](../../data/derived/stt_b01_b03/dev/14301804876253465717.wav) | 68,52% | 25,93% | 37,04% | Tên vận động viên, `trượt tuyết`, `về đích` và Super-G đều khó; Qwen viết `13/14` trong khi nhãn viết `mười ba/mười bốn`. Cần tách lỗi nhận âm và khác cách viết. |
| [5380420816515716433](../../data/derived/stt_b01_b03/dev/5380420816515716433.wav) | 77,27% | 13,64% | 36,36% | Xe buýt Coaster: Zipformer có 3 lỗi nhưng giữ `vốn rất thoải mái và chắc chắn`; Qwen có 8 lỗi, gồm `vũng các thỏi máy`. Cả hai còn lỗi `loại` và Coaster. |

Ba transcript người thực hiện gửi từ ô nghe (ID 4767212356465567922, 14301804876253465717 và 5380420816515716433) khớp prediction đã lưu. Ngày 10/10/2026, người thực hiện xác nhận đã nghe và đối chiếu cả ba với nhãn chuẩn. Chúng được chọn theo WER Qwen cao nhất, nên dùng để tìm lỗi và không đại diện cho toàn bộ dev100. Cần xem cả hai câu Qwen tốt hơn trong bảng này để tránh chỉ trình bày một phía; hai câu đó chưa được xác nhận đã nghe. Không suy xác nhận ba câu thành kiểm tra toàn bộ nhãn dev100.

Phân tích text cho thấy hai loại lỗi cần phân biệt. `mười ba/mười bốn` so với `13/14` khác cách viết số; scorer giữ quy tắc hiện hành nên vẫn tính lỗi. `vận động viên trượt tuyết` thành `phần đông viên trực tiếp`, `về đích` thành `về đất` hoặc `thoải mái` thành `thỏi máy` làm thay đổi nội dung lời nói. Các tên như bhajan, Shri Shyam, Maciej Krezel và Coaster cũng bị nhận sai; chưa thể quy toàn bộ lỗi cho tên riêng hay cách viết số. Chữ hoa của Zipformer được chuẩn hóa về chữ thường khi chấm, không tạo thêm lỗi.

## Trình bày trong 3–5 phút

Mở bảng ba model, nói rõ tập dev100 và thiết bị. Phát một câu Qwen tốt hơn và một câu Zipformer tốt hơn, hiện ba transcript cùng reference. Giải thích khác cách viết số và một lỗi nhận âm. Kết thúc bằng quyết định thử Zipformer ONNX INT8 trên Pi trước, giữ Qwen trên Colab làm đối chiếu.

Đây là ứng viên cho bước đo Pi, chưa phải cấu hình kính đã chốt. [Model card Zipformer](https://huggingface.co/hynt/Zipformer-30M-RNNT-6000h) liệt kê FLEURS trong dữ liệu huấn luyện; kết quả này chưa chứng minh khả năng tổng quát trên môi trường mới. Bảng self dev20 đã hoàn tất riêng ở phần dưới. Cả ba còn lỗi làm sai nội dung trong các mẫu đã nghe; WER trung bình thấp nhất không đồng nghĩa phụ đề đã đạt yêu cầu sử dụng. Giữ test đóng; chưa cần fine-tune hoặc thêm model trước khi bổ sung dữ liệu thực tế và số đo Pi.

## Self dev20 — ba model đã chạy ngày 13/10

Run Qwen `self_dev20_qwen_v1` hoàn tất 20/20 trên A100-SXM4-40GB bfloat16; hai baseline CPU được dùng lại nguyên vẹn. Cùng 20 WAV/nhãn đã nghe xác nhận, 181 đơn vị reference/607 ký tự; kiểm tra input/code/nhãn/hash và JiWER độc lập đều đạt. [Bảng tổng hợp](results/self_dev20/summary.csv), [đối chiếu từng câu](results/self_dev20/comparison.csv), nguồn/hash tại [source.json](results/self_dev20/source.json). Tách khỏi FLEURS và bộ bốn đối chiếu.

| Model/runtime | WER_ws | CER | Hoàn tất |
|---|---:|---:|---:|
| Whisper-base, CPU laptop | 27,6243% | 17,7924% | 20/20 |
| Zipformer ONNX INT8, CPU laptop | 0,5525% | 0,1647% | 20/20 |
| Qwen3-ASR-0.6B Transformers, A100 | 1,1050% | 1,3180% | 20/20 |

Qwen chỉ sai [câu 20](../../data/self_recorded/dev/self_20.wav): reference “Kết quả trên máy tính chưa phải kết quả trên kính.”, prediction “cách quả trên máy tính chưa phải cách quả trên kính”. Hai lần “kết” thành “cách” tạo 2 lỗi đơn vị và 8 lỗi ký tự; 19 câu còn lại khớp sau chuẩn hóa. Zipformer sai “gốc/góc” câu 14. Nhận xét này dựa trên text và nhãn đã xác nhận; người trình bày cần nghe thêm câu 20 trước khi gọi đây là phân tích bằng nghe. Ô nghe lấy top 3 WER Qwen nên hai câu WER 0 cũng xuất hiện khi chỉ một câu lỗi; chúng không phải ba lỗi khác nhau.

Gói Zipformer dùng token chữ hoa; Whisper/Qwen giữ cách viết model sinh ra, runner không ép kiểu chữ. Qwen self20 viết thường nhưng FLEURS trước có chữ hoa; không kết luận mọi output Qwen đều viết thường. Scorer dùng lower/NFC trên cả reference/prediction nên chữ hoa/thường không thêm WER/CER. Giữ output gốc; chưa cần thêm phần mềm phục hồi chữ hoa/dấu câu cho nghiên cứu này.

Bộ nhỏ một người đọc, điện thoại cách miệng khoảng 30 cm, 2 câu phòng ngủ/18 câu cà phê. Chênh WER Zipformer/Qwen trên self20 là một lỗi đơn vị, chưa đủ kết luận hơn kém tổng quát. Zipformer vẫn là ứng viên thực tế để đo Pi; chưa cần training. Phần chạy/chấm B01–B03 đã xong, còn tập demo/nghe thêm lỗi và B04 đo Pi; chưa mở test, chưa chứng minh chạy trên kính.

[^1]: JiWER là thư viện Python để tính WER và CER từ reference và prediction
