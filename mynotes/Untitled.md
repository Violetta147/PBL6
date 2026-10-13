# Bức tranh toàn cảnh buổi 1 đến buổi 4

Bốn buổi này đi từ **hiểu cách nhận dạng lời nói, so sánh model, đến kiểm tra model trên Raspberry Pi**. Mục tiêu là chọn một mô hình có sẵn để tạo phụ đề tiếng Việt cho hướng nghiên cứu kính thông minh. Ta chưa huấn luyện model mới; công việc chính là chuẩn bị audio, chạy nhận dạng, chấm lỗi và đo tài nguyên trên thiết bị thật.

**Buổi 1: hiểu một audio đi đến kết quả như thế nào.** Ta dùng Whisper-base với 10 câu pilot lấy từ phần train của FLEURS tiếng Việt. Pilot là bộ thử nhỏ để kiểm tra luồng và học cách đọc kết quả; lấy từ train không có nghĩa ta đã huấn luyện Whisper. Model chỉ nhận audio và sinh bản chép lời, gọi là prediction. Bản chép lời chuẩn để đối chiếu gọi là reference, tức nhãn của audio; reference không được đưa vào model để giúp nó trả lời.

Sau khi có prediction, ta đối chiếu với reference để đếm từ bị thay, mất hoặc thêm. Bạn đã nghe một mẫu pilot, xác nhận nhãn và đếm được bốn lỗi trên 13 đơn vị cách nhau bằng khoảng trắng, nên WER_ws của câu là 4/13 ≈ 30,77%. Với tiếng Việt, đơn vị này thường là tiếng, chưa chắc là từ hoàn chỉnh. Việc cần hiểu ở B01 là cách một lỗi trong transcript trở thành điểm số; không bắt buộc tính tay cả 10 câu. [Demo B01](../experiments/B01/DEMO.md) giữ audio và ví dụ đó.

**Buổi 2: chuyển từ chạy thử sang so sánh có cùng điều kiện.** Ta chạy Whisper-base và Zipformer trên cùng 100 câu FLEURS dev, dùng cùng nhãn và cách chấm. Dev là tập dùng để xem lỗi và lựa chọn cấu hình trong quá trình làm đề tài. Không lấy điểm pilot B01 thay điểm Whisper trên dev, vì hai tập gồm những câu khác nhau.

Cách chấm chung chuẩn hóa Unicode NFC, chữ thường, dấu câu và khoảng trắng; vẫn giữ dấu tiếng Việt. Vì vậy Zipformer viết hoa toàn bộ không tự tạo thêm lỗi so với Whisper. WER_ws đo lỗi ở đơn vị cách nhau bằng khoảng trắng; CER đo lỗi ký tự. Điểm cả tập được tính từ tổng lỗi chia tổng đơn vị reference tương ứng, không lấy trung bình đơn giản điểm từng câu. Prediction gốc vẫn được lưu để đọc và phân tích.

B02 còn chuẩn bị dữ liệu gần tình huống của mình hơn: self dev20 gồm 20 câu chính do bạn đọc, hai câu ở phòng ngủ và 18 câu ở cà phê, bằng Galaxy M15, ứng dụng ghi âm có sẵn, khoảng cách xấp xỉ 30 cm. Bạn đã nghe và xác nhận nhãn. Hai bản cà phê đọc lại câu 01–02 được giữ riêng, không cộng vào 20 câu chính. Bộ này giúp kiểm tra lời nói tự thu, nhưng một người đọc 20 câu chưa đại diện cho nhiều giọng nói hoặc mọi môi trường.

**Buổi 3: thêm Qwen và hoàn tất bảng ba model.** Qwen3-ASR-0.6B chạy trên GPU A100 của Colab, không chạy CPU laptop hoặc Pi. Nó được chấm trên đúng các câu mà hai baseline đã chạy. Trên FLEURS dev100, WER_ws của Whisper-base, Zipformer và Qwen lần lượt là 49,37%, 7,51% và 9,76%. Trên self dev20, các điểm tương ứng là 27,62%, 0,55% và 1,10%. Hai bảng được giữ riêng vì chúng đo hai bộ audio khác nhau.

