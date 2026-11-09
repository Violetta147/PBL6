# UI/UX sản phẩm — giao tiếp đa phương thức giữa hai người

Cập nhật 09/11/2026. Tài liệu ghi các quyết định thiết kế, những điểm đang thảo luận và kịch bản cần duyệt trên bản phác. Kết quả triển khai P1 được ghi riêng trong [báo cáo P1](reports/stt_v1_p1_20261107/BAO_CAO.md).

> **Yêu cầu cốt lõi của người dùng: “giao tiếp giữa 2 người, giao tiếp multi modal”.**
>
> Hai người dùng chung màn hình để trao đổi. PBL6 phụ trách chuyển giọng nói thành chữ, đọc chữ thành tiếng và Settings. Chữ để đọc có thể đến từ luồng khác, chẳng hạn kết quả của dự án nhận dạng ký hiệu.

Đọc mục 1–3 để nắm phạm vi, luồng thu và quy tắc Lịch sử. Mục 4 ghi các tham chiếu. Mục 5–6 hướng dẫn duyệt một lượt STT trên bản phác. [Bàn giao phiên tiếp theo](START_NEXT_CHAT_STT.md) · [Đặc tả STT hiện tại](STT_SYSTEM_SPEC.md) · [BOM](STT_BOM.md)

## 1. Những gì đã xác nhận

**Hai người dùng một vùng soạn chung.** Ai cũng có thể nhập vào vùng này. Hai người có thể ngồi cạnh hoặc chếch nhau, cùng nhìn màn hoặc xoay cả thiết bị để đổi hướng nhìn. Giá đỡ là phụ kiện, còn kiểu giá đỡ và cách lắp sẽ bàn riêng.

| Phương thức | Vai trò trong cuộc giao tiếp | Trạng thái |
| :--- | :--- | :--- |
| **Nhận dạng giọng nói (STT)** | Một người nói, xem và sửa chữ nhận được rồi gửi cho người kia đọc. | P1 nhận dạng một file và trả chữ cuối. Thu và dừng bằng mic trên Pi thuộc phần V1 còn lại. |
| **Nhập chữ** | Có thể gõ trực tiếp vào cùng vùng soạn rồi gửi. | Vùng soạn hội thoại thuộc thiết kế đang duyệt. Việc gõ chữ để phát thành tiếng sẽ bàn cùng TTS. |
| **Đọc chữ thành tiếng (TTS)** | **Đọc to** là thao tác riêng với **Gửi**. | Tạm hoãn chốt vị trí nút loa, phần chữ được đọc và bộ tạo giọng. Giải pháp PBL6 phải hoạt động độc lập với gói đăng ký ChatGPT. |
| **Văn bản từ luồng khác** | PBL6 có thể nhận chữ có sẵn, ví dụ đầu ra của dự án nhận dạng ký hiệu. | Mô hình nhận dạng ký hiệu và camera phục vụ mô hình thuộc phần tích hợp riêng. Cách đưa chữ vào PBL6 còn để bàn. |
| **Settings** | Có mục **Xóa lịch sử** theo quy tắc ở mục 3. | P1 đã có cài đặt key Deepgram tại máy. Các mục còn lại sẽ chốt theo từng luồng. |

- **Sản phẩm đích.** Thiết bị để bàn có màn cảm ứng và Electron ở chế độ kiosk. Stack đã chốt là React + TypeScript + Tailwind CSS, Next.js/Node.js và Electron.
- **Màu sắc.** Ảnh tham khảo dùng để xem bố cục. Bảng màu thay thế, theme sáng hoặc tối, font và bộ icon còn để duyệt.
- **Mốc phần mềm.** Hoàn thành V1 STT trước V2 và V3. Duyệt giao diện là một bước riêng trước khi người dùng yêu cầu triển khai.

## 2. Thu, sửa và gửi trong vùng soạn chung

Chạm biểu tượng **mic** để bắt đầu thu. Vùng soạn vẫn hiện phía trên thanh báo thu và nút mic đổi thành **hình vuông** ngay tại chỗ. Chạm hình vuông để dừng. Trong lúc nhận dạng, nút hiện **vòng xoay**. Khi có chữ cuối, biểu tượng mic trở lại và ứng dụng đưa chữ vào vùng soạn để người dùng đọc lại. Nếu câu đã đúng, có thể bấm **Gửi** ngay.

Chạm vùng soạn để mở **bàn phím ảo** khi cần nhập hoặc sửa. Dùng **Backspace** trên bàn phím để xóa chữ. Việc nhận dạng xong tự điền chữ vào vùng soạn và giữ bàn phím ở trạng thái đóng nếu người dùng chưa chạm vào vùng đó. Người dùng cũng có thể gõ trực tiếp. Chỉ thao tác **Gửi** mới đưa chữ vào hội thoại.

