# Chọn phương pháp phù hợp với MVP nhận dạng ký hiệu PBL6

Đánh giá **39 phương pháp theo số gốc** cho luồng webcam laptop → trích điểm khớp tay và thân bằng MediaPipe → tách đoạn → SL-GCN.

Mục #32 là phương pháp người viết đã đánh dấu để thử. Kết quả #32 và các phép thử sau đó nằm trong [kế hoạch tách đoạn](02_TEMPORAL_SEGMENTATION_AND_TRIMMING_PLAN.md). Đối chứng cải tiến tiếp theo nằm trong [kế hoạch đánh giá VSL400 và kiosk](08_VSL400_AND_KIOSK_EVALUATION_PLAN.md).

**Căn cứ chọn.** Hai clip quay khoảng 15 fps nhận đúng hai thứ tự **Cảm ơn ↔ Khăn quàng cổ** khi bộ tách ghi nhận **26 và 32 khung nghỉ liên tiếp**. Clip `23_04_34` bị gộp khi khoảng nghỉ liên tiếp dài nhất ở vùng nối là **3 khung**, dưới ngưỡng **8**. Trên chính clip đó, **Cảm ơn từ hạng 15 lên hạng 1 khi cắt tay theo thời gian**. Hai clip trước đó vẫn nhầm Cảm ơn thành Tham ăn sau khi cắt tay. Vì vậy cần đo riêng lỗi tách đoạn và lỗi nhận dạng khi đã biết biên. Kết quả hiện có từ một người ký. [Kế hoạch tách đoạn và số liệu](02_TEMPORAL_SEGMENTATION_AND_TRIMMING_PLAN.md) · [Tổng hợp các lượt quay](../outputs/segmentation_experiments/TONG_HOP_WEBCAM_20261115.html)

## Phương án kỹ thuật ưu tiên và các việc hỗ trợ kiểm chứng

| # gốc | Phương pháp | Áp dụng cho PBL6 |
| --- | --- | --- |
| 01 | Thu dữ liệu từ môi trường thực | Quay bằng webcam laptop trong bố trí dự kiến khi demo. Ghi FPS thực, nhãn và thứ tự ký trước khi xem dự đoán. |
| 05 | Gán nhãn thủ công | Biên thủ công đã cho **Cảm ơn** lên hạng 1 ở `23_04_34` và hai lượt bị hụt pha mở tay. Giữ các biên này làm mốc so sánh cho bộ tách tự động. |
| 09 | Mẫu âm tính | Thử đứng yên, hạ tay, chỉnh tư thế và với tay bấm nút. Đếm lượt hệ thống phát sinh ký hiệu khi không ký. Giữ nguyên pha mở tay mang nghĩa của Cảm ơn. |
| 13 | Tập test độc lập | Dùng phiên quay mới để kiểm tra sau khi chọn cấu hình. Muốn đánh giá khả năng tổng quát, giữ riêng người ký chưa dùng để tinh chỉnh hoặc huấn luyện. |
| 14 | Khai thác ca khó | Giữ hai clip nhầm Cảm ơn thành Tham ăn, clip gộp `23_04_34` và các lượt mất khớp để tái hiện lỗi. So với ca đúng ở cả hai thứ tự. |
| 32 | <strong style="background-color:#DDF7E9;color:#0B6B45;padding:1px 4px;border-radius:3px;">Thống kê theo thời gian</strong> | Đã thử offline bộ đếm nghỉ chịu ngắt quãng và quy đổi theo FPS. Sửa ca gộp `23_04_34`, nhưng để lọt thêm chuỗi dài sai trong tập đã đo. Giữ cấu hình này để đối chiếu. |
| 36 | Camera cố định | Đánh dấu vị trí camera và người ký. Giữ bố trí ổn định khi so sánh hai nhịp nghỉ hoặc hai phương án tách. |
| 39 | Ánh sáng đồng đều | Chiếu sáng từ trước. Kiểm tra FPS thực, độ nhòe ở pha mở tay và tỷ lệ thiếu điểm khớp trước khi quy lỗi cho thiết bị. |
| 48 | AI hỗ trợ phân tích lỗi | Dùng AI để lập giả thuyết, sau đó kiểm tra bằng video gốc, nhãn thật, tín hiệu cổ tay và kết quả trên cùng đoạn cắt. |