Kết quả này đưa Zipformer thành ứng viên thử Pi, thay vì chọn Qwen chỉ vì model mới hơn. Ta vẫn cần nghe lỗi: trên self dev20, Zipformer sai “gốc/góc” ở câu 14; Qwen sai hai lần “kết” thành “cách” ở câu 20. Điểm thấp trên bộ nhỏ không có nghĩa mọi câu đều tốt. Output, nhãn và bảng ba model nằm trong [kết quả B03](../experiments/B03/results/self_dev20/summary.csv); các điểm đã được kiểm tra lại bằng JiWER, thư viện tính lỗi bản chép lời.

**Buổi 4: kiểm tra ứng viên có phù hợp Pi thật không.** Ta đưa cùng model Zipformer ONNX INT8 và self dev20 lên Pi 4B 8 GB, chạy CPU hai luồng qua hai lượt. Mỗi lượt đủ 20 câu; prediction giống laptop, WER_ws vẫn 0,55%. Với khoảng 84,16 giây audio, tổng inference mất khoảng 10,2–10,3 giây, RTF khoảng 0,12. RTF là thời gian xử lý chia thời lượng audio. Thời gian nạp model khoảng 3,74 giây được đo riêng; RAM cực đại toàn tiến trình khoảng 199 MiB. Hai lượt lặp vẫn là cùng 20 câu, không biến thành 40 mẫu độc lập.

Ta cũng thử Whisper qua runtime có sẵn whisper.cpp. Whisper-base nhận đúng câu thử nhưng mất 20,87 giây cho audio 5,35 giây, nên chuyển sang tiny dự phòng theo tiêu chí đã đặt trước. Tiny chạy đủ self dev20 hai lượt, WER_ws khoảng 41,99%, tổng thời gian khoảng 171–173 giây mỗi lượt. Thời gian CLI này gồm nạp model cho từng WAV, khác phạm vi inference riêng của Zipformer; không chia hai con số để tuyên bố mức tăng tốc. Tiny cũng là checkpoint khác base, nên không coi điểm tiny/Pi là điểm Whisper-base/laptop.

Đến đây, **phần thí nghiệm B01–B04 đã hoàn tất và Zipformer được chọn để thử tiếp ở B05**. Ta đã có bằng chứng audio → chữ trên Pi, cùng chất lượng, tốc độ và RAM; chưa có kết quả thu micro, chia đoạn lời nói liên tục hoặc hiển thị kính. Pi hiện chưa có micro, nên B05 có thể bắt đầu bằng replay audio theo thời gian thực rồi thử phần phát hiện đoạn có lời nói, gọi là VAD, trước khi nối ASR. B04 chưa chứng minh độ trễ phụ đề trong hội thoại thực tế. Tập test dành cho đánh giá cuối vẫn chưa mở.

Việc bạn làm ngay là theo [hướng dẫn demo B04](../experiments/B04/DEMO.md), chạy một WAV trên Pi và tập giải thích vì sao chọn Zipformer. Chưa cần chạy lại toàn bộ benchmark hay huấn luyện thêm. Bảng kết quả, metadata và log đã được lưu; việc tập demo và trình bày với thầy vẫn cần bạn thực hiện.


