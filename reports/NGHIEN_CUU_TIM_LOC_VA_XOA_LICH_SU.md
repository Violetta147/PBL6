# Nghiên cứu tìm, lọc và xóa hội thoại đã lưu

**PBL6.** Đối chiếu `dsh-chat-manager` của DeepSeek Harness và LearnHarness để thiết kế mục **Cài đặt → Lịch sử** trên màn 7 inch. Đọc theo thứ tự **vấn đề → cách hai ứng dụng xử lý → quyết định của PBL6**.

## 1. Vấn đề trong bản phác

Bản phác ban đầu của khung 10 dùng ô chọn từng dòng và nút **Xóa N hội thoại**. Với lịch sử dài, người dùng phải cuộn để tìm hội thoại và chạm từng dòng muốn xóa. ==Tìm và lọc giúp thu hẹp danh sách. Chọn hàng loạt giúp giảm số lần chạm.== [Đặc tả UI/UX và khung Pencil](../STT_PRODUCT_UI_UX.md#5-kịch-bản-v1-trên-bản-phác)

## 2. Cách hai ứng dụng xử lý

| Ứng dụng | Tìm và lọc | Xóa |
| --- | --- | --- |
| **DeepSeek Harness + `dsh-chat-manager`** | Bản **DSH-Portable** có trang phiên đã lưu trữ, tìm theo tên, workspace hoặc nội dung tin nhắn của người dùng và trợ lý. Trên **DSH chính thức**, plugin bổ sung mục xóa vào menu phiên và dùng trang lưu trữ gốc. [Hướng dẫn bản 1.5.21](https://github.com/WSL043/dsh-chat-manager/blob/v1.5.21/README.en.md#use) | Chọn **⋯ → Delete permanently**. Hộp thoại hiện tên phiên, rồi gửi yêu cầu xóa sau khi người dùng xác nhận. Luồng kiểm tra xử lý **một phiên mỗi lần**, với một `sessionId` trong yêu cầu. [Mã menu và hộp thoại xóa](https://github.com/WSL043/dsh-chat-manager/blob/v1.5.21/lib/client.js#L20-L72) |
| **LearnHarness 0.5.0** | Thanh bên **Sessions** tìm theo tiêu đề và lọc **Teaching / All / Practice**. Bộ lọc chạy trên danh sách phiên đã tải. [Mã tìm và lọc](https://github.com/amosblomqvist/learnharness/blob/713377f366771e3e4730e6acd1bc290e0ebc6d6e/components/sidebar.tsx#L419-L435) | Nhấn chuột phải vào một phiên, chọn **Delete…** rồi xác nhận trong hộp thoại có tên phiên. Mặc định giữ đóng góp của phiên trong đồ thị kiến thức. Có tùy chọn dọn cả các dấu vết đó. [Menu phiên](https://github.com/amosblomqvist/learnharness/blob/713377f366771e3e4730e6acd1bc290e0ebc6d6e/components/sidebar.tsx#L919-L942), [Hộp thoại xóa](https://github.com/amosblomqvist/learnharness/blob/713377f366771e3e4730e6acd1bc290e0ebc6d6e/components/delete-session-dialog.tsx#L167-L237) |

**Luồng xóa nhiều phiên của LearnHarness.** Trong phần quản lý nguồn, người dùng có thể xóa nhiều nguồn cùng lúc và chọn xóa kèm các phiên liên quan. Đây là thao tác xuất phát từ phần quản lý nguồn. Trong thanh bên **Sessions**, hộp thoại mở từ menu của từng phiên. [Hộp thoại xóa nguồn](https://github.com/amosblomqvist/learnharness/blob/713377f366771e3e4730e6acd1bc290e0ebc6d6e/components/delete-source-dialog.tsx#L14-L28)

**Phạm vi xác minh.** Đã đọc mã từ bản cài `dsh-chat-manager` 1.5.20 và LearnHarness 0.5.0 trên Windows, đồng thời đối chiếu nguồn công khai của plugin 1.5.21. Hành vi được xác định từ mã và tài liệu. Chưa thực hiện thao tác xóa phiên trên hai ứng dụng.

## 3. Quyết định đã duyệt cho PBL6

1. **Tìm và lọc.** Đặt ô **Tìm theo tên** và bộ lọc **Thời gian** ngay trên danh sách. Bộ lọc dùng thời điểm gửi tin thành công gần nhất, cùng mốc với thứ tự Lịch sử. [Nghiên cứu quy tắc sắp xếp](NGHIEN_CUU_SAP_XEP_LICH_SU.md)
2. **Chọn hàng loạt.** Khi đang tìm hoặc lọc, hiện **Chọn N kết quả**. Nút chọn tất cả kết quả khớp điều kiện hiện tại, kể cả các dòng nằm ngoài vùng nhìn thấy. Có thể bỏ chọn từng dòng.
3. **Đổi phạm vi.** Khi đổi điều kiện tìm hoặc lọc, ==bỏ toàn bộ lựa chọn trước đó== để danh sách xóa chỉ gồm các hội thoại được chọn trong kết quả mới.
4. **Vị trí thao tác.** Chỉ danh sách cuộn. Ô tìm và bộ lọc giữ ở phía trên, nút **Xóa N hội thoại** giữ ở phía dưới. N là số hội thoại đang được chọn.
5. **Xóa.** Bấm **Xóa N hội thoại** để xóa ngay các hội thoại đã chọn, theo quy tắc đã chốt của PBL6. [Đặc tả UI/UX](../STT_PRODUCT_UI_UX.md#3-bố-cục-lịch-sử-và-settings)

**Ví dụ.** Lọc **Cũ hơn 30 ngày** và thấy **12 kết quả**. Bấm **Chọn 12 kết quả**, bỏ chọn hai hội thoại muốn giữ, rồi bấm **Xóa 10 hội thoại**. Hai hội thoại được bỏ chọn vẫn còn trong lịch sử. Mốc 30 ngày trong ví dụ minh họa cách lọc.

**Trạng thái.** Phương án đã duyệt ở mức thiết kế. Khung Pencil 10 đã minh họa tìm, lọc, chọn theo kết quả và nút xóa trong ví dụ trên. Hành vi khi đổi bộ lọc, cuộn hoặc xóa thuộc tiêu chí kiểm tra khi triển khai ứng dụng.
