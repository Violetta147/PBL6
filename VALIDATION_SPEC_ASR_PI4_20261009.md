# Kiểm tra bộ tài liệu lean

Ngày 09/10/2026, phiên bản phạm vi 2.0. Kiểm tra [đặc tả](SPEC_ASR_PI4_RESEARCH_20261009.md), [kế hoạch](PLAN_DEMO_STT_7_BUOI.md), [ghi chú học tập](REVIEW_CONCEPTS_20261009.md), trang đặc tả cũ và [README](README.md). Đây là kiểm tra tài liệu, chưa phải thực nghiệm ASR.

## Phạm vi được thống nhất

Ba ứng viên C0/C1/C2; trọng số có sẵn; một notebook và script/CLI Pi khi cần. Đánh giá dự kiến: 100 FLEURS dev/200 test, 20 câu tự thu dev/30–50 test, khoảng 2 phút không có lời nói. Benchmark Pi 20 tệp dev × hai lượt, thử micro 5–10 phút. B01–B07 tương ứng một buổi mỗi tuần.

Bỏ các yêu cầu bắt buộc về đủ 35 bước ML, phụ đề tạm, giao thức caption riêng, bộ phần mềm nhiều tầng, chiến dịch thu dữ liệu lớn, stress test ba lượt và thống kê suy luận. Giữ scorer chung, chọn trên dev, test sau chốt, ghi lỗi/coverage, phân biệt Pi/Colab và lưu output.

Tài liệu cũ trở thành trang dẫn; ghi chú Concepts giữ các điểm cần cho học tập. Bản chi tiết trước thay đổi xem bằng `git show c566918:<tên-file>`. Quy tắc làm việc trong AGENTS.md và các nguồn dữ liệu không thay đổi.

## Kiểm tra tài liệu: đạt

Đã kiểm tra đủ 10 mục đặc tả, T1–T5 và B01–B07 với ba việc chuẩn bị mỗi buổi. Số mẫu và phạm vi thống nhất, test sau chốt B05; liên kết tệp tồn tại, code fence cân bằng, không có lỗi Unicode/khoảng trắng. Đối chiếu Git xác nhận phần nguồn/revision/checksum dataset trong README giữ nguyên, AGENTS.md và .gitignore không đổi; chỉ sáu tệp tài liệu thuộc thay đổi này. Kiểm tra `git diff --check` đạt. Đây là kiểm tra tài liệu, không phải kiểm thử runtime hoặc chất lượng model.

Các nguồn model/runtime đã được đối chiếu trong đợt soạn trước cùng ngày; lần này sửa phạm vi và cách tổ chức công việc, không thực hiện một đợt tìm kiếm model mới. Các liên kết chính vẫn nằm trong đặc tả. Chín chat tham chiếu và các trang Stage/bài tập là bối cảnh đã đọc; chúng không tạo thêm checklist bắt buộc.

## Trạng thái thực nghiệm

Rà soát phạm vi ngày 09/10/2026: sáu tệp tài liệu hiện hành chỉ hướng dẫn bài toán STT; đã loại bỏ các tham chiếu đến bài toán nhận dạng khác và yêu cầu kết nối với bài toán đó. Kiểm tra nội dung, liên kết nội bộ và `git diff --check` đạt.

Chưa có inference, thu âm, training, đo WER/CER, benchmark Pi hoặc thử kính trong thay đổi này. Mọi số mẫu/thời lượng là kế hoạch; các ô kết quả thực nghiệm phải ghi “chưa đo” đến khi chạy. Không xác nhận quota/thiết bị từ xa, không tải lại archive hoặc kiểm tra lại CRC toàn bộ dữ liệu ở lần sửa tài liệu này.
