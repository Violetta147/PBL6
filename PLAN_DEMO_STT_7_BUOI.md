# Kế hoạch lean: 7 buổi học và demo STT

Phiên bản 3.0 — cập nhật 13/10/2026 sau rà soát phép đo. Một người phụ trách STT, một buổi gặp thầy mỗi tuần; giữ khung bảy buổi. B01–B07 là các mốc nội dung, không có nghĩa đã qua bốn tuần hoặc đã demo bốn lần. Chưa có lịch gặp cụ thể được xác nhận.

Mục tiêu: hiểu và so sánh các model có sẵn đủ để lựa chọn có căn cứ, rồi tạo pipeline STT cơ bản phục vụ hướng nghiên cứu kính thông minh. Ưu tiên một đầu ra nhỏ chạy được và giải thích được; không mở thêm model, huấn luyện hoặc UI lớn nếu chưa cần. Zipformer là ứng viên tạm thời, chưa phải kết luận model/kiến trúc tốt nhất.

**Trạng thái hiện tại:** B01–B03 có output và bảng dev. B04 đã có số đo riêng của Zipformer và khảo sát Whisper, nhưng **C0 Whisper-base chưa chạy đủ self dev20/Pi và phép so tốc độ cùng điều kiện chưa hoàn tất**. Tiny không thay C0-base. B05 chưa triển khai; Pi chưa có micro. Chưa xác nhận đã trình bày với thầy.

Dùng kế hoạch này để xác định việc tiếp theo. [Tiến độ thực hành](experiments/PROGRESS.md), [báo cáo demo](reports/DEMO_BUOI_01_04.md), [bản đồ pipeline](reports/PIPELINES_BUOI_01_04.md) và [điểm chưa chặt](reports/DIEM_CHUA_CHAT_BUOI_01_04.md) dẫn tới bằng chứng. [Đặc tả](SPEC_ASR_PI4_RESEARCH_20261009.md) và [ghi chú khái niệm](REVIEW_CONCEPTS_20261009.md) là tài liệu tra cứu; chưa mặc định mọi phần của chúng đã đồng bộ với quyết định mới trong kế hoạch này.

## Nhịp làm việc mỗi tuần

Chọn một đầu ra nhỏ, làm cho chạy được, lưu output rồi tập demo khoảng 3–5 phút. Trình bày: tuần này thêm gì → cho thấy kết quả → một lỗi/điều học được → bước tiếp theo. Video ngắn và bảng đã lưu là dự phòng khi mạng/thiết bị lỗi; luôn nói rõ live hay ghi trước. Không lấy output người khác hoặc dữ liệu mock làm kết quả model của nhóm.

Giữ notebook so sánh, script/CLI Pi, bảng/output đã lưu và báo cáo gộp B01–B04 trong reports/. Không cần dashboard hoặc một bộ báo cáo riêng cho từng stage. Trước demo, tự giải thích được input, model/runtime, phạm vi đo và giới hạn; không lấy hình đẹp thay kiểm tra bằng chứng. Mỗi thay đổi mã hoàn chỉnh cập nhật tài liệu/test, chạy kiểm tra liên quan rồi commit theo `AGENTS.md`.

## Bảy buổi

| Buổi | Vì sao cần bước này | Đầu ra nhỏ để demo |
|---|---|---|
| B01 | Hiểu audio thành chữ và lỗi được tính ra sao | Một WAV, transcript và WER tính tay |
| B02 | So hai baseline trên cùng dữ liệu | Hai transcript và bảng WER_ws/CER |
| B03 | Đối chiếu model mới và dữ liệu tự thu | Hai bảng ba model, một lỗi thật |
| B04 | Kiểm tra phần cứng và sửa phép so chưa đồng nhất | WAV trên Pi, số đo rõ phạm vi; C0-base đầy đủ còn phải làm |
| B05 | Ghép chức năng STT cơ bản | Audio đến dần → chốt đoạn nếu cần → ASR → hiện chữ |
| B06 | Kiểm tra lựa chọn trên dữ liệu mới và luồng thực tế | Chất lượng, thời gian chờ, RAM và lỗi pipeline |
| B07 | Giải thích được điều đã làm và giới hạn | Demo 3–5 phút, kết luận và báo cáo ngắn |

Buổi 1–5 dùng pilot/dev để học và lựa chọn. Thu/kiểm tra nhãn test được phép; chỉ xem prediction/điểm test để đánh giá sau khi ghi cố định cấu hình ở cuối B05. Câu thầy nói trực tiếp là minh họa, không tự thành một benchmark. Hoàn thành lượt chạy và đã demo với thầy là hai trạng thái riêng.

