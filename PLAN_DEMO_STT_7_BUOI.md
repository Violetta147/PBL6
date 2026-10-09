# Kế hoạch STT: 7 tuần, 7 buổi demo

Ngày lập: 09/10/2026. Lịch gặp thầy: **một buổi mỗi tuần**. Người phụ trách STT hiện là một người; kế hoạch dùng mô hình đã huấn luyện và giữ nguồn lực cho phần SLR. Chưa có ngày gặp cụ thể, nên Buổi 1 là lần gặp thầy tiếp theo, không gán ngày lịch giả định.

Kế hoạch này chuyển [đặc tả ASR trên Pi 4](SPEC_ASR_PI4_RESEARCH_20261009.md) thành các phần việc nhỏ để thực hiện và trình bày. Đặc tả quy định cách làm và cách đo; tài liệu này quy định **làm đến đâu trước mỗi buổi và lấy gì ra demo**. Các chức năng, thí nghiệm và chỉ số trong kế hoạch hiện đều chưa thực hiện.

## Cách đi theo kế hoạch

Mỗi tuần cần một thay đổi chạy được hoặc một kết quả đo được. Bắt đầu bằng luồng đơn giản, giữ nó chạy qua các tuần, rồi thêm so sánh, phần cứng và phép đo. Không dành tuần đầu chỉ đọc lý thuyết; học phần đang cần để hoàn thành demo. Không mở training, model mới ngoài danh sách hoặc giao diện phức tạp khi công việc tuần hiện tại chưa xong.

Ba model chính giữ nguyên: C0 Whisper-base làm baseline, C1 Zipformer-30M với gói ONNX INT8 có sẵn, C2 Qwen3-ASR-0.6B làm đối chiếu trên Colab. Pi thử C0/C1; Whisper-tiny là dự phòng. PhoASR chỉ mở rộng nếu bộ chính đã xong hoặc cần thay C2 theo quy tắc trong đặc tả.

Mỗi tuần chia thành ba lượt làm việc: **xây đầu ra nhỏ → kiểm tra và lưu bằng chứng → tập demo**. Việc thu/kiểm tra nhãn đi song song từ tuần 1 đến tuần 5, không dồn sang tuần đánh giá cuối. Trước buổi học, chạy thử lại một lượt, giữ video ngắn và output đã lưu trên laptop. Chỉ ghi “đã hoàn thành” khi đạt tiêu chí của buổi đó.

Demo khoảng 5 phút: nói thay đổi mới trong 30 giây; chạy hoặc trình bày kết quả trong 2–3 phút; cho thấy một bằng chứng và một giới hạn trong 1 phút; chốt việc tuần sau trong 30 giây. Thầy cần thấy phần mới so với tuần trước, không cần xem lại toàn bộ quá trình cài đặt.

## Lịch tổng quan

| Buổi | Kết quả mới phải có | Nội dung đem demo | Liên hệ thí nghiệm |
|---|---|---|---|
| B01 — Tuần 1 | Một pipeline baseline chạy và lưu được output | Audio tiếng Việt → chữ; một ví dụ WER/CER tính đúng | E0 |
| B02 — Tuần 2 | Ba ứng viên chạy trên cùng dev và có bảng so sánh | Cùng audio, ba transcript; điểm dev và lỗi khác nhau | E1 |
| B03 — Tuần 3 | Ứng viên nhỏ chạy trên Pi và có benchmark | Pi xử lý WAV; RTF, RAM, nhiệt trên tập cố định | E2 |
| B04 — Tuần 4 | Luồng thu âm → VAD → ASR → final chạy liên tục | Nói vào micro, thấy chữ; theo dõi queue và độ trễ | E3 |
| B05 — Tuần 5 | Bộ hiển thị, giao diện SLR và cấu hình khóa | Phụ đề tiếng Việt; sự kiện ASR/SLR đi vào cùng renderer | Hoàn thiện E3, chuẩn bị E4/E5 |
| B06 — Tuần 6 | Kết quả held-out và độ ổn định có bằng chứng | Bảng test; biểu đồ nhiệt/queue/latency; lỗi còn lại | E4 và E5 |
| B07 — Tuần 7 | Bản thử nghiệm, báo cáo và gói bàn giao | Demo toàn luồng, chạy lại một phần từ cấu hình đã lưu | Tổng hợp E0–E5 |

