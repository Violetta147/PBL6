# Kết nối AI cho tài khoản PBL6 — thiết kế màn 23

Ngày: 23/11/2026. Trạng thái: thiết kế đủ để triển khai; ngày 23/11 đã viết source code OAuth và Responses, đang triển khai Pi. Chưa có kết quả đăng nhập/tạo câu với tài khoản thật.

## 1. Yêu cầu hiện tại

Mỗi shop hoặc người sử dụng PBL6 có thể tự kết nối tài khoản GPT của mình, chọn model và dùng LLM để tạo/chỉnh câu. Sau này mở rộng thêm nhà cung cấp và API key. Người phát triển PBL6 không mặc nhiên cấp tài khoản AI của mình cho tất cả shop.

**Thay thế thiết kế trước:** bỏ việc bắt buộc khai báo “đơn vị chịu phí”, tách nguồn quầy/cá nhân và quy tắc “subscription chỉ phục vụ một người trực tiếp tại quầy”. Người dùng không yêu cầu những hạn chế sản phẩm này. Kết nối được ràng buộc với tài khoản PBL6 sở hữu nó, không được tự lấy kết nối từ tài khoản PBL6 khác.

Ví dụ: shop A kết nối GPT của shop A cho app tại quầy shop A; shop B dùng kết nối của shop B. Khách đến giao tiếp tại shop A không vì thế phải đăng nhập GPT riêng. Đây là mô hình quyền sở hữu của PBL6; điều kiện được nhà cung cấp cho phép dùng trong kiểu triển khai cụ thể vẫn phải xác minh, không suy ra chỉ từ việc OAuth đăng nhập thành công.

## 2. Phạm vi và kiểm chứng

- Đầu vào: giải thích mới nhất của người dùng, nguồn OAuth LearnHarness đã kiểm tra, tài liệu Sign in with ChatGPT và wireframe hiện có.
- Đầu ra: màn 23 đơn giản hơn, trường thiết lập rõ ràng và khả năng mở rộng provider.
- File sửa: tài liệu này và file Pencil hiện có. Không sửa thêm runtime, đăng nhập tài khoản, đọc token LearnHarness hoặc gọi model trong lượt thiết kế này.
- Kiểm tra: xem ảnh màn 23, lưu Pencil, chạy `git diff --check -- slr-app/MVP/plans/12_CHATGPT_SUBSCRIPTION_ASSESSMENT.md`.

## 3. Thông tin xử lý trong Thêm/Quản lý, không bày thành form chính

| Trường | Mục đích | ChatGPT subscription hiện minh họa |
|---|---|---|
| Nhà cung cấp | Chọn dịch vụ tạo câu | OpenAI / ChatGPT |
| Cách kết nối | Xác thực qua tài khoản hay API key | Đăng nhập ChatGPT |
| Tài khoản/kết nối | Xác định tài khoản AI mà chủ tài khoản PBL6 đã kết nối | Continue with ChatGPT; sau đăng nhập hiển thị tài khoản đã xác minh |
| Model | Chọn model được kết nối đó thực sự cho phép sử dụng | Tải danh sách sau đăng nhập, không gán một danh sách model cố định |

Không yêu cầu API key đối với nhánh đăng nhập ChatGPT. Nếu thêm nhánh API key sau này, hiển thị API key và endpoint theo dịch vụ; token/key chỉ lưu phía server phù hợp với máy chạy backend thực tế.

## 4. Luồng sử dụng

1. Vào Cài đặt → Ký hiệu → Nhà cung cấp.
2. Nhóm API KEY có “+ Thêm nhà cung cấp”; chỉ mở trường provider/key/endpoint khi người dùng thêm kết nối.
3. Nhóm SUBSCRIPTION hiển thị ChatGPT: chưa có kết nối thì nút Kết nối; đã có thì dropdown tài khoản và Quản lý… như ảnh người dùng cung cấp. Đăng nhập phải xác minh kết nối và lấy model theo quyền thực tế.
4. Các chi tiết thêm/ngắt tài khoản đặt trong Quản lý…, không bày thành một form dài ở màn danh sách. Màn 26–29 minh họa phần này. Dropdown tài khoản không phải dropdown model; chọn model và kiểm tra tạo câu thuộc phần thiết lập tạo câu riêng, chưa vẽ chi tiết ở bước này.
5. Khi sử dụng app, chuỗi gloss đã được chỉnh đi qua kết nối/model đã lưu của tài khoản PBL6 đó; câu trả về vẫn cần người sử dụng kiểm tra và Gửi câu theo luồng đã chốt.

Chưa kết nối thì chưa cho dùng model từ nguồn đó. Đổi tài khoản phải tải lại model; kết nối lỗi hoặc hết hạn mức thì giữ bản nháp, không tự sử dụng kết nối của tài khoản PBL6 khác.

## 5. Màn 23 mới