## Phương pháp hỗ trợ dữ liệu và pipeline

| # gốc | Phương pháp | Áp dụng cho PBL6 |
| --- | --- | --- |
| 02 | Đa dạng dữ liệu | Thu thêm người ký, nhịp ký, góc và ánh sáng sau khi có cấu hình đối chứng. Ghi tay thuận và biến thể, kiểm tra tính đúng nghĩa khi đổi tay. |
| 06 | Gợi ý nhãn và rà soát | Dùng cặp nhầm lẫn để gợi ý nhãn sửa. Lưu nhãn gốc và nhãn người dùng xác nhận. Chỉ cân nhắc dùng mẫu đã rà soát cho huấn luyện sau này. |
| 12 | Kiểm tra độ phủ dữ liệu | Đếm clip theo từ, cặp từ, thứ tự, người ký, phiên, khoảng nghỉ và FPS để biết cần quay thêm ca nào. |
| 24 | Pipeline hai giai đoạn | Tái sử dụng MediaPipe để lấy điểm khớp, tách đoạn, rồi chạy SL-GCN trên từng đoạn. Kết quả chuỗi hiện đã có ở bài chạy offline. |
| 29 | Theo dõi tay trái/phải qua các khung | Kiểm tra tracking và cờ `handedness_valid` có sẵn khi mất khớp hoặc gán nhầm bên. Chưa có căn cứ thêm bộ tracker riêng. |
| 40 | Nền ít gây nhiễu | Giữ nền đơn giản khi xây dựng mốc so sánh. Thử đa dạng nền ở phiên khác nếu cần kiểm tra khả năng triển khai. |

## Chưa đưa vào kế hoạch hiện tại

| # gốc | Phương pháp | Điều kiện cân nhắc |
| --- | --- | --- |
| 03 | Bổ sung dữ liệu công khai | Xác minh ngôn ngữ ký hiệu, từ vựng, quy ước nhãn và quyền sử dụng trước khi ghép với VSL400. |
| 04 | Trích/lọc frame | Trích ảnh để xem và gán nhãn được. Việc bỏ khung khỏi đầu vào làm thay đổi nhịp mà SL-GCN nhận được. |
| 07 | AI hỗ trợ annotation | Các clip hiện đủ ít để đánh dấu biên bằng tay. Chỉ thử tự động hóa khi tăng quy mô gán nhãn. |
| 08 | Crop vùng quan tâm | Cắt trước khi trích điểm khớp có thể mất vai hoặc cổ tay dùng để chuẩn hóa và gán bên. Chỉ thử khi có ca lỗi do vùng xem. |
| 10 | Data augmentation | Cân nhắc trong một vòng huấn luyện đã duyệt, có tập kiểm tra độc lập và biến đổi bảo toàn nhãn. |
| 11 | Dữ liệu tổng hợp GPT/GAN | Chưa có quy trình xác nhận ký hiệu tổng hợp đúng nghĩa, hình tay và quỹ đạo. |
| 15 | Fine-tune detector | Chỉ đáng thử khi đo được lỗi định vị tay bền vững và có dữ liệu gán vùng. Việc này không xử lý trực tiếp lỗi gộp từ đã quan sát. |
| 16 | Model lớn hơn / nhiều epoch | Chưa có bằng chứng dung lượng hoặc số epoch là nguyên nhân chính. Đo tách đoạn và phân loại trên biên chuẩn trước. |
| 17 | Điều chỉnh ngưỡng điểm mô hình | Có thể kiểm chứng để quyết định hỏi xác nhận hay quay lại. Điểm cao vẫn xuất hiện ở các lượt nhầm Tham ăn. |
| 18 | Điều chỉnh IoU | Ngưỡng IoU hộp của detector không thuộc luồng hiện tại. IoU theo thời gian có thể dùng riêng để chấm độ khớp biên. |
| 19 | Freeze backbone, dropout | Chỉ liên quan khi có thí nghiệm fine-tune đã duyệt. |
| 20 | Detector vật thể nhỏ | Cân nhắc nếu tay quá nhỏ trong ảnh và căn lại khung vẫn không giúp. |
| 21 | RT-DETR | Chưa có đối chứng cho thấy thay bộ định vị giải quyết lỗi chính. |
| 22 | RF-DETR | Cùng điều kiện như RT-DETR. Nếu thử, đo cả chất lượng điểm khớp và độ trễ. |
| 23 | Instance segmentation | Có thể hỗ trợ với nền khó. Mặt nạ không khôi phục bàn tay bị che hoàn toàn và pipeline hiện dùng tọa độ khớp. |
| 25 | Grayscale/đổi kênh màu | Chưa có bằng chứng nội bộ cho thấy cải thiện trích điểm khớp. Ưu tiên thử ánh sáng và khung hình. |
| 26 | ROI + khác biệt frame | Có thể đối chứng như tín hiệu phụ khi cổ tay chập chờn. Chuyển động đầu, thân và nền cũng làm thay đổi ảnh. |
| 27 | Background subtraction | Chỉ đáng đối chiếu khi camera cố định và điểm khớp chưa đủ để phát hiện chuyển động. |
| 28 | Multi-scale detection | Cân nhắc sau khi đo lỗi theo kích thước tay trong ảnh. Trước mắt cố định khoảng cách quay. |
| 30 | Re-identification | Luồng hiện tại có một người ký mỗi lượt. Chưa có bài toán ghép danh tính nhiều người xuyên video. |
| 31 | Nhiều camera | Chưa cần cho demo có hướng dẫn trên một webcam. Cần đồng bộ và hiệu chỉnh nếu mở rộng. |
| 34 | Phát hiện một bộ phận thay toàn thân | Luồng đã lấy đặc trưng tay và thân. Giảm còn riêng tay cần kiểm tra lại chuẩn hóa và phân biệt từ. |
| 38 | Camera nhìn ngang | Cân nhắc như góc phụ sau khi có kết quả chính diện ổn định. |
| 41 | Camera chất lượng cao | Nếu có thiết bị sẵn, có thể thử đối chứng. Các clip đúng và sai đều khoảng 15 fps nên chưa đủ căn cứ để quy lỗi cho FPS hay mua camera. |

## Cách xác nhận #32 có hiệu quả

1. Dùng `23_04_20` và `23_13_00` làm ca nhận đúng, `23_04_34` làm ca gộp và hai clip `22_34` làm ca nhầm nhãn.
2. Chạy cấu hình hiện tại trên clip mới ở cả hai chiều, gồm nhịp nghỉ rõ, nhịp nối tự nhiên và lượt không ký. Ghi **chuỗi đúng đủ từ và đúng thứ tự**, **lượt gộp/tách thừa** và **lượt phát sinh nhãn khi không ký**. Dùng biên thủ công cho ca mơ hồ cần chẩn đoán.
3. Sau khi duyệt thay đổi tiền xử lý, đối chiếu bộ đếm nghỉ hiện tại với phương án chịu nhiễu ngắn trên cùng clip. Xác nhận trên phiên quay độc lập. Nếu vẫn sai trên đoạn có biên chuẩn, thu thêm ca khó trước khi đề xuất fine-tune.

Gợi ý sửa nhãn và trạng thái `fixed` là đề xuất thiết kế. [Báo cáo cặp nhầm lẫn](04_GOLDEN_DEMO_WORDS_AND_CONFUSION_REPORT.md)