## B01 — Chạy một câu qua baseline

- [x] Chọn 10 audio FLEURS train; kiểm tra transcript và input.
- [x] Chạy C0 Whisper-base, lưu text và model/môi trường; lần đã đo dùng CPU laptop do Computer Use/Colab lỗi, notebook Colab có sẵn để chạy lại.
- [x] Xác nhận Pi 4B 8 GB và thiết bị thu dev Samsung Galaxy M15, ứng dụng ghi âm có sẵn, khoảng cách xấp xỉ 30 cm. Micro để nối trực tiếp Pi vẫn chưa chốt.
- [x] Nghe mẫu pilot 18182759805207678941, xác nhận nhãn đúng và tính WER theo output DEMO; người thực hiện xác nhận ngày 13/10/2026. Output khớp kết quả đã lưu: 4 thay thế / 13 đơn vị ≈ 30,77%. Không bắt buộc nghe/tính tay cả 10 câu.

**Demo:** phát audio và hiện text do model tạo. Chỉ ra model nhận đúng/sai ở đâu. **Xong khi:** chạy lại được, output có lưu và giải thích được audio → model → text. Chưa cần Pi inference hoặc bộ chấm hoàn chỉnh trong buổi đầu.

## B02 — So hai model và học cách chấm

- [x] Viết hàm chuẩn hóa/scorer chung; kiểm tra dấu tiếng Việt, lỗi chèn/xóa/thay và nhãn rỗng bằng đáp án tính tay.
- [x] Chạy C0/C1 trên 100 FLEURS dev đã chọn cố định; giữ đủ output/status.
- [x] Hoàn thành 20 câu dev chính ngày 13/10: 2 phòng ngủ, 18 cà phê; người thực hiện nghe xác nhận nhãn, metadata/manifest/WAV đã kiểm tra. Hai baseline chạy đủ 20/20, bảng riêng đã lưu. Hai bản cà phê câu 01–02 giữ ngoài bộ chính. Test tự thu sẽ dùng phiên/người khác khi có thể ở B05, giữ riêng đến khi chốt cấu hình; hiện chưa thu hoặc chạy test.

**Demo:** cùng một audio hiện hai transcript và cách tính WER/CER; mở bảng dev, chỉ một khác biệt đáng chú ý. **Xong khi:** hai model được chấm cùng dữ liệu/quy tắc. Nếu chưa đủ nhãn tự thu, hoàn thành trước khi chốt cấu hình ở B05.

## B03 — Thử model mới và hoàn thành so sánh

- [x] Chạy C2 Qwen3-ASR-0.6B trên Colab A100 bằng Transformers; đủ 100/100 cùng subset dev, output và metadata đã lưu.
- [x] Chấm ba model trên 100 FLEURS dev; chấm lại bằng JiWER khớp, bảng ba model đã lưu.
- [x] Chấm ba model trên self dev20, giữ bảng riêng. Qwen hoàn tất 20/20 trên A100 ngày 13/10, run `self_dev20_qwen_v1`; receipt/hash/nhãn và JiWER đã kiểm tra. WER_ws Whisper 27,6243%, Zipformer 0,5525%, Qwen 1,1050%. Output/bảng ba model ở B03/results/self_dev20. Cần nghe thêm câu 20 trước khi trình bày phân tích bằng nghe; không dùng kết quả FLEURS thay tự thu.
- [x] Nghe ba câu lỗi và đối chiếu nhãn/output, người thực hiện xác nhận ngày 10/10/2026; Zipformer là ứng viên thử trên Pi theo bảng dev, chưa khẳng định chất lượng phụ đề đã đạt. Test vẫn đóng.

**Demo:** ba transcript cạnh nhau và bảng chất lượng; [kịch bản B03](experiments/B03/DEMO.md) có năm audio để nghe. Trên dev đã đo, Zipformer WER_ws 7,5080%, Qwen 9,7605%, Whisper-base 49,3743%. Giải thích model mới năm 2026 giúp nghiên cứu điều gì, không mặc định nó thắng hoặc phải chạy trên Pi. **Xong khi:** có bảng ba model, output từng mẫu và nhận xét có căn cứ. Bảng self dev20 đã có; giữ riêng với FLEURS. Hai bảng là so các cấu hình có sẵn, không cô lập kiến trúc.

C2 hiện đã chạy đủ nên không cần chạy lại để thay model. Nếu một cấu hình ở lần sau lỗi, giữ log/status và báo đúng phần thiếu; model bổ sung phải có tên riêng, không thay âm thầm cấu hình baseline. Qwen vẫn chỉ chạy GPU theo phạm vi đã chọn, chưa thử ONNX INT8/CPU.