tôi chưa hiểu "Với tiếng Việt, đơn vị này thường là tiếng, chưa chắc là từ hoàn chỉnh", tiếng với từ trong tiếng việt khác nhau chỗ nào?
-> Tiếng thường tương ứng một âm tiết, còn từ là đơn vị có nghĩa và có thể gồm nhiều tiếng. Ví dụ “học sinh” gồm hai tiếng “học”, “sinh” nhưng là một từ ghép. Vì tiếng Việt thường đặt khoảng trắng giữa các tiếng, cách chấm của ta tách “học sinh” thành hai đơn vị; tên WER_ws giúp nói rõ chưa dùng bộ tách từ tiếng Việt.
chúng ta có dùng dev để lựa chọn cấu hình chưa hay là chỉ dùng để chọn mô hình thôi do nghe từ cấu hình tôi liên tưởng tới tham số và siêu tham số?
-> Chủ yếu đã dùng dev để chọn model. Ta cũng có chọn cấu hình chạy như runtime, hai luồng CPU và chuyển base sang tiny dự phòng, nhưng chưa quét nhiều tham số rồi chọn cấu hình có điểm dev tốt nhất. Hai luồng là lựa chọn cố định ban đầu, chưa được chứng minh tối ưu. “Lựa chọn cấu hình” trong phần tổng quan mô tả mục đích của dev nói chung, không có nghĩa ta đã thực hiện tối ưu siêu tham số hay huấn luyện.

Ta đã áp dụng Unicode NFC sao?
-> Có. Hàm normalize() trong experiments/common.py gọi unicodedata.normalize("NFC", text) cho cả reference và prediction trước khi chấm. NFC đưa những cách mã hóa Unicode tương đương về dạng thống nhất; ở đây nó phục vụ so sánh văn bản, không phải bước làm model nhận dạng tốt hơn. Prediction gốc vẫn được giữ.

Tại sao vì việc áp dụng trên mà Zipformer viết hoa toàn bộ?
-> Không phải do NFC. Bộ token của checkpoint Zipformer đang dùng có chữ hoa nên output của nó thường là chữ hoa. Khi chấm, ta mới chuyển cả reference và prediction về chữ thường bằng lower(); bước này loại khác biệt hoa/thường khỏi điểm số. NFC và lower() là hai thao tác khác nhau.

CER đo lỗi ký tự thì có tính whitespace không? và WER_ws không tính whitespace phải không?
-> Trong dự án này, CER bỏ khoảng trắng trước khi đếm ký tự. WER_ws dùng khoảng trắng để tách đơn vị, không tính từng dấu cách như một đơn vị lỗi riêng. Tuy nhiên khoảng trắng vẫn có thể làm đổi cách tách: “học sinh” và “họcsinh” có CER bằng 0 theo quy tắc này nhưng WER_ws khác 0. Nhiều dấu cách liên tiếp được chuẩn hóa thành một.

B02 còn chuẩn bị dữ liệu gần tình huống của mình hơn, "mình" là ai?
-> “Mình” là bạn và đề tài kính thông minh của bạn. Ý câu đó là audio bạn tự thu bằng thiết bị và trong môi trường đã ghi nhận, gần bối cảnh thử nghiệm của đề tài hơn câu đọc từ dataset công khai; chưa có nghĩa đó là audio thu bằng micro trên kính.

