# UI/UX sản phẩm — giao tiếp đa phương thức giữa hai người

Cập nhật: 07/11/2026. Trạng thái: **ghi nhận yêu cầu và chuẩn bị thảo luận**, chưa phải thiết kế giao diện đã duyệt hoặc tính năng đã triển khai.

> **Yêu cầu cốt lõi của người dùng: “giao tiếp giữa 2 người, giao tiếp multi modal”.**
>
> Hai người có thể trao đổi qua ngôn ngữ ký hiệu, giọng nói hoặc chữ. Sản phẩm cần tổ chức cuộc hội thoại, chuyển đổi nội dung sang dạng người kia có thể tiếp nhận, và có menu Settings. Giao diện P1 hiện tại chưa được xem là giao diện sản phẩm cuối.

Đọc nhanh: phần 1 là yêu cầu đã xác nhận; phần 2–4 là ý tưởng để bàn; phần 5 là những quyết định còn mở. [Bàn giao phiên tiếp theo](START_NEXT_CHAT_STT.md) · [Đặc tả STT hiện tại](STT_SYSTEM_SPEC.md) · [BOM](STT_BOM.md).

## 1. Những gì đã xác nhận

**Đa phương thức (multimodal)** ở đây là nhiều cách đưa vào và tiếp nhận nội dung trong **cuộc giao tiếp giữa hai người**. Các phương thức người dùng nêu:

| Phương thức | Vai trò trong cuộc giao tiếp | Trạng thái |
| :--- | :--- | :--- |
| Ngôn ngữ ký hiệu → chữ (sign-to-text) | Một người ký hiệu, nội dung được chuyển thành chữ để người kia đọc | Định hướng sản phẩm; chưa triển khai trong ứng dụng P1 |
| Giọng nói → chữ (speech-to-text, STT) | Một người nói, người kia đọc nội dung đã nhận dạng | P1 mới có một file audio → chữ cuối; chưa có thu micro Pi/Record/Stop |
| Nhập chữ | Soạn nội dung trực tiếp để người kia đọc | Yêu cầu giao tiếp bằng text; chưa có vùng soạn hội thoại trong P1 |
| Chữ → giọng nói (text-to-speech, TTS) | Phát nội dung chữ thành tiếng khi người dùng cần | Định hướng sản phẩm; chưa có TTS trong P1 |
| Settings / Cài đặt | Cấu hình thiết bị, dịch vụ và cách hiển thị/phát nội dung | P1 mới có cấu hình Deepgram tại máy; các mục cho sản phẩm đa phương thức còn phải thiết kế |

- **Tham khảo tinh thần UI/UX:** Codex, LearnHarness, các Agent Harness và ứng dụng chat/messenger — cách tổ chức nội dung hội thoại, vùng nhập, điều hướng và Settings. Đây là tham chiếu người dùng nêu, chưa phải kết quả khảo sát trực tiếp các giao diện đó trong lượt này.
- **Sản phẩm đích:** thiết bị để bàn có màn cảm ứng, Electron và kiosk mode. Stack đã chốt vẫn là React + TypeScript + Tailwind CSS, Next.js/Node.js + Electron.
- **Màu sắc:** người dùng không thích bảng màu trong ảnh tham khảo. Chưa chốt bảng màu thay thế, theme sáng/tối, font hay bộ icon.
- **Thứ tự triển khai:** tiếp tục nghiệm thu V1 STT trước V2/V3. Tài liệu này mở hướng thảo luận sản phẩm đa phương thức, chưa giao thêm phần việc sign-to-text/TTS hoặc thay giao diện ngay.

## 2. Ý tưởng tổ chức hội thoại để cùng bàn

**Đề xuất, chưa chốt:** một không gian hội thoại chung, có nhãn rõ người A/người B, phương thức đầu vào và trạng thái của từng lượt. A/B chỉ là nhãn tạm, không mặc định khả năng nghe/nói hoặc phương thức cố định của mỗi người.

Ví dụ minh họa tương tác, không phải kết quả nhận dạng thật:

1. A dùng ký hiệu → hệ thống tạo bản chữ nháp → A có thể kiểm tra/sửa trước khi gửi cho B.
2. B trả lời bằng giọng nói → STT tạo chữ → A đọc; hoặc B gõ chữ trực tiếp.
3. Khi cần, người dùng chọn phát một nội dung chữ bằng TTS; hiển thị rõ đang phát lượt nào và có nút dừng phát.

Việc kiểm tra trước khi gửi, cách sửa chữ và cách phát TTS ở ví dụ này là đề xuất cần duyệt. **Không tự động phát mọi kết quả nhận dạng hoặc tự suy người đang nói.** Cần bàn cơ chế chọn người/lượt và xử lý khi hai người cùng tương tác.

Với V1 STT, vẫn giữ Record → Stop dừng capture → nhận dạng → chữ cuối hoặc lỗi. Chữ tạm thay đổi khi đang nói thuộc các mốc sau theo kế hoạch; không dùng bản phác UI để khẳng định V1 đã có streaming.

## 3. Bố cục sơ bộ, chưa phải mockup đã duyệt