## B04 — Pi thật và phép đo baseline còn thiếu

**Vì sao:** phải biết ứng viên chạy trên Pi ra sao và có một phép đối chiếu đúng với C0. **Đánh đổi:** giữ model baseline dù chậm; chỉ đo đủ câu hỏi cần trả lời, không thêm nhiều cấu hình để làm dự án lớn.

- [x] Zipformer ONNX INT8 chạy thật trên Pi 4B 8 GB, CPU hai luồng, cùng gói model/hash như laptop; hai lượt cùng self dev20, 20/20 mỗi lượt.
- [x] Lưu số đo riêng C1: WER_ws 0,5525%, CER 0,1647%; inference 10,278/10,226 s cho 84,160 s audio, wall runner 14,644/14,578 s, peak RSS khoảng 199 MiB. Prediction từng lượt giống laptop.
- [x] Giữ Whisper-base smoke một câu và tiny hai lượt như khảo sát đã chạy. Tiny WER_ws 41,9889%, wall 172,807/171,309 s; nạp lại từng WAV. Không coi tiny là C0-base, không chia wall này cho inference C1 để báo tăng tốc.
- [ ] Giải thích được một lượt từ manifest đến JSONL/log và nguồn số 10,278/14,644 s; tập demo một WAV, chưa tự coi đã trình bày với thầy.
- [ ] Ghi giao thức đo bổ sung trước khi chạy: cùng self dev20/thứ tự WAV, Pi/CPU hai luồng, mỗi model nạp một lần cho cả lượt. Chọn cùng điểm bắt đầu/kết thúc đo và ghi rõ việc nào nằm trong thời gian đó; tách phần chấm điểm ra khỏi vùng đo chung.
- [ ] Giữ C0 là Whisper-base đa ngôn ngữ, chạy ít nhất một lượt đủ 20 WAV qua whisper.cpp. Ghi nguồn/hash/backend/kiểu số/giải mã; chậm là kết quả, không phải tiêu chí đổi sang tiny. Nếu không hoàn thành do giới hạn đã đặt, báo thiếu/timeout đúng trạng thái.
- [ ] Đo C1 bằng cùng giao thức bổ sung; lưu transcript, wall cả lượt gồm một lần nạp, thời gian nạp riêng nếu đo được, RAM/nhiệt và kiểm tra chất lượng. Chỉ báo inference/RTF inference riêng khi hai backend đo cùng vùng; nếu không thì dùng chỉ số chung đã định nghĩa.
- [ ] Tổng hợp bảng C0-base/C1 đúng tên cấu hình, cùng phạm vi và số mẫu. Một lượt đầy đủ/cấu hình là mức bắt đầu; chỉ lặp thêm khi cần kiểm tra độ ổn định hoặc có vấn đề mới.

**Demo:** một WAV → text trên Pi và mở số đo có nguồn; nói rõ phép đối chiếu nào còn thiếu. **Xong phần so sánh B04 khi:** C0-base và C1 có kết quả cùng bộ/cùng giao thức hoặc trạng thái thất bại được báo rõ; không dùng khảo sát tiny lấp vào C0. Chưa kết luận kiến trúc hoặc runtime tối ưu.

Có thể chuẩn bị pipeline C1 ở B05 trong khi phần đối chiếu B04 còn thiếu, nhưng phải theo dõi hai việc riêng. Nếu cắt phần so baseline vì giới hạn đề tài thì phải sửa mục tiêu/kết luận công khai, không đánh dấu đã hoàn thành so sánh.

## B05 — Dựng một pipeline STT nhỏ

**Vì sao:** nhận dạng WAV sẵn chưa trả lời cách tạo phụ đề khi audio đến dần. **Đánh đổi:** dùng final text theo từng đoạn trước; chưa cần partial, giao diện đẹp hoặc kính thật.

- [ ] Bắt đầu bằng replay WAV theo thời gian thực vì Pi chưa có micro; ghi rõ replay. Khi có micro mới thử đường thu trực tiếp, không coi replay là bằng chứng micro đã hoạt động.
- [ ] Dùng ví dụ/runtime có sẵn: audio đến dần → gom/chốt đoạn → ASR → hiện text. Nếu backend cần thì dùng VAD/chốt đoạn; không thêm VAD chỉ để đủ bước. Ghi rõ ASR nhận cả đoạn hay streaming nguyên sinh.
- [ ] Nạp ASR một lần khi khởi động, giữ trong RAM; mỗi đoạn chỉ tạo/đặt lại trạng thái nhận dạng. Nếu dùng VAD thì cũng nạp một lần. Không mở tiến trình/nạp trọng số lại cho từng đoạn.
- [ ] Dùng dev thử 5–10 phút: câu ngắn, khoảng nghỉ, nhiễu, số/phủ định. Ghi lỗi, đoạn bị cắt/mất và thời gian chờ; chỉnh đơn giản khi có bằng chứng cần thiết.
- [ ] Thu bộ tự thu mới khoảng 30–50 câu và khoảng hai phút không có lời nói. Ưu tiên thêm người nếu muốn kiểm tra người nói mới; nếu chỉ một người thì tách phiên/câu và ghi giới hạn. Không cần tự thu train.
- [ ] Trước đánh giá cuối, lưu cấu hình model/runtime/kiểu số, số luồng, tiền xử lý, giải mã, VAD/chốt đoạn nếu dùng, scorer và ID test. Kiểm tra nhãn không đồng nghĩa được dùng lỗi prediction test để chỉnh tiếp rồi gọi điểm sau là độc lập.

**Demo:** replay hoặc micro → chữ, một lỗi thật và cách giải thích. **Xong khi:** luồng lặp lại được, model được giữ nạp, output/log có nguồn và cách chốt đoạn được giải thích. Nếu chưa có micro thì ghi “xong replay, chưa thử micro”; màn hình kính không phải điều kiện chặn bước này.

## B06 — Đánh giá pipeline đã chốt, không mở thêm nhánh

**Vì sao:** cần kiểm tra lựa chọn trên dữ liệu chưa dùng để điều chỉnh. **Đánh đổi:** một bộ mới nhỏ, có mô tả rõ, thay vì bắt buộc mở rộng nhiều benchmark.

- [ ] Ưu tiên bộ tự thu mới để chấm bản model/runtime thực sự chạy trên Pi. Báo WER_ws/CER, số mẫu hoàn tất/lỗi và phạm vi người/phiên/môi trường; giữ output gốc.
- [ ] Thử pipeline micro hoặc replay 5–10 phút và phần không lời nói. Đo thời gian từ một mốc rõ ràng, ví dụ hết lời nói đến khi chữ xuất hiện; ghi cả chờ chốt đoạn/VAD, xử lý và hiển thị theo vùng đã chọn. Không thay độ trễ này bằng inference của WAV sẵn.
- [ ] Ghi peak RAM, các đoạn mất/cắt sai, chữ sinh khi không có lời nói và trường hợp số/phủ định sai. “Chưa đo” để trống/ghi chưa đo, không điền 0.
- [ ] Nếu báo so chất lượng ba model trên bộ mới, chạy cả C0/C1/C2 trên đúng cùng WAV/reference và scorer; Qwen ở GPU. Giữ bảng đó riêng với đánh giá pipeline end-to-end và bảng hiệu năng Pi.
- [ ] Chỉ mở lại cấu hình khi có lỗi cần xử lý. Bản sửa sau khi xem test phải ghi là bản điều chỉnh; điểm trên tập đã xem không còn là đánh giá độc lập của lựa chọn mới.

**FLEURS test200:** chuyển thành phần bổ sung khi cần tái lập/đối chiếu benchmark và còn thời gian; không là điều kiện chặn pipeline. Nếu chạy, chốt subset trước và giữ giới hạn chưa xác minh FLEURS trong train của checkpoint. Không gán điểm subset/WER_ws thành benchmark toàn tập hoặc WER đã tách từ.

**Demo:** bảng chất lượng + độ trễ/RAM của pipeline + một lỗi đáng chú ý. **Xong khi:** chỉ số có định nghĩa, đúng cấu hình/thiết bị/tập và có raw để kiểm tra; báo trung thực nếu chưa đạt nhu cầu. Không cần chứng minh sử dụng tốt cho mọi người/môi trường.

## B07 — Demo và báo cáo phần đã kiểm chứng

- [ ] Viết lệnh khởi động và cách chạy một lượt nhỏ; kiểm tra lại được trên thiết bị đã dùng.
- [ ] Hoàn thiện báo cáo ngắn từ output có sẵn: mục tiêu, quyết định model/runtime, dữ liệu, cách đo, kết quả, lỗi và giới hạn. Dùng reports/ làm tài liệu trình bày, không lấy sơ đồ đẹp thay bằng chứng.
- [ ] Tập demo 3–5 phút và video dự phòng; tự trả lời được vì sao chọn, cách chạy, thời gian gồm gì, chưa kết luận được gì. Ghi rõ dùng công cụ hỗ trợ như thế nào khi trình bày phương pháp.
- [ ] Bàn giao mã, cấu hình, raw/output và những việc còn thiếu; không ghi kết quả kính/micro/streaming chưa làm thành đã hoàn tất.

**Demo:** audio → text, mở một bảng để giải thích lựa chọn và một lỗi/giới hạn. **Xong khi:** pipeline nhỏ chạy lại được, báo cáo khớp output và người thực hiện giải thích được phần mình trình bày. Không bắt buộc một sản phẩm kính hoàn chỉnh hoặc thuật toán mới.

## Cách giảm tải mà không làm lệch câu hỏi

Giữ dữ liệu/output đã có; không chạy lại chỉ để có tên run mới. Chưa thêm model, thử Qwen CPU, huấn luyện, bộ sửa lỗi văn bản, dashboard hoặc pipeline streaming khác. Hai luồng là cấu hình cố định đã thử, chưa gọi tối ưu. VAD là thành phần lựa chọn theo cách chốt đoạn, không là một đề tài riêng.

Cắt phần mở rộng như partial, tích hợp kính chưa sẵn sàng và FLEURS test bổ sung trước. Giữ ba việc cốt lõi: hiểu kết quả đã chạy, hoàn tất hoặc báo đúng giới hạn phép so baseline đã nhận, và có pipeline STT nhỏ đo được. Không đổi baseline để làm nó đủ nhanh rồi gọi đó là cùng thí nghiệm; không tạo số liệu để làm báo cáo đủ mục.

## Theo dõi trạng thái

| Mốc | Trạng thái thực tế ngày 13/10 | Phần còn thiếu |
|---|---|---|
| B01 | Đã chạy pilot và nghe/đếm một mẫu | Tập/demo với thầy chưa xác nhận |
| B02 | Hai baseline, FLEURS dev100 và self dev20 | Tập/demo với thầy chưa xác nhận |
| B03 | Ba model có bảng và audit cùng scorer | Nghe thêm lỗi câu 20 nếu phân tích bằng nghe; demo chưa xác nhận |
| B04 | C1/Pi đã đo; C0-base smoke và tiny bổ sung đã có | C0-base đủ 20 WAV, giao thức/tốc độ đồng nhất; chưa hoàn tất phần so sánh |
| B05 | Chưa triển khai; Pi chưa có micro | Replay pipeline trước, micro khi có thiết bị, cấu hình chốt |
| B06 | Chưa đánh giá cuối | Bộ mới nhỏ và số đo pipeline theo cấu hình đã chốt |
| B07 | Có tài liệu demo sơ bộ trong reports/ | Tập demo, báo cáo cuối và bàn giao |

Mỗi mốc lưu vài dòng: vì sao làm → cấu hình đã chạy → output ở đâu → lỗi/điều học được → việc tiếp theo. Không có ngày hẹn cụ thể nên chưa gán mốc lịch hoặc tự suy buổi nào đã gặp thầy.

## Việc làm tiếp theo

1. Đi qua một WAV và raw/log cùng mã để người thực hiện giải thích được luồng, scorer và nguồn thời gian; rà các điểm trong reports/DIEM_CHUA_CHAT_BUOI_01_04.md.
2. Chốt giao thức B04 bổ sung và hoàn tất C0-base/C1 cùng bộ/cùng phạm vi. Đây là thí nghiệm còn thiếu, không phải nhiệm vụ đã được thực hiện khi sửa file kế hoạch.
3. Dựng replay pipeline C1 theo B05; có thể chuẩn bị song song bước 2, nhưng giữ trạng thái và kết luận riêng.

## Những thay đổi so với bản 2.0

- Sửa trạng thái B04 từ hoàn tất sang còn thiếu C0-base/Pi và phép so tốc độ đồng nhất; tiny chỉ là khảo sát bổ sung.
- Giữ bảy mốc trong cùng một file; ưu tiên pipeline cơ bản và thí nghiệm trả lời quyết định cụ thể.
- B05 bắt đầu replay do chưa có micro, model giữ trong RAM; VAD chỉ dùng khi cần cho chốt đoạn.
- B06 ưu tiên bộ tự thu mới nhỏ và đánh giá pipeline; test200 FLEURS là bổ sung, không chặn chức năng cơ bản.
- Bổ sung điều kiện giải thích được phương pháp trước demo; không đồng nhất trạng thái có output, hoàn tất phép so và đã trình bày với thầy.
