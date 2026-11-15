# Kiến Trúc "Everything is a Plugin" & Nền Tảng Meta-Framework Cordis

Tài liệu này hệ thống hóa triết lý thiết kế mô-đun hóa triệt để (**"Everything is a Plugin"**), giải mã nền tảng **Cordis** đứng sau thành công của nhiều hệ thống lớn (như Koishi hay DeepSeek Harness), đồng thời đưa ra bản thiết kế mẫu (Blueprint) cho ứng dụng thực tế và các nguyên tắc cốt lõi khi xây dựng hệ thống dựa trên plugin.

## 1. Triết lý Kiến trúc "Everything is a Plugin"

Trong kiến trúc phần mềm truyền thống, các tính năng chính thường được gắn chặt (hardcode) vào lõi hệ thống (Core). Ngược lại, tư duy **"Everything is a Plugin"** thiết kế toàn bộ hệ thống theo dạng mô-đun hóa triệt để:

* **Lõi rỗng (Empty Core):** Phần mềm cốt lõi hoàn toàn trống rỗng về mặt tính năng nghiệp vụ. Nó chỉ đóng vai trò là một bệ phóng (Runtime / Event Bus / Plugin Registry) cung cấp đường ống để các thành phần cắm vào và giao tiếp với nhau.

* **Mọi thành phần đều có thể thay thế:** Không có tính năng nào là cố định. Mọi chức năng từ giao diện, cơ sở dữ liệu, phần cứng đến xử lý logic đều đóng vai trò là các plugin độc lập.

* **Cơ chế hoạt động:** Các plugin tương tác và đóng góp `service` (dịch vụ), `event` (sự kiện), và `capability` (năng lực) vào một hệ thống quản lý ngữ cảnh dùng chung.

### Đánh giá Ưu điểm & Thách thức

| Đối tượng | Lợi ích / Ưu điểm | Thách thức / Rủi ro | 
| ----- | ----- | ----- | 
| **Nhà phát triển (Developers)** | **Mở rộng không giới hạn:** Không cần sửa mã nguồn gốc (Core) vẫn có thể thêm/bớt/hoán đổi tính năng, tạo giao diện nổi hoặc chia sẻ plugin cho cộng đồng. | Đòi hỏi tư duy thiết kế trừu tượng cao, phải định nghĩa rõ ràng các giao diện giao tiếp (Interfaces/Contracts) ngay từ đầu. | 
| **Người dùng cuối (End-Users)** | **Linh hoạt tùy biến:** Tự do lắp ghép ứng dụng theo đúng nhu cầu cá nhân, tránh làm nặng máy bởi các tính năng thừa. | **Nghịch lý Plugin (Plugin Paradox):** Kiến trúc mở mang lại sự linh hoạt tuyệt đối nhưng lại đẩy sự phức tạp trong việc cấu hình, cài đặt và quản lý phụ thuộc về phía người dùng phổ thông. | 

## 2. Cordis: Meta-Framework Hiện Thực Hóa Tư Duy Mô-đun

### 2.1. Cordis là gì?

**Cordis** là một *open-source general-purpose meta-framework* (khung kiến trúc nền tảng đa dụng mã nguồn mở, chuyên dùng để xây dựng các framework hoặc hệ thống dạng mô-đun khác) được viết bằng **TypeScript/Node.js**.

* **Nguồn gốc:** Được phát triển từ năm 2019 bởi nhà lập trình *Shigma* để làm nhân (core) cho chatbot framework nổi tiếng **Koishi**.

* **Độ phủ sóng:** Dù không được thiết kế riêng cho AI, Cordis đã bùng nổ danh tiếng trong giới công nghệ gần đây khi được **DeepSeek** lựa chọn làm xương sống kiến trúc cho hệ thống **DeepSeek Harness**.

### 2.2. Triết lý cốt lõi: "Tính hợp thành Không - Thời gian" (Spatiotemporal Composability)

