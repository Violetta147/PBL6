# Kiểm tra Anatomy02 —29/10/2026

## Đạt
- Unit tests:4/4, checks/unit-tests.log.
- Trình duyệt Chrome:16 nhóm thao tác;0 lỗiJavaScript,0 yêu cầuHTTP ngoài. checks/ui-results.json.
- Rộng390px/320px:không tràn ngang.
- Anatomy lines:0 đầu nét thừa ở lắp/tách/mở vỏ cả sáng và tối.
- Đã xem ảnh tổng thể, phía sau, Pi riêng và cận4× ở hai chủ đề.
- Audit hình học tĩnh:0 lỗi hỗ trợ/tiếp xúc/xuyên khối.
- Orbit audit QUICK: mọi dòng lỗi0;251,83giây. Lấy mẫu nhanh không thay full audit; audit-quick.log.

## Chưa đạt hoặc chưa hoàn tất
- Full orbit audit:log chưa có dòng kết thúc turn audit passed; không báo đạt.
- Fidelity:khối tròn đạt; prism thất bại. Sai khác lớn nhất5,865px tại mic.mesh, khoảng3,78px tại miếng mặt camera; nhiều sai khác0,06–0,07px. Giữ log checks/fidelity.log, không tăng ngưỡng để che lỗi.
- Browser order/pops:bài đối chứng đảo thứ tự/ẩn khối không phát hiện lỗi; công cụ tự báo check is broken. Các số0 ở đây không phải bằng chứng đạt. checks/turn-browser.log.
- Chưa đủ phép đo để hứa60FPS.

## Giới hạn
Không kiểm chứng lỗ/vít, lắp ráp, khoảng hở dây, nguồn, nhiệt, âm học, AEC, FPS hoặc toàn pipelineAI trên Pi. Nội dung màn minh họa. Hình chiếu3D và tách cụm phục vụ giải thích bố trí.
# Cập nhật 04/11/2026

Đã bỏ dữ liệu trích xuất lịch sử học tập và phần truy vết nguồn khỏi bản phác thảo. Tab Thông số & giới hạn chỉ giữ mô tả bố trí và giới hạn kiểm chứng. README xác định đây là tham khảo cho thiết kế sản phẩm cuối, không phải điều kiện triển khai STT.

4/4 unit test và 16 nhóm kiểm tra trình duyệt đạt; không có lỗi JavaScript hoặc yêu cầu mạng ngoài. Đã xem ảnh mới. Các phép kiểm tra hình học, xoay, tách, cô lập và xuất SVG tiếp tục đạt. Chi tiết trong `cleanup_validation_20261104.json`. Nội dung còn lại giữ lịch sử kiểm tra trước.