- Người dùng đưa ảnh danh sách provider và yêu cầu làm đơn giản như ảnh. Đã rút màn 23 thành danh sách Nhà cung cấp trong Cài đặt → Ký hiệu, giữ ba nhóm STT/SLR/Lịch sử. Vị trí điều hướng theo quy tắc đã duyệt ở mục 8.
- Nhóm API KEY: chỉ có “+ Thêm nhà cung cấp” khi chưa có API key.
- Nhóm SUBSCRIPTION: ChatGPT, dropdown “Tài khoản đã kết nối” và Quản lý…; đây là dữ liệu minh họa trạng thái sau kết nối, không phải thông báo app đã đăng nhập thật. Không sao chép email cá nhân trong ảnh vào bản vẽ.
- Không còn form nhà cung cấp/cách xác thực/model hay nút kiểm tra/lưu ở màn danh sách. Không tự thêm GitHub Copilot hoặc Grok vào danh sách hỗ trợ chỉ vì chúng có trong ảnh tham chiếu.
- Giữ màu sáng/font của PBL6, dùng ảnh làm tham chiếu cho cấu trúc tối giản. Khi triển khai, panel cần co theo chiều rộng và dòng tài khoản cần xuống hàng trên màn dọc; không áp cố định chiều rộng bản vẽ lên DOM.
- Kích thước 1024×600, màu/font theo bộ wireframe. Các màn 01–22 và 24 giữ nguyên trong lượt sửa màn 23 này.
- Màn mới là đề xuất trực quan, chưa phải chức năng đăng nhập đã chạy trong app.

## 6. Thiết kế mở rộng provider ở bước triển khai sau

Một kết nối tối thiểu gồm: ID kết nối, tài khoản PBL6 sở hữu, provider, cách xác thực, nhãn tài khoản đã xác minh, model đã chọn, tham chiếu bí mật phía server và trạng thái. Không cần tạo thêm một backend riêng chỉ vì có thêm provider.

Phần tạo câu gọi một giao diện chung cho việc lấy model và tạo câu. OAuth/refresh token của ChatGPT, API key của OpenAI hoặc API key của Gemini được xử lý trong adapter tương ứng. Không ép các cách xác thực khác nhau thành cùng một trường API key.

Các tác vụ phải gắn với kết nối và revision đầu vào cụ thể. Đổi tài khoản, model hoặc gloss phải vô hiệu hóa kết quả không còn phù hợp; không tự chuyển sang nguồn khác hoặc gửi câu chưa được duyệt.

## 7. Căn cứ kỹ thuật và giới hạn đã xác minh