| Vùng giao diện | Nội dung đề xuất | Việc cần bàn |
| :--- | :--- | :--- |
| Điều hướng gọn | Cuộc hội thoại, công cụ nhập file, Settings | Sidebar cố định, thu gọn hay menu; lịch sử hội thoại có lưu hay không |
| Vùng hội thoại chính | Lượt của hai người, chữ dễ đọc, nhãn phương thức/trạng thái | Bubble chat hay hai vùng người A/B; hiển thị cho hai người cùng phía hay đối diện |
| Vùng tạo lượt | Chọn người, nhập chữ, chọn giọng nói/ký hiệu; điều khiển Record/Stop | Một vùng dùng chung hay điều khiển riêng cho từng người |
| Vùng camera/ký hiệu | Preview có thể mở rộng khi cần thu ký hiệu | Camera có bắt buộc hiện liên tục không; phần nào phục vụ người dùng/phần nào chỉ để kiểm tra |
| Trạng thái và Settings | Nguồn mic/camera đã chọn, đang thu/xử lý/phát, lỗi và cách thử lại | Mục thường dùng đưa ra màn chính; mục kỹ thuật đặt trong Settings |

Đề xuất giữ nhận dạng một file/batch ở công cụ nhập dữ liệu hoặc kiểm thử, để màn hội thoại tập trung vào cuộc trao đổi. Chưa chốt vị trí cuối cùng; chức năng file/batch của V1 vẫn phải được giữ và kiểm thử.

Các mục Settings cần bàn thêm: nguồn mic/device path trên Pi, camera, Deepgram `language=vi` và key trên backend, cỡ chữ, âm lượng/giọng TTS, hành vi lưu/xóa hội thoại. Chưa chọn engine TTS hay mô hình ký hiệu. Browser laptop không tự dùng micro của nó khi đang điều khiển thiết bị Pi.

## 4. Ghi nhận ảnh tham khảo người dùng gửi

![Ảnh tham khảo Hand Morse do người dùng cung cấp](reports/ui_ux_20261107/assets/hand_morse_user_reference.png)

**Quan sát từ ảnh tĩnh:** vùng camera lớn ở giữa, các panel trạng thái/đo bàn tay, bảng Morse bên phải, vùng message phía dưới và các gợi ý phím tắt. Chưa kiểm chứng cách ứng dụng trong ảnh thực sự hoạt động; lớp nút Play/tìm kiếm có thể thuộc trình xem video và không dùng làm yêu cầu sản phẩm.

**Ý có thể thử khi phác thảo:** phối hợp preview camera với nội dung chữ, báo trạng thái thu rõ ràng, mở/ẩn panel phụ. Người dùng thấy giao diện này hay nhưng chưa chỉ định chính xác phần nào cần giữ, nên đây là các đề xuất để trao đổi.

**Không đưa bảng màu ảnh vào thiết kế mặc định.** Camera, panel và bố cục có thể được nghiên cứu với bảng màu khác. Bảng Morse, số FPS, góc ngón tay và phím tắt trong ảnh chưa phải yêu cầu của sản phẩm. Nhận dạng ký hiệu của dự án không được coi là mã Morse hoặc đã giải được chỉ từ nhận dạng khung xương bàn tay.

## 5. Quyết định cho phiên thảo luận tiếp theo

Ưu tiên bàn ba việc đầu để có thể vẽ các phương án bố cục:

1. **Hai người dùng màn hình thế nào?** Cùng nhìn một mặt màn, ngồi đối diện, hay luân phiên thao tác? Điểm này ảnh hưởng góc nhìn, cỡ màn và giá đỡ trong BOM.
2. **Tổ chức cuộc trao đổi thế nào?** Hội thoại cuộn như messenger, hai vùng A/B, hay kết hợp camera với hội thoại? Cách chọn người đang tạo lượt?
3. **Hướng màu nào muốn thử?** Nền sáng trung tính hoặc nền tối dịu là các khả năng để so sánh, chưa phải lựa chọn đã duyệt. Không lấy bảng màu ảnh làm mặc định.
4. **Phạm vi ký hiệu nào?** Ngôn ngữ ký hiệu/tập từ vựng, dữ liệu, model, đầu vào camera và cách xác nhận chữ chưa chốt; không tự hứa dịch ký hiệu tự do.
5. **Hành vi gửi/phát/lưu?** Gửi ngay hay xác nhận; cho sửa chữ thế nào; TTS theo nút bấm hay tự phát; lịch sử giữ trong phiên hay lưu sau khi đóng?

Sau khi có lựa chọn sơ bộ, đề xuất tạo 2–3 wireframe (bản phác vị trí các vùng, chưa đầu tư màu) theo cùng một kịch bản hai người. Đánh giá khả năng đọc/chạm/nhập chữ trên kích thước màn dự kiến, rồi mới chốt giao diện chi tiết. Đây là bước đề xuất, chưa triển khai trong lượt ghi nhận này.

## 6. Những điểm dùng để duyệt bản phác sau này

- Nhìn vào biết lượt của ai, nhập bằng phương thức gì, đang thu/xử lý/chờ xác nhận/đã gửi hay lỗi; không chỉ dùng màu để phân biệt.
- Cả hai người có cách trả lời và nhận nội dung phù hợp; có thể đổi phương thức khi cần.
- Chữ và vùng chạm phù hợp màn thật; thao tác chính, Settings và bàn phím ảo dùng được bằng cảm ứng, không phụ thuộc hover hoặc phím tắt.
- Khi lỗi pipeline, nói rõ lượt nào lỗi, cho thử lại và giữ nội dung đã có; không hiện kết quả chưa nhận được như thành công.
- Điều khiển Record/Stop và dừng TTS rõ ràng; thử thu khi phát loa trước khi quyết định xử lý vọng âm.

Đây là tiêu chí thảo luận thiết kế, **chưa phải kiểm thử đã đạt**. Hiện chỉ cập nhật tài liệu và lưu ảnh tham chiếu; không thay mã ứng dụng, mua thiết bị hoặc mở thêm một nhánh triển khai đa phương thức.
