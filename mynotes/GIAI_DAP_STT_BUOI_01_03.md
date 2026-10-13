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
-> Không bắt buộc. Mỗi thí nghiệm có câu hỏi, cấu hình, lần chạy và đánh giá; có thể dùng lại dữ liệu/mã đã kiểm tra. Các buổi chia nhỏ công việc, không lặp toàn bộ quy trình từ đầu.
Tôi chưa hiểu "Buổi 1–5 dùng pilot/dev để học và điều chỉnh. Test chỉ dùng đánh giá sau khi chốt ở cuối buổi 5. Câu trình diễn thầy nói trực tiếp là minh họa, không tự trở thành điểm benchmark."
-> Pilot dùng kiểm tra luồng; dev dùng thử và chọn cấu hình. Cuối buổi 5 chốt cấu hình rồi mới đánh giá trên test, tránh chọn theo điểm test. Câu thầy nói trực tiếp chỉ minh họa vì chưa có bộ nhãn và quy trình chấm cố định.

Có phải từ buổi 1 tới buổi 3 là như này?
Buổi 1:
Chọn 10 file wav từ tập train của FLEURS -> Soi cái transcript có đúng với âm thanh (input) hay chưa
Đưa 10 file wav này vào Whisper-base (mô hình C0) là baseline, lưu output text từ model, môi trường điều kiện chạy
Rồi đối chiếu thử 1 output với audio, tính WER bằng tay, quyết định xem dùng Rasberry Pi mấy, Microphone hay điện thoại

-> Cơ bản đúng. Mười câu train chỉ dùng pilot, không huấn luyện Whisper. Pi đã chốt là Pi 4B 8 GB; phần cần xác nhận là thiết bị thu. Output, môi trường đã lưu; phần nghe mẫu B01 và tự tính WER vẫn cần bạn xác nhận hoàn thành.

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
-> Đúng, chưa có bảng ba model trên self dev20. Hiện trên ổ Drive G đã có self_01.m4a và self_02.m4a; chưa có manifest self_dev20.csv để đánh giá đủ 20 câu.
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
-> Nếu baseline đáp ứng chất lượng và tốc độ cần cho demo thì giữ, không thêm training/cải tiến cho đủ hình thức. Hiện chưa đủ bằng chứng gọi baseline đạt yêu cầu vì còn thiếu dữ liệu tự thu và số đo Pi.

Mình muốn chia thành nhiều giai đoạn thí nghiệm, bạn đánh giá trên thang điểm 100 bạn đã đáp ứng được yêu cầu này chưa?
-> Tôi tự đánh giá khoảng 70/100, không phải chỉ số đo khách quan: đã chia bảy buổi và có output riêng B01–B03, nhưng giải thích hai nguồn dev còn lẫn, notebook thao tác chưa thuận và phần tự thu chưa xong.

Bạn còn nhớ cấu hình Rasberry pi chứ?
-> Raspberry Pi 4B rev 1.5, RAM 8 GB, Raspberry Pi OS 13 (Trixie), kiến trúc kernel aarch64.

Tính mới mẻ mà thầy supervisor cần là gì hay nói đúng hơn bạn hiểu như thế nào về tính mới mẻ ở đây có thể là và không nên là?
-> Theo bạn thuật lại, thầy chưa yêu cầu cải tiến STT và muốn tập trung vào SLR. Với STT, tính mới có thể là khảo sát model 2025–2026 và kết quả so sánh trong điều kiện của đề tài; không nên gọi việc dùng model mới là phát minh thuật toán hoặc mặc định model mới thắng.

Tôi có những phần cứng, nguồn tài nguyên nào?
-> Pi 4B 8 GB; laptop i5-7200U, RAM 12 GB, Intel HD Graphics 620; Colab Pro 250 credits theo thông tin bạn cung cấp, đã dùng A100 40 GB; Google Drive 5 TB và home server HDD 1 TB. Micro và phần kính/màn hình chưa chốt; số credits còn lại chưa được kiểm tra.