Buổi 1–5 dùng pilot/dev hoặc tập minh họa riêng. Buổi 6 mới sử dụng test đã khóa để đánh giá. Buổi 7 trình bày kết quả đó và câu demo mới; không dùng phản hồi từ test để âm thầm chọn lại model.

## B01 — Chạy được baseline và biết kết quả được tạo thế nào

**Mục tiêu:** có một câu tiếng Việt đi qua mô hình có sẵn, lưu được transcript và giải thích được input/output. Đây là nền để mọi buổi sau có một luồng demo hoạt động.

Việc làm trước buổi học:

- [ ] Đọc mục 1–5, 7–8 và 12 của đặc tả theo phần cần dùng; chốt RQ1–RQ3 và danh sách C0/C1/C2.
- [ ] Chọn 20–30 mẫu FLEURS train làm pilot, giữ ID cố định. Đọc đúng TSV 6/7 cột, lấy transcript theo quy tắc đã ghi; không dùng test.
- [ ] Tạo notebook/script tối thiểu chạy C0 trên Colab, lưu model/runtime/config và output từng mẫu. Chạy một mẫu trước rồi mới chạy cả pilot.
- [ ] Tạo scorer `vi_eval_v1`, kiểm tra câu có dấu, chèn/xóa/thay thế và nhãn rỗng bằng đáp án tính tay. Chấm pilot và ghi rõ đây là điểm kiểm tra luồng.
- [ ] Kiểm kê Pi, nguồn, tản nhiệt và thiết bị thu. Kiểm tra/mượn micro USB nếu cần; thu thử một câu và nghe lại. Hẹn người thu dev/test, chia nhóm trước khi thu.

**Demo:** phát một audio ngắn, chạy C0 và hiện transcript cạnh nhãn. Cho thầy thấy một câu nhận đúng và một lỗi thật nếu có; chỉ ra một phép tính WER/CER đã kiểm chứng. Mở file output để cho thấy kết quả đã lưu, thay vì chỉ tồn tại trong ô notebook.

**Xong khi:** chạy lại được một mẫu mà không sửa tay output; đủ kết quả cho pilot; scorer khớp ví dụ tính tay; biết checkpoint, môi trường và input đã dùng. Chưa cần giao diện đẹp hoặc Pi chạy ASR ở buổi này.

**Bằng chứng:** notebook/script, manifest pilot, predictions, cấu hình và báo cáo B01. Bắt đầu bộ pilot tự thu 20–30 câu riêng nếu chưa hoàn thành; các câu này không chuyển thành test cuối.

**Dự phòng:** lưu sẵn audio, transcript, log và video chạy thành công. Nếu Colab không kết nối được trên lớp, phát video và mở output đã lưu, ghi rõ đó là lượt chạy trước. Nếu chưa có lượt inference thành công, phải báo trạng thái đang vướng; bảng WER minh họa tính tay chỉ chứng minh scorer, không được gọi là kết quả model.

Thông điệp cần truyền đạt: **“Baseline pretrained đã đi qua pipeline có kiểm tra; em đang xây cách đánh giá trước khi so model.”** Chỉ dùng câu này khi tiêu chí đã đạt.

## B02 — Cho thấy model mới và so sánh có căn cứ

**Mục tiêu:** C0/C1/C2 xử lý cùng dữ liệu, dùng chung scorer và có kết quả dev. Qwen3-ASR là phần mới để thầy thấy nhóm đã khảo sát hướng ASR hiện nay, còn bảng đo trả lời nó có ích gì trong đề tài.

Việc làm trước buổi học:

- [ ] Chạy C1 bằng đúng gói ONNX INT8 đã chọn; chạy C2 trên Colab với backend Transformers. Thử ít mẫu trước, lưu phiên bản và precision thực tế.
- [ ] Dùng chung giao diện trả transcript và cùng scorer. Chạy FLEURS dev 361 mẫu; lưu đủ prediction/status cho từng ID của mỗi model.
- [ ] Hoàn thành dữ liệu tự thu dev của khoảng 2–3 người, mỗi người khoảng 20 đoạn, có người kiểm tra transcript. Chạy ba model trên dev này nếu đã đủ nhãn; ghi rõ số mẫu thực tế.
- [ ] Tạo bảng WER_ws/CER, số mẫu hoàn tất và vài ví dụ lỗi theo model. Điểm trên corpus/nhãn khác nhau đặt thành bảng riêng.
- [ ] Đăng ký tập 50 tệp dev cố định dùng đo Pi, các chỉ số và cấu hình thử ít nhất cần thiết. Hoàn tất quy tắc dữ liệu/nhãn/test trước các run cuối.

**Demo:** chọn 2–3 audio dev gồm câu thường, một câu có số/tên riêng và một đoạn khó; hiện ba transcript cạnh nhau. Sau đó mở bảng dev toàn bộ để tránh chỉ kết luận từ vài câu trình diễn. Giải thích một khác biệt thực tế và vì sao C2 chạy trên Colab còn C0/C1 được thử tiếp trên Pi.

**Xong khi:** ba model chạy được và output được chấm cùng giao thức; bảng có đúng corpus/split, coverage và cấu hình; điểm minh họa được phân biệt với điểm dev toàn tập. Nếu tập tự thu dev chưa đủ, đánh dấu rõ và bổ sung đầu tuần 3 trước khi chốt lựa chọn Pi.

**Bằng chứng:** ba run E1, bảng dev, ID của các câu demo và danh sách lỗi. Thời gian GPU của C2 không được đem xếp hạng ngang thời gian CPU của C1 như một phép đo công bằng.

**Dự phòng:** trình bày các output/metrics đã lưu, không tải model lại trong lớp. Giới hạn sửa lỗi runtime khoảng một ngày; nếu C2 không chạy được, thay bằng PhoASR theo đặc tả và ghi quyết định trước khi khóa ứng viên. Không lấy WER trên model card điền vào bảng của nhóm.

Thông điệp cần truyền đạt: **“Em đã so sánh các lựa chọn trên cùng dev; model mới là đối tượng nghiên cứu, chưa mặc định là lựa chọn tốt nhất cho Pi.”**

## B03 — Chuyển từ máy mạnh sang phần cứng đích

**Mục tiêu:** ít nhất một ứng viên nhỏ chạy được trên Pi; có số đo để chọn cấu hình, thay vì chọn theo cảm giác.

Việc làm trước buổi học:

- [ ] Chạy C0 qua whisper.cpp và C1 qua sherpa-onnx trên Pi. Giữ một bộ WAV đã chuyển đúng định dạng; xác nhận output tiếng Việt.
- [ ] Với C0, kiểm tra 5–10 mẫu giữa backend Colab và GGML. Ghi khác biệt nếu có; không giả định hai bản tương đương tuyệt đối.
- [ ] Đo 50 tệp dev đã đăng ký, warm-up và ba lượt; lưu RTF, RAM và nhiệt. Tách nạp model với warm inference; không dùng wall time của tiến trình mới làm warm time.
- [ ] Nếu cần, thử số luồng 1/2/4 trên một phần dev rồi khóa lựa chọn. Chỉ thử tiny nếu C0 chưa phù hợp; không mở thêm model khác.
- [ ] Tiếp tục thu test đã định nhóm người/phiên, khoảng 4–5 người và 80–100 đoạn trong kế hoạch đầy đủ; kiểm tra nhãn và sao lưu, chưa chấm bằng model để chọn cấu hình.

**Demo:** cho Pi xử lý một WAV, hiện transcript và log. Trình bày bảng benchmark của C0/C1, hoặc tiny nếu đã chạy; giải thích chất lượng, tốc độ và RAM ảnh hưởng quyết định thế nào. Nói rõ WAV nhanh chưa chứng minh hội thoại liên tục nhanh.

**Xong khi:** có run thực sự từ Pi với artifact/runtime được ghi; số đo có tập mẫu và cách tính; chốt ứng viên cho luồng micro. Nếu còn thiếu phép đo của một ứng viên, công bố phần thiếu và giới hạn thời gian bổ sung.

