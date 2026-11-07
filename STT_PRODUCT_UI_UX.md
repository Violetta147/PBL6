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

- **Ba tham chiếu chính cho wireframe/khung giao diện:** Codex, LearnHarness và Deepseek Harness (hướng plugin-based do người dùng nêu). Người dùng thích cơ chế chat/conversation/session của LearnHarness và Codex, đồng thời nhận xét Codex phức tạp hơn. Messenger là tham chiếu bổ sung. Mục đích từng nền tảng khác sản phẩm này; lấy cách tổ chức tương tác làm chất liệu thiết kế, chưa chọn sao chép toàn bộ tính năng hoặc kiến trúc.
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

### Cách hình dung “harness bao quanh model”

**Nhận định sơ bộ của người dùng, cần tiếp tục làm rõ:** sản phẩm có thể được hình dung là một lớp phần mềm tổ chức việc sử dụng các model/engine STT, TTS và sign-to-text. Trong tài liệu này, *harness* chỉ cách hình dung lớp điều phối đó, chưa phải một kiến trúc plugin đã chốt.

Ở mức đề xuất, lớp phần mềm này quản lý người tham gia, phiên hội thoại, thiết bị đầu vào, trạng thái thu/xử lý/phát và cách đưa kết quả cho người kia. Adapter (bộ kết nối) chuyển yêu cầu tới engine chạy tại máy hoặc dịch vụ API, rồi trả kết quả/lỗi về đúng lượt. Model thực hiện nhận dạng hoặc tổng hợp; ứng dụng tổ chức trải nghiệm giao tiếp và vòng đời xử lý.

Luồng để thảo luận: **người A/B → phương thức nhập → lượt trong phiên → engine phù hợp → chữ/âm thanh cho người kia**. Một phiên chứa nhiều lượt; một lượt có thể trải qua nhiều bước, ví dụ STT → chữ đã xác nhận → TTS. Không mặc định mọi lượt cần đi qua cả ba engine.

**Tách hai quyết định:** khả năng đổi engine qua adapter và một hệ thống plugin cài thêm là hai mức thiết kế khác nhau. Việc tham khảo Deepseek Harness chưa chốt plugin runtime, marketplace, LLM điều phối hoặc cơ chế gọi tool cho dự án. Mục tiêu đánh giá vẫn là giao tiếp đa phương thức giữa hai người.

## 3. Bố cục sơ bộ, chưa phải mockup đã duyệt

| Vùng giao diện | Nội dung đề xuất | Việc cần bàn |
| :--- | :--- | :--- |
| Điều hướng gọn | Cuộc hội thoại, Lịch sử, công cụ nhập file, Settings | Sidebar cố định, thu gọn hay menu |
| Vùng hội thoại chính | Lượt của hai người, chữ dễ đọc, nhãn phương thức/trạng thái | Bubble chat hay hai vùng người A/B; hiển thị cho hai người cùng phía hay đối diện |
| Vùng tạo lượt | Chọn người, nhập chữ, chọn giọng nói/ký hiệu; điều khiển Record/Stop | Một vùng dùng chung hay điều khiển riêng cho từng người |
| Vùng camera/ký hiệu | Preview có thể mở rộng khi cần thu ký hiệu | Camera có bắt buộc hiện liên tục không; phần nào phục vụ người dùng/phần nào chỉ để kiểm tra |
| Trạng thái và Settings | Nguồn mic/camera đã chọn, đang thu/xử lý/phát, lỗi và cách thử lại | Mục thường dùng đưa ra màn chính; mục kỹ thuật đặt trong Settings |

### Cơ chế phiên hội thoại được người dùng ưu tiên tham khảo

Đây là hướng tương tác người dùng thích; các thao tác cụ thể dưới đây là đề xuất wireframe:

- **Nút + Hội thoại mới** trong bảng **Lịch sử** mở một hội thoại trống. Người dùng có thể bắt đầu cuộc khác ngay khi ứng dụng đang mở, kể cả khi đang xem một cuộc đã lưu.
- **Danh sách phiên và phiên đang chọn:** chuyển giữa các cuộc hội thoại, thấy tên hoặc thời điểm để tìm lại; tìm kiếm là khả năng cần cân nhắc trên màn nhỏ.
- **Nội dung theo lượt:** nhãn người A/B và phương thức, trạng thái xử lý, bản chữ cuối cùng. Phải phân biệt văn bản đang soạn, kết quả nhận dạng và nội dung đã gửi.
- **Vùng nhập ổn định:** chuyển giữa chữ, giọng nói và ký hiệu trong cùng cuộc hội thoại; đặt điều khiển cần thiết gần nội dung đang tạo.
- **Settings dễ tìm, điều hướng gọn:** thử phương án sidebar thu gọn trên màn thiết bị. Không mặc định bê nguyên các chế độ lập trình, giảng dạy hoặc quản lý agent vào sản phẩm.