Bạn hiểu thế nào về câu này "tôi nghĩ dự án này không có phải quá lớn hay cầu kỳ mà nên tập trung vào việc thử nghiệm, đánh giá... vào trọng tâm đề tài, nói chung mục tiêu là để học tập chứ không cần dự án đồ sộ cao siêu gì cả, mà là tập trung vào trọng tâm cái muốn giải quyết hơn, kiểu như lean project. Cho nên bây giờ bạn hãy sửa lại toàn bộ các files mà bạn đã viết như file đặc tả, file kế hoạch... đi"?
-> Giảm khối lượng phần mềm và tài liệu để dành thời gian cho chạy model, so sánh, tìm lỗi và đo Pi. Chỉ giữ pipeline cơ bản, output kiểm tra được và demo từng buổi; không mở rộng thành hệ thống sản phẩm.
bạn đã làm gì sau khi tôi nhắn "Qwen nặng lắm tôi không muốn chạy trên cpu máy tôi"?
-> Tôi dừng Qwen CPU, giữ kết quả chạy dở riêng, thêm chặn Qwen chạy CPU và chuyển sang notebook GPU Colab lưu kết quả trên Drive. Bạn đã chạy thành công Qwen trên A100; lần CPU dở không được đưa vào bảng dev100.

Sau khi thấy "Phần dọn máy **chưa hoàn tất**: bộ kiểm duyệt tự động chặn lệnh xóa môi trường và checkpoint Qwen với lý do “blocked by policy” ", tôi đã làm gì?
-> Trong phần chat hiện có, tôi chưa thấy bạn xác nhận cụ thể đã dọn bằng cách nào. Kiểm tra ngày 13/10 cho thấy ba đường dẫn môi trường/checkpoint Qwen từng chờ xóa không còn tồn tại; tôi không suy đoán ai đã xóa hoặc toàn bộ việc dọn máy đã xong.

Tóm tắt ngắn có ý nghĩa các output notebook đã chạy và tôi đã đưa cho bạn?
-> Ảnh output xác nhận Qwen chạy A100 và đủ 100/100 FLEURS dev: WER_ws Whisper 49,37%, Zipformer 7,51%, Qwen 9,76%; CER tương ứng 33,92%, 5,35%, 6,28%. Ba transcript bạn gửi cho thấy còn lỗi đổi nghĩa và tên riêng; điểm trung bình chưa chứng minh phụ đề dùng tốt.

Sự khác nhau giữa lựa chọn một và lựa chọn hai sẽ ảnh hưởng tới kết quả như thế nào là sao?
-> Bạn hỏi điện thoại khác micro laptop/tai nghe thế nào khi thu dữ liệu. Thiết bị, khoảng cách và tiếng ồn làm đổi audio nên có thể đổi điểm; để so model công bằng, cả ba phải nhận cùng các file. Chưa có phép đo khẳng định thiết bị nào của bạn tốt hơn.
tại sao tôi nhắn "Mình thấy 3 models cũng chưa thực sự làm tốt như bạn đã nhận xét"?
-> Vì khi nghe và đọc các câu cụ thể, bạn thấy cả ba còn lỗi làm sai nội dung, trong khi lời nhận xét trước của tôi khiến chất lượng có vẻ tốt hơn bằng chứng. Tôi đã sửa lại: Zipformer là ứng viên thử tiếp, chưa phải phương án đã đạt yêu cầu.

Ba câu bạn nghe được chọn vì Qwen có WER cao là sao?
-> Ô nghe sắp xếp 100 câu theo qwen_WER_ws giảm dần rồi lấy ba câu đầu. Vì chọn các câu Qwen lỗi nhiều, chúng dùng để tìm điểm yếu, không đại diện mức lỗi trung bình của Qwen hoặc toàn bộ ba model.

NEXT ACTIONS để hoàn thành buổi 01-03

1. B01: nghe mẫu trong DEMO B01, tự đếm bốn lỗi thay thế trên 13 đơn vị reference, kiểm tra WER_ws = 4/13 ≈ 30,77%; xác nhận thiết bị thu.
2. B02: kiểm tra hai file self_01.m4a/self_02.m4a đã có trên Drive, nghe xác nhận nhãn rồi thu tiếp đủ 20; Codex chuẩn hóa WAV và lập manifest từ metadata đã xác nhận.
3. B03: chạy ba model trên self dev20, Qwen chỉ dùng GPU Colab; lưu bảng riêng, nghe lỗi và nhận xét đối chiếu với FLEURS dev100.
4. Chuẩn bị demo ngắn từ output đã lưu: audio → reference/prediction → điểm → lỗi/giới hạn → ứng viên thử Pi. Giữ test đóng; không cần chạy lại FLEURS dev100 đã hoàn tất.