**Bằng chứng:** run E2, log Pi, bảng tốc độ/tài nguyên, quyết định chọn cấu hình và trạng thái dữ liệu test.

**Dự phòng:** dùng video/log đã chạy thành công trên Pi nếu thiết bị gặp lỗi tại lớp. Nếu Pi chưa chạy được ASR, demo inference tệp trên máy tính và phần input/hiển thị trên Pi với nhãn rõ “ASR chưa chạy trên Pi”; đưa lỗi cài đặt và phương án tiếp theo. Cắt partial và model mở rộng để ưu tiên sửa bước đích này.

Thông điệp cần truyền đạt: **“Đây là kết quả đo trên Pi thật; em chọn cấu hình theo đánh đổi đã quan sát.”**

## B04 — Tạo phụ đề từ âm thanh đang đến

**Mục tiêu:** chuyển từ xử lý tệp sang thu âm liên tục, chia đoạn bằng VAD và hiển thị final. Đây là buổi đầu có demo tương tác trực tiếp.

Việc làm trước buổi học:

- [ ] Nối micro → bộ đệm → VAD → worker ASR giữ model đã nạp. Callback thu không chờ inference; sample index giúp phát hiện frame bị mất.
- [ ] Dùng cấu hình endpoint/pre-roll/độ dài tối đa xuất phát từ đặc tả, chỉnh ít tham số trên dev nếu cần. Giữ cấu hình và lý do thay đổi.
- [ ] Hiển thị final trên terminal/cửa sổ đơn giản. Chưa cần partial, kính thật hoặc ứng dụng điện thoại.
- [ ] Replay phiên dev 10–15 phút đúng tốc độ thực; log mốc thu, kết thúc tiếng nói/VAD, đợi queue, inference và hiển thị. Kiểm tra câu nối nhanh, đầu/cuối câu và từ lặp.
- [ ] Chuẩn bị audio im lặng/tiếng động dev và quan sát phụ đề sai. Tiếp tục kiểm tra nhãn test; không sửa bằng gợi ý lấy từ test.

**Demo:** nói 2–3 câu vào micro, có một khoảng nghỉ; thấy phụ đề final xuất hiện. Chỉ ra khi VAD đóng đoạn và thời gian xử lý. Mở một đoạn log/đồ thị dev dài để cho thấy hệ có theo kịp hay queue đang tăng, thay vì chỉ dựa vào demo vài câu.

**Xong khi:** audio trực tiếp tạo được chữ và có log truy vết; phát lại liên tục không âm thầm bỏ đoạn; giới hạn tốc độ được ghi. Chất lượng/độ trễ còn thiếu mục tiêu được báo cáo trung thực, chưa cần tuyên bố mọi tiêu chí đã đạt.

**Bằng chứng:** run E3, video micro-to-text, log replay, lỗi VAD và số phụ đề sai trên dữ liệu dev không có lời nói.

**Dự phòng:** nếu không có micro, replay WAV theo tốc độ thực qua cùng VAD/queue/ASR và gọi đúng là replay. Nếu worker chưa theo kịp, demo chế độ từng lượt nói và số đo queue; không bỏ audio để tạo cảm giác thời gian thực. Giữ bản demo file của B03 hoạt động.

Thông điệp cần truyền đạt: **“Pipeline đã nhận âm thanh liên tục; em đang đo phần chênh giữa kết quả trên tệp và phụ đề thực tế.”**

## B05 — Hiển thị được và khóa phiên bản để đánh giá

**Mục tiêu:** một renderer có thể nhận sự kiện văn bản từ ASR và giao diện SLR, đồng thời hoàn tất điều kiện chạy test cuối.

Việc làm trước buổi học:

- [ ] Triển khai hợp đồng `caption_v1`: source, segment/sequence, kind và text UTF-8. Final chốt một lần; partial chỉ thử nếu final ổn định và còn thời gian.
- [ ] Dùng màn hình hiện có; kiểm tra dấu tiếng Việt, font, ngắt dòng và chữ không bị lặp do sự kiện trùng. Nếu có thiết bị kính, nối renderer phù hợp; nếu chưa, giữ màn hình thay thế.
- [ ] Nối output SLR thực nếu mô-đun đã có. Nếu chưa có, dùng sự kiện mẫu gắn nhãn mock để kiểm tra giao diện; không tuyên bố đã nhận dạng ký hiệu.
- [ ] Hoàn tất nhãn và manifest test, kiểm tra trùng người/phiên/hash và đủ mẫu. Chuẩn bị phiên test dài riêng và 10–20 phút không có tiếng nói; mốc thủ công phục vụ đo độ trễ.
- [ ] Khóa model/artifact/runtime, scoring, VAD, số luồng, split và tiêu chí; commit cấu hình khóa. Dừng thêm feature, giữ nguyên định nghĩa WER/CER và tỷ lệ phụ đề sai.

**Demo:** nói một câu, đưa final lên màn hình và kiểm tra dấu. Gửi sự kiện SLR vào cùng renderer, nêu rõ dữ liệu thật hay mock. Mở manifest/config đã khóa để giải thích tuần sau nhóm sẽ đánh giá gì và vì sao chưa dùng test để chọn.

**Xong khi:** renderer đọc được text tiếng Việt và xử lý đúng sự kiện; phạm vi tích hợp SLR/kính được ghi rõ; mọi điều kiện E4/E5 đã khóa. Nếu thiếu nhãn test, công bố phần thiếu và hoàn tất trước chạy E4, không lấp bằng nhãn máy chưa kiểm tra.

**Bằng chứng:** video hiển thị, kiểm tra hợp đồng/UTF-8, commit khóa cấu hình, manifest hash và checklist sẵn sàng E4/E5.

**Dự phòng:** demo trên màn hình HDMI/laptop nếu phần kính chưa có. Dùng mock chỉ cho giao diện SLR và chỉ rõ phần mô phỏng. Nếu final-only đã đáp ứng, giữ nó làm phiên bản cuối, dành thời gian còn lại cho dữ liệu và SLR.

Thông điệp cần truyền đạt: **“Luồng phụ đề đã có giao diện dùng chung; cấu hình được khóa để đánh giá cuối có ý nghĩa.”**

## B06 — Báo cáo kết quả cuối và chứng minh độ ổn định

**Mục tiêu:** trả lời RQ1–RQ3 bằng kết quả trên test đã khóa, kể cả những phần chưa đạt.

Việc làm trước buổi học:

- [ ] Chạy E4 cho ba ứng viên trên FLEURS test 857 mẫu và tập tự thu test. Lưu đủ ID/status; inference lỗi được giữ trong thống kê coverage và scoring theo đặc tả.
- [ ] Chạy toàn bộ tập tự thu test bằng đúng artifact/runtime chọn trên Pi; tách hàng GGML/Pi với HF/Colab nếu khác. Nếu tiny là cấu hình cuối, đánh giá theo cùng giao thức.
- [ ] Chạy E5: phiên test dài 10–15 phút phát đúng tốc độ thực, ba lượt; log RAM/nhiệt/queue/latency/gap. Chấm transcript nối final của toàn phiên, không chỉ các đoạn VAD phát hiện được.
- [ ] Đo phụ đề sai trên tập không có tiếng nói, final và partial riêng nếu bật partial. Báo chất lượng theo người/điều kiện và lỗi số/phủ định.
- [ ] Tạo bảng/hình từ output thật, viết lựa chọn cuối và giới hạn. Sao lưu run, config, manifest và báo cáo sang Drive/home server trước khi đóng phiên Colab.

**Demo:** mở bảng test và giải thích một kết luận có số liệu. Phát video ngắn của phiên dài, kèm biểu đồ queue/nhiệt/độ trễ đã đo. Trình bày một lỗi còn tồn tại và phân biệt nó do model, VAD, queue hay renderer khi có bằng chứng.

**Xong khi:** có đủ kết quả cuối hoặc lý do thiếu có log; tách rõ dev/test và Pi/Colab; cấu hình lựa chọn được giải thích bằng dữ liệu; không giấu OOM, timeout hoặc audio bị mất. Đạt quy trình đánh giá không đồng nghĩa mọi ngưỡng kỹ thuật đã đạt.