Trong các framework truyền thống (như VS Code hay Express), khi bạn tắt một extension/plugin lúc đang chạy, mã nguồn của nó thường không được dọn dẹp triệt để: các event listener ẩn vẫn chạy, bộ định thời (timer) tiếp tục đếm, gây rò rỉ bộ nhớ (memory leak) trừ khi khởi động lại ứng dụng.

Cordis giải quyết triệt để bài toán này qua hai trục:

#### 1. Chiều Thời gian (Temporal Composability) – *Reversible Effects (Hiệu ứng đảo ngược)*

* **Cơ chế:** Mọi tác vụ hoặc đăng ký tính năng trong Cordis đều là một hiệu ứng có thể đảo ngược.

* **Cách hoạt động:** Khi một plugin được kích hoạt, nó mở ra các tiến trình con (**Fiber**). Khi plugin đó bị gỡ bỏ (unload), Cordis tự động "tua ngược" lại quá trình, xóa sạch mọi listener, timer, và trạng thái mà plugin đó đã tạo ra.

* **Giá trị:** Cho phép bật, tắt, hoặc nâng cấp nóng (**Hot-Swap**) plugin ngay khi ứng dụng đang chạy mà không cần khởi động lại.

#### 2. Chiều Không gian (Spatial Composability) – *Reactive Coeffects (Đồng hiệu ứng phản ứng)*

* **Cơ chế:** Quản lý sự phụ thuộc lẫn nhau giữa các thành phần thông qua **Tiêm phụ thuộc mạng lưới (Reactive Dependency Injection)**.

* **Cách hoạt động:** Khi `Plugin A` cần dịch vụ từ `Plugin B`, Cordis sẽ tự động theo dõi mối liên kết này. Nếu `Plugin B` bị tắt hoặc được thay thế nóng bằng `Plugin C`, `Plugin A` sẽ ngay lập tức thích ứng (tạm dừng hoạt động hoặc chuyển sang dùng `Plugin C` theo thời gian thực) mà toàn bộ hệ thống không bị sập (crash).

### 2.3. 5 Khái niệm kỹ thuật nền tảng trong Cordis

Khi đọc mã nguồn của bất kỳ ứng dụng nào chạy trên Cordis, bạn sẽ luôn bắt gặp 5 thành phần cốt lõi này:

1. **Context (Ngữ cảnh):** Thùng chứa phụ thuộc (Dependency Container). Toàn bộ ứng dụng thực chất là một cây gồm các Context lồng nhau và cô lập với nhau.

2. **Plugin:** Đơn vị chức năng độc lập có thể tải (load), cấu hình và gỡ bỏ (unload) linh hoạt.

3. **Inject:** Cơ chế khai báo các dịch vụ (`services`) bắt buộc phải có mặt trong Context thì plugin hiện tại mới được phép kích hoạt.

4. **Typed Events:** Hệ thống giao tiếp bằng sự kiện giữa các plugin, được định nghĩa và kiểm tra kiểu dữ liệu nghiêm ngặt (strictly typed) thông qua TypeScript.

5. **Disposer (Bộ hủy):** Mỗi khi một hàm đăng ký một tài nguyên nào đó (sự kiện, timer, route...), nó bắt buộc phải trả về một hàm dọn dẹp (cleanup function) để phục vụ quá trình gỡ plugin an toàn.

## 3. Ứng Dụng Thực Tế & Khi Nào Nên Chọn Cordis?

Cordis không bị giới hạn ở Backend hay AI, mà có thể chạy trên cả môi trường Server (Node.js) lẫn Trình duyệt (Browser):

* **Hệ thống Plugin cho Ứng dụng Client (tương tự VS Code, Figma, App Browser):**

  * *Ví dụ:* Giao diện quản lý (Web Console) của Koishi là một ứng dụng Cordis chạy trực tiếp trên trình duyệt để quản lý các plugin UI.

  * *Lý do dùng:* Khi người dùng tắt một plugin giao diện (như widget xem lịch), Cordis đảm bảo component đó biến mất hoàn toàn, mọi event listener được dọn sạch, chống đơ trình duyệt do tràn bộ nhớ.