**Mỗi lần mở ứng dụng, màn chính hiện một hội thoại mới.** Hội thoại chỉ xuất hiện trong **Lịch sử** sau khi người dùng gửi tin nhắn đầu tiên. Các tin nhắn đã gửi được lưu để người dùng mở lại sau khi đóng và mở ứng dụng. Tên phiên, tìm kiếm, đổi tên, xóa, xuất và chính sách giữ nội dung cần quyết định riêng trước triển khai.

Đề xuất giữ nhận dạng một file/batch ở công cụ nhập dữ liệu hoặc kiểm thử, để màn hội thoại tập trung vào cuộc trao đổi. Chưa chốt vị trí cuối cùng; chức năng file/batch của V1 vẫn phải được giữ và kiểm thử.

Các mục Settings cần bàn thêm: nguồn mic/device path trên Pi, camera, Deepgram `language=vi` và key trên backend, cỡ chữ, âm lượng/giọng TTS, hành vi lưu/xóa hội thoại. Chưa chọn engine TTS hay mô hình ký hiệu. Browser laptop không tự dùng micro của nó khi đang điều khiển thiết bị Pi.

## 4. Ghi nhận ảnh tham khảo người dùng gửi

### Codex và LearnHarness — ảnh bổ sung ngày 07/11/2026

![Ảnh Codex do người dùng cung cấp](reports/ui_ux_20261107/assets/codex_conversation_user_reference.png)

**Quan sát từ ảnh Codex:** thanh điều hướng icon bên trái, tiêu đề cuộc trao đổi phía trên, nội dung hội thoại ở vùng trung tâm và vùng nhập ở phía dưới với các điều khiển kèm theo. Ảnh cho thấy bố cục của một cuộc trao đổi; không đủ để xác nhận toàn bộ cơ chế lưu/chuyển phiên.

![Ảnh LearnHarness do người dùng cung cấp](reports/ui_ux_20261107/assets/learnharness_sessions_user_reference.png)

**Quan sát từ ảnh LearnHarness:** sidebar có danh sách SESSIONS, ô tìm kiếm, mục được chọn; vùng nội dung có tiêu đề và vùng nhập/điều khiển phía dưới; Settings ở cuối sidebar. Các chế độ teaching/practice thuộc mục đích của nền tảng tham khảo, chưa phải yêu cầu sản phẩm này.

**Deepseek Harness:** tham chiếu thứ ba do người dùng nêu, đặc biệt ý tưởng plugin-based. Chưa có ảnh, repo/URL hoặc phiên bản được xác định trong tài liệu này; chưa khảo sát cơ chế plugin thực tế. Khi nghiên cứu wireframe sâu hơn cần xác định đúng nền tảng, rồi ghi rõ đặc điểm quan sát được và phần đề xuất áp dụng.

Các ảnh là nguồn tham chiếu bố cục, không chốt bảng màu tối hoặc độ phức tạp tương ứng cho thiết bị. Phần thích từ Codex/LearnHarness được người dùng xác nhận là cơ chế hội thoại/phiên; cách lưu dữ liệu thật vẫn chưa được kiểm chứng ở lượt này.

### Hand Morse — ảnh tham khảo trước đó

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
5. **Thử luồng gửi, phát và mở lại hội thoại.** Bấm **+ Hội thoại mới**, sửa chữ trong vùng soạn và kiểm tra hội thoại xuất hiện trong **Lịch sử** khi bấm **Gửi** tin đầu tiên. Thử nút **Đọc to** như một thao tác riêng. Đóng rồi mở ứng dụng để kiểm tra màn chính hiện hội thoại mới và tin đã gửi vẫn mở lại được từ **Lịch sử**.

Sau khi có lựa chọn sơ bộ, đề xuất tạo 2–3 wireframe (bản phác vị trí các vùng, chưa đầu tư màu) theo cùng một kịch bản hai người. Đánh giá khả năng đọc/chạm/nhập chữ trên kích thước màn dự kiến, rồi mới chốt giao diện chi tiết. Đây là bước đề xuất, chưa triển khai trong lượt ghi nhận này.

## 6. Những điểm dùng để duyệt bản phác sau này

- Nhìn vào biết lượt của ai, nhập bằng phương thức gì, đang thu/xử lý/chờ xác nhận/đã gửi hay lỗi; không chỉ dùng màu để phân biệt.
- Cả hai người có cách trả lời và nhận nội dung phù hợp; có thể đổi phương thức khi cần.
- Chữ và vùng chạm phù hợp màn thật; thao tác chính, Settings và bàn phím ảo dùng được bằng cảm ứng, không phụ thuộc hover hoặc phím tắt.
- Khi lỗi pipeline, nói rõ lượt nào lỗi, cho thử lại và giữ nội dung đã có; không hiện kết quả chưa nhận được như thành công.
- Điều khiển Record/Stop và dừng TTS rõ ràng; thử thu khi phát loa trước khi quyết định xử lý vọng âm.

Đây là tiêu chí thảo luận thiết kế, **chưa phải kiểm thử đã đạt**. Hiện chỉ cập nhật tài liệu và lưu ảnh tham chiếu; không thay mã ứng dụng, mua thiết bị hoặc mở thêm một nhánh triển khai đa phương thức.