**Bằng chứng:** run E4/E5, bảng chất lượng/tài nguyên, hình có nguồn dữ liệu, danh sách lỗi và kết luận nháp.

**Dự phòng:** không chạy lại toàn bộ benchmark trong lớp; mở artifact đã lưu. Nếu E4/E5 bị ngắt, ghi phạm vi đã chạy và tiếp tục các ID còn thiếu với cùng config. Demo trạng thái một phần có nhãn rõ, không gọi bảng thiếu là bảng kết quả cuối. Không fine-tune hoặc chọn lại cấu hình từ các lỗi test vừa thấy.

Thông điệp cần truyền đạt: **“Em đã có kết quả held-out và bằng chứng chạy liên tục; đây là lựa chọn phù hợp trong phạm vi đã thử và những giới hạn của nó.”**

## B07 — Demo toàn luồng và bàn giao để nhóm dùng tiếp

**Mục tiêu:** gom các phần đã làm thành một bản thử nghiệm có thể chạy lại và một báo cáo người khác đọc hiểu được.

Việc làm trước buổi học:

- [ ] Tạo hướng dẫn khởi động từ môi trường đã chuẩn bị: vị trí model, input, lệnh/ô notebook cần chạy, output và cách dừng. Kiểm tra lại sau khi restart tiến trình.
- [ ] Chạy lại một phần nhỏ với config đã lưu để xác minh đường dẫn/scorer; không mở vòng chọn model mới. Đối chiếu ID/status và giải thích khác biệt nếu có.
- [ ] Hoàn thiện báo cáo: câu hỏi, model, dữ liệu/nhãn, giao thức, kết quả, bản thử nghiệm, giới hạn và phần STT nối SLR. Dùng số của E4/E5, không thay bằng số nguồn ngoài.
- [ ] Chuẩn bị demo 5 phút và video 60–90 giây; mang nguồn/micro, audio, bảng kết quả và bản sao trên laptop. Phần cài/tải model phải xong trước buổi học.
- [ ] Commit mã/tài liệu và lưu gói kết quả. Ghi rõ phiên bản, quyền sử dụng dữ liệu và phần đã/ chưa tích hợp trên kính thật.

**Demo:** chạy micro → ASR → phụ đề, sau đó thể hiện luồng SLR nếu đã có hoặc nhắc rõ phần giao diện còn mock. Mở bảng cuối để giải thích vì sao chọn model này thay vì chỉ chọn model mới nhất. Cho thấy một run có thể truy về config, manifest và output.

**Xong khi:** bản thử nghiệm khởi động lại được, kết quả có nguồn, báo cáo khớp artifact và nhóm biết cách dùng tiếp. Nếu chưa đạt xử lý liên tục, trình bày chế độ từng lượt cùng giới hạn đã đo; không đổi tên nó thành thời gian thực đã đạt.

**Bằng chứng:** README chạy demo, report cuối, video, commit bàn giao, config/checksum và đường dẫn bản sao kết quả.

**Dự phòng:** dùng video của chính phiên bản bàn giao và artifacts lưu cục bộ; chỉ rõ live hay ghi trước. Nếu thiết bị lỗi, phần kết quả nghiên cứu vẫn có thể kiểm tra từ log và predictions. Không sửa feature gấp trong lớp làm mất phiên bản đã đánh giá.

Thông điệp cần truyền đạt: **“Nhóm có một pipeline STT cơ bản, đã so sánh model hiện có và biết giới hạn trên Pi; phần này sẵn sàng phục vụ hướng SLR của đề tài.”**

## Công việc song song và các mốc phải giữ

| Công việc | Bắt đầu | Hoàn tất cần thiết |
|---|---|---|
| Micro, nguồn và tản nhiệt Pi | B01 | Sẵn sàng trước B03/B04; thiếu micro phải có replay dự phòng |
| Pilot và scorer chung | B01 | Trước khi so sánh điểm ở B02 |
| Tự thu dev, nhãn đã kiểm tra | B01–B02 | B02 hoặc đầu tuần 3 trước chốt cấu hình Pi |
| Tự thu test, phiên dài và bộ không có lời nói | B03 | Trước khóa B05, chưa dùng chọn cấu hình |
| Giao diện SLR/kính | Chuẩn bị từ B01, nối ở B05 | B05 có renderer và trạng thái tích hợp rõ ràng |
| Viết báo cáo và lưu bằng chứng | Sau từng buổi | B06 có kết luận nháp, B07 có bản cuối |