* **Backend Server có tính năng Hot-Swap (Thay đổi tính năng lúc đang chạy):**

  * *Lý do dùng:* Các backend framework như Express, NestJS hay Fastify đòi hỏi phải khởi động lại (restart) máy chủ mỗi khi cập nhật code. Cordis cho phép xây dựng hệ thống Microservices hoặc Modular Monolith có khả năng cập nhật tính năng liên tục.

### Khi nào bạn nên chọn Cordis thay vì NestJS hay Express?

Hãy chọn Cordis nếu dự án của bạn có một trong 3 đặc điểm sau:

1. **Hệ sinh thái mở:** Bạn đang xây dựng một nền tảng cho phép người dùng hoặc lập trình viên bên thứ ba tự viết plugin cắm vào ứng dụng.

2. **Yêu cầu Zero-Downtime tuyệt đối:** Hệ thống bắt buộc phải chạy liên tục $24/7$, không được phép dừng hoạt động kể cả khi cập nhật tính năng mới hay vá lỗi.

3. **Phụ thuộc động phức tạp:** Các tính năng có mối quan hệ phụ thuộc chéo thay đổi liên tục (Tính năng A chỉ kích hoạt khi Tính năng B sẵn sàng, và tự động "ngủ đông" an toàn nếu Tính năng B bị gỡ bỏ).

## 4. Case Study: Thiết Kế Ứng Dụng Giao Tiếp Đa Phương Thức Với Cordis

Để hình dung rõ cách áp dụng triệt để tư duy **"Everything is a Plugin"**, chúng ta hãy thiết kế kiến trúc cho một **Ứng dụng giao tiếp đa phương thức** (hỗ trợ người khiếm thính và người bình thường giao tiếp qua Camera, Micro, Ngôn ngữ ký hiệu, Giọng nói và Văn bản).

### 4.1. Kiến trúc tổng thể

Phần mềm cốt lõi (**App Core**) hoàn toàn trống rỗng. Nó không hề biết "Sign-to-Text" (Ngôn ngữ ký hiệu sang văn bản) hay "Camera" là gì. Nó chỉ khởi tạo một `Context` gốc của Cordis đóng vai trò là **Plugin Registry & Event Bus**.

Toàn bộ tính năng được chia thành **5 nhóm Plugin** chạy trên hệ thống quản lý Context dùng chung này:

```
+-----------------------------------------------------------------------+
|                       APP CORE (Cordis Runtime)                       |
|            [ Context Tree | Service Registry | Event Bus ]            |
+-----------------------------------------------------------------------+
       ^                 ^                  ^                 ^
       |                 |                  |                 |
+--------------+  +--------------+  +---------------+  +----------------+
| Nhóm 1: I/O  |  | Nhóm 2: AI   |  | Nhóm 3: Logic |  | Nhóm 4: UI     |
| Phần cứng    |  | Chuyển đổi   |  | & Luồng hội   |  | Hiển thị       |
|              |  | Đa phương    |  | thoại         |  |                |
| - Camera     |  | thức         |  |               |  | - Chat Box     |
| - Microphone |  | - Sign2Text  |  | - Session Mgr |  | - Floating Cam |
| - Speaker    |  | - STT / TTS  |  | - Translator  |  | - Avatar 3D    |
+--------------+  +--------------+  +---------------+  +----------------+

```

### 4.2. Chi tiết các nhóm Plugin (Điền khuyết kiến trúc)

#### Nhóm 1: Plugin Phần cứng & Đầu vào/Đầu ra (Hardware I/O Plugins)

Nhóm này chịu trách nhiệm giao tiếp với thiết bị vật lý và cung cấp luồng dữ liệu thô (raw stream) dưới dạng các `Service`.

