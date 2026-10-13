# Những điểm chưa chặt trong B01–B04

Đối chiếu tài liệu hỏi–đáp, mã runner và output đã lưu ngày 13/10/2026. Cần phân biệt lỗi phép so sánh với giới hạn của thí nghiệm; không phải mọi câu hỏi khái niệm đều là mâu thuẫn.

1. **Hai phạm vi thời gian khác nhau.** Zipformer có tổng inference khoảng 10,3 s; Whisper-tiny báo wall khoảng 171–173 s, gồm các việc ngoài inference. Chia hai số để báo “nhanh hơn bao nhiêu lần” không hợp lệ.

2. **Hai chính sách nạp model khác nhau.** Zipformer nạp một lần cho 20 WAV; adapter Whisper.cpp nạp lại tuần tự từng WAV. Đây là khác biệt do cách triển khai phép đo, không phải yêu cầu bắt buộc của Whisper. Dùng CLI cho tiện không làm phép so trở nên đồng nhất.

3. **Baseline Whisper thay cả checkpoint và runtime.** Laptop dùng base/openai-whisper, Pi có base smoke một câu rồi tiny/whisper.cpp trên 20 câu. Không gọi đây là cùng một model đã được đo đầy đủ trên hai thiết bị; C0-base/Pi còn thiếu lượt đủ self dev20. Chậm là kết quả cần ghi khi đánh giá baseline cố định; tiny chỉ là khảo sát bổ sung, không thay kết quả C0-base.

4. **“B04 hoàn tất” trước đó nói quá rộng.** Đã có output và số đo từng cấu hình, nhưng chưa hoàn tất đối chiếu tốc độ cùng điều kiện, chưa có pipeline audio liên tục. Phần tổng quan cũ và các đính chính về sau trong file hỏi–đáp chưa thống nhất cách gọi trạng thái. Tôi đã đánh dấu xong quá sớm so với phạm vi kết luận.

5. **Dễ biến lựa chọn thực dụng thành kết luận về kiến trúc.** Model có sẵn khác nhau ở trọng số, dữ liệu huấn luyện, kích cỡ, giải mã và runtime. Có thể so chất lượng các hệ thống trên cùng dữ liệu; chưa thể quy chênh lệch cho riêng kiến trúc hoặc INT8. Runtime/hai luồng cũng chưa được thử để chứng minh tối ưu.

6. **FLEURS chưa xác minh độc lập với train của checkpoint.** Model card Zipformer liệt kê FLEURS, nhưng chưa xác minh split/ID đã dùng. Đây là điều chưa biết, không phải bằng chứng đã rò rỉ. Đổi sang FLEURS test không tự xóa nghi vấn ấy.

7. **Self dev20 chưa đại diện cho sử dụng kính.** Chỉ một người đọc, 2 câu phòng ngủ/18 câu cà phê; các câu khác nội dung nên chưa cô lập được tác động môi trường. Điểm tốt trên bộ này hỗ trợ chọn ứng viên, chưa chứng minh chất lượng hội thoại nhiều người hoặc micro trên kính.

8. **RTF tệp chưa là độ trễ phụ đề.** WAV đã có đủ và được chia sẵn; chưa đo chờ người nói kết thúc, VAD, hàng đợi hoặc hiển thị. ASR offline có thể ghép vào một pipeline nhận audio liên tục, nhưng không vì thế trở thành streaming ASR nguyên sinh.

9. **“Chưa thử Qwen trên Pi” không đồng nghĩa “không chạy được”.** Qwen được giới hạn GPU theo phạm vi đã chọn. Có đường triển khai ONNX INT8 được ghi trong hỏi–đáp, nhưng chưa chạy/đo trên Pi. Không khẳng định bất khả thi hoặc gán điểm GPU cho bản INT8.

Những việc **không tự tạo lỗi so sánh**: dùng WER_ws thay tách từ nếu ghi đúng tên; chữ hoa/thường khác nhau khi scorer xử lý giống nhau; dùng model pretrained có runtime khác nhau để so các hệ thống thực dụng; giữ dev để lựa chọn và bộ mới để đánh giá dù không huấn luyện lại. Với từng việc, phải nói rõ câu hỏi nghiên cứu và giới hạn.

**Giữ được:** transcript, điểm trên các subset đã chấm, log và số đo riêng từng cấu hình. **Chưa được kết luận:** tỷ lệ tăng tốc trực tiếp, kiến trúc tốt nhất hoặc phụ đề thực tế đã đạt. Không cần bỏ toàn bộ kết quả; cần sửa cách đo hoặc thu hẹp kết luận.

Chưa chạy lại benchmark và chưa thay đổi kế hoạch 7 buổi trong lần lập báo cáo này.