Cuối tuần 3 phải biết Pi chạy được gì. Cuối tuần 4 phải có bản thử nghiệm cơ bản hoặc chế độ từng lượt có giới hạn rõ. Cuối tuần 5 dừng thêm tính năng và khóa đánh giá. Nếu chậm, cắt theo thứ tự: model mở rộng → partial → phần kính chưa có; giữ scorer, bằng chứng Pi và đánh giá test.

Đối với từng thay đổi mã hoàn chỉnh, cập nhật tài liệu/test, chạy test liên quan rồi commit theo `AGENTS.md`. Một buổi có thể có nhiều commit; không đợi đến ngày demo mới gom tất cả. Không push, chia sẻ audio hoặc gửi báo cáo ra ngoài nếu chưa có chỉ dẫn tương ứng.

## Bộ bằng chứng và bảng theo dõi sau mỗi buổi

Dùng `reports/demo_sessions/B01.md` đến `B07.md` làm nhật ký ngắn khi triển khai; video/output lớn lưu ngoài Git theo chính sách dữ liệu. Đây là các đường dẫn **dự kiến**, chưa có file/run. Một báo cáo buổi chỉ cần:

```text
Buổi / ngày:
Commit được demo:
Điểm mới so với buổi trước:
Dữ liệu: pilot / dev / test / demo riêng:
Thiết bị, model, runtime và run ID:
Đã demo gì: live / replay / video ghi trước / mock giao diện:
Kết quả đo và đường dẫn bằng chứng:
Lỗi hoặc phần chưa đạt:
Phản hồi của thầy:
Việc tiếp theo:
```

| Buổi | Trạng thái ban đầu | Commit / run / bằng chứng khi hoàn thành |
|---|---|---|
| B01 | Chưa thực hiện | — |
| B02 | Chưa thực hiện | — |
| B03 | Chưa thực hiện | — |
| B04 | Chưa thực hiện | — |
| B05 | Chưa thực hiện | — |
| B06 | Chưa thực hiện | — |
| B07 | Chưa thực hiện | — |

Chuẩn bị 3–5 câu pilot/dev làm bộ demo cố định để thấy thay đổi qua các tuần. Có thể chọn ví dụ dễ/khó để giải thích, nhưng điểm đánh giá phải lấy toàn tập đã quy định; bộ trình diễn không thay test. Câu thầy nói trực tiếp là minh họa mới, không tự trở thành điểm benchmark.

## Cách bắt đầu làm từng buổi với Codex

Gửi yêu cầu theo mã buổi, ví dụ: “Thực hiện B01 trong `PLAN_DEMO_STT_7_BUOI.md`. Đọc đặc tả trước, kiểm tra những gì đã có, triển khai phần cần cho demo B01, chạy kiểm tra phù hợp, lưu bằng chứng và commit. Chưa làm sang B02.” Các buổi sau dùng cùng mẫu, thay mã buổi và thêm phản hồi của thầy nếu có.

Khi đủ tiêu chí của một buổi, cập nhật trạng thái và nhật ký. Nếu chưa đủ, ghi phần đã làm và blocker; vẫn chuẩn bị một demo có bằng chứng theo phương án dự phòng. Không đánh dấu toàn buổi hoàn thành chỉ vì đã viết kế hoạch hoặc có một video mẫu của người khác.

## Kiểm tra bản kế hoạch này

Kiểm tra tài liệu đã đạt: đủ B01–B07, mỗi buổi có bảy phần hướng dẫn và năm việc chuẩn bị, tổng 35 việc; liên hệ E0–E5; khóa trước test; liên kết tệp tồn tại; code fence cân bằng; không có lỗi Unicode/khoảng trắng. Đã xác nhận đặc tả và các tài liệu gốc không thay đổi. Không có inference, thu âm hoặc phép đo phần cứng mới được thực hiện trong lần lập kế hoạch.
