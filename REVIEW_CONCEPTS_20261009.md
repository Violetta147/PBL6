# Ghi chú ASR để làm đề tài lean

Bản rút gọn — 09/10/2026. Đây là tài liệu học để tra khi thực hành, không phải danh sách chức năng phải xây. Phạm vi thực hiện theo [đặc tả lean](SPEC_ASR_PI4_RESEARCH_20261009.md) và [kế hoạch 7 buổi](PLAN_DEMO_STT_7_BUOI.md).

## 1. STT, ASR và baseline

ASR/STT ở đây cùng chỉ nhận dạng tiếng nói thành chữ. Thu micro, VAD, chia đoạn và hiện chữ là các phần xung quanh model. SLR nhận dạng ngôn ngữ ký hiệu là bài toán riêng; không phải triển khai SLR để đánh giá STT.

Baseline là phương án tham chiếu có cấu hình rõ, không mặc định đồng nghĩa “không training”. Trong đề tài này, chủ động chọn baseline pretrained và giữ trọng số. PhoWhisper/PhoASR được tác giả fine-tune không có nghĩa người dùng checkpoint phải fine-tune lại. Baseline đáp ứng mục tiêu có thể là lựa chọn cuối.

## 2. Không training vẫn cần dev/test

Dev dùng thử/chọn checkpoint, frontend đúng, decoding hoặc VAD. Test dùng báo cáo sau khi chốt. Giữ nguyên trọng số vẫn có thể chọn quá mức theo test nếu dùng lỗi test để sửa cấu hình.

Không cần tự chia train/validation/test theo tỷ lệ cố định khi nguồn có split sẵn. Dùng một ít train làm pilot là được; không phải chạy training loop. Với tự thu, chia trước theo người/phiên, giữ các đoạn cùng nguồn và bản biến đổi ở cùng split. Nếu chỉ có một người nói, cần ghi giới hạn và tách phiên, không khẳng định đã kiểm tra giọng mới.

Test chưa dùng để phát triển của nhóm không bảo đảm chưa xuất hiện trong dữ liệu pretrained. C1 có liệt kê FLEURS trong nguồn huấn luyện. Vì vậy bảng public benchmark và audio tự thu cần được trình bày với đúng giới hạn.

## 3. Hiểu âm thanh đủ để không làm sai input

Sample rate là số mẫu mỗi giây; channel là số kênh tín hiệu, không phải số người nói. Stereo có thể trộn về mono sau khi kiểm tra kênh/ngược pha. Resample phải biến đổi tín hiệu, không chỉ sửa nhãn sample rate.

Micro/ADC lấy mẫu tín hiệu âm thanh; PCM 16 bit có dấu thường dùng mã từ −32.768 đến 32.767. Các mã này không phải dB. Float32 không tự giới hạn waveform trong [−1, 1]; đó là quy ước quy đổi biên độ mà nhiều processor dùng.

dBFS tham chiếu full scale; dB SPL tham chiếu áp suất vật lý. Không suy mức dB SPL chính xác từ WAV khi micro chưa hiệu chuẩn. Giảm biên độ một nửa khoảng −6 dB, giảm công suất một nửa khoảng −3 dB. Phần này giúp hiểu mức thu; đề tài không bắt buộc đo âm học chuyên nghiệp.

## 4. Frontend và tokenizer thuộc checkpoint

Dùng processor/tokenizer/runtime đi kèm model. Whisper dùng log-Mel; không thay bằng MFCC, F0, Z-score, PCA hoặc đặc trưng tự nghĩ ra. Số chiều Mel và cấu hình frontend có thể khác giữa các phiên bản.

Tokenizer chuyển token của model thành text. Không cần huấn luyện tokenizer mới. Transcript chuẩn chỉ đi vào scorer, không đưa làm prompt hoặc input phụ cho inference test. [Frontend Whisper](https://github.com/openai/whisper/blob/main/whisper/audio.py).

## 5. VAD và phụ đề trực tiếp

VAD tìm vùng có lời nói, không tạo transcript, tách người nói hoặc căn chỉnh từng từ. Dùng VAD có sẵn là đủ cho phần STT. Bài tập lớp yêu cầu tự viết VAD năng lượng/F0 được làm trong project bài tập riêng.

Whisper chạy theo cửa sổ; ngữ cảnh khoảng 30 giây không bắt buộc chờ 30 giây mới hiện chữ. Giải mã lại cửa sổ tạo partial tăng chi phí và có thể làm queue chậm. Đề tài lean bắt đầu bằng final sau khi đóng đoạn; partial không bắt buộc.

Model offline kết hợp VAD có thể tạo trải nghiệm theo từng lượt, nhưng không vì vậy thành model streaming nguyên sinh. Một file có RTF < 1 cũng chưa chứng minh hệ liên tục theo kịp. Cần thử micro/replay đúng tốc độ thực và quan sát mất/lặp/chậm chữ.

## 6. WER/CER và cách đọc bảng

WER theo khoảng trắng của tiếng Việt thường gần mức âm tiết, nên ghi `WER_ws`. Công thức là tổng thay thế/xóa/chèn chia tổng đơn vị reference. Không dùng trung bình từng câu thay cho điểm tổng mà không ghi rõ. WER có thể vượt 100% khi chèn nhiều chữ.

CER trong kế hoạch dùng Unicode code point sau NFC, bỏ khoảng trắng. Giữ dấu tiếng Việt: “ma” và “má” khác nhau. Chuẩn hóa phục vụ scoring khác với sửa nội dung để hiển thị. Quy tắc số phải cố định; phiên bản cơ bản còn phân biệt “25” với “hai mươi lăm”.

Với nhãn rỗng, báo chữ sai xuất hiện mỗi phút thay vì chia cho 0. Inference không hoàn tất phải giữ status và tính coverage; không bỏ mẫu thất bại để làm đẹp WER. [JiWER](https://jitsi.github.io/jiwer/), [Evaluation ASR](https://huggingface.co/learn/audio-course/chapter5/evaluation).

## 7. Đánh giá model và đánh giá hệ thống

Output trên WAV phản ánh recognizer với input đó. Output từ micro còn chịu mức thu, VAD, chia đoạn và chờ xử lý. Lỗi chữ đầu câu có thể do VAD, lặp có thể do overlap, mất dấu có thể do font; nghe audio và xem log trước khi quy hết cho model.

Thời gian nạp, thời gian inference và khoảng chờ phụ đề khác nhau. CLI nạp model mỗi lần có wall time gồm startup; không gọi là warm inference. Colab GPU và Pi CPU là môi trường khác nhau; có thể so chất lượng trên cùng dữ liệu, còn tốc độ phải ghi đúng thiết bị/backend.

Giữ bảng theo corpus/split/backend, số mẫu, WER/CER và trạng thái. Chấm cùng audio bằng cùng scorer. Số tác giả công bố chỉ là nguồn tổng quan, không điền vào bảng thực nghiệm của nhóm.

## 8. Học thêm khi cần

Ưu tiên waveform/resampling → processor/inference → evaluation → VAD và đo Pi từ [khóa Audio Hugging Face](https://huggingface.co/learn/audio-course/chapter0/introduction). CTC/RNN-T/encoder–decoder giúp hiểu các ứng viên, nhưng không phải tự cài các kiến trúc. ACF/AMDF/F0 và nhãn phoneme phục vụ bài tập riêng; MAE/RMSE của F0 không so với WER/CER như cùng bài toán.

Năm stage/35 bước ML dùng để tham khảo tư duy nghiên cứu. SMOTE, PCA, feature importance, regularization và pipeline sklearn không phải việc bắt buộc cho inference pretrained. Thử một thay đổi khi kết quả chỉ ra vấn đề, dừng khi đã trả lời mục tiêu.

Bản rà soát Concepts chi tiết trước đây được giữ trong Git, ví dụ `git show c566918:REVIEW_CONCEPTS_20261009.md`. Các file export nguồn vẫn giữ nguyên. Hai hình nội bộ trong export chưa được xác minh riêng; ghi chú này không phụ thuộc chúng.