Trong V1, ứng dụng nhận dạng sau khi dừng thu và trả về chữ cuối hoặc lỗi rõ ràng. V2 gửi âm thanh trong lúc thu và vẫn hiển thị chữ cuối. V3 bổ sung chữ tạm cập nhật trong lúc nói. Khi laptop điều khiển Pi, nguồn thu là thiết bị đã chọn trên Pi.

**Còn để bàn.** Cách xử lý khi vùng soạn đã có chữ hoặc khi hai người thao tác đồng thời, cách giữ bản nháp, có lưu audio thô hay tệp tạm hay không, và định dạng lưu. JSON và tệp phân mảnh là các ý tưởng để xem xét khi cần.

### Cách hình dung “harness bao quanh model”

*Harness* là cách hình dung lớp ứng dụng tổ chức phiên, thiết bị đầu vào và trạng thái thu, xử lý hoặc phát. Một bộ kết nối có thể chuyển yêu cầu tới dịch vụ hoặc bộ xử lý chạy tại máy rồi trả kết quả về đúng lượt. Đây là một cách phân chia đang bàn.

Đổi bộ xử lý qua bộ kết nối và cho cài plugin lúc chạy là hai quyết định riêng. Cordis, cơ chế plugin và cách các luồng trao đổi dữ liệu vẫn là chủ đề thảo luận. [Bản so sánh Cordis](comparision_everything_is_a_plugin.md) · [Ghi chú Everything is a Plugin](everything_is_a_plugin_cordis.md)

## 3. Bố cục, Lịch sử và Settings

| Vùng giao diện | Nội dung đã xác định | Việc cần duyệt trên bản phác |
| :--- | :--- | :--- |
| Điều hướng | Hội thoại, Lịch sử và Settings. | Cách mở và thu gọn Lịch sử trên màn nhỏ. Vị trí công cụ nhập file hoặc batch. |
| Vùng hội thoại | Hiển thị các tin đã gửi để hai người cùng đọc. | Cỡ chữ, bố cục từng tin và việc có cần nhãn nguồn nhập. |
| Vùng soạn | Một vùng soạn chung có mic và **Gửi**. Khi chạm vào vùng soạn, bàn phím mở dưới cùng. Vùng soạn và **Gửi** ở ngay phía trên. Vùng hội thoại dùng phần chiều cao còn lại và có thể cuộn. | Kiểm tra độ dễ nhận ra các trạng thái thu, chờ và lỗi. Bàn cách xử lý bàn phím sau khi gửi. |
| Settings | Cài đặt Deepgram đã có ở P1. **Xóa lịch sử** đã chốt ở mức thiết kế. | Cách trình bày nguồn mic trên Pi và các mục hiển thị. Mục âm thanh sẽ bàn cùng TTS. |

Khi triển khai bàn phím, cập nhật vùng soạn và trạng thái nút **Gửi** theo từng phím. [Khảo sát vùng soạn và bàn phím ảo](reports/NGHIEN_CUU_VUNG_SOAN_VA_BAN_PHIM_AO.md)

### Quy tắc Lịch sử đã chốt

**Mỗi lần mở ứng dụng, màn chính hiện một hội thoại mới.** Người dùng cũng có thể bấm **+ Hội thoại mới** trong lúc ứng dụng đang mở. Bản phác đặt nút này trong bảng Lịch sử. Hội thoại chỉ xuất hiện trong **Lịch sử** sau khi gửi thành công tin đầu tiên. Các tin đã gửi mở lại được sau khi đóng và mở ứng dụng.

**Thứ tự trong Lịch sử.** Dùng quy tắc **Last updated** của DeepSeek Harness theo thời điểm gửi thành công tin nhắn gần nhất. Gửi thêm tin đưa hội thoại lên đầu. Mở để xem, đổi tên hoặc bấm **Đọc to** giữ nguyên vị trí. [Nghiên cứu cách sắp xếp Lịch sử](reports/NGHIEN_CUU_SAP_XEP_LICH_SU.md)

**Xóa lịch sử trong Settings.** Người dùng chọn hội thoại cần xóa trong danh sách đã lưu. Bấm **Delete** để xóa ngay các hội thoại đã chọn.

### Phương án đang thảo luận

**Tên hội thoại.** Phương án tham khảo LearnHarness dùng tin đã gửi đầu tiên làm tên ban đầu và rút gọn ở ranh giới từ nếu câu dài. ID hội thoại tách với tên hiển thị. Hai cách mở phần đổi tên đang bàn là chạm tiêu đề trên cùng hoặc dùng menu chuột phải của một mục trong Lịch sử. [Nghiên cứu cách đặt và đổi tên](reports/NGHIEN_CUU_DAT_TEN_HOI_THOAI.md)

**Các điểm còn mở.** Khả năng nhắn tiếp trong hội thoại đã mở lại, tìm kiếm hoặc xuất Lịch sử và chính sách giữ nội dung. Nhận dạng một file và batch vẫn thuộc phạm vi V1. Đặt chúng trong một công cụ nhập hoặc kiểm thử riêng là phương án đang bàn.