Có khả năng Qwen yếu hơn vì không được huấn luyện đặc biệt trên dữ liệu tiếng việt không, hãy để ý Zipformer phiên bản ta đang dùng là 1 phiên bản cực kỳ tối ưu hóa cho tiếng việt trên thiết bị biên với INT8, và nếu đúng là như vậy thì sẽ mở ra khả năng mới và chưa chắc Qwen thua
-> Có thể khác biệt dữ liệu huấn luyện và mức chuyên biệt tiếng Việt góp phần tạo chênh lệch, nhưng ta chưa có thí nghiệm chứng minh nguyên nhân. [Qwen3-ASR-0.6B có hỗ trợ tiếng Việt](https://huggingface.co/Qwen/Qwen3-ASR-0.6B), nên không nên giả định nó chưa được học tiếng Việt. [Zipformer đang dùng chuyên tiếng Việt, khoảng 30M tham số, được tác giả công bố huấn luyện khoảng 6.000 giờ và hướng tới CPU](https://huggingface.co/hynt/Zipformer-30M-RNNT-6000h). INT8 chủ yếu là cách biểu diễn số để giảm chi phí lưu trữ/tính toán; ta chưa so với bản không lượng tử hóa nên không thể nói INT8 làm nó chính xác hơn. Model card Zipformer cũng liệt kê FLEURS trong nguồn train, nhưng không đủ thông tin để khẳng định trùng các câu dev đang chấm. Kết luận hiện tại chỉ là checkpoint/cấu hình Zipformer đạt điểm tốt hơn trên hai bộ đã đo; chưa chứng minh kiến trúc Qwen kém hơn. Giả thuyết của bạn là hướng nghiên cứu hợp lý, chưa buộc phải fine-tune Qwen để kiểm chứng trong đề tài lean này.
Điểm thấp trên bộ nhỏ không có nghĩa mọi câu đều tốt, vậy có cần tăng quy mô?
-> Có, cần đánh giá đa dạng hơn trước kết luận cuối, nhưng chưa cần mở rộng thành dataset lớn. Kế hoạch đã dành 30–50 câu tự thu test và 200 câu FLEURS test ở B06; tự thu nên có thêm người hoặc ít nhất phiên thu mới, cùng câu dài, số, tên riêng và phủ định. Chốt cấu hình trước khi mở test. Tăng số câu mà vẫn chỉ một người đọc câu dễ chưa giải quyết hết hạn chế.
chạy CPU hai luồng qua hai lượt là sao và mục đích của nó, tại sao ko chạy 1 luồng hoặc nhiều hơn?
-> Hai luồng là số luồng tính toán CPU mà runtime được cấu hình dùng cho một lần nhận dạng; không phải nhận hai audio cùng lúc. Hai lượt là chạy lại toàn bộ 20 câu để xem tốc độ và output có ổn định không. Chọn hai luồng làm cấu hình cố định, vừa phải cho Pi; chưa thử một hoặc bốn luồng nên chưa biết hai là nhanh nhất. Nếu cần tối ưu tiếp, có thể so 1/2/4 luồng trên cùng dev; nhiều luồng hơn không mặc nhiên nhanh hơn.
Buổi 4 là đang so Zipformer candidate với baseline Whisper hả?
-> Đúng về mục đích: kiểm tra Zipformer ứng viên trên Pi và đối chiếu với họ Whisper làm baseline. Nhưng Whisper-base trên Pi chỉ chạy smoke một câu vì chậm; bảng đủ 20 câu là Whisper-tiny dự phòng. Vì vậy phải gọi đúng “Zipformer so với Whisper-tiny trên self dev20/Pi”, không nói đã có so sánh đầy đủ với Whisper-base trên Pi.
Nếu vậy tại sao ta không thử nghiệm Qwen trên Rasberry pi mà chỉ Whisper baseline và Zipformer vậy?
-> Vì bạn đã chọn Qwen chỉ chạy GPU và muốn giữ phạm vi gọn; Pi không có GPU CUDA như A100. B04 ưu tiên model nhỏ/runtime CPU có sẵn, còn Qwen đóng vai trò đối chiếu chất lượng trên Colab. Ta chưa đo Qwen trên Pi, nên không kết luận nó chắc chắn không chạy được hoặc đưa số tốc độ Pi cho nó. Đây là giới hạn phạm vi thí nghiệm đã chọn.
Tôi chưa thấy tổng thời gian của Zipformer trong bức tranh toàn cảnh?
-> Trong phần tổng quan có tổng inference 10,2–10,3 giây, nhưng chưa ghi wall time cả tiến trình. Với 20 WAV: lượt 1 inference 10,278 giây, toàn tiến trình 14,644 giây; lượt 2 inference 10,226 giây, toàn tiến trình 14,578 giây. Wall time gồm nạp model, đọc/ghi và các việc khác của runner. Tổng thời lượng audio là 84,160 giây; nạp model đã nằm trong wall time, không cộng thêm lần nữa.
Có thực sự tất cả model đang được đánh giá trên cùng 1 bộ chỉ số không vậy?
-> Về chất lượng, có: các model trong cùng bảng dùng cùng audio, reference, chuẩn hóa, WER_ws và CER; false_captions_per_minute hiện chưa có giá trị vì chưa đo tập không lời nói. FLEURS và self dev20 là hai bảng riêng. Về hiệu năng, chưa hoàn toàn đồng nhất: Qwen chạy GPU, hai baseline chạy CPU; trên Pi Zipformer đo inference riêng, Whisper.cpp đo wall gồm nạp lại model mỗi WAV. Ta đang so checkpoint/runtime cụ thể, chưa phải thí nghiệm cô lập chỉ khác kiến trúc model.
không chia hai con số để tuyên bố mức tăng tốc là sao?
-> Ví dụ lấy 172,8 giây của Whisper-tiny chia 10,28 giây của Zipformer rồi nói “Zipformer nhanh hơn khoảng 16,8 lần” sẽ không cùng phạm vi đo: số đầu gồm nạp model từng WAV, số sau bỏ nạp model và đọc/ghi. Muốn báo mức tăng tốc phải đo cùng phạm vi và chính sách nạp model, chẳng hạn cả hai nạp một lần rồi đo xử lý 20 WAV. Các số hiện tại vẫn hữu ích để mô tả từng cách chạy, nhưng chưa cho tỷ lệ tăng tốc công bằng.
Thời gian CLI này gồm nạp model cho từng WAV là sao, tôi tưởng là chỉ chạy 1 audio 1 lần 1 lượt, ko lẽ nạp 20 cái model instances cho 20 wav luôn hả, tương tự 100 wav FLEURS luôn hả?
-> Riêng adapter Whisper.cpp B04: mở CLI → nạp model → xử lý WAV 01 → thoát; sau đó làm lại với WAV 02, lần lượt đến WAV 20. Tức là 20 lần nạp tuần tự, không phải 20 model cùng nằm trong RAM. Đây là cách dùng CLI đơn giản đã triển khai, không phải bắt buộc của Whisper.cpp. Zipformer B04 và runner B01–B03, kể cả FLEURS 100 câu/Qwen, nạp một model rồi xử lý lần lượt các WAV trong cùng tiến trình; không nạp 100 model. Hai lượt benchmark là hai lần chạy cả tập riêng biệt.
Chia đoạn lời nói liên tục là sao?
-> Khi micro thu liên tục, ta chưa có sẵn file tách từng câu như dev20. Cần quyết định đoạn lời nói bắt đầu/kết thúc ở đâu để đưa audio vào ASR và xuất chữ. Ví dụ nói → nghỉ đủ lâu → chốt một đoạn → nhận dạng. VAD giúp phát hiện có/không có lời nói, nhưng ranh giới nó tìm được không nhất thiết trùng ranh giới câu về ngữ nghĩa.
Tức là ta chưa thử streaming mode hay thí nghiệm trên realtime mà ta chỉ thử Batch ASR aka Offline ASR aka non-streaming ASR thôi hả
-> Đúng là đến B04 ta mới nhận dạng toàn bộ các WAV đã có, chưa thử audio đến theo thời gian thực hay streaming ASR. Nhưng “batch”, “offline/non-streaming” và “không cần Internet” không đồng nghĩa hoàn toàn: batch nói về xử lý nhiều đầu vào, còn non-streaming nói về nhận cả đoạn trước khi nhận dạng. Runner hiện xử lý từng WAV, không chạy một batch nhiều WAV đồng thời. Sau này có thể dùng VAD cắt đoạn từ micro rồi gọi model offline; hệ thống chạy theo luồng audio nhưng bản thân ASR vẫn nhận từng đoạn hoàn chỉnh.
Tức là ở buổi 05 sẽ thí nghiệm về VAD phải không?
-> Đúng, B05 sẽ thử VAD như một phần của luồng audio → chia đoạn → ASR → hiển thị chữ. Mục tiêu là xem cả luồng hoạt động ra sao, không làm một nghiên cứu VAD riêng. Do chưa có micro, có thể phát lại WAV theo thời gian thực để thử trước; cần gọi đúng là replay và ghi nhận chưa thử thu trực tiếp.
nối ASR là sao nhỉ?
-> “Nối ASR” nghĩa là đưa đoạn audio mà VAD đã gom/chốt vào model nhận dạng, rồi lấy text trả ra để hiển thị. Ví dụ VAD phát hiện bạn nói xong “Tôi muốn xem phụ đề” thì chuyển audio của đoạn đó sang Zipformer. Đây là ghép các bước xử lý có sẵn, không phải nối trọng số hoặc huấn luyện hai model cùng nhau.


Tức là hiện tại ta chấm theo tiếng, chưa chấm theo từ hoàn chỉnh à?
-> Đúng hơn là chấm theo đơn vị tách bằng khoảng trắng, trong tiếng Việt thường tương ứng với tiếng. Ví dụ “học sinh” được tính thành hai đơn vị, dù là một từ ghép. Vì vậy ta ghi WER_ws để nói rõ cách tách này, không mặc định đó là WER đã tách từ tiếng Việt.

Tại sao chưa thêm chấm theo từ và theo câu? Hai cách đó khác gì?
-> Ban đầu ta giữ WER_ws và CER để pipeline đơn giản, thống nhất giữa các model. Muốn chấm WER theo từ, cần dùng cùng một bộ tách từ cho cả reference và prediction; điểm còn phụ thuộc công cụ này. Theo câu có thể tính tỷ lệ câu có ít nhất một lỗi, gọi là SER, hoặc tỷ lệ câu khớp hoàn toàn sau chuẩn hóa. Cách chấm câu dễ hiểu nhưng câu sai một tiếng và câu sai gần hết đều bị tính là một câu lỗi. Các chỉ số bổ sung cho nhau; hiện bạn đã chọn chưa thêm chỉ số mới.

Bộ tách từ tiếng Việt là gì, nó làm như thế nào?
-> Đây là công cụ xác định những tiếng nào thuộc cùng một từ, dựa vào từ điển hoặc mô hình đã học và ngữ cảnh. Ví dụ “Tôi là học sinh trung học”: tách bằng khoảng trắng cho “Tôi | là | học | sinh | trung | học”, gồm sáu đơn vị; bộ tách từ có thể cho “Tôi | là | học_sinh | trung_học”, gồm bốn từ. Dấu gạch dưới chỉ biểu diễn các tiếng thuộc cùng một từ. Tiếng Việt thường đặt khoảng trắng giữa các tiếng nên chỉ nhìn dấu cách chưa đủ xác định ranh giới từ; công cụ cũng có thể tách sai.

Bộ tách từ có nghe audio hay sửa chữ mà ASR nhận sai không?
-> Không trong cách dùng đang bàn. Nó xử lý văn bản sau ASR để xác định ranh giới từ, không nghe audio và không được dùng để sửa nội dung prediction. Nếu chấm WER theo từ thì áp dụng cùng công cụ, phiên bản và quy tắc cho reference lẫn prediction, đồng thời vẫn giữ văn bản gốc.

Nếu sau này thêm các chỉ số này thì có phải chạy lại model không?
-> Không cần chạy lại model nếu prediction và reference đã được lưu đầy đủ. Có thể tính thêm điểm từ các văn bản đó, giữ điểm WER_ws/CER cũ để đối chiếu. Hiện ta chỉ ghi lại kiến thức này; chưa cài bộ tách từ, chưa sửa scorer hoặc bổ sung bảng điểm.