- Bản LearnHarness đang cài có OAuth riêng và quyền `chatgpt.tokens.use.direct`; file kết nối đã được đối chiếu SHA-256 với mã có trên máy. Chưa dùng token của LearnHarness để cấp cho PBL6.
- OpenAI công bố luồng ChatGPT plan usage cho app mã nguồn mở/chạy cục bộ; kiểu paid/remote-hosted có quy trình khác. Không đánh đồng khả năng tích hợp kỹ thuật với quyền sử dụng cho mọi mô hình sản phẩm. [Phạm vi](https://developers.openai.com/siwc/token-sharing-open-source).
- Đăng ký đầu dùng host ID bền, state/nonce/PKCE, callback loopback và kiểm tra ID token/quyền được cấp. Luồng này không cần API key hoặc client secret để bắt đầu. [Đăng nhập](https://developers.openai.com/siwc/token-sharing-open-source/sign-in).
- Subscription gọi Responses API với `store:false`, `stream:true`; cần nhận `response.completed` trước khi coi thành công, model lấy từ danh mục của tài khoản. Adapter Chat Completions/API-key trong bản thử PBL6 chưa hỗ trợ OAuth bằng việc chỉ đổi key. [Model và suy luận](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).
- Vị trí đăng nhập/callback phải đúng máy chạy luồng OAuth; callback loopback từ điện thoại không tự quay về server ở laptop/Pi. Luồng trên Pi đã được duyệt ở mục 9; chưa thiết kế đăng nhập subscription trực tiếp từ Companion web điện thoại. [Host từ xa](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms).
- LearnHarness dùng AGPL-3.0 ở bản mã đã kiểm tra. Dùng tài liệu giao thức để triển khai độc lập; không sao chép module LearnHarness vào PBL6 ở bước này.

Chưa có thử tạo câu bằng subscription thật trên app. Code thử trước đó vẫn nằm trên nhánh `codex/gloss-sentence-flow`, chưa commit hoặc deploy; lượt hiện tại chỉ chỉnh thiết kế.

## 8. Quy tắc điều hướng Cài đặt đã được duyệt

Người dùng chỉ ra màn 09 dùng menu bên trái, trong khi màn 23 lại có tab phía trên dù cả hai đều 1024×600. Đã xác định nguyên nhân: màn 23 theo code vừa pull, còn màn 09 theo wireframe cũ; đây là bất nhất, không phải do hai màn có kích thước khác nhau.

Người dùng đã duyệt quy tắc chung cho Cài đặt:

- Ngang 1024×600: menu nhóm bên trái, nội dung bên phải; lấy vị trí điều hướng của màn 09 làm chuẩn.
- Dọc 600×1024: tab nhóm phía trên, nội dung bên dưới để giữ chiều rộng.
- Nội dung provider/API key/subscription không tự quyết định vị trí menu chung.

Đã đưa màn 23 về menu trái và thêm màn 25 bản dọc với tab phía trên. Trong bản dọc, tên ChatGPT ở hàng riêng; dropdown tài khoản và Quản lý… ở hàng kế tiếp để không tràn ngang. Danh sách provider vẫn tối giản theo ảnh tham chiếu. Đã kiểm tra ảnh và lưu Pencil; chưa đổi code điều hướng Cài đặt trong app. Các màn trước ngoài màn 23 được giữ nguyên.

## 9. Luồng Pi–laptop–GPT đã được duyệt

Người dùng trả lời Accept cho sơ đồ sau. Đây là quyết định triển khai mong muốn, không phải bằng chứng các dịch vụ hoặc OAuth đang chạy.

- Pi chạy giao diện và backend PBL6 giữ kết nối ChatGPT. Model GPT chạy trên cloud OpenAI, không chạy trên Pi.
- Laptop tiếp tục xử lý Vision theo kiến trúc đã dùng; kết nối GPT không tạo thêm yêu cầu phải chuyển backend sang laptop.
- Đăng nhập lần đầu: bấm Kết nối/Thêm tài khoản trên trình duyệt Pi → OpenAI đăng nhập và cấp quyền → callback về backend Pi để xác minh, lưu kết nối → app hiển thị tài khoản đã kết nối.
- Khi dùng: camera Pi → Vision laptop → nhận dạng gloss trên Pi → người dùng chỉnh gloss/kết thúc câu → backend Pi gửi gloss tới GPT → câu gợi ý hiện trên Pi → người dùng kiểm tra/sửa/gửi → lưu hội thoại trên Pi.
- Chỉ gửi chuỗi gloss cần xử lý trong luồng tạo câu. Quản lý… thao tác với các kết nối được backend Pi quản lý cho tài khoản PBL6 tương ứng.
- Trình duyệt đăng nhập ở Pi để callback loopback quay về đúng Pi. Luồng Companion đăng nhập từ điện thoại không tự được coi là đã giải quyết.

## 10. Các hộp thoại ChatGPT theo ảnh tham chiếu

Người dùng gửi bốn ảnh LearnHarness để tham chiếu. Đã bổ sung trong Pencil, chưa phải triển khai runtime hoặc các chi tiết mới đã được duyệt riêng:

- Màn 26: Quản lý ChatGPT, chọn tài khoản đã lưu, Thêm tài khoản, các liên kết quyền riêng tư/hạn mức, Ngắt kết nối và Đóng.
- Màn 27: Kết nối ChatGPT, lựa chọn thêm tài khoản/workspace, thông tin gloss sẽ gửi tới OpenAI và hạn mức tài khoản được sử dụng; Hủy hoặc Continue with ChatGPT.
- Màn 28: xác nhận ngắt tài khoản đang chọn; nêu xóa kết nối đã lưu trên Pi, không hủy gói ChatGPT. Hủy hoặc Ngắt kết nối. Không xóa tài khoản PBL6 hoặc các câu đã gửi.
- Màn 29: dropdown mở với hai tài khoản minh họa và lựa chọn thêm tài khoản/workspace. Không sao chép email trong ảnh, không đọc credential thật.
- Dùng màu sáng PBL6 và màn 23 làm nền; giữ nguyên các màn 01–25. Đã kiểm tra ảnh các hộp thoại và lưu Pencil.
- Công tắc cho phép chạy nền trong ảnh LearnHarness chưa được sao chép vào các hộp thoại này: PBL6 hiện thiết kế tạo câu theo lượt ký đang dùng; tác vụ nền độc lập cần nhu cầu/đồng ý riêng. Không suy ra việc người dùng gửi ảnh là đã cho phép dùng hạn mức nền.
- Đổi/ngắt tài khoản phải hủy yêu cầu tạo câu còn gắn với kết nối đó, tải lại model theo tài khoản mới và không tự chuyển sang tài khoản khác để tiếp tục dùng hạn mức.


## 11. Source code đã triển khai theo yêu cầu ngày 23/11

Các ghi chú “chưa triển khai” ở mục 1–10 mô tả thời điểm duyệt thiết kế. Hiện đã thêm stt-app/src/server/chatgptConnection.ts, app/api/chatgpt/route.ts và cập nhật SentenceServiceSettings.tsx theo thiết kế tối giản. Luồng tạo câu chọn adapter ChatGPT subscription khi người dùng kích hoạt kết nối đó; nhánh OpenAI-compatible/Gemini API vẫn độc lập.

Nguồn triển khai chính: tài liệu OpenAI Registration and sign-in, Models and inference, Accounts and sessions, Preview limitations và OIDC discovery của auth.openai.com, đọc lại ngày 23/11/2026. Không sao chép source AGPL của LearnHarness. Kết quả kiểm chứng/triển khai và giới hạn hiện tại ghi tại kế hoạch 11. Chưa tuyên bố hỗ trợ tài khoản PBL6/đa shop hoàn chỉnh hoặc kết quả dịch đúng ý người ký chỉ từ test mô phỏng.