* `plugin-camera`: Quản lý quyền truy cập webcam, phát ra sự kiện `video-frame` liên tục. Khi tắt plugin, đèn báo camera trên máy tính lập tức tắt nhờ cơ chế *Disposer* giải phóng MediaStream.

* `plugin-microphone`: Thu âm thanh, khử nhiễu cơ bản và phát ra luồng `audio-chunk`.

* `plugin-speaker`: Nhận dữ liệu âm thanh đầu ra để phát ra loa.

#### Nhóm 2: Plugin Xử lý & Chuyển đổi Đa phương thức (Modality Engine Plugins)

Nhóm này đóng vai trò là các "bộ dịch" AI, sử dụng `@inject` để lắng nghe dữ liệu từ Nhóm 1 và biến đổi chúng thành định dạng khác.

* `plugin-sign-to-text`:

  * *Inject:* Yêu cầu `plugin-camera` phải đang chạy.

  * *Hoạt động:* Nhận `video-frame`, dùng mô hình thị giác máy tính nhận diện cử chỉ tay và phát ra sự kiện `message:text-received`.

  * *Linh hoạt:* Có thể hot-swap giữa mô hình chạy nội bộ (MediaPipe nhẹ máy) hoặc mô hình đám mây (Cloud AI chính xác cao) mà không làm gián đoạn cuộc gọi.

* `plugin-stt` (Speech-to-Text): Inject `plugin-microphone`, chuyển giọng nói thành sự kiện `message:text-received`.

* `plugin-tts` (Text-to-Speech): Lắng nghe văn bản cần đọc, tổng hợp giọng nói và đẩy sang `plugin-speaker`.

* `plugin-text-to-sign`: Chuyển văn bản thành chuỗi tọa độ chuyển động (motion data) cho nhân vật 3D biểu diễn ngôn ngữ ký hiệu.

#### Nhóm 3: Plugin Điều phối & Nghiệp vụ (Core Logic & Orchestration Plugins)

* `plugin-conversation-bus`: Quản lý lịch sử cuộc trò chuyện, đồng bộ hóa thời gian (timestamp) giữa các luồng văn bản, giọng nói và ký hiệu.

* `plugin-auto-translate`: Tự động dịch ngôn ngữ (ví dụ: Tiếng Việt sang Tiếng Anh) ngay trên đường ống sự kiện trước khi văn bản được hiển thị hoặc đọc lên.

#### Nhóm 4: Plugin Giao diện Người dùng (UI & Presentation Plugins)

* `plugin-ui-floating-caption`: Tạo một cửa sổ phụ đề nổi (overlay) trên màn hình. Nếu người dùng tắt plugin này, toàn bộ DOM và sự kiện kéo thả cửa sổ bị xóa sạch khỏi bộ nhớ.

* `plugin-ui-sign-avatar`: Hiển thị nhân vật hoạt hình 3D thực hiện ngôn ngữ ký hiệu (phụ thuộc vào `plugin-text-to-sign`).

#### Nhóm 5: Plugin Hạ tầng & Giải quyết "Nghịch lý Plugin" (Infrastructure & UX Plugins)

Để người dùng cuối không bị choáng ngợp bởi hàng chục plugin rời rạc:

* `plugin-preset-manager`: Gom nhóm các plugin thành các "Chế độ" (Presets) chỉ với 1 cú nhấp chuột (ví dụ: *Chế độ Khiếm thính*, *Chế độ Thuyết trình*, *Chế độ Tiết kiệm pin*).

## 5. Quy Tắc Vàng Khi Thiết Kế Hệ Thống Plugin-Based (Golden Rules)

Để xây dựng một kiến trúc mô-đun hóa bền vững với Cordis và tránh biến hệ thống thành một "mớ hỗn độn phân tán", nhà phát triển cần tuân thủ 6 quy tắc vàng sau:

### Quy tắc 1: Lõi tối giản tuyệt đối (Zero-Business-Logic Core)