## 4. Ghi nhận ảnh tham khảo người dùng gửi

### Codex và LearnHarness — ảnh bổ sung ngày 07/11/2026

![Ảnh Codex do người dùng cung cấp](reports/ui_ux_20261107/assets/codex_conversation_user_reference.png)

**Quan sát từ ảnh Codex:** thanh điều hướng icon bên trái, tiêu đề cuộc trao đổi phía trên, nội dung hội thoại ở vùng trung tâm và vùng nhập ở phía dưới với các điều khiển kèm theo. Ảnh cho thấy bố cục của một cuộc trao đổi; không đủ để xác nhận toàn bộ cơ chế lưu/chuyển phiên.

![Ảnh LearnHarness do người dùng cung cấp](reports/ui_ux_20261107/assets/learnharness_sessions_user_reference.png)

**Quan sát từ ảnh LearnHarness:** sidebar có danh sách SESSIONS, ô tìm kiếm, mục được chọn; vùng nội dung có tiêu đề và vùng nhập/điều khiển phía dưới; Settings ở cuối sidebar. Các chế độ teaching/practice thuộc mục đích của nền tảng tham khảo, chưa phải yêu cầu sản phẩm này.

**DeepSeek Harness.** Đã khảo sát bản `0.2.1-rc.5` trên máy cùng Codex Desktop và LearnHarness `0.5.0`. Kết quả được lưu riêng theo chủ đề [đặt và đổi tên](reports/NGHIEN_CUU_DAT_TEN_HOI_THOAI.md), [sắp xếp Lịch sử](reports/NGHIEN_CUU_SAP_XEP_LICH_SU.md) và [nút Đọc to](reports/NGHIEN_CUU_DOC_TO_CAC_HARNESS.md).

Các ảnh dùng để đối chiếu bố cục và cách tổ chức hội thoại. Kiểu hiển thị, màu sắc và cách lưu dữ liệu của PBL6 được quyết định theo nhu cầu của nhóm.

### Hand Morse — ảnh tham khảo trước đó

![Ảnh tham khảo Hand Morse do người dùng cung cấp](reports/ui_ux_20261107/assets/hand_morse_user_reference.png)

**Quan sát từ ảnh tĩnh:** vùng camera lớn ở giữa, các panel trạng thái/đo bàn tay, bảng Morse bên phải, vùng message phía dưới và các gợi ý phím tắt. Chưa kiểm chứng cách ứng dụng trong ảnh thực sự hoạt động; lớp nút Play/tìm kiếm có thể thuộc trình xem video và không dùng làm yêu cầu sản phẩm.

Ảnh Hand Morse được giữ làm tham chiếu bố cục từ phạm vi thảo luận ban đầu. Camera và mô hình nhận dạng ký hiệu thuộc phần tích hợp riêng. Lượt duyệt STT dùng mic và vùng soạn chung.

## 5. Kịch bản duyệt trong phiên tiếp theo

Mở bản phác Pencil và xem các khung **Trao đổi**, **Bàn phím mở** và **Mở lịch sử**. Duyệt một người chạm mic, dừng thu và đợi câu xuất hiện trong vùng soạn. Người đó đọc lại, chạm vào vùng soạn để sửa nếu cần, rồi bấm **Gửi**. Sau đó đối chiếu cách tin hiển thị và hội thoại xuất hiện trong Lịch sử. [Bản phác Pencil 1024 × 600](reports/ui_ux_20261107/assets/wireframe-hoi-thoai-1024x600.pen)

Nếu có điểm chưa rõ, bàn từng điểm trực tiếp trên kịch bản này. Các nút **Đọc** và **Chọn file** trong bản phác là cách bố trí để tham khảo. Khi quay lại TTS, xem các phương án vị trí, phần chữ cần đọc và cách tạo giọng. [Khảo sát nút Đọc to](reports/NGHIEN_CUU_DOC_TO_CAC_HARNESS.md)

## 6. Tiêu chí duyệt bản phác

- Biểu tượng mic và trạng thái cho biết lúc nào đang thu, đang nhận dạng hoặc có lỗi.
- Phân biệt được chữ đang soạn và tin đã gửi. Chạm vùng soạn mở bàn phím và vẫn nhìn thấy câu đang sửa cùng nút **Gửi**.
- Người dùng có thể thao tác chính bằng một lần chạm trên vùng điều khiển và cùng đọc nội dung trên màn 7 inch.
- Tin đầu tiên được gửi thành công thì hội thoại xuất hiện trong **Lịch sử**. Sau khi đóng và mở ứng dụng, màn chính hiện cuộc mới và người dùng có thể mở lại cuộc đã lưu.

Đây là tiêu chí duyệt thiết kế. Lượt thử trên phần cứng sẽ đối chiếu thêm độ phân giải, vị trí chạm, vuốt và bàn phím tiếng Việt theo [hướng dẫn NH2067](HUONG_DAN_NH2067_PI4.md).
