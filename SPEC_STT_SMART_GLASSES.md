# Đặc tả nghiên cứu: phụ đề lời nói tiếng Việt trên kính thông minh

- **Phiên bản:** 1.0 — 24/09/2026.
- **Đối tượng:** nhóm sinh viên PBL6.
- **Mục tiêu:** học và nghiên cứu một hệ thống speech to text (STT) hỗ trợ người khiếm thính trong hội thoại trực tiếp.
- **Giả định đã xác nhận:** lời nói tiếng Việt; điện thoại thu và xử lý âm thanh; kính nhận và hiển thị phụ đề gần thời gian thực.
- **Phạm vi:** nguyên mẫu nghiên cứu có đo lường, không phải thiết bị hỗ trợ y tế hay sản phẩm thương mại.

## 1. Đọc nhanh trước khi bắt đầu

### 1.1. Bài toán

Một người đối diện nói tiếng Việt. Điện thoại nhận âm thanh từ micro, chuyển lời nói thành chữ và gửi các dòng chữ ngắn đến kính. Người đeo có thể theo dõi nội dung hội thoại mà không phải liên tục nhìn xuống điện thoại. Kính phải cho biết khi nào chữ còn đang thay đổi và khi nào một câu đã được chốt.

STT chỉ chuyển **lời nói** thành chữ. Nhận diện chuông xe, còi, tiếng gọi tên, xác định người nói, dịch ngôn ngữ hay suy đoán cảm xúc là các bài toán khác. Chúng được ghi nhận để nghiên cứu sau; không được báo cáo như năng lực đã có của STT. Phụ đề cho người khiếm thính lý tưởng còn có thông tin người nói và âm thanh quan trọng, theo [W3C WAI](https://www.w3.org/WAI/WCAG21/Understanding/captions-live); vì vậy nhóm phải nêu rõ giới hạn của nguyên mẫu.

### 1.2. Câu hỏi nghiên cứu chính

> Với điện thoại và kính của nhóm, cấu hình STT tiếng Việt nào cho cân bằng tốt nhất giữa lỗi bản chép lời, độ trễ hiển thị, tính ổn định của phụ đề và tài nguyên máy trong hội thoại ngắn có tiếng ồn thực tế?

Câu hỏi phụ: (1) micro điện thoại và micro gắn kính khác nhau thế nào; (2) chia đoạn theo phát hiện giọng nói (VAD) có cải thiện độ trễ và lỗi không; (3) câu nói ở khoảng cách/ồn khác nhau làm hệ thống xuống cấp ra sao; (4) người dùng có đọc kịp và hiểu đúng phụ đề không?

### 1.3. Đầu ra cuối kỳ bắt buộc

1. Nguyên mẫu thu âm → STT → phụ đề trên điện thoại → truyền đến kính hoặc màn hình giả lập kính, có video demo trực tiếp.
2. Bộ dữ liệu đánh giá hội thoại tiếng Việt **tự thu có đồng ý**, bản chép tay, bảng metadata và chia tập cố định; không cần công bố âm thanh gốc.
3. Notebook/báo cáo Stage 1–3; mã tiền xử lý và cấu hình thí nghiệm Stage 4; ít nhất hai baseline/cấu hình so sánh Stage 5.
4. Bảng kết quả trên test giữ kín: lỗi chữ, độ trễ, độ ổn định, tiêu thụ tài nguyên, phân tích lỗi và khoảng tin cậy.
5. Tài liệu cách tái lập: phiên bản thư viện, model, thiết bị, tập dữ liệu, lệnh chạy, cấu hình và giới hạn.

### 1.4. Điều kiện đạt cho bản demo nghiên cứu

Đây là **mục tiêu thử nghiệm ban đầu**, không phải tuyên bố hiệu năng của bất kỳ model nào. Sau pilot, nhóm có thể chỉnh mục tiêu và ghi lý do trước khi mở test.

| Tiêu chí | Mục tiêu pilot | Cách đo |
|---|---:|---|
| Lời nói thành phụ đề cuối | CER ≤ 15% và WER theo khoảng trắng ≤ 30% trên tập hội thoại sạch nội bộ | Micro-aggregate trên test; báo cáo thêm theo người nói/điều kiện |
| Độ trễ câu cuối | p50 ≤ 2,5 giây; p90 ≤ 5 giây | Từ lúc người nói kết thúc câu đến lúc kính hiển thị câu đã chốt |
| Độ trễ chữ đầu | p50 ≤ 2 giây | Từ lúc bắt đầu phát âm đến ký tự đầu tiên hiển thị |
| Chạy liên tục | ≥ 15 phút không treo hoặc mất kết nối không tự phục hồi | 3 phiên thử trên thiết bị thật |
| Hiểu nội dung | ≥ 80% câu hỏi hiểu ý đúng trong bài thử nhỏ | Người tham gia trả lời câu hỏi sau đoạn hội thoại, có/không phụ đề |

Nếu không đạt, vẫn hoàn thành đề tài khi có đo lường đúng, giải thích nguyên nhân và kế hoạch cải thiện. Không dùng các ngưỡng này để khẳng định khả năng sử dụng an toàn ngoài thực tế.

## 2. Phạm vi, người dùng và kiến trúc

### 2.1. Kịch bản sử dụng và ngoài phạm vi

**Kịch bản chính:** hội thoại 1 người nói, tiếng Việt, trong phòng học hoặc nơi tương đối yên tĩnh; câu ngắn và vừa; người đeo chủ động bật/tắt. **Kịch bản mở rộng đánh giá:** quán cà phê/tiếng ồn nền có kiểm soát, nhiều giọng vùng miền, khoảng cách 0,5–2 m, câu có tên riêng và số. **Ngoài phạm vi MVP:** dịch, nhận diện người nói đáng tin cậy, nhận diện âm thanh nguy hiểm, hội thoại nhiều người nói chồng, ghi âm bí mật, tự huấn luyện mô hình lớn từ đầu.

### 2.2. Luồng kỹ thuật đề xuất

```text
Người nói → micro điện thoại → PCM + timestamp → VAD/đệm âm thanh
          → STT tiếng Việt → chuẩn hóa hiển thị → partial/final
          → giao thức truyền ngắn gọn → kính hoặc màn hình giả lập
          → nhật ký thời gian và lỗi (ẩn danh, không lưu âm thanh mặc định)
```

Làm theo thứ tự: **A** xử lý file ghi âm trên laptop; **B** live trên điện thoại hoặc điện thoại gửi âm thanh sang laptop trong lab; **C** xử lý trực tiếp trên điện thoại; **D** gửi chữ lên kính. Nếu điện thoại không đủ mạnh, dùng laptop làm máy suy luận trong demo nhưng ghi rõ đường đi âm thanh và không gọi đó là xử lý trên điện thoại. Nếu chưa có kính có API hiển thị, dùng một màn hình nhỏ giả lập kính; chỉ công bố là giả lập. Chọn phần cứng sau khi đo được giới hạn tốc độ, cổng kết nối và cách nhận chữ của thiết bị thực tế.

### 2.3. Yêu cầu chức năng

| ID | Chức năng | Tiêu chí chấp nhận |
|---|---|---|
| F1 | Bật/tắt phiên và xin quyền micro | Trạng thái ghi âm luôn nhìn thấy; tắt là dừng thu |
| F2 | Thu âm kèm mốc thời gian đơn điệu | Không mất khung âm thanh âm thầm; nếu tràn đệm có log |
| F3 | Phát hiện đoạn có giọng nói | Không tạo phụ đề từ im lặng trong bài thử chuẩn |
| F4 | Nhận dạng tiếng Việt | Giữ dấu tiếng Việt, không tự dịch sang tiếng Anh |
| F5 | Hiển thị partial/final | Partial có ký hiệu riêng; final không bị sửa lùi sau khi chốt |
| F6 | Đẩy chữ lên kính | Có sequence ID để bỏ bản tin cũ/trùng; đứt kết nối có trạng thái rõ |
| F7 | Điều chỉnh cỡ chữ, tương phản, tốc độ cuộn | Người dùng đổi được ít nhất 2 cỡ chữ; dòng không bị cắt khó đọc |
| F8 | Xuất kết quả thí nghiệm | JSON/CSV có ID mẫu, cấu hình, dự đoán và các timestamp, không chứa tên thật |

Ưu tiên giao diện: 1–2 dòng ngắn, chữ có dấu rõ, tương phản cao, giữ final đủ lâu để đọc, không nhấp nháy theo từng token. Mức tương phản 4,5:1 là tham chiếu từ [W3C WCAG](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum) cho giao diện số; kiểm tra thực nghiệm vì màn hình kính và nền ngoài đời khác màn hình web.

### 2.4. Yêu cầu phi chức năng

- **Quyền riêng tư:** có sự đồng ý của người nói; không ghi âm nền khi đã tắt; không đưa dữ liệu hội thoại riêng tư vào API bên ngoài khi chưa được chấp thuận.
- **Khả năng tái lập:** một file cấu hình cho mỗi lần chạy; cố định phiên bản model, hash/checksum dữ liệu và seed khi có ngẫu nhiên.
- **Độ bền:** ngắt micro, mất Bluetooth/mạng, thiết bị ngủ, app bị dừng phải có trạng thái lỗi thay vì hiển thị câu cũ như câu mới.
- **Năng lượng:** ghi % pin đầu/cuối, thời gian chạy và nhiệt độ cảm nhận trong cùng điều kiện; không so sánh máy khác nếu thiếu thông số.
- **Khả năng tiếp cận:** thiết kế cùng người dùng khiếm thính, cho họ quyền điều chỉnh chữ và quyền dừng ngay.

## 3. Thiết kế dữ liệu và cách đo thống nhất

### 3.1. Nguồn dữ liệu

| Nguồn | Vai trò | Hành động của nhóm | Giới hạn |
|---|---|---|---|
| [Common Voice Scripted Speech 27.0 – Vietnamese](https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk) | Thử pipeline, baseline trên lời đọc | Tải phiên bản cố định, lưu thông tin giấy phép và metadata | Lời đọc không đại diện hội thoại đời thường; điều kiện tải có thể thay đổi |
| [FLEURS vi_vn](https://tensorflow.google.cn/datasets/catalog/xtreme_s) | Benchmark độc lập đa người nói | Dùng test sẵn có; không tinh chỉnh rồi báo cáo trên cùng test | Chủ yếu lời đọc; giữ nguyên split; [dataset card](https://huggingface.co/datasets/google/fleurs) ghi CC BY 4.0 |
| Tự thu tiếng Việt có đồng ý | **Tập đánh giá chính** đúng bối cảnh kính | Thu hội thoại ngắn, chép tay, kiểm chéo, gắn điều kiện thu | Quy mô nhỏ, không suy rộng cho toàn bộ người dùng |

Không gộp bản trùng giữa nguồn; không dùng transcript test làm prompt, từ điển sửa lỗi hoặc dữ liệu tinh chỉnh. Nếu bộ công khai cập nhật phiên bản, giữ URL, phiên bản, ngày tải và điều kiện sử dụng tại thời điểm tải. Không đưa file âm thanh có người thật vào Git.

### 3.2. Kế hoạch thu thập tối thiểu khả thi

- **Pilot:** 5 người nói × 10 câu; dùng để kiểm tra micro, câu hỏi đồng ý, nhãn và chất lượng file.
- **Bộ chính:** mục tiêu 15–20 người nói, mỗi người 20–30 phát ngôn (khoảng 300–600 đoạn, 30–60 phút tiếng nói). Đây là mục tiêu tổ chức công việc, không phải cỡ mẫu thống kê đủ để khẳng định hiệu quả.
- **Phủ tình huống:** ít nhất 3 mức nền (yên tĩnh, ồn nhẹ, ồn vừa), 2 khoảng cách, nhiều giới/giọng địa phương nếu tuyển được; báo số lượng thực tế từng nhóm, tránh hứa cân bằng hoàn hảo.
- **Nội dung:** câu giao tiếp thường ngày, số, tên riêng giả lập, câu hỏi, câu trả lời, ngập ngừng. Không bắt người tham gia đọc dữ liệu nhạy cảm.
- **Tách phiên:** mỗi phiên lưu thiết bị, micro, vị trí micro, khoảng cách, địa điểm, loại ồn, người nói ẩn danh và người gán nhãn. Có người kiểm tra chéo ít nhất 10% transcript; bất đồng được giải quyết trước khi đóng băng test.
- **Âm thanh:** lưu file gốc đúng sample rate rồi tạo bản mono PCM 16 kHz cho pipeline; không đổi nhãn hoặc xoá gốc vì thao tác xử lý.

### 3.3. Lược đồ dữ liệu bắt buộc

Một hàng cho một phát ngôn, với ít nhất: `utterance_id`, `session_id`, `speaker_id_hash`, `source`, `split`, `audio_path`, `audio_sha256`, `duration_s`, `sample_rate_hz`, `channels`, `transcript_raw`, `transcript_eval`, `language`, `region_self_reported_optional`, `mic_type`, `distance_m`, `noise_condition`, `consent_version`, `annotator_id`, `review_status`. Giá trị không biết là rỗng có giải thích; không điền số 0 giả. `transcript_eval` được sinh bằng hàm chuẩn hóa có phiên bản từ `transcript_raw`; bản gốc không bị ghi đè.

Cho mỗi lần suy luận lưu thêm `run_id`, `model_id`, `model_version`, `device_id`, `vad_config`, `chunk_config`, `decode_config`, `pred_raw`, `pred_eval`, `speech_start_ms`, `speech_end_ms`, `first_text_ms`, `final_text_ms`, `glass_display_ms`, `inference_ms`, `dropped_frames`, `error_code`. Đồng hồ giữa điện thoại và kính phải đồng bộ hoặc đo độ lệch; nếu không, chỉ báo độ trễ trong cùng thiết bị.

### 3.4. Quy tắc đánh giá

1. **Khóa chuẩn hóa trước test:** Unicode NFC, chữ thường, chuẩn khoảng trắng; quy định trước cách xử lý dấu câu, chữ số và từ đệm. Giữ dấu thanh để lỗi tiếng Việt vẫn bị tính. Công bố cả câu gốc và câu chuẩn hóa cho mẫu phân tích lỗi.
2. **CER:** tổng số thay thế + xóa + chèn ký tự, chia tổng ký tự tham chiếu. Đếm theo grapheme/Unicode sau chuẩn hóa; nêu rõ thư viện và chính sách dấu/space.
3. **WER theo khoảng trắng:** cùng công thức trên token cách bằng khoảng trắng. Trong tiếng Việt khoảng trắng thường ngăn cách **âm tiết**, nên gọi rõ là *WER theo khoảng trắng / tỷ lệ lỗi âm tiết*, không đồng nhất với lỗi từ vựng. Có thể đo thêm WER sau tách từ bằng một tokenizer đã cố định.
4. **Micro và macro:** micro cộng lỗi và độ dài tham chiếu toàn bộ; macro lấy trung bình lỗi theo phát ngôn hoặc người nói. Báo cả hai, cùng số mẫu. WER/CER có thể vượt 100% khi có nhiều chèn.
5. **Độ trễ:** `first_text_ms − speech_start_ms`; `final_text_ms − speech_end_ms`; `glass_display_ms − speech_end_ms`. Báo p50/p90/p95 theo phát ngôn và tỷ lệ câu không ra chữ. Dùng đồng hồ đơn điệu.
6. **Ổn định partial:** số lần sửa/ngược chữ trước final, số ký tự thay đổi trên mỗi câu, số lần phụ đề giật/nhấp nháy. Kết quả final dùng cho CER/WER chính.
7. **Lỗi im lặng:** số lần xuất hiện chữ khi đoạn chuẩn không có lời nói; đo trên một tập im lặng/tiếng ồn riêng.
8. **Tài nguyên:** peak RAM, CPU hoặc % sử dụng, pin/phút, nhiệt độ và real-time factor (thời gian xử lý / thời lượng âm thanh). Với pipeline live, thêm thời gian chờ hàng đợi.

WER và CER là thước đo chuẩn của ASR; [Hugging Face Audio Course](https://huggingface.co/learn/audio-course/chapter5/evaluation) giải thích cách tính. Không dùng accuracy/F1/AUC/RMSE thay thế cho lỗi chép lời. F1 chỉ dùng khi nhóm thêm một **bài toán phân loại** riêng, chẳng hạn phát hiện tiếng nói hoặc từ khóa quan trọng.

## 4. Stage 1 — Data Understanding & Light Cleaning

**Câu hỏi:** nhóm đang có dữ liệu gì và dữ liệu có đúng, đủ quyền dùng, đủ chất lượng tối thiểu không?
**Đầu ra:** `data_inventory.csv`, `data_dictionary.md`, `consent_template.md`, `cleaning_log.csv`, tập pilot đã kiểm tra; phiên bản dữ liệu đóng băng `dataset_v1`.

| Bước gốc | Cách làm tương ứng cho âm thanh/STT | Minh chứng cần nộp |
|---|---|---|
| **Data Collection** | Lập danh mục nguồn công khai và giấy phép; thu âm pilot có đồng ý, transcript tay, metadata thiết bị/ồn/khoảng cách. | Manifest, mẫu đồng ý, số người/giờ âm thanh |
| **Light Cleaning** | Loại file hỏng, file rỗng, file ngoài tiếng Việt ngoài phạm vi, trùng checksum; chỉ xóa khỏi *manifest làm việc*, giữ gốc cách ly. | Số trước/sau, lý do loại từng ID |
| **Logic Check** | `duration_s > 0`, sample rate hợp lệ, transcript không rỗng nếu có lời, thời điểm đầu < cuối, `speaker_id` hợp lệ, split chưa chồng. Nghe lại mẫu nghi vấn. | Báo cáo lỗi quy tắc và cách xử lý |
| **Basic Formatting** | Tên cột snake_case, UTC hoặc offset rõ ràng cho thời gian tường, Unicode NFC, đơn vị giây/Hz, mã điều kiện thu thống nhất. | Data dictionary và hàm chuẩn hóa có ví dụ trước/sau |

**Ranh giới:** chưa loại phát ngôn khó chỉ vì model nhận sai; chưa khử ồn hàng loạt; chưa nội suy metadata không biết. Kiểm tra nội dung bằng tai và transcript, không suy luận chỉ từ thống kê file. **Điều kiện qua Stage 2:** 100% file trong manifest mở được; mọi phát ngôn có ID, nguồn, quyền sử dụng và nhãn trạng thái; mọi ngoại lệ có lý do.

## 5. Stage 2 — Exploratory Data Analysis (EDA)

**Câu hỏi:** dữ liệu phân bố thế nào và có thiên lệch nào làm đánh giá sai?
**Đầu ra:** notebook EDA, biểu đồ có tiêu đề/đơn vị/số mẫu, `eda_findings.md` với mỗi phát hiện gồm bằng chứng → giả thuyết → hành động tiếp theo.

| Bước gốc | Phép phân tích cho bài toán STT | Biểu đồ/bảng tối thiểu |
|---|---|---|
| **Data Overview** | Số file/người/phiên, tổng giờ, nguồn, sample rate, kênh, transcript, độ phủ metadata. | Bảng shape, dtype, non-null, giờ theo nguồn |
| **Summary Statistics** | Mean/median/mode/std cho thời lượng, số âm tiết, mức âm lượng, khoảng cách; ưu tiên median/p90 khi lệch. | Bảng theo split và điều kiện |
| **Distribution Analysis** | Phân bố độ dài câu, thời lượng, độ ồn ước tính, độ dài khoảng lặng. | Histogram/density theo nguồn và điều kiện |
| **Outliers Analysis** | Tìm file cực dài/ngắn, âm lượng clip, transcript quá lệch thời lượng, số token bất thường bằng IQR/boxplot/z-score khi phù hợp; nghe lại. | Danh sách ID nghi vấn và quyết định giữ/sửa/loại |
| **Missing Values Analysis** | Tỷ lệ thiếu từng cột; thiếu theo nguồn/người/phiên để phát hiện pattern. | Ma trận hoặc bảng phần trăm; giải thích `unknown` |
| **Categorical Analysis** | Tần suất và cardinality của giọng tự khai, loại micro, môi trường, vùng miền, thiết bị, nhãn lỗi. | Bảng đếm và tỷ lệ; tránh công bố nhóm quá nhỏ có thể nhận diện |
| **Relationships Analysis** | Scatter/boxplot độ dài ↔ độ trễ, ồn ↔ CER/WER pilot, khoảng cách ↔ lỗi; tương quan chỉ là mô tả. | 2–3 hình có số mẫu và khoảng tin cậy nếu có |
| **Preliminary Feature Importance** | Đánh giá sơ bộ bằng so sánh nhóm hoặc mô hình giải thích đơn giản trên **pilot** (hoặc train/validation nếu đã chia nhóm trước): ồn, khoảng cách, micro, độ dài ảnh hưởng lỗi ra sao. | Bảng effect thô; ghi rõ chưa phải nhân quả |
| **Patterns & Trends** | Diễn tiến lỗi/độ trễ theo phút trong phiên, ngày thu, pin/nhiệt, mốc bắt đầu hội thoại. Không có thời gian đủ dài thì ghi “chưa đánh giá chu kỳ/mùa vụ”. | Line chart hoặc lý do không áp dụng |
| **Aggregations** | Gộp theo người nói, điều kiện ồn, nguồn, độ dài; tính lỗi và độ trễ kèm `n`. | Bảng pivot cho nhóm chính |
| **Initial Insights & Documentation** | Ghi 5–10 phát hiện, đính kèm ID hình, giới hạn mẫu và quyết định Stage 3–4. | `eda_findings.md` có ngày và tác giả |

**Lưu ý chống rò rỉ:** EDA có thể mô tả metadata toàn bộ dữ liệu để kiểm kê, nhưng không nhìn lỗi model trên test rồi chọn cấu hình/chuẩn hóa theo test. Nếu phát hiện lỗi nhãn test, sửa theo quy trình có log trước khi chạy đánh giá cuối. **Điều kiện qua Stage 3:** biết rõ dữ liệu nào không đại diện tình huống dùng kính và có giả thuyết kiểm chứng cụ thể.

## 6. Stage 3 — Statistical Analysis

**Câu hỏi:** chênh lệch thấy ở EDA có đủ tin cậy và đủ lớn để đáng quan tâm không?
**Đầu ra:** `analysis_plan.md` khóa trước thí nghiệm chính, notebook thống kê pilot, bảng hiệu ứng + khoảng tin cậy, kết luận có giới hạn. Ở Stage 3, nhóm thực hành phép kiểm định trên pilot/train/validation và chốt kế hoạch; phép kiểm định xác nhận trên test khóa chỉ được chạy sau khi Stage 4–5 hoàn tất. Cách này giữ đủ bước thống kê mà không dùng test sớm.

| Bước gốc | Áp dụng hoặc phương án tương đương | Quy tắc ra quyết định |
|---|---|---|
| **Hypothesis Testing** | Đặt H0/H1 trước: ví dụ VAD không giảm median độ trễ final; micro gần miệng không giảm CER; ồn không làm tăng CER. Thiết kế **paired**: cùng câu/phiên qua 2 cấu hình. | Chọn phép thử theo đơn vị độc lập, có p-value và khoảng tin cậy; không “chứng minh” H0/H1 tuyệt đối |
| **Relationship Validation** | Kiểm tra xu hướng ồn/khoảng cách với CER bằng scatter, mô hình hồi quy phù hợp hoặc bootstrap theo người/phiên; xem yếu tố gây nhiễu (thiết bị, người nói). | Báo chênh lệch và giới hạn; tương quan không suy ra nhân quả |
| **Significance & Effect Size** | Báo chênh lệch CER/WER tuyệt đối tính theo điểm %, chênh lệch p50/p90 độ trễ, CI 95%. | Ưu tiên mức cải thiện có ý nghĩa thực tế cho việc đọc, không chỉ p < 0,05 |
| **Assumptions Checking** | Kiểm tra tính độc lập theo người/phiên, phân phối độ trễ lệch phải, ngoại lệ, phương sai nhóm; chỉ dùng t-test/ANOVA nếu giả định phù hợp. | Nếu không phù hợp: paired permutation, Wilcoxon hoặc bootstrap cụm; ghi lý do |
| **Feature Selection** | Nếu có mô hình **dự đoán lỗi/độ trễ** phụ trợ, chọn yếu tố đo được và ít trùng lặp trên train/validation bằng domain knowledge + regularization/ablation. | Không “chọn feature” cho Whisper end-to-end như bài toán bảng; không dùng test để chọn |

**Ví dụ kế hoạch kiểm định:** mỗi file test chạy A (không VAD) và B (có VAD) trên cùng thiết bị, cùng model/decode và cùng thứ tự ngẫu nhiên hoặc đổi thứ tự để giảm hiệu ứng nhiệt máy. Tính `ΔCER = CER_B − CER_A` và `Δlatency = p50_B − p50_A` theo **người/phiên**. Bootstrap cụm 2.000 lần với seed ghi lại để lấy CI; với ít cụm, diễn giải CI thận trọng. Có thể dùng paired permutation trên giá trị theo cụm. Nếu thử nhiều giả thuyết, ghi số phép thử và phân biệt phân tích xác nhận với khám phá; có thể dùng Holm cho nhóm phép thử xác nhận. Không áp dụng t-test lên từng ký tự vì chúng không độc lập.

**Điều kiện qua Stage 4:** kế hoạch phân tích đã khóa, đơn vị lấy mẫu/ghép cặp rõ, metric chính và ngưỡng ý nghĩa thực tế đã định, cách xử lý các bước không áp dụng đã ghi.

## 7. Stage 4 — Data Preparation (Heavy Cleaning)

**Câu hỏi:** làm sao tạo dữ liệu huấn luyện/đánh giá và đầu vào model mà không rò rỉ hoặc bóp méo lời nói?
**Đầu ra:** manifest split bất biến, pipeline tiền xử lý có phiên bản, báo cáo dữ liệu trước/sau, bài kiểm thử dữ liệu.

| Bước gốc | Cách làm hoặc alternative đúng với âm thanh | Điều cấm/kiểm tra |
|---|---|---|
| **Data Splitting** | Chia theo **người nói** cho dữ liệu tự thu: khoảng 60/20/20 theo số người nếu đủ; cân đối điều kiện bằng chọn nhóm. Khóa test trước mọi tinh chỉnh. FLEURS/Common Voice giữ split chính thức nếu dùng. | Không để cùng người/phiên hoặc câu đọc trùng giữa train/val/test; báo số giờ và người từng split |
| **Missing Values Handling** | Transcript thiếu: đánh dấu `unlabeled`, chép bổ sung hoặc loại khỏi tập tính CER; metadata thiếu: `unknown` + cờ thiếu, chỉ nội suy nếu phân tích phụ trợ có lý do. | Không sinh transcript bằng model rồi coi là ground truth; không fit imputer trên test |
| **Outliers Treatment** | Sửa metadata sai, tách file rất dài theo quy tắc, giữ trường hợp khó hợp lệ và báo riêng; chỉ loại file hỏng/không thể gán nhãn. | Không cắt biên độ/khử ồn theo test để tăng điểm rồi giấu thao tác |
| **Feature Preparation** | Resample đúng kỹ thuật sang mono PCM 16 kHz khi model yêu cầu; đo/ghi độ ồn, độ dài, thiết bị; chuẩn hóa transcript để tính metric. One-hot/Min-Max chỉ cho mô hình phụ trợ dạng bảng. | Không biến đặc trưng từ transcript dự đoán thành đầu vào mô hình sẽ đánh giá cùng mẫu |
| **Imbalance Handling** | Nếu train có giọng/điều kiện lệch, dùng weighted sampling/augmentation **chỉ trên train**; test giữ phân bố thật và báo slice. SMOTE chỉ dành cho bảng phân loại phụ trợ, không tạo âm thanh “SMOTE”. | Không nhân bản một người rồi để bản sao sang validation/test |
| **Dimensionality Reduction** | PCA/UMAP/t-SNE chỉ để trực quan embedding âm thanh hoặc feature bảng và khảo sát cụm; không bắt buộc cho Whisper. Nếu làm dự đoán phụ trợ, fit PCA trên train và áp dụng val/test. | t-SNE không dùng làm bằng chứng “giữ tối đa phương sai” hay thước đo chất lượng STT |
| **Sklearn Pipeline** | Dùng `sklearn.Pipeline`/`ColumnTransformer` cho bài toán phụ trợ bảng; pipeline STT chính là chuỗi versioned `audio decode → resample → VAD/chunk → model → postprocess → metric`. | Test mỗi bước riêng, lưu config; không ép waveform vào sklearn chỉ để đủ tên bước |

**Thứ tự:** chốt split trước mọi phép fit/thống kê dùng để điều chỉnh pipeline. File gốc chỉ đọc; artefact đã xử lý ghi thư mục riêng kèm script và hash. Có `preprocess_config.yaml` ghi sample rate, VAD threshold, độ dài đoạn, overlap, quy tắc chuẩn hóa; thay đổi config phải tạo `run_id` mới.

**Bài kiểm thử tối thiểu cho Stage 4:** (1) không trùng checksum/`speaker_id_hash` qua split nội bộ; (2) resample giữ thời lượng sai lệch dưới 1 frame hợp lý; (3) transcript UTF-8/NFC và dấu không mất; (4) file rỗng/hỏng có lỗi có kiểm soát; (5) chuẩn hóa văn bản cho cùng kết quả khi chạy lại; (6) mock audio im lặng không tạo nhãn lời nói trong pipeline VAD; (7) cùng config tạo manifest giống nhau.

## 8. Stage 5 — Modeling & Machine Learning

**Câu hỏi:** cấu hình nào tốt trên dữ liệu chưa từng dùng để chọn model và có phù hợp với demo kính?
**Đầu ra:** bảng thí nghiệm, model/config chốt, kết quả test một lần theo kế hoạch, phân tích lỗi và demo.

| Bước gốc | Cách triển khai có thể học được | Sản phẩm |
|---|---|---|
| **Baseline Model** | B0: chép tay lý tưởng để kiểm tra giới hạn giao diện; B1: `Whisper tiny` đa ngôn ngữ, không tinh chỉnh; B2: `Whisper base` đa ngôn ngữ. Cùng dữ liệu, chuẩn hóa, thiết bị và decoding khi so sánh. | Bảng CER/WER, p50/p90 latency, tài nguyên |
| **Advanced Feature Engineering** | Thử vị trí micro, tăng chất lượng thu, VAD/chunk/overlap, danh sách từ riêng **chỉ khi model hỗ trợ và không chứa test**; ablation từng thay đổi. | Bảng A/B và sai lệch so với baseline |
| **Advanced Sampling** | Group cross-validation theo người trên train/val nếu đủ người; bootstrap cụm người/phiên cho CI. | Phân phối điểm; không trộn speaker |
| **Multi-Algorithm Modeling** | So sánh `faster-whisper` với `whisper.cpp` cùng trọng số/cỡ model khi khả thi; hoặc so sánh Whisper với một model ASR tiếng Việt khác có license, input và tài nguyên rõ. | Ma trận tốc độ/chất lượng; ghi cấu hình decode để công bằng |
| **Regularization** | Nếu chỉ dùng model pretrained để suy luận, ghi “không áp dụng huấn luyện”; alternative là chống overfit khi chọn cấu hình: ít tham số tìm, val cố định, test khóa. Nếu fine-tune nhỏ, dùng weight decay/early stopping trên val. | Lý do không fine-tune hoặc log train/val |
| **Model Interpretation** | Phân loại lỗi: mất dấu, tên riêng, số, nuốt từ, thêm chữ trong im lặng, cắt câu, giọng vùng, ồn; xem 20–30 ca lỗi và audio có quyền. | Bảng ví dụ ẩn danh và giả thuyết nguyên nhân |
| **Evaluation** | Final CER, WER theo khoảng trắng, latency, stability, false caption rate, RTF, RAM/pin, khảo sát hiểu nội dung. F1 cho VAD nếu có nhãn nói/im lặng; RMSE/AUC chỉ nếu thêm mục tiêu dự đoán phù hợp. | Báo cáo test giữ kín, CI, slice, số mẫu |
| **Optimization** | Grid nhỏ trên val: model tiny/base/small; chunk 2/4/6 s; overlap 0/0,5 s; VAD on/off; beam 1/5 khi đủ tài nguyên. Chỉ mở rộng sau khi đo. | Config được chọn + quy tắc chọn (ví dụ CER dưới ngưỡng rồi tối thiểu latency) |

Whisper gốc xử lý các cửa sổ 30 giây khi phiên âm file; muốn phụ đề gần thời gian thực phải tự thiết kế đệm, cắt đoạn, xử lý partial/final và đo độ trễ. Đây là suy luận kỹ thuật từ [mã và tài liệu Whisper](https://github.com/openai/whisper/blob/main/README.md) cùng [ví dụ streaming của whisper.cpp](https://github.com/ggml-org/whisper.cpp/blob/master/examples/stream/README.md), **không phải cam kết model streaming sẵn có**. `faster-whisper` có VAD và tăng tốc suy luận, nhưng kết quả benchmark của dự án chỉ áp dụng cho phần cứng/cấu hình họ thử; nhóm phải benchmark trên máy của mình và giữ beam size tương đương khi so sánh ([nguồn](https://github.com/SYSTRAN/faster-whisper)). Trên Android, `whisper.cpp` có ví dụ app và gợi ý model tiny/base để bắt đầu ([nguồn](https://github.com/ggml-org/whisper.cpp/blob/master/examples/whisper.android/README.md)); bản `.en` chỉ dành tiếng Anh, dùng model đa ngôn ngữ cho tiếng Việt ([danh sách model](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md)).

### 8.1. Thứ tự thí nghiệm và điểm dừng

1. **E0 — offline:** chạy file kiểm thử nhỏ qua tiny/base; tính CER/WER bằng transcript chuẩn. Nếu pipeline không ổn, chưa làm live.
2. **E1 — live điện thoại/máy tính:** thu liên tục, cắt đoạn cố định, hiển thị final trên điện thoại; đo timestamp từng khâu.
3. **E2 — VAD và partial:** thêm VAD, overlap, logic không lặp chữ; so với E1 trên cùng bản ghi phát lại và trong phiên live.
4. **E3 — so model/runtime:** tiny/base/small hoặc faster-whisper/whisper.cpp; chọn theo Pareto CER–latency–RAM/pin trên val.
5. **E4 — kính:** gửi phụ đề đã chốt và partial; thử đứt kết nối, độ dài dòng, tương phản, khả năng đọc. Không để lỗi màn hình làm sai metric STT: báo riêng latency từ model và từ truyền/hiển thị.
6. **E5 — test cuối:** khóa code/config; chỉ một lần đánh giá chính trên test. Sau đó được phân tích lỗi nhưng mọi cải tiến tiếp theo phải đặt tên phiên bản mới và cần test mới nếu muốn kết luận xác nhận.

### 8.2. Báo cáo thí nghiệm mẫu

Mỗi run ghi một hàng: `run_id | git_commit | dataset_version | split | model/version | runtime/version | device | VAD | chunk/overlap | beam | normalization_version | CER | WER_space | latency_first_p50/p90 | latency_final_p50/p90 | RTF | peak_RAM | battery_delta | n_utterances | n_speakers | notes`. Đính kèm 5 câu tốt, 5 câu lỗi điển hình, 5 câu bị chậm; không chọn ví dụ chỉ để khoe điểm.

## 9. Kiểm thử hệ thống và đánh giá với người dùng

### 9.1. Bài kiểm thử kỹ thuật

| Cấp | Tình huống | Kết quả cần quan sát |
|---|---|---|
| Unit | Chuẩn hóa Unicode, tính CER/WER bằng chuỗi đã biết, timestamp đơn điệu, ghép partial/final | Kết quả chính xác, không lặp chữ |
| Data | File hỏng, im lặng, clipping, transcript rỗng, trùng audio, lệch sample rate | Bị bắt lỗi hoặc xử lý theo quy tắc, có log |
| Integration | Audio đã biết → model → điện thoại → màn hình giả lập/kính | Đúng thứ tự và không thiếu bản tin cuối |
| Recovery | Bluetooth/mạng mất rồi nối lại, điện thoại khóa màn hình, micro bị rút, buffer tràn | Trạng thái rõ và phục hồi hoặc dừng an toàn |
| Performance | 15 phút liên tục, nhiều độ dài câu, ồn và im lặng | Không tích lũy hàng đợi vô hạn; thống kê p50/p90/p95 |
| Regression | 10–20 file chuẩn cố định không thuộc test khóa | Đổi code không làm suy giảm ngoài ngưỡng nhóm đặt |

Sau **mỗi lần viết code**: chạy test liên quan, ghi lệnh và kết quả trong commit/PR hoặc `experiments/log.md`; nếu thiếu test, thêm test cho hành vi vừa làm. Khi thay đổi chức năng, cập nhật đặc tả/README và test trong cùng commit, theo `AGENTS.md`.

### 9.2. Thử với người khiếm thính

Tuyển 3–5 người nếu có thể, trả công/hỗ trợ đi lại nếu phù hợp, xin đồng ý bằng văn bản dễ hiểu, cho phép rút lui và xóa dữ liệu. Đồng thiết kế màn hình trước khi “chốt” UI. Dùng 2–3 nhiệm vụ ngắn: (1) hiểu một câu chỉ dẫn; (2) theo dõi hội thoại 1 phút; (3) nhận biết phụ đề chưa chốt và đã chốt. Ghi tỷ lệ trả lời đúng, thời gian đọc, lỗi bỏ sót, điểm dễ đọc 1–5, nhận xét tự do và mức khó chịu khi chữ thay đổi. Thứ tự điều kiện có/không phụ đề cần đổi giữa người tham gia. Kết quả với mẫu nhỏ là phản hồi thiết kế, **không** đại diện cho toàn bộ cộng đồng.

## 10. Kế hoạch 10 tuần và phân công

| Tuần | Công việc chính | Tiêu chí xong |
|---|---|---|
| 1 | Chốt kịch bản, thiết bị có sẵn, người dùng, mẫu đồng ý, kiến trúc, metric | Đặc tả v1, risk log, demo đường hiển thị giả |
| 2 | Thu pilot, nhập manifest, kiểm tra file, Stage 1 | Dataset pilot có quyền và cleaning log |
| 3 | Thu bộ chính, chép/kiểm transcript, Stage 2 | EDA và các thiếu hụt dữ liệu được ghi |
| 4 | Khóa giả thuyết, split, chuẩn hóa, Stage 3 | Analysis plan và test lock |
| 5 | Pipeline tiền xử lý và unit/data tests, Stage 4 | Manifest bất biến, test data pass |
| 6 | E0/E1 baseline offline và live | Bảng CER/WER + latency đầu tiên |
| 7 | E2 VAD/partial + ablation | Không lặp chữ, có so sánh paired |
| 8 | E3 runtime/model + tối ưu val | Chọn config theo quy tắc đã viết |
| 9 | E4 kính và thử người dùng | Demo 15 phút, phản hồi UX |
| 10 | E5 test khóa, báo cáo, video, trình bày | Báo cáo đủ CI/slice/giới hạn và cách tái lập |

Nếu nhóm 3 người: **A** dữ liệu/đạo đức + Stage 1–3; **B** âm thanh/model + Stage 4–5; **C** điện thoại/kính/UI + đo latency. Cả nhóm cùng duyệt nhãn, kiểm thử và phân tích kết quả; mỗi hạng mục có 1 người chịu trách nhiệm cuối. Họp ngắn 2 lần/tuần: một lần xem dữ liệu/lỗi, một lần xem demo/metric.

## 11. Cấu trúc repo khi bắt đầu viết code

```text
PBL6/
  AGENTS.md
  SPEC_STT_SMART_GLASSES.md
  README.md
  docs/              # consent, data dictionary, EDA, analysis plan, thiết kế UI
  configs/           # dataset/model/VAD/normalization versioned
  src/               # audio, VAD, ASR, caption protocol, UI integration
  tests/             # unit, data, integration, regression
  notebooks/         # Stage 1–3; không lưu raw audio trong output
  experiments/       # run manifest, metrics, log, plots
  data/              # local only; raw/processed/manifest (Git ignore audio gốc)
```

Quy tắc commit: một thay đổi hoàn chỉnh → test liên quan → cập nhật tài liệu liên quan → commit có mô tả. Không commit khóa API, âm thanh người tham gia hoặc thông tin nhận dạng. Mỗi biểu đồ/bảng báo cáo phải gắn `dataset_version`, `run_id` và cách tính metric.

## 12. Rủi ro, quyết định và giới hạn cần nói thẳng

| Rủi ro | Tác động | Biện pháp học thuật thực tế |
|---|---|---|
| Hiểu nhầm “real-time” | Hứa phụ đề tức thì dù model ra chữ theo đoạn | Đo độ trễ chữ đầu/final/kính; gọi “gần thời gian thực” |
| Rò rỉ test hoặc cùng người nói | Điểm đẹp giả | Group split, khóa config, log test access |
| Dữ liệu công khai khác hội thoại | Điểm benchmark không phản ánh kính | Tập tự thu là bài đánh giá chính, công khai chỉ phụ |
| Ít người tham gia | CI rộng, nhóm con yếu | Báo số mẫu, CI, không tuyên bố tổng quát |
| Âm thanh nhạy cảm | Xâm phạm riêng tư | Đồng ý rõ, mã ẩn danh, lưu hạn chế, xóa theo yêu cầu |
| Kính khó đọc/thiếu SDK | Demo không hoàn chỉnh | Kiểm tra API phần cứng tuần 1; màn hình giả lập là phương án có nhãn rõ |
| Pin/nhiệt/CPU | App rớt khung | Model nhỏ, VAD, đo trên máy thật, giới hạn queue |
| Ồn, nhiều người nói | Sai lời hoặc bỏ sót | Báo slice, hiển thị “không chắc/chưa nhận được” khi phù hợp; không tự thêm nội dung |
| Model tự tạo chữ ở im lặng | Người dùng hiểu sai | Bộ test im lặng, VAD, chỉ hiển thị khi điều kiện phát lời đủ |

**Giới hạn thiết kế:** STT sai có thể làm người dùng hiểu nhầm lời người khác; nguyên mẫu không được quảng bá như công cụ duy nhất để xử lý tình huống nguy hiểm. Màn hình không được che tầm nhìn. Số liệu và đánh giá người dùng phải phân biệt kết quả đo được, giả thuyết và ý kiến cá nhân.

## 13. Danh sách kiểm tra trước khi nộp

- [ ] Đúng đối tượng người khiếm thính, tiếng Việt, điện thoại xử lý, kính hiển thị; mọi giả lập được gắn nhãn.
- [ ] Mỗi bước của Stage 1–5 có artefact; bước không phù hợp có alternative và lý do.
- [ ] Có nguồn/giấy phép/đồng ý, dữ liệu gốc và manifest; không có âm thanh riêng tư trong Git.
- [ ] Split theo người, test khóa, không tinh chỉnh theo test; chuẩn hóa và metric có phiên bản.
- [ ] CER, WER theo khoảng trắng, latency p50/p90, lỗi im lặng, slice theo điều kiện, CI được báo cùng `n`.
- [ ] Có ít nhất baseline, so sánh có kiểm soát, ablation và phân tích 20–30 lỗi.
- [ ] Test code/data/integration đã chạy sau code; trạng thái chạy 15 phút và lỗi kết nối được ghi.
- [ ] Người dùng đánh giá cách đọc phụ đề; nhóm nêu hạn chế cỡ mẫu và tính an toàn.
- [ ] Hướng dẫn tái lập bao gồm commit, dataset/model/runtime version, thiết bị, lệnh và config.

## 14. Nguồn kỹ thuật chính (truy cập 24/09/2026)

1. [OpenAI Whisper README](https://github.com/openai/whisper/blob/main/README.md) và [model card](https://github.com/openai/whisper/blob/main/model-card.md): tác vụ, model, xử lý âm thanh và giới hạn.
2. [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp), [model list](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md), [stream example](https://github.com/ggml-org/whisper.cpp/blob/master/examples/stream/README.md), [Android example](https://github.com/ggml-org/whisper.cpp/blob/master/examples/whisper.android/README.md): prototype cục bộ và mô hình đa ngôn ngữ.
3. [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper): runtime so sánh, VAD, lưu ý benchmark cùng beam size.
4. [Mozilla Data Collective – Common Voice](https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk): dữ liệu lời nói tiếng Việt; kiểm tra lại điều kiện tải/giấy phép của phiên bản sử dụng.
5. [Google FLEURS publication](https://research.google/pubs/fleurs-few-shot-learning-evaluation-of-universal-representations-of-speech/), [TFDS vi_vn](https://tensorflow.google.cn/datasets/catalog/xtreme_s), [dataset card](https://huggingface.co/datasets/google/fleurs): benchmark và split.
6. [Hugging Face Audio Course – ASR evaluation](https://huggingface.co/learn/audio-course/chapter5/evaluation): WER/CER.
7. [W3C WAI – Captions Live](https://www.w3.org/WAI/WCAG21/Understanding/captions-live) và [Contrast Minimum](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum): nội dung phụ đề và khả năng đọc.