* **Nguyên tắc:** Không bao giờ viết logic nghiệp vụ vào App Core. Nếu bạn đang định thêm một hàm xử lý cụ thể vào Core, hãy dừng lại và tách nó thành một plugin.

* **Mục tiêu:** Core chỉ nên chứa dưới vài trăm dòng code để khởi tạo Context, cấu hình hệ thống tải plugin (Plugin Loader) và xử lý lỗi cấp hệ thống.

### Quy tắc 2: Giao tiếp qua Hợp đồng, không giao tiếp trực tiếp (Contract-First Communication)

* **Nguyên tắc:** `Plugin A` không bao giờ được import trực tiếp mã nguồn hoặc gọi thẳng hàm nội bộ của `Plugin B`. Mọi tương tác phải thông qua **Service Interface** (qua cơ chế `inject`) hoặc **Typed Events** đã được định nghĩa trên Context chung.

* **Mục tiêu:** Đảm bảo tính khả thay thế (Substitutability). Bạn có thể xóa `Plugin B` và thay bằng `Plugin C` (cùng tuân thủ một Interface) mà `Plugin A` không hề hay biết.

### Quy tắc 3: Mọi hành động đều phải có lối thoát (Strict Disposability)

* **Nguyên tắc:** Tuân thủ nghiêm ngặt chiều Thời gian (Temporal Composability). Mọi sự kiện được lắng nghe (`ctx.on`), mọi bộ đếm thời gian (`ctx.setInterval`), mọi kết nối mạng hoặc phần cứng (Camera, WebSocket, Database) được mở ra trong một plugin **bắt buộc** phải được gắn với một `Disposer` (hoặc sử dụng API có sẵn của Cordis Context) để tự động dọn dẹp khi plugin dừng hoạt động.

* **Mục tiêu:** Đảm bảo 0% rò rỉ bộ nhớ (Zero Memory Leak) khi thực hiện Hot-Swap hàng nghìn lần.

### Quy tắc 4: Thiết kế chịu lỗi và Suy giảm duyên dáng (Graceful Degradation)

* **Nguyên tắc:** Một plugin bị lỗi (crash) hoặc bị gỡ bỏ đột ngột không bao giờ được phép kéo sập toàn bộ ứng dụng. Các plugin phụ thuộc phải phân biệt rõ giữa **Phụ thuộc cứng (Hard Dependency)** và **Phụ thuộc mềm (Optional Dependency)**.

* **Ví dụ:** Trong ứng dụng giao tiếp, nếu `plugin-camera` bị rút cáp đột ngột, `plugin-sign-to-text` sẽ tự động tạm dừng (ngủ đông), nhưng `plugin-microphone` và khung chat văn bản vẫn phải hoạt động bình thường.

### Quy tắc 5: Trạng thái cô lập hoặc Phi trạng thái (Stateless or Scoped State)

* **Nguyên tắc:** Hạn chế tối đa việc lưu trữ trạng thái toàn cục (Global State) bên trong biến cục bộ của một plugin. Nếu một plugin cần lưu trữ dữ liệu quan trọng (như lịch sử chat), hãy đẩy dữ liệu đó sang một `plugin-storage` chuyên biệt.

* **Mục tiêu:** Khi bạn nâng cấp nóng (Hot-Reload) một plugin xử lý logic, trạng thái của người dùng không bị mất đi.

### Quy tắc 6: Che giấu sự phức tạp trước người dùng cuối (Taming the Plugin Paradox)

* **Nguyên tắc:** Kiến trúc bên dưới có thể chia thành 100 micro-plugins để phục vụ lập trình viên, nhưng giao diện phía người dùng cuối phải được đóng gói thành các **Gói tính năng (Feature Bundles / Presets)** trực quan.

* **Mục tiêu:** Giải quyết triệt để "Nghịch lý Plugin" — giữ trọn vẹn sự linh hoạt ở tầng kỹ thuật nhưng mang lại trải nghiệm "chỉ việc dùng ngay" (Out-of-the-box) cho người dùng phổ thông.