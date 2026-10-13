Tại sao là FLEURS mà không phải là cái khác?
-> Ta chọn FLEURS vì có tiếng Việt, audio kèm transcript, split chính thức và dữ liệu 16 kHz, thuận tiện tạo một bộ đối chiếu cố định cho nhiều model. [Dataset card chính thức](https://huggingface.co/datasets/google/fleurs) mô tả các đặc điểm này. Trong dự án, dữ liệu đã có sẵn, revision/ID/hash được lưu nên dùng lại dễ và không phải gán nhãn từ đầu. Đây là lựa chọn thực dụng để học pipeline; ta chưa làm thí nghiệm chứng minh FLEURS phù hợp nhất hoặc tốt hơn mọi dataset khác.

Đánh đổi là FLEURS chủ yếu là lời nói đọc, chưa đại diện hội thoại và tiếng ồn của kính; Zipformer còn liệt kê FLEURS trong nguồn train nên chưa chắc dữ liệu đang chấm độc lập với checkpoint. Vì vậy nó đóng vai trò bộ đối chiếu công khai, cần bổ sung tự thu để trả lời bối cảnh của đề tài. Nếu thay bằng bộ khác thì phải xét nguồn nhãn, ngôn ngữ/miền, split và khả năng trùng train, không chỉ thay vì tên dataset khác.
Ngoài các metrics đã thực sự tính còn có thể đánh giá thêm bằng các chỉ số nào?
-> Ngoài WER_ws/CER và các số đo thời gian, RTF, RAM đã có, có thể bổ sung các chỉ số theo câu hỏi muốn trả lời; không cần làm hết:

- Tỷ lệ câu có lỗi (SER) hoặc câu khớp hoàn toàn: dễ hiểu, nhưng sai một tiếng và sai gần hết đều là một câu lỗi. Có thể tính từ transcript đã lưu.
- Độ trễ phụ đề end-to-end: ví dụ từ lúc hết lời nói đến khi final text hiện ra; báo median/p50 và p95 để thấy cả những lần chờ lâu. Phải ghi mốc đo; không lấy inference WAV thay chỉ số này. Với ít lượt, p95 chỉ là mô tả sơ bộ.
- Chữ sinh khi không có lời nói: số lần phát final caption không rỗng mỗi phút audio không lời nói. Hàm hiện đã có trường false_captions_per_minute, nhưng chưa có tập im lặng để đo; cần định nghĩa một lần phát caption và lưu log khi thử pipeline.
- Bỏ sót/cắt mất lời: tỷ lệ đoạn có lời nói nhưng không có output, hoặc ranh giới chia đoạn làm mất tiếng đầu/cuối. Muốn chấm VAD chính xác hơn phải có nhãn khoảng thời gian lời nói để tính precision/recall hoặc mức bỏ sót/báo nhầm.
- Độ đúng thông tin quan trọng: số, tên riêng, phủ định; cần xác định trước cách chấm và mẫu nào được tính. Chỉ số này bổ sung cho WER, không thay WER bằng nhận xét chủ quan.
- Mức ổn định: tỷ lệ lỗi/timeout, thời gian từng lượt hoặc theo nhóm điều kiện. S/D/I đã được đếm trong JSONL nên có thể tổng hợp để biết thiên về thay, xóa hay chèn. Không suy riêng tác động tiếng ồn từ hai nhóm khác cả câu/người.

Với pipeline nhỏ, nên giữ WER_ws/CER và ưu tiên thêm độ trễ end-to-end, chữ khi im lặng, đoạn bị bỏ sót và tỷ lệ lỗi chạy. Các chỉ số mới chưa được đo chỉ vì đã liệt kê ở đây; chưa thêm bộ tách từ, scorer mới hoặc chạy thí nghiệm.
