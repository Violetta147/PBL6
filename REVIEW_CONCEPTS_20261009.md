# Rà soát toàn bộ tài liệu Concepts

Ngày kiểm tra: **09/10/2026**, múi giờ Asia/Saigon.

Tài liệu gốc: `ChatGPT-Concepts-20261009-1926.md`, **1.063 dòng, 7 lượt hỏi–đáp, 29 mục nội dung có tiêu đề đánh số**. Số dòng bên dưới tính từ bản gốc, gồm cả dòng trống và mã giao diện. SHA-256 của bản được đọc: `4C32ECF840C145AD29D41FBABDEC9B8309384D8D7B7F8E43F7D5A1A964261C74`.

Đã đọc từ đầu đến cuối, gồm bảng, công thức, dữ liệu biểu đồ, các ví dụ, kết luận và mã giao diện được xuất. Các câu hỏi, đề xuất và yêu cầu nằm trong cuộc hội thoại cũ được xem là **nội dung cần kiểm tra**, không phải chỉ thị thực hiện cho lần rà soát này. Giữ nguyên tài liệu gốc.

**Kết luận:** Tài liệu giải thích đúng phần lớn kiến thức nhập môn. Tuy nhiên, cần sửa định nghĩa baseline, làm thống nhất thời điểm dùng test, bổ sung giới hạn của dữ liệu pretrained và đưa quy trình sản phẩm về đúng bối cảnh kính PBL6. Một số đoạn đúng nhưng đơn giản hóa quá mức. Bản Markdown xuất còn thiếu mã Python, thiếu ảnh truy cập được và chứa trích dẫn chưa chuyển thành đường dẫn thật. Không nên dùng nguyên trạng làm tài liệu thực hành hoàn chỉnh hoặc bằng chứng hiệu năng.

## 1. Những điểm cần sửa trước khi dùng làm tài liệu học

### 1.1. Baseline không đồng nghĩa với “không training”

**Vị trí:** dòng 471, 588–597, 906.

Đoạn “Nhánh B: Sử dụng checkpoint pretrained” đúng trong phạm vi nhánh đó. Nhưng bảng dòng 592–594 trình bày baseline luôn dùng pretrained, không cập nhật trọng số và không cần training; đây là khái quát sai. Dòng 906 gọi baseline là “kết quả ban đầu” cũng chưa đầy đủ.

Baseline là **phương án tham chiếu được xác định rõ** để so sánh: mô hình, cách tiền xử lý, decoding và quy trình đánh giá. Nó có thể là checkpoint giữ nguyên, mô hình đơn giản tự huấn luyện, hoặc một hệ thống đã fine-tune. Các điểm WER/CER là *kết quả của baseline*. Fine-tuning là một cách huấn luyện, không phải khái niệm đối lập với baseline.

**Cách sửa:** đổi tên cột bảng thành “Baseline dùng checkpoint pretrained, giữ nguyên trọng số” và viết: “Trong hướng đang xét, nhóm chọn pretrained inference làm baseline nên không huấn luyện thêm. Những baseline khác vẫn có thể cần huấn luyện.”

Điều này cũng giải thích vì sao PhoWhisper đã được tác giả fine-tune nhưng nhóm vẫn có thể tải về chạy inference làm baseline của mình.

### 1.2. Phần đầu dễ dẫn đến mở test quá sớm; phần cuối đã giải thích đúng

**Vị trí:** dòng 477–530, 553, 608–630 so với dòng 740 và 1028–1033.

Phần đầu đưa “Test Dataset” vào sơ đồ baseline, rồi đề xuất phân tích lỗi và chọn hướng cải tiến. Nếu nhóm nhìn lỗi test để quyết định cách khử ồn, chia chunk, sửa chữ hay chọn checkpoint thì test đã tham gia phát triển hệ thống. Giữ nguyên trọng số không ngăn được rò rỉ này.

Phần cuối đã nói đúng: lựa chọn trên validation; chỉ so sánh baseline và phương án cuối trên cùng test sau khi chốt. Vì vậy đây là **sự không nhất quán trong cách hướng dẫn**, không phải toàn bộ tài liệu đều hiểu sai test. Nên sửa các sơ đồ và đoạn trước theo cách giải thích cuối. Nguyên tắc giữ test riêng để tránh lựa chọn theo test được trình bày trong [tài liệu cross-validation của scikit-learn](https://scikit-learn.org/stable/modules/cross_validation.html).

**Quy trình thống nhất:** pilot/dev → chạy baseline trên validation → phân tích lỗi validation → lựa chọn model/preprocessing/decoding → khóa cấu hình và chuẩn hóa metric → chạy các phương án đã định trước trên test → báo kết quả cuối.

Có thể đánh giá một checkpoint cố định trực tiếp trên test nếu chỉ làm một nghiên cứu mô tả đã định trước, không dùng kết quả đó để lựa chọn hay sửa hệ thống. Test không phải loại dữ liệu “chỉ được đọc đúng một lần” trong mọi hoàn cảnh; vấn đề là kết quả có được dùng để điều chỉnh hay không. Riêng đặc tả PBL6 hiện có quy định một đợt đánh giá chính sau khi khóa cấu hình, nên nhóm theo quy tắc đó.

Sau báo cáo cuối vẫn được phân tích lỗi test để mô tả giới hạn. Nếu dùng những lỗi ấy để làm phiên bản mới thì phải thừa nhận đã khai thác test; cần bộ đánh giá mới/giữ kín khác cho kết luận xác nhận mới. Không so WER baseline trên validation với WER phiên bản cuối trên test rồi gọi chênh lệch đó là cải thiện.

### 1.3. “Dữ liệu mô hình chưa từng nhìn thấy” chưa được chứng minh

**Vị trí:** dòng 477; liên quan các dòng 948 và 1010.

Nhóm giữ riêng test không chứng minh dữ liệu đó chưa xuất hiện trong quá trình pretrained của nhà phát hành. Với dữ liệu công khai, có thể có trùng dữ liệu nguồn, người nói hoặc nội dung. [Whisper model card](https://github.com/openai/whisper/blob/main/model-card.md) mô tả nguồn huấn luyện từ Internet, nhưng không cung cấp ở đây một danh mục từng mẫu để kiểm tra toàn bộ đối chiếu.

**Cách sửa:** “Dữ liệu chưa được nhóm dùng để huấn luyện, chọn checkpoint hoặc điều chỉnh pipeline; việc trùng với dữ liệu pretrained cần kiểm tra theo thông tin nhà phát hành và có thể chưa xác minh đầy đủ.” Tự thu mới có thể giảm nguy cơ trùng bản ghi, nhưng cũng không tự chứng minh người nói/nội dung hoàn toàn mới với mô hình.

### 1.4. Ví dụ ứng dụng tải file chưa đủ cho sản phẩm PBL6

**Vị trí:** dòng 812, 827, 880; đối chiếu `SPEC_STT_SMART_GLASSES.md`, mục 1–3, 8 và 8.1.

Xây dựng ứng dụng tải file là ví dụ hợp lệ về STT không training. Tuy nhiên, dự án này đặt mục tiêu thu lời nói hội thoại, xử lý trên điện thoại và hiển thị phụ đề gần thời gian thực trên kính. Demo tải file chỉ là bước offline ban đầu; chưa hoàn thành mục tiêu chính.

Phải bổ sung: thu micro liên tục, đệm âm thanh, VAD/chunk/overlap, xử lý partial/final, chống chữ lặp, truyền và hiển thị trên kính, phục hồi kết nối, đo trễ đầu/cuối/hiển thị, độ ổn định, RAM/pin và lỗi xuất chữ khi im lặng. Nếu dùng laptop hoặc màn hình giả lập thì ghi rõ mức triển khai.

[Whisper README](https://github.com/openai/whisper/blob/main/README.md) mô tả xử lý file bằng cửa sổ 30 giây. Điều này không có nghĩa mọi ứng dụng phải đợi đủ 30 giây mới chạy; ứng dụng có thể đưa đoạn ngắn hơn và dùng padding theo runtime. Nhưng chất lượng, chi phí chạy lặp và độ trễ của cách đó phải đo. Model card cũng không tuyên bố Whisper cung cấp live transcription sẵn dùng.

### 1.5. Thiếu điều kiện giấy phép khi bàn về sản phẩm

**Vị trí:** dòng 795, 835–842, 894.

Mô tả VietAI wav2vec2/CTC và mô hình ngôn ngữ n-gram là đúng, nhưng tài liệu không nhắc điều kiện dùng trọng số. [VietAI ASR README](https://github.com/vietai/ASR) ghi **CC BY-NC 4.0, chỉ dùng phi thương mại**, và cung cấp mô hình ngôn ngữ 4-gram. Vì thế không thể mặc định mọi checkpoint trong danh sách đều dùng cho sản phẩm thương mại như nhau.

[Whisper README](https://github.com/openai/whisper/blob/main/README.md) ghi MIT cho mã và trọng số; [model card PhoWhisper-small](https://huggingface.co/vinai/PhoWhisper-small) hiển thị BSD-3-Clause. Đây là thông tin của nguồn được kiểm tra ngày 09/10/2026; khi chọn một checkpoint hoặc bản chuyển đổi cụ thể, vẫn cần lưu đúng model ID, revision và giấy phép đi kèm. Rà soát này ghi nhận điều kiện kỹ thuật từ nhà phát hành, không thay thế tư vấn pháp lý.

## 2. Rà từng phần theo thứ tự tài liệu

Nhãn “Đúng” là đúng trong phạm vi được nói tới; “Cần làm rõ” là thiếu điều kiện hoặc dễ gây hiểu sai; “Cần sửa” là phát biểu khái quát sai hoặc quy trình chưa nhất quán; “Chưa kiểm chứng” là thiếu bằng chứng truy cập được. Không quy đổi những nhãn này thành phần trăm chất lượng.

### 2.1. Channel, Mono, Stereo — dòng 19–155

| Mục | Vị trí | Đánh giá và điều chỉnh |
|---|---|---|
| 1. Channel | 25–60 | Đúng về luồng tín hiệu theo kênh. Từ “độc lập” nên hiểu là được lưu/xử lý riêng, không phải độc lập thống kê: hai kênh có thể giống hệt hoặc tương quan. Channel tồn tại cả trong luồng thu trực tiếp, không chỉ trong file. Các dạng sóng sin trong mã được ghi rõ là minh họa. |
| 2. Mono và Stereo | 64–72 | Mono một kênh; stereo hai kênh trái/phải: đúng. Stereo có thể tạo không gian nhưng không đảm bảo: hai kênh giống nhau là dual mono. “Stereo không đồng nghĩa hai người nói” là lưu ý đúng. Bảng ứng dụng là ví dụ, không phải hạn chế dùng mono/stereo. |
| 3. Ảnh hưởng tới STT | 76–127 | Đúng với model nhận mono. Tách kênh có thể giúp khi mỗi kênh thu một nguồn ưu thế; không đảm bảo mỗi micro chỉ thu đúng một người vì có âm lọt và tiếng chồng. Gắn người nói theo kênh không đồng nghĩa diarization tổng quát. Ghép kết quả cần mốc thời gian chung. |
| 4. Stereo → Mono | 132–138 | Công thức trung bình hai kênh đúng cho cách trộn trọng số bằng nhau. Đã cảnh báo mất tách người và triệt tiêu pha: đúng. Lệch pha không luôn triệt tiêu hoàn toàn; đối pha và cùng biên độ mới cho ví dụ triệt tiêu hoàn toàn. Có thể chọn kênh tốt hơn hoặc xử lý riêng thay vì trộn. |
| 5. Python | 140–155 | 16.000 Hz × 5 s = 80.000 audio frame; mono `(80000,)`, stereo `(80000, 2)` đúng theo cách đọc mặc định của soundfile. Bản xuất thiếu toàn bộ mã kiểm tra và chuyển mono. Không có chương trình để xác minh chạy. |

Dung lượng **payload PCM** bằng `duration × sample_rate × channels × bytes_per_sample`, nên hai kênh gấp đôi một kênh khi các yếu tố còn lại bằng nhau. Tổng dung lượng file có header/metadata nên không nhất thiết đúng gấp đôi từng byte; với codec nén, không được áp dụng kết luận này máy móc.

Theo [soundfile documentation](https://python-soundfile.readthedocs.io/en/latest/), `always_2d=True` trả cả mono thành `(frames, 1)`. Vì thế shape trong bảng không phải quy luật của mọi thư viện. Mono conversion không đổi sample rate; resampling là phép riêng. Khi bổ sung mã, cần ghi rõ trục kênh và dùng kiểu số phù hợp để tránh tràn khi cộng số nguyên. Ví dụ hai kênh `L=x`, `R=-x` có trung bình bằng 0 giải thích trực tiếp cảnh báo pha.

### 2.2. Transcript Tokenization — dòng 166–346

| Mục | Vị trí | Đánh giá và điều chỉnh |
|---|---|---|
| 1. Transcript thành token ID | 166–232 | Đúng với huấn luyện STT có transcript. Chuỗi `xin chào` gồm 8 ký tự nếu dạng NFC như ví dụ; 8 ID giả định tương ứng hợp lý. Ví dụ character-level và ID được ghi rõ minh họa, không phải tokenizer Whisper. Câu mô tả loss cần nói chính xác hơn, xem dưới bảng. |
| 2. Có bắt buộc không? | 238–251 | Đúng: nhãn cần biểu diễn phù hợp và có thể do processor/tokenizer thực hiện. Inference thường không nhận ground-truth transcript. Bảng CTC, wav2vec2 và Whisper phù hợp. API cũng xử lý token nội bộ; “không tự tokenization” không có nghĩa hệ thống không có token. |
| 3. Tokenization khác normalization | 253–286 | Phân biệt đúng. Lowercase/bỏ dấu câu là chính sách tùy mô hình, không bắt buộc; tài liệu đã nói điều này. Giữ dấu thanh tiếng Việt là phù hợp. Ví dụ `xin | ch | ào` không phải kết quả tokenizer thực tế. Tách từ tiếng Việt khác tokenization của model là đúng. |
| 4. Vị trí trong STT | 288–346 | Sơ đồ đúng ở mức nhập môn cho huấn luyện có nhãn. Cần làm rõ nhánh audio và nhánh target gặp nhau khi tính loss, không phải đưa transcript chuẩn vào inference. Fine-tune Whisper dùng tokenizer tương ứng là đúng. Không bắt buộc xây vocabulary mới nếu CTC đã có bộ token phù hợp. |

**Hai bổ sung để tránh nhầm:**

- Loss huấn luyện dùng logits/xác suất và target. Không phải lấy chuỗi ID đã `argmax`/decode rồi so trực tiếp để cập nhật trọng số. Whisper dùng mục tiêu seq2seq; CTC xử lý các đường căn chỉnh qua thời gian, blank và target length. Hai cách không yêu cầu mỗi audio frame khớp một ký tự.
- Tokenizer Whisper có các token điều khiển cho ngôn ngữ/tác vụ và cấu trúc chuỗi. Khi fine-tune phải dùng đúng processor, target formatting và mask padding của cách triển khai. Xem [mã tokenizer Whisper](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py) và [hướng dẫn fine-tuning ASR](https://huggingface.co/learn/audio-course/en/chapter5/fine-tuning).

Cần giữ riêng **token dùng huấn luyện** với **đơn vị dùng tính metric**. Chẳng hạn, mô hình có thể sinh subword nhưng WER vẫn tính trên văn bản đã decode và chia theo quy tắc đánh giá; không tính WER bằng cách so trực tiếp ID subword của Whisper.

Đối với inference có đánh giá, không đưa transcript chuẩn vào model nhưng vẫn phải có transcript chuẩn để tính WER/CER ở bước sau. Prompt ngữ cảnh tùy chọn cũng không được lấy từ đáp án test.

### 2.3. Feature Normalization — dòng 356–459

| Mục | Vị trí | Đánh giá và điều chỉnh |
|---|---|---|
| 1. Vị trí trong pipeline | 356–394 | Đúng với pipeline trích đặc trưng trước; tài liệu đã nêu có model nhận waveform. Resample/mono/xử lý im lặng là lựa chọn theo dữ liệu và model, không phải ba bước buộc làm cho mọi mẫu. |
| 2. Ví dụ Z-score/CMVN | 398–420 | Công thức và số minh họa đúng với độ lệch chuẩn tổng thể (`ddof=0`). CMVN là chuẩn hóa mean/variance của đặc trưng cepstral; Z-score trên một chuỗi là minh họa cơ chế, không đủ mô tả toàn bộ cấu hình CMVN. |
| 3. Lý do chuẩn hóa | 424–431 | Đúng khi dùng “có thể giảm một phần”. Không đảm bảo khử ồn, phục hồi phần bị clip hoặc phục hồi thông tin mất do micro xa. Ảnh hưởng mức âm lên MFCC/log-Mel không đồng đều trên mọi hệ số. |
| 4. Có bắt buộc không? | 435–444 | Hướng dẫn theo processor của wav2vec2 và log-Mel của Whisper đúng. Bảng HMM-GMM cần mềm hơn: có cấu hình chỉ chuẩn hóa mean; không phải mọi recipe đều chia variance. “CNN/LSTM thường nên thử” là gợi ý thí nghiệm, không phải đảm bảo cải thiện. |
| 5. Python và chống rò rỉ | 446–459 | Đúng khi phân biệt thống kê toàn train với chuẩn hóa từng đoạn. Nhưng thiếu mã Python; chưa chỉ rõ ma trận `(frames, coefficients)` hay ngược lại, trục thống kê, epsilon/std bằng 0 và xử lý padding. Cần bổ sung giới hạn live bên dưới. |

Kiểm tra số bằng phép tính trực tiếp: với `[10, 20, 30, 40, 50]`, mean = 30; variance tổng thể = 200; std = 14,1421356; Z-score làm tròn = `[-1,41; -0,71; 0; 0,71; 1,41]`. Nếu dùng std mẫu (`ddof=1`) thì kết quả khác; không gọi đó là lỗi của bảng khi bảng đang dùng std tổng thể.

[Kaldi](https://kaldi-asr.org/doc/transform.html) mô tả CMVN theo phát ngôn hoặc người nói và cũng nêu không mặc định khuyến nghị phương pháp này cho mọi recipe. [Wav2Vec2FeatureExtractor](https://huggingface.co/docs/transformers/en/model_doc/wav2vec2) có cấu hình `do_normalize`; phải đọc cấu hình checkpoint đã chọn.

Whisper có xử lý log-Mel riêng, không phải Z-score mean 0/std 1. [Mã audio.py](https://github.com/openai/whisper/blob/main/whisper/audio.py) cho thấy log, giới hạn dynamic range và phép biến đổi cố định. Lời khuyên không tự thêm Z-score/Min-Max đúng cho cả inference lẫn fine-tuning thông thường, không chỉ riêng fine-tuning.

Nếu chuẩn hóa từng đoạn test bằng chính waveform của đoạn đó theo thuật toán inference cố định, điều này không tự động là rò rỉ huấn luyện. Nó khác việc dùng toàn bộ test để fit một scaler rồi chọn pipeline. Với live, dùng thống kê của cả câu đã hoàn tất có thể cần mẫu tương lai; nhóm phải thiết kế theo chunk/thống kê có sẵn, tính cả thời gian đợi và chấp nhận việc phân bố có thể đổi theo chunk. Epsilon tránh chia 0 nhưng không biến im lặng thành lời nói hữu ích.

### 2.4. Có baseline rồi làm gì? — dòng 471–635

| Mục | Vị trí | Đánh giá và điều chỉnh |
|---|---|---|
| 1. Vai trò baseline | 477–530 | Đúng rằng chạy model rồi so với ground truth để có mốc WER/CER. Cần sửa “chưa từng nhìn thấy” và sơ đồ test nếu còn phát triển; xem mục 1.2–1.3. Ví dụ bỏ `rất` có WER theo khoảng trắng = 20%, đúng. |
| 2. Ba hướng tiếp theo | 534–584 | Ba hướng đánh giá/tối ưu inference, fine-tune, phát triển ứng dụng đều hợp lệ. Chúng có thể kết hợp; không phải ba nhánh loại trừ nhau. Fine-tune không đảm bảo cải thiện. So sánh trên cùng test chỉ có ý nghĩa sau khi chốt trên validation. |
| 3. Baseline và fine-tuning | 590–599 | Bảng cần sửa phạm vi vì baseline không luôn pretrained/no-training. Lời nhắc giữ test riêng và không liên tục chỉnh theo test đúng. |
| 4. Trình tự đề tài | 603–635 | Cơ bản đúng. Phải gắn bước phân tích lỗi phát triển với validation. Không fine-tune thì không bắt buộc dành một tập để cập nhật trọng số; vẫn cần dev/validation và test nếu có lựa chọn. Các phát biểu về hoàn thành học phần phụ thuộc yêu cầu giảng viên. |

Ví dụ “Hôm nay trời rất đẹp” → “Hôm nay trời đẹp”: bỏ một token trên năm token khoảng trắng, `D=1`, `S=I=0`, nên `WER=1/5=20%`. Trong tiếng Việt, đơn vị này thường là âm tiết; ví dụ cụ thể có các đơn vị một âm tiết không thể chứng minh khoảng trắng luôn tách từ vựng tiếng Việt. Khi viết báo cáo PBL6, gọi rõ **WER theo khoảng trắng**; cần quy tắc chuẩn hóa và micro/macro thống nhất. Công thức S/I/D được giải thích trong [Hugging Face ASR evaluation](https://huggingface.co/learn/audio-course/en/chapter5/evaluation).

“Phân tích lỗi” phải phân biệt: lỗi trên validation để cải tiến; lỗi trên test sau đánh giá cuối để mô tả. “Cùng một quy trình” gồm dữ liệu, transcript, normalization, aggregation, model revision, runtime/decode, phần cứng và cách đo thời gian. Các sai khác có chủ đích phải được công bố, không ép mọi kiến trúc khác nhau dùng cùng tokenizer hoặc tham số không tương thích.

### 2.5. Hyperparameter Tuning — dòng 647–742

| Mục | Vị trí | Đánh giá và điều chỉnh |
|---|---|---|
| 1. Baseline cần tuning? | 647–659 | Không bắt buộc tuning là đúng với pretrained inference. Vẫn phải cấu hình và lưu tham số thực tế. Sample rate là yêu cầu tương thích đầu vào; không phải tùy ý tìm 8/16/44,1 kHz rồi khai báo sai cho model. Chunk length là biến thiết kế hệ thống. Batch size cũng có thể là tham số inference, không chỉ training. |
| 2. Khi nào tuning? | 665–692 | Tách giữ trọng số/thay decoding/cập nhật trọng số đúng. Beam 1/3/5 và temperature là ví dụ, không phải bảng kết quả. Thiết lập tiếng Việt là lựa chọn đúng tác vụ, không nhất thiết là một cuộc tìm tham số. “Baseline tối ưu hóa” hợp lệ nếu định nghĩa rõ baseline nào là mốc. |
| 3. Điều chỉnh Stage 6 | 698–742 | Nhánh tối ưu tùy chọn và Final Testing sau validation đúng. Cần ghi 6.1–6.2 trên validation nếu còn tối ưu. Không thể kiểm tra sơ đồ ảnh gốc hoặc xác nhận bước 6.3 bị bỏ có chủ đích. Số Stage trong hội thoại không trùng hệ đánh số Stage 1–5 của đặc tả hiện có. |

**Bổ sung quan trọng:** “mặc định” phụ thuộc runtime, phiên bản và cách gọi API/CLI. Phải lưu language, task, beam, temperature/fallback, VAD, chunk/overlap, dtype/quantization và các tùy chọn ngữ cảnh thực dùng. Không mặc định beam size = 1 của ví dụ cuối là default của mọi thư viện. Beam lớn hơn không bảo đảm WER giảm đơn điệu và thường tăng tính toán.

Trong [Whisper transcribe.py](https://github.com/openai/whisper/blob/main/whisper/transcribe.py), nhánh fallback temperature > 0 loại `beam_size`/`patience`; temperature = 0 loại `best_of`. Vì vậy không nên grid-search mọi tổ hợp như các nút độc lập mà bỏ qua semantics của runtime. Chọn cấu hình theo cả chất lượng và giới hạn trễ/tài nguyên của kính, không chỉ theo WER nhỏ nhất.

### 2.6. Dùng model có sẵn để phát triển sản phẩm — dòng 759–896

| Mục | Vị trí | Đánh giá và điều chỉnh |
|---|---|---|
| 1. Danh sách model | 775–800 | Whisper đa ngôn ngữ, PhoWhisper 844 giờ, VietAI wav2vec2/CTC + n-gram đều có nguồn gốc xác nhận. Thiếu model ID/revision, license và hạn chế triển khai. Đây là danh sách ứng viên, không phải ranking chứng minh model nào tốt nhất cho PBL6. |
| 2. Quy trình không training | 804–844 | Đúng rằng có thể bỏ tự thiết kế tokenizer/kiến trúc/training loop. Nhưng phải dùng processor đi kèm; bỏ tự xây không có nghĩa bỏ tiền xử lý. Ví dụ upload file chưa bao quát live/kính. Chọn checkpoint trên validation theo tiêu chí sản phẩm đã định. |
| 3. Trọng tâm đề tài | 848–866 | Các việc API/bất đồng bộ/triển khai/đo hiệu suất phù hợp. Tỷ lệ 20/30/25/25 cộng thành 100% và được ghi rõ tham khảo, không phải dữ liệu thực nghiệm hay yêu cầu bắt buộc. Với kính cần thêm thu live, truyền chữ, pin và khả năng đọc. |
| 4. Rủi ro và MVP | 870–896 | Benchmark không bảo đảm hiệu năng đích: đúng. Tìm được bài 2026 phù hợp mô tả; xem mục 3. 30–50 file phù hợp pilot/smoke test, chưa đủ tự chứng minh bao phủ tiếng Việt/giọng/ồn và khả năng dùng kính. Không fine-tune là lựa chọn khả thi, nhưng phải đáp ứng yêu cầu học phần và nguyên mẫu. |

Whisper cần bản **đa ngôn ngữ** cho tiếng Việt; các checkpoint `.en` không phải lựa chọn tiếng Việt. Tên `large` chưa đủ xác định revision; danh sách Tiny–Large trong bản gốc cũng không phải danh sách đầy đủ mọi phiên bản. [PhoWhisper paper](https://arxiv.org/abs/2406.02555) và [model card](https://huggingface.co/vinai/PhoWhisper-small) xác nhận năm phiên bản fine-tune trên 844 giờ nhiều giọng Việt. Thông tin này không tự chứng minh độ chính xác live của nhóm.

VietAI nên được nhận diện bằng checkpoint cụ thể, ví dụ `nguyenvulebinh/wav2vec2-base-vietnamese-250h`. Không có số đo trong tài liệu để kết luận nó nhanh hơn hay tốt hơn Whisper trên điện thoại của nhóm. CTC tự nó cũng không bảo đảm model hỗ trợ streaming đúng nghĩa: phải kiểm tra context và implementation.

30–50 file không nên vừa dùng chọn checkpoint, vừa làm test cuối. Pilot để kiểm tra pipeline; sau đó giữ một tập độc lập có transcript kiểm chéo, nhiều người/điều kiện theo khả năng nhóm. WER/CER thấp và RTF < 1 chưa đủ bảo đảm phụ đề đến đúng lúc: thời gian chờ chunk, VAD kết thúc câu, queue và truyền/hiển thị cũng góp vào trễ. Đây là suy luận hệ thống, chưa phải số đo của dự án.

### 2.7. Baseline đánh giá trên validation hay test? — dòng 906–1058

| Mục | Vị trí | Đánh giá và điều chỉnh |
|---|---|---|
| 1. Train/validation/test | 912–955 | Vai trò ba tập đúng. 700/150/150 cộng 1.000 và 70/15/15 đúng, đã ghi là ví dụ. Chia theo người nói khi đánh giá người chưa gặp là đúng; phải kiểm tra thêm bản ghi/câu trùng, phiên và điều kiện. Không buộc tỷ lệ này cho mọi dataset. |
| 2. Quy trình checkpoint | 959–1019 | Dùng val, thử beam rồi khóa, test cuối đúng. 18/16/17/19% đều được gắn giả định, không phải kết quả thật. WER test có thể cao/thấp hơn val đúng. Chọn beam 3 là hợp lý theo WER ví dụ, nhưng PBL6 cần tiêu chí trễ/RAM bổ sung. |
| 3. Nên dùng tập nào? | 1028–1033 | Cốt lõi đúng, đặc biệt so baseline và cải tiến trên cùng test sau khi chốt. “So sánh nhiều checkpoint cần val để lựa chọn” đúng khi nhóm chọn model; một benchmark mô tả với danh sách và protocol cố định có thể báo nhiều model trên test mà không chọn theo đó. |
| 4. Câu hỏi kiểm tra | 1040–1058 | Đáp án Validation đúng cho việc tìm beam có WER thấp nhất. Mã radio/checkbox là giao diện xuất, không phải bài kiểm tra đã được chạy trong lần rà soát. Kết luận về vai trò ba tập đúng; nên dùng “validation/dev”, không viết “validate set”. |

Không cần fine-tune vẫn có thể overfit validation khi thử quá nhiều cấu hình; ghi số cấu hình/thử nghiệm và không chọn lặp vô hạn. Không gọi test “chưa sử dụng” chỉ vì không chạy gradient trên nó: các quyết định về chuẩn hóa, từ điển sửa lỗi, prompt, VAD hay cách hiển thị cũng có thể khai thác test.

## 3. Trích dẫn và độ đầy đủ của bản xuất

### 3.1. Bốn trích dẫn chưa xuất thành nguồn có thể bấm

**Vị trí:** dòng 775, 777, 785, 787, 795–796, 872.

Các thẻ `Cite` và biến `turn345531search*.url.uri` là tham chiếu nội bộ của lần chat cũ, không phải URL thực trong Markdown. Dòng “Searched 6 websites” không chứng minh sáu nguồn đã được đối chiếu đúng. Đã kiểm tra lại các nhận định bằng nguồn gốc hiện truy cập được và ghi đường dẫn thật trong báo cáo này.

Riêng câu về nghiên cứu robot năm 2026 có một nguồn phù hợp rất sát mô tả: [Optimizing Vietnamese Speech Recognition Models Through Dataset-Level Audio and Speech Characteristics](https://doi.org/10.1145/3797912), ACM TALLIP, công bố 16/04/2026. Bài có phần đánh giá SIUBOT, so mô hình dùng dữ liệu phù hợp môi trường với các model Việt có sẵn. Như vậy **nội dung khái quát có căn cứ**, không nên kết luận đây là nghiên cứu bịa.

Tuy nhiên, bản xuất không chứa URL đã giải tham chiếu nên chưa chứng minh đây chính xác là nguồn mà chat cũ dùng. Không diễn giải “khác biệt đáng kể” thành “có ý nghĩa thống kê” chỉ từ câu đó. Nghiên cứu trong một môi trường robot cũng không chứng minh nhóm bắt buộc fine-tune hoặc sẽ nhận được cùng mức cải thiện trên kính. Rà soát này dùng bài để xác nhận ví dụ có thật; chưa thẩm định toàn bộ protocol/kết quả bài đó và không lấy số liệu bài làm kết quả PBL6.

### 3.2. Hai ảnh gốc chưa kiểm chứng được

**Vị trí:** dòng 464 và 640.

Ảnh được trỏ bằng URL backend ChatGPT. Đã thử truy cập cả hai qua công cụ web nhưng nhận lỗi, và danh sách file hiện có trong repo không chứa hai ảnh tương ứng. Vì vậy chưa đọc được ảnh để kiểm tra “Nhánh B”, toàn bộ Stage 6, bước 6.3 hoặc tính đúng của sơ đồ cũ. Không suy đoán ảnh đúng/sai từ lời mô tả của chatbot. Những sơ đồ được viết trực tiếp bằng mã trong Markdown đã được đọc về nội dung, nhưng chưa được render tương tác.

### 3.3. Hai phần Python thiếu mã và giao diện chưa chạy

**Vị trí:** dòng 140–151 và 446–450.

Bản xuất có lời dẫn thực hành nhưng không có code fence hay chương trình Python. Chưa xác định mã bị mất khi export hay đã thiếu từ chat gốc. Muốn thành tài liệu thực hành cần bổ sung mã đọc audio/kiểm tra channel/chọn trộn; và mã chuẩn hóa MFCC có shape, axis, epsilon, padding, kiểm tra số hữu hạn. Đây là khuyến nghị nội dung, không phải chức năng được triển khai trong lượt rà soát này.

Các thẻ `box`, `Chart`, `DIL.useState`, `#each`, radio và checkbox không phải cú pháp Markdown thuần. Đã kiểm tra ý nghĩa và dữ liệu viết trong chúng; chưa kiểm chứng khả năng render, layout, state hay hành vi nút bấm. Footer ChatGPT Exporter và metadata là thông tin xuất, không phải bằng chứng khoa học. Không có căn cứ quy lỗi thiếu mã/ảnh cho tác giả hay công cụ cụ thể.

## 4. Bản diễn giải đúng để áp dụng ngay vào PBL6

**Channel:** một luồng mẫu âm thanh theo kênh. Mono có một; stereo có hai trái/phải. Số kênh không phải số người nói. Kiểm tra nội dung trước khi chọn kênh hoặc trộn; chuyển mono không tự resample.

**Transcript:** bản chép chuẩn dùng làm target trong supervised training hoặc reference khi đánh giá. Nếu chỉ inference, model nhận audio, không cần đáp án chuẩn. Khi tính WER/CER vẫn cần reference.

**Tokenization:** chuyển văn bản target thành biểu diễn phù hợp model khi huấn luyện, và decode token dự đoán ra văn bản khi suy luận. Dùng đúng tokenizer/processor checkpoint. Normalization văn bản là quy tắc khác; giữ bản raw, quy định NFC/chữ thường/dấu câu/số và giữ dấu thanh khi đánh giá Việt.

**Feature normalization:** tuân thủ frontend của checkpoint. Không tự áp scaler của bài toán bảng vào log-Mel Whisper. Nếu một bước cần học thống kê trên dataset thì fit trên train; quy tắc chuẩn hóa từng input phải được định trước và khả thi với live.

**Baseline:** một hệ thống tham chiếu có cấu hình và điểm đo cụ thể. Nhóm có thể bắt đầu bằng Whisper tiny/base đa ngôn ngữ theo đặc tả; PhoWhisper là ứng viên so sánh nếu phù hợp tài nguyên. Chưa có số đo để chọn một model thắng cuộc.

**Train/dev/test:** nếu không cập nhật trọng số thì không cần bước training. Dùng pilot/dev để sửa pipeline, validation để chọn model/cấu hình, test độc lập để báo cuối. Nếu fine-tune, train mới tham gia cập nhật trọng số; validation vẫn để chọn và test vẫn để đánh giá cuối.

**Trình tự:** offline với file chuẩn → thu micro live → VAD/chunk và partial/final → so model/runtime trên validation → truyền chữ lên kính/giả lập có nhãn → khóa code/config/metric → đánh giá cuối cả baseline lẫn phương án chọn. Đo CER, WER theo khoảng trắng, trễ chữ đầu/final/kính, ổn định partial, lỗi im lặng, RTF, RAM/pin và các nhóm người/ồn. Báo kết quả cùng số mẫu, phần cứng và giới hạn; không biến số minh họa thành kết quả đo.

## 5. Phạm vi kiểm tra và kết quả xác minh

- Đã phủ **7/7 lượt hỏi–đáp và 29/29 mục có tiêu đề đánh số**, cùng các đoạn mở đầu/kết luận, 2 liên kết ảnh và footer; bảng ở mục 2 là sổ đối chiếu theo thứ tự bản gốc.
- Đã tính trực tiếp: 80.000 frame ở 16 kHz/5 s; Z-score của 5 giá trị đúng với `ddof=0`; WER bỏ `rất` là 20%; split cộng 1.000; phân bổ việc cộng 100%. Không có phép đo ASR thật được xác nhận bởi các phép tính này.
- Đã đối chiếu đặc tả PBL6 hiện có, giấy phép/checkpoint, xử lý audio/tokenizer, quy tắc train/validation/test và bài 2026. Các nguồn web là bản truy cập ngày 09/10/2026, không khẳng định tái tạo nguyên trạng phiên bản web mà chat ngày 24/09 đã đọc.
- **Chưa xác minh:** nội dung 2 ảnh; code Python bị thiếu; giao diện DIL; benchmark inference, fine-tuning hoặc hiệu năng trên phần cứng nhóm. Không chạy training/inference vì tài liệu không có mã hay protocol chạy hoàn chỉnh và yêu cầu lần này là rà soát.
- Thay đổi của lượt này chỉ là báo cáo tài liệu. Không thêm chức năng mã nên không có unit/integration test mới cần chạy; kiểm tra nhất quán văn bản/số liệu và `git diff --check` trước commit. Tài liệu gốc và các file chưa được theo dõi khác của người dùng không thuộc commit báo cáo.

## 6. Nguồn và phương pháp

Nguồn được gắn gần nhận định cần đối chiếu; danh sách này giúp tái kiểm tra:

1. [soundfile documentation](https://python-soundfile.readthedocs.io/en/latest/): shape và trục audio.
2. [Whisper README](https://github.com/openai/whisper/blob/main/README.md), [model card](https://github.com/openai/whisper/blob/main/model-card.md), [audio.py](https://github.com/openai/whisper/blob/main/whisper/audio.py), [tokenizer.py](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py), [transcribe.py](https://github.com/openai/whisper/blob/main/whisper/transcribe.py): nguồn chính thức cho frontend, model, license và decoding.
3. [Wav2Vec2 documentation](https://huggingface.co/docs/transformers/en/model_doc/wav2vec2): processor/normalization; [Kaldi transforms](https://kaldi-asr.org/doc/transform.html): CMVN.
4. [scikit-learn cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html): lựa chọn cấu hình và test leakage.
5. [Hugging Face ASR evaluation](https://huggingface.co/learn/audio-course/en/chapter5/evaluation), [fine-tuning](https://huggingface.co/learn/audio-course/en/chapter5/fine-tuning): metric và quy trình target/training.
6. [PhoWhisper paper](https://arxiv.org/abs/2406.02555), [vinai/PhoWhisper-small](https://huggingface.co/vinai/PhoWhisper-small): 844 giờ, nhiều giọng, checkpoint/license.
7. [VietAI ASR](https://github.com/vietai/ASR): wav2vec2/CTC, 4-gram và điều kiện trọng số phi thương mại.
8. [ACM TALLIP, DOI 10.1145/3797912](https://doi.org/10.1145/3797912): nguồn phù hợp ví dụ SIUBOT năm 2026; không dùng làm bằng chứng hiệu năng PBL6.
9. `SPEC_STT_SMART_GLASSES.md`: tài liệu nội bộ để kiểm tra phạm vi dự án; không phải nguồn độc lập chứng minh hiệu năng.

Phương pháp rà soát sử dụng skill `scientific-critical-thinking`: trích vị trí trước khi đánh giá, phân biệt lỗi thật/thiếu báo cáo/chưa đủ căn cứ và đề xuất sửa cụ thể. Ghi nhận nguồn phương pháp: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065). Đã đối chiếu metadata arXiv ngày 09/10/2026; bản hiện hành v2, sửa ngày 02/09/2026. Nguồn này ghi nhận workflow, không chứng minh các model STT chính xác.
