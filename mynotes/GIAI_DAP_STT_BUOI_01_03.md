- [ ] Chọn một đầu ra nhỏ, làm cho chạy được, lưu output
- [ ] Tuần này thêm gì → cho thấy kết quả → một lỗi/điều học được → bước tiếp theo


Một notebook so sánh nghĩa là sao?
-> Một notebook để đọc prediction đã lưu, chấm điểm, hiện bảng và nghe các mẫu cần so sánh. Không có nghĩa mọi thí nghiệm phải nằm trong một file; hiện mỗi buổi có notebook riêng.
Có phải một notebook nghĩa là nó sẽ aggregates kết quả từ nhiều thí nghiệm được stored ở google drive vào chung một chỗ để so sánh không?
-> Đúng. Nó có thể đọc kết quả các lần chạy trên Drive rồi tổng hợp, miễn cùng dữ liệu và quy tắc chấm; không cần chạy lại model chỉ để xem bảng.
Script/CLI Pi khi cần nghĩa là ?
-> Script là file chương trình; CLI là chạy chương trình bằng lệnh terminal. Trên Pi, cách này đủ để nhận WAV hoặc micro và in chữ, không cần giao diện riêng.
Tôi tưởng nếu đã có notebook ở trên để aggreagate rồi thì sao lại còn có "Một bảng kết quả và ghi chú tiến độ ngắn"?
-> Bảng là đầu ra được notebook lưu để xem lại mà không chạy notebook. Ghi chú tiến độ ghi phần đã xong, còn thiếu và bước tiếp theo; đó không phải một hệ thống bổ sung.
Chưa cần UI, dashboard hoặc báo cáo riêng từng stage nghĩa là sao?
-> Chưa làm giao diện ứng dụng, trang theo dõi kết quả hoặc báo cáo riêng cho mỗi giai đoạn. Notebook, bảng đã lưu và vài dòng ghi chú đủ cho giai đoạn này.
Tôi tưởng chúng ta chưa cần xây dựng ứng dụng / web hoặc dashboard phần mềm?
-> Đúng, hiện chưa cần. Hiển thị text trong notebook hoặc terminal đã đủ cho thí nghiệm STT.
Tôi tưởng mỗi thí nghiệm là 1 chu kỳ đi qua toàn bộ stages?
-> Không bắt buộc. Mỗi thí nghiệm có ==🟡câu hỏi==, cấu hình, lần chạy và đánh giá; có thể dùng lại dữ liệu/mã đã kiểm tra. Các buổi chia nhỏ công việc, không lặp toàn bộ quy trình từ đầu.
Tôi chưa hiểu "Buổi 1–5 dùng pilot/dev để học và điều chỉnh. Test chỉ dùng đánh giá sau khi chốt ở cuối buổi 5. Câu trình diễn thầy nói trực tiếp là minh họa, không tự trở thành điểm benchmark."
-> Pilot dùng kiểm tra luồng; dev dùng thử và chọn cấu hình. Cuối buổi 5 chốt cấu hình rồi mới đánh giá trên test, tránh chọn theo điểm test. Câu thầy nói trực tiếp chỉ minh họa vì chưa có bộ nhãn và quy trình chấm cố định.

Có phải từ buổi 1 tới buổi 3 là như này?
Buổi 1:
Chọn 10 file wav từ tập train của FLEURS -> Soi cái transcript có đúng với âm thanh (input) hay chưa
Đưa 10 file wav này vào Whisper-base (mô hình C0) là baseline, lưu output text từ model, môi trường điều kiện chạy
Rồi đối chiếu thử 1 output với audio, tính WER bằng tay, quyết định xem dùng Rasberry Pi mấy, Microphone hay điện thoại

-> Cơ bản đúng. Mười câu train chỉ dùng pilot, không huấn luyện Whisper. Pi đã chốt là Pi 4B 8 GB; thiết bị thu dev là Galaxy M15 với ứng dụng ghi âm có sẵn, cách miệng khoảng 30 cm. Output/môi trường đã lưu; ngày 13/10 bạn xác nhận đã nghe đúng mẫu pilot, nhãn đúng và đã tính được WER theo output DEMO.

Buổi 2:

Tôi chưa hiểu hàm chuẩn hóa hoặc scorer chung là gì?
-> Chuẩn hóa đưa reference và prediction về cùng quy tắc viết: chữ thường, Unicode NFC, xử lý dấu câu/khoảng trắng, giữ dấu tiếng Việt và chữ số. Scorer chung là cùng một hàm tính WER/CER cho mọi model.
Kiểm tra dấu tiếng việt là sao?
-> Kiểm tra dấu được giữ và chấm đúng: “cọ” khác “cộ”. Hai cách mã hóa Unicode của cùng một chữ có dấu phải được coi là giống nhau sau NFC.
Giải thích ngắn gọn lỗi chèn/xóa/thay thế và nhãn rỗng
-> Chèn: “tôi đi” → “tôi đang đi”; xóa: “tôi đi học” → “tôi học”; thay: “đi” → “về”. Nhãn rỗng là reference không có chữ; khi đó không chia WER cho 0 mà kiểm tra model có sinh chữ khi không có lời nói hay không.
- [ ] Thu và kiểm tra khoảng 20 câu dev của nhóm, ghi điều kiện và người/phiên; chuẩn bị kế hoạch test tách biệt sẽ được thực hiện như nào?
-> Thu đủ 20 file riêng, nghe lại và sửa nhãn theo lời thực sự nói; ghi mã người nói, phiên, thiết bị và điều kiện. Giữ bản gốc, chuẩn hóa WAV và tạo manifest trước khi chấm. Test thu ở phiên/người khác khi có thể, để riêng và chưa dùng chọn cấu hình.

C1 là model gì?
-> C1 là hynt/Zipformer-30M-RNNT-6000h, dùng bản ONNX INT8 có sẵn qua sherpa-onnx. Đây là model nhỏ chuyên tiếng Việt đang được ưu tiên thử trên Pi.
Chạy xong C1 trên 100 files wav của tập dev FLEURs thì vẫn sẽ lưu trữ output như buổi 1 phải không?
-> Đúng. Buổi 2 lưu prediction từng câu, metadata lần chạy và điểm tổng hợp; C0 cũng được chạy trên cùng 100 câu dev để so với C1, không lấy điểm pilot buổi 1 thay vào.
dev có phải validation?
-> Đúng trong dự án này: dev là tập validation để thử và chọn cấu hình. Vì dùng model có sẵn, nó không phải validation theo từng epoch huấn luyện.
Ta có phải chuẩn bị so sánh demo bằng việc chuẩn bị 1 audio trong 100 FLEURs dev không?
-> Đúng, chọn một câu đã chạy, có audio, nhãn và output của cả hai model. Không chạy riêng câu đẹp rồi coi nó đại diện toàn bộ tập.
Nếu có thì ta sẽ tiếp tục hiện 2 cái transcript out prediction của model và WER/CER phải không?
-> Đúng: phát audio, hiện reference và hai prediction, kèm WER/CER của câu. Điểm toàn bộ 100 câu được trình bày riêng.
mở bảng dev là sao nhỉ?
-> Là mở bảng điểm trên FLEURS dev100 đã lưu, ví dụ summary.csv của B02; comparison.csv chứa đối chiếu từng câu. Không phải mở tập test hoặc bảng tự thu.
chỉ một khác biệt đáng chú y là sao nhỉ?
-> Chọn một điểm cụ thể để giải thích, chẳng hạn model nào giữ đúng “không” hoặc tên riêng mà model kia nhận sai. Dẫn audio và output thật để chứng minh.
Ở buổi 3 ta có phải:
1. Cài C2 Qwen3-ASR-0.6B trên colab A100 rồi lưu vào drive không?
-> Đúng, cài thư viện và nạp Qwen trên runtime GPU Colab; lưu prediction, metadata và bảng vào Drive. Không cần lưu cả môi trường Colab vào Drive. Lần A100 ngày 10/10 đã chạy xong, không cần chạy lại.
2. bằng Transformers là sao nhỉ?
-> Transformers là thư viện Hugging Face dùng để nạp và chạy model. Đây là công cụ inference, không có nghĩa ta huấn luyện Qwen hoặc tự xây kiến trúc Transformer.
100/100 cùng subset dev là cùng với 100 mẫu đã chạy cho C1 ở trên hả?
-> Đúng, cùng 100 WAV, reference và quy tắc chấm đã dùng cho cả C0 và C1. “100/100” nghĩa là đã xử lý đủ 100 mẫu.
Và ở buổi 3 sau khi chạy C2 vẫn lưu output và metadata như buổi 2 và buổi 1 chứ?
-> Đúng. Kết quả Qwen nằm trong runs/qwen_gpu_20261010_023946 trên Drive; bản sao prediction/metadata và bảng ba model nằm trong B03/results của dự án.
Có vẻ ta vẫn chưa score 3 model trên 20 file tự thu (tập validation) thì phải?
-> Đúng, bảng ba model self dev20 còn chờ Qwen. Ngày 13/10 đã đủ 20 câu chính (2 phòng ngủ/18 cà phê), nhãn nghe xác nhận, WAV/metadata/manifest đã kiểm tra. Whisper/Zipformer đã chạy đủ 20/20; hai bản cà phê câu 01–02 và bảng bốn bản cũ giữ riêng. Qwen tự thu chờ bạn chạy notebook GPU riêng.
Sau có cần 1 bảng riêng nữa đúng ko?
-> Đúng, bảng self dev20 tách khỏi bảng FLEURS dev100. Không gộp điểm hai nguồn thành một số rồi bỏ tên dữ liệu.

Tôi đã làm "Nghe ba câu lỗi và đối chiếu nhãn/output, người thực hiện xác nhận ngày 10/10/2026; Zipformer là ứng viên thử trên Pi theo bảng dev, chưa khẳng định chất lượng phụ đề đã đạt. Test vẫn đóng." cái này như nào?
-> Bạn phát ba audio ở ô cuối notebook Qwen, đọc reference và ba prediction, gửi toàn bộ transcript vào chat, rồi xác nhận đã nghe và đối chiếu cả ba. Tôi đã ghi nhận; việc đó chưa chứng minh mọi nhãn dev100 đều đúng.

ba transcript cạnh nhau và bảng chất lượng là gì, cái bảng này lưu ở đâu vậy?
-> Ba transcript là ba prediction cho cùng một audio, đặt cạnh reference để đối chiếu. Bảng tổng hợp ở [summary.csv](<C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/PBL6/experiments/B03/results/summary.csv>); chi tiết từng câu ở [comparison.csv](<C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/PBL6/experiments/B03/results/comparison.csv>).
Tôi tưởng có 1 bảng riêng ở trên khi score 3 model trên 20 file tự thu thập rồi hay là cái này là khác?
-> Có hai nguồn riêng: bảng FLEURS dev100 đã có; bảng self dev20 chưa có. Mỗi nguồn đều có thể có bảng điểm tổng hợp và bảng chi tiết từng câu.
Rồi tự nhiên có kịch bản B03 có 5 audio để nghe là sao?
-> Đó là năm mẫu chọn từ kết quả FLEURS dev100 đã chạy: ba câu Qwen lỗi nhiều và hai câu Qwen tốt hơn Zipformer. Chỉ để nghe và trình bày cân bằng, không phải năm thí nghiệm mới.
Trên dev đã đo là dev của FLEURS à?
-> Đúng. Các điểm đã báo cho ba model hiện là trên 100 mẫu FLEURS vi_vn dev, không phải 20 câu tự thu.
Mọi thứ đang khá lộn xộn khi không phân biệt trong tài liệu về dev của nhóm tự thu hay dev của tập dữ liệu nổi tiếng
-> Bạn đúng, cách ghi “dev” chung chung gây nhầm. Trong phần giải đáp này: FLEURS dev100 là dữ liệu công khai đã chấm; self dev20 là dữ liệu tự thu chưa chấm. Hai nguồn phải được gọi tên và báo điểm riêng.

Giải thích model mới năm 2026 giúp nghiên cứu điều gì, không mặc định nó thắng hoặc phải chạy trên Pi?
-> Model năm 2026 giúp kiểm tra liệu lựa chọn mới có nhận tiếng Việt, số và tên riêng tốt hơn các baseline hay không. Kết quả phải đo trên cùng audio; model mới có thể thua và chỉ làm đối chiếu trên Colab nếu không phù hợp tài nguyên Pi.

Tôi thấy có thể thử thêm PhoASR, bạn thấy sao?
-> Có thể thử thêm [PhoASR-whisper-small của Qualcomm](https://huggingface.co/Qualcomm-AI-Research/PhoASR-whisper-small), là Whisper-small đã được tác giả fine-tune cho tiếng Việt. Tôi đề xuất thử sau khi xong self dev20, trên cùng dữ liệu/scorer và GPU Colab; không cần tự huấn luyện, chưa mặc định tốt hơn hay chạy được tốt trên Pi.

[BỨC TRANH TOÀN CẢNH]
SUmmarization:

Buổi 1 kiểm tra audio → Whisper bằng 10 mẫu pilot; buổi 2 dùng scorer chung so Whisper/Zipformer trên FLEURS dev100; buổi 3 thêm Qwen trên cùng tập. Tiếp đó hoàn thành bảng self dev20 riêng để biết lỗi trong điều kiện tự thu, rồi mới đo ứng viên trên Pi.


Confirm this?
Có phải là SPEC->PLAN->PICK TASK theo buổi-> Hoàn thành -> Go to experiments folder each buổi-> tự tay soạn slides báo cáo report dựa trên notebook đã chạy, file DEMO để biết làm slides như nào, thuyết trình buổi nào thì xem experiment buổi đó, manifests chứa metadata của dataset, protocol, tests chứa gì thì tôi chưa biết, PROGRESS.md là dành cho ai agent lưu trữ tiến độ, VALIDATION là để kiểm kê lại toàn bộ những expriement đã chạy

-> Đúng về hướng đi: SPEC → PLAN → chọn việc theo buổi → chạy/kiểm tra → dùng kết quả thật và DEMO để chuẩn bị trình bày; không bắt buộc làm slide mỗi buổi. Manifests liệt kê mẫu, nhãn, đường dẫn và hash; protocol là quy tắc thí nghiệm. Tests kiểm tra mã chấm, dữ liệu và notebook, không đo chất lượng model. PROGRESS cho cả bạn và Codex theo dõi; VALIDATION ghi các kiểm tra đã chạy và giới hạn, không thay bảng kết quả thí nghiệm.


bạn hiểu như nào là "dùng /prose style articulate không quá dài dòng, không dùng skills prose."?
-> Viết tiếng Việt mạch lạc, giải thích rõ, đi thẳng vào câu hỏi và dùng đoạn văn vừa đủ. Không kích hoạt skill viết prose; chỉ dùng danh sách khi nó giúp đọc dễ hơn.

bạn hiểu như nào là "mục tiêu" của project này?
-> Học cách dùng và đánh giá STT tiếng Việt có sẵn, so chất lượng/tốc độ/RAM để tìm lựa chọn phù hợp Pi 4, rồi làm demo thu âm → chữ phục vụ hướng kính thông minh. Không đặt mục tiêu sản phẩm thương mại hay thuật toán mới.

bạn hiểu cái gì được làm cái gì không được làm và cái gì nên làm và cái gì nên làm?
Trả lời theo từng nhóm:

- Được làm: dùng model/runtime có sẵn, viết mã nối tối thiểu và chạy thí nghiệm.
- Không làm trong phạm vi hiện tại: sản phẩm doanh nghiệp, app/web/dashboard, tự thiết kế model hay training mặc định; không dùng test để chọn cấu hình, không bịa kết quả, không chạy Qwen CPU laptop.
- Nên làm: hoàn tất dữ liệu tự thu, so cùng dữ liệu/scorer, giữ lỗi và đo Pi trước khi chọn.
- Chưa nên làm: thêm nhiều model, fine-tune hoặc mở rộng phần kính khi các phép đo cơ bản còn thiếu.

Đây có phải điều kiện bắt buộc không "Nếu được tôi không muốn phải xây dựng, huấn luyện mà dùng những gì có sẵn"?
-> Đó là ưu tiên mạnh, có điều kiện “nếu được”, không phải cấm tuyệt đối. Phạm vi hiện tại dùng model/runtime có sẵn và không huấn luyện; chỉ cân nhắc thay đổi khi có bằng chứng cần thiết và thống nhất lại phạm vi.

nếu không thực sự cần thiết nếu baseline đủ tốt nghĩa là gì theo ý của tôi?
-> Nếu baseline đáp ứng chất lượng và tốc độ cần cho demo thì giữ, không thêm training/cải tiến cho đủ hình thức. Đã có self dev20 nhưng tập nhỏ một người đọc chưa đủ kết luận chất lượng sử dụng; vẫn cần bảng Qwen tự thu và số đo Pi.

Mình muốn chia thành nhiều giai đoạn thí nghiệm, bạn đánh giá trên thang điểm 100 bạn đã đáp ứng được yêu cầu này chưa?
-> Tôi tự đánh giá khoảng 70/100, không phải chỉ số đo khách quan: đã chia bảy buổi và có output riêng B01–B03, nhưng giải thích hai nguồn dev còn lẫn, notebook thao tác chưa thuận và phần tự thu chưa xong.

Bạn còn nhớ cấu hình Rasberry pi chứ?
-> Raspberry Pi 4B rev 1.5, RAM 8 GB, Raspberry Pi OS 13 (Trixie), kiến trúc kernel aarch64.

Tính mới mẻ mà thầy supervisor cần là gì hay nói đúng hơn bạn hiểu như thế nào về tính mới mẻ ở đây có thể là và không nên là?
-> Theo bạn thuật lại, thầy chưa yêu cầu cải tiến STT và muốn tập trung vào SLR. Với STT, tính mới có thể là khảo sát model 2025–2026 và kết quả so sánh trong điều kiện của đề tài; không nên gọi việc dùng model mới là phát minh thuật toán hoặc mặc định model mới thắng.

Tôi có những phần cứng, nguồn tài nguyên nào?
-> Pi 4B 8 GB; laptop i5-7200U, RAM 12 GB, Intel HD Graphics 620; Colab Pro 250 credits theo thông tin bạn cung cấp, đã dùng A100 40 GB; Google Drive 5 TB và home server HDD 1 TB. Galaxy M15 và ứng dụng ghi âm có sẵn đã được xác nhận để thu dev; micro nối Pi và phần kính/màn hình chưa chốt. Số credits còn lại chưa được kiểm tra.

Bạn hiểu thế nào về câu này "tôi nghĩ dự án này không có phải quá lớn hay cầu kỳ mà nên tập trung vào việc thử nghiệm, đánh giá... vào trọng tâm đề tài, nói chung mục tiêu là để học tập chứ không cần dự án đồ sộ cao siêu gì cả, mà là tập trung vào trọng tâm cái muốn giải quyết hơn, kiểu như lean project. Cho nên bây giờ bạn hãy sửa lại toàn bộ các files mà bạn đã viết như file đặc tả, file kế hoạch... đi"?
-> Giảm khối lượng phần mềm và tài liệu để dành thời gian cho chạy model, so sánh, tìm lỗi và đo Pi. Chỉ giữ pipeline cơ bản, output kiểm tra được và demo từng buổi; không mở rộng thành hệ thống sản phẩm.
bạn đã làm gì sau khi tôi nhắn "Qwen nặng lắm tôi không muốn chạy trên cpu máy tôi"?
-> Tôi dừng Qwen CPU, giữ kết quả chạy dở riêng, thêm chặn Qwen chạy CPU và chuyển sang notebook GPU Colab lưu kết quả trên Drive. Bạn đã chạy thành công Qwen trên A100; lần CPU dở không được đưa vào bảng dev100.

Sau khi thấy "Phần dọn máy **chưa hoàn tất**: bộ kiểm duyệt tự động chặn lệnh xóa môi trường và checkpoint Qwen với lý do “blocked by policy” ", tôi đã làm gì?
-> Bạn đã xác nhận tự xóa ba thư mục môi trường/checkpoint Qwen. Kiểm tra ngày 13/10 cho thấy cả ba không còn tồn tại; phần dọn ba thư mục đã xong. Xác nhận này không bao gồm các log hoặc toàn bộ máy.

Tóm tắt ngắn có ý nghĩa các output notebook đã chạy và tôi đã đưa cho bạn?
-> Ảnh output xác nhận Qwen chạy A100 và đủ 100/100 FLEURS dev: WER_ws Whisper 49,37%, Zipformer 7,51%, Qwen 9,76%; CER tương ứng 33,92%, 5,35%, 6,28%. Ba transcript bạn gửi cho thấy còn lỗi đổi nghĩa và tên riêng; điểm trung bình chưa chứng minh phụ đề dùng tốt.

Sự khác nhau giữa lựa chọn một và lựa chọn hai sẽ ảnh hưởng tới kết quả như thế nào là sao?
-> Bạn hỏi điện thoại khác micro laptop/tai nghe thế nào khi thu dữ liệu. Thiết bị, khoảng cách và tiếng ồn làm đổi audio nên có thể đổi điểm; để so model công bằng, cả ba phải nhận cùng các file. Chưa có phép đo khẳng định thiết bị nào của bạn tốt hơn.
tại sao tôi nhắn "Mình thấy 3 models cũng chưa thực sự làm tốt như bạn đã nhận xét"?
-> Vì khi nghe và đọc các câu cụ thể, bạn thấy cả ba còn lỗi làm sai nội dung, trong khi lời nhận xét trước của tôi khiến chất lượng có vẻ tốt hơn bằng chứng. Tôi đã sửa lại: Zipformer là ứng viên thử tiếp, chưa phải phương án đã đạt yêu cầu.

Ba câu bạn nghe được chọn vì Qwen có WER cao là sao?
-> Ô nghe sắp xếp 100 câu theo qwen_WER_ws giảm dần rồi lấy ba câu đầu. Vì chọn các câu Qwen lỗi nhiều, chúng dùng để tìm điểm yếu, không đại diện mức lỗi trung bình của Qwen hoặc toàn bộ ba model.

NEXT ACTIONS để hoàn thành buổi 01-03

1. [x] B01: đã chạy 10 mẫu pilot, xác nhận thiết bị thu; bạn đã nghe mẫu DEMO, xác nhận nhãn đúng và tính được WER theo output. Câu mẫu có 4 lỗi thay thế trên 13 đơn vị, WER_ws ≈ 30,77%. Không bắt buộc nghe/tính tay cả 10 câu.
2. [x] B02: đã đủ 20 câu chính (01–02 phòng ngủ, 03–20 cà phê), nhãn được nghe xác nhận, WAV/metadata/manifest đã kiểm tra. Whisper/Zipformer chạy đủ 20/20; WER_ws 27,6243% và 0,5525%, có bảng riêng. Hai bản cà phê câu 01–02 và bảng bốn bản cũ giữ ngoài bộ chính.
3. [ ] B03: mở B03_Self_dev20_Qwen_GPU.ipynb trong STT_B01_B03 trên Drive, chọn GPU và chạy các ô. Giữ RUN_NAME=self_dev20_qwen_v1; notebook dùng lại hai baseline đã đo và chỉ chạy Qwen. Sau đó kiểm tra bảng ba model/nhãn/output và nghe lỗi; không chạy lại FLEURS dev100.
4. [ ] Tập demo ngắn từ output đã lưu: audio → reference/prediction → điểm → lỗi/giới hạn → ứng viên thử Pi. Giữ test đóng; không cần chạy lại FLEURS dev100 đã hoàn tất.

## Giải đáp bổ sung — 13/10/2026

Nếu phải xây dựng trang theo dõi kết quả hoặc báo cáo riêng cho từng stage, nó sẽ như thế nào?
-> Trang theo dõi sẽ đọc các output đã lưu để hiện tiến độ, model/dữ liệu/thiết bị từng run, bảng WER/CER và audio/reference/prediction từng câu. Báo cáo stage là ghi chú mục tiêu → cách làm → bằng chứng/kết quả → giới hạn → bước tiếp theo cho mỗi giai đoạn; một stage có thể kéo dài nhiều buổi. Hiện notebook, CSV và PROGRESS đã đủ, chưa cần xây dashboard hay báo cáo stage riêng.

Pilot set có được dùng cho buổi 1–3 không? Có phải chỉ buổi 1 dùng pilot, các buổi khác không dùng?
-> Trong các lần chạy chính hiện tại: B01 dùng 10 mẫu pilot từ FLEURS train; B02–B03 dùng FLEURS dev100 và bổ sung self dev20. Pilot vẫn có thể dùng kiểm tra nhanh trước một lần chạy, nhưng không bắt buộc dùng lại. Không so điểm model trên pilot với model khác trên dev100; không huấn luyện bằng pilot.

Hai file ở phòng ngủ có điều hòa; có cần đổi tên hay mô tả? Khi thu ở cà phê thì theo dõi thế nào?
-> Giữ self_01.m4a/self_02.m4a cho phiên bedroom_01, điều kiện bedroom_ac_on. Bản cà phê mang tên self_01_cafe.m4a/self_02_cafe.m4a, phiên cafe_01. Bạn đã xác nhận cả hai dùng Samsung Galaxy M15, ứng dụng ghi âm có sẵn, khoảng cách xấp xỉ 30 cm. Metadata ghi phòng ngủ có điều hòa phía trên; cà phê có điều hòa lớn, chim, nhân viên tầng 1 khi bạn ở tầng 2 và tiếng ồn ngẫu nhiên từ khách. Bốn bản đã được nhận, không còn là dự định.

Reference có phải nhãn/label/ground truth không? Đây có phải thuật ngữ giới nghiên cứu ASR thường dùng?
-> Đúng. Reference transcript là bản chép lời chuẩn dùng đối chiếu; trong phép chấm này nó đóng vai trò label/ground truth. Prediction hoặc hypothesis là chữ model sinh ra. Reference phải khớp audio và được kiểm tra; câu gợi ý hoặc nhãn có sẵn không tự đảm bảo đúng tuyệt đối.

Lưu kết quả bốn file self vào B02 có nghĩa đang làm mục thu và kiểm tra 20 câu dev không?
-> Đúng. Ban đầu đo bốn bản self_dev_pairs4 để kiểm tra; hiện đã thu đủ và chấm hai baseline trên self dev20. Hai bộ này và FLEURS dev100 giữ bảng riêng; test tự thu chưa thực hiện.

C0 đã chạy trên 100 câu dev chưa?
-> Đã chạy Whisper-base đủ 100/100 FLEURS vi_vn dev trên CPU laptop; WER_ws 49,37%, CER 33,92%. Prediction và metadata nằm trong [B02/results](<C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/PBL6/experiments/B02/results>), tên whisper_dev.jsonl và whisper_dev.run.json. Đây là lần chạy riêng, cùng audio với C1, không lấy điểm pilot thay vào.

Tại sao lại là Transformer/Transformers trong khi đang làm ASR?
-> ASR là bài toán âm thanh → văn bản; Transformer là một kiến trúc mạng có thể dùng cho bài toán đó. Transformers viết hoa có thêm “s” là tên thư viện Hugging Face để nạp/chạy model. “Chạy Qwen3-ASR bằng Transformers” nói đến thư viện; vẫn làm ASR, không chuyển sang bài toán khác hoặc tự huấn luyện model.

Unicode NFC có ảnh hưởng kết quả không? Có phải nguyên liệu cần thiết cho mô hình AI không?
-> NFC chuẩn hóa cách mã hóa những chữ tương đương: “á” dựng sẵn và “a” cộng dấu sắc được đưa về cùng dạng để không bị chấm nhầm. Trong pipeline này NFC áp dụng cho reference/prediction khi chấm, có thể ảnh hưởng WER/CER nhưng không đổi audio hoặc giúp model nhận âm tốt hơn. Nó giữ dấu, nên “má” khác “mà”; không phải nguyên liệu bắt buộc của mọi AI. Xem [chuẩn Unicode NFC](https://unicode.org/reports/tr15/).

Không chia WER cho 0 mà kiểm tra model sinh chữ khi không có lời nói để làm gì?
-> Để phát hiện phụ đề không có thật: audio chỉ có tiếng nền nhưng model vẫn sinh câu. Reference của audio đã xác nhận không có lời nói có 0 đơn vị, nên WER không xác định; ta đếm các đoạn sinh chữ hoặc số lần mỗi phút. Nhãn bị thiếu chưa đủ để coi audio là không lời; bốn file tự thu hiện có lời nên chấm WER bình thường.

Reference units và reference chars là gì?
-> reference_units là số đơn vị trong nhãn sau chuẩn hóa, tách theo khoảng trắng; “học sinh” tính hai đơn vị. reference_chars là số ký tự nhãn sau chuẩn hóa NFC/xử lý dấu câu, bỏ khoảng trắng và giữ dấu tiếng Việt. “Tôi đi học.” có 3 đơn vị và 8 ký tự sau chuẩn hóa. Đây là số đếm của reference, không phải prediction.

false_captions_per_minute là gì?
-> Số đoạn audio không lời mà model sinh chữ, chia cho tổng số phút audio không lời. Ví dụ 2 phút có 3 đoạn sinh chữ sai thì được 1,5 lần/phút. Mã hiện tại tính mỗi đoạn có prediction không rỗng là một lần, nên cách chia đoạn cũng ảnh hưởng chỉ số. Cột trống/NaN trong các bảng hiện tại nghĩa là chưa đo audio không lời, không phải bằng 0.

WER_ws và CER được tính dựa trên reference_units/reference_chars phải không?
-> Đúng, chúng là mẫu số. WER_ws = (số đơn vị bị thay + xóa + chèn) / reference_units; CER tương tự theo lỗi ký tự / reference_chars. “Tôi đi học” → “Tôi đi họp” có một đơn vị sai và một ký tự sai: WER_ws = 1/3 ≈ 33,33%, CER = 1/8 = 12,5%. “ws” chỉ việc tách theo khoảng trắng.

Tại sao không lấy trung bình đơn giản điểm từng câu? Có khác không?
-> Có. Câu A có 2 đơn vị, 1 lỗi: WER 50%; câu B có 20 đơn vị, 1 lỗi: WER 5%. Trung bình từng câu là 27,5%, coi hai câu có trọng lượng bằng nhau; WER toàn tập là (1+1)/(2+20) ≈ 9,09%, coi mỗi đơn vị reference có trọng lượng bằng nhau. Dự án dùng tổng lỗi/tổng đơn vị; CER cũng dùng tổng lỗi ký tự/tổng ký tự, không lấy trung bình đơn giản từng câu.

Nếu kết quả đã nằm trong experiments thì khi làm báo cáo dùng gì? NEXT ACTIONS đã tới đâu?
-> Dùng output từng run, metadata, bảng điểm và DEMO để viết nhận xét; file giải đáp chỉ cần tra khi quên. B01 và B02 đã xong phần thực hành; FLEURS dev100 đã chạy đủ ba model; self dev20 đã có nhãn/metadata và hai baseline. Tiếp theo bạn chạy Qwen bằng notebook GPU riêng rồi kiểm tra/nghe bảng ba model tự thu; xem NEXT ACTIONS phía trên. Chưa có số đo Pi hoặc đánh giá test.

WAV trong DEMO B01 có phải một trong 10 mẫu pilot? Có cần nghe hết 10 câu và tính WER từng câu không?
-> Đúng, WAV 18182759805207678941 thuộc bộ 10 mẫu pilot. B01 chỉ yêu cầu nghe/đối chiếu và tính tay một mẫu; không bắt buộc nghe hay tính tay cả 10. Bạn đã xác nhận nhãn đúng và tính được WER theo output DEMO ngày 13/10. Output đó khớp JSONL đã lưu: 4 thay thế, 0 xóa, 0 chèn trên 13 đơn vị, WER_ws ≈ 30,77%. Đây là điểm một câu; WER_ws toàn bộ pilot là 36,875%.
