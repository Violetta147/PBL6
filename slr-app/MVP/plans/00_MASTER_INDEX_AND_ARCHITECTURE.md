# Kế Hoạch Tổng Thể (Master Plan): Giải Quyết 3 Vấn Đề Cốt Lõi & Tối Ưu Hóa Độ Chính Xác Demo SLR MVP

## 1. Giải Đáp Học Thuật & Kỹ Thuật Cho 3 Vấn Đề Cốt Lõi

### 1.1. Vấn đề 1: Đã có sẵn 400 file MP3 cho 400 nhãn từ vựng, tại sao vẫn cần mô-đun Sign-to-Gloss (và vai trò của Gloss-to-Text/Speech)?

| Khâu trong Pipeline | Đầu vào → Đầu ra | Vai trò kỹ thuật thực tế trong `slr-app/MVP` | Có bị dư thừa khi đã có 400 file MP3 không? |
| :--- | :--- | :--- | :--- |
| **1. Sign-to-Gloss (ISLR)** (`mediapipe_extractor.py` → `prepare_clip.py` → `SL-GCN`) | Video $X \in \mathbb{R}^{T \times H \times W \times 3}$ → Chỉ số lớp $i \in \{0, \dots, 399\}$ và nhãn từ (Gloss) | Ánh xạ chuỗi khung hình cử chỉ sang định danh từ vựng rời rạc (`index` và `gloss` trong `label_map_v1.json`). | **Tuyệt đối KHÔNG dư thừa (Bắt buộc 100%)**. Nếu không có Sign-to-Gloss, hệ thống chỉ có 400 file `0.mp3..399.mp3` nằm tĩnh trên ổ đĩa nhưng không biết người dùng đang ký từ số mấy để phát. |
| **2. Gloss-to-Audio Lookup** (`demo.py`: `audio_path(index)`) | Chỉ số lớp $i \in \{0, \dots, 399\}$ → File `local_data/tts/{i}.mp3` | Tra cứu bảng băm $O(1)$ từ nhãn Gloss sang âm thanh tiếng Việt đã tổng hợp trước (pre-generated TTS). | **Thay thế cho Dynamic TTS ở chế độ Từ Đơn (Isolated Word)**: Với 1 ký hiệu/lượt, 400 file MP3 giúp bỏ qua bước gọi API TTS thời gian thực, giảm độ trễ phát âm xuống $< 5\text{ ms}$ và chạy offline 100% trên Raspberry Pi 4. |
| **3. Gloss-to-Sentence (SLT) + Dynamic TTS** *(Giai đoạn ghép chuỗi câu)* | Chuỗi Gloss $(g_1, g_2, \dots, g_k)$ → Câu tiếng Việt tự nhiên → Âm thanh | Sắp xếp lại trật tự từ và thêm từ hư/ngữ điệu khi người dùng ký một chuỗi nhiều ký hiệu liên tiếp. | **Bắt buộc khi mở rộng lên Chuỗi Ký Hiệu (Multi-Sign Sequence)**: Ngôn ngữ Ký hiệu Việt Nam (VSL) có cấu trúc cú pháp độc lập với tiếng Việt (SOV / Topic-Comment đối lập với SVO, từ hỏi/phủ định đặt cuối câu, lược bỏ hư từ). Nếu chỉ ghép nối cơ học 400 file MP3 sẽ tạo chuỗi âm thanh đảo trật tự ngữ pháp và đứt gãy ngữ điệu. |

#### Đối Sánh Cú Pháp VSL (Chuỗi Gloss) và Tiếng Việt Chuẩn (Text / TTS)
Dựa trên các công trình nghiên cứu ngôn ngữ học ký hiệu thực nghiệm, sự khác biệt cú pháp giữa VSL và Tiếng Việt thể hiện qua 4 đặc trưng cốt lõi:

| Đặc điểm cú pháp | Chuỗi Gloss trong VSL (Đầu ra Sign-to-Gloss) | Tiếng Việt chuẩn (Đầu ra Gloss-to-Text) | Hệ quả nếu chỉ ghép nối trực tiếp các file MP3 từ đơn |
| :--- | :--- | :--- | :--- |
| **1. Trật tự thành phần nòng cốt** | Phổ biến cấu trúc **Chủ ngữ + Bổ ngữ/Tân ngữ + Vị ngữ (SOV)** hoặc **Đề – Thuyết (Topic–Comment)** đưa đối tượng/điểm nhấn lên đầu câu. | Cấu trúc **Chủ ngữ + Vị ngữ + Tân ngữ (SVO)**. | Phát âm bị đảo ngược vị trí động từ và tân ngữ (ví dụ: phát ra *"Tôi – Sách – Mua"* thay vì *"Tôi mua sách"*). |
| **2. Vị trí trạng ngữ thời gian & từ để hỏi** | Trạng từ thời gian thường đặt đầu câu để định khung bối cảnh; từ nghi vấn (*ai, cái gì, ở đâu, tại sao*) và từ phủ định thường đặt cuối câu (post-positioned). | Trạng từ linh hoạt; từ để hỏi và từ phủ định (*không, chưa*) thường đứng trước động từ hoặc vị ngữ. | Câu phát ra sai quy tắc câu hỏi/phủ định tiếng Việt (ví dụ: *"Bạn – Đi – Đâu"* hoặc *"Tôi – Ăn – Không"*). |
| **3. Vị trí số từ & định ngữ** | Trong nhiều phương ngữ VSL (Hà Nội, TP.HCM), số từ và tính từ thường đứng sau danh từ chính (**Danh từ + Số từ/Tính từ**). | Số từ đứng trước danh từ + loại từ (**Số từ + Loại từ + Danh từ**). | Phát ra *"Nhà – Hai"* thay vì *"Hai ngôi nhà"*. |
| **4. Lược bỏ hư từ & từ chức năng (Function Words)** | Lược bỏ các hư từ, giới từ, hệ từ và trợ từ (*là, của, ở, đang, sẽ, đã, mà, thì*); thông tin ngữ pháp được mã hóa vào biểu cảm mặt (Non-Manual Markers) và không gian ký hiệu. | Bắt buộc có hư từ và quan hệ từ để liên kết ngữ nghĩa và tạo nhịp điệu câu (prosody). | Chuỗi âm thanh rời rạc dạng điện tín (telegraphic speech), thiếu từ nối và đứt gãy ngữ điệu giữa các file .mp3 cắt lẻ. |

#### Nguồn Tài Liệu Học Thuật Đã Kiểm Chứng (Verified References)
1. **Luận án Tiến sĩ Khoa học Máy tính (Viện Hàn lâm KH&CN Việt Nam — Học viện KH&CN / GUST, 2023)**:
   - *Tác giả*: Nguyễn Thị Bích Điệp (HDKH: TS. Vũ Tất Thắng, PGS.TS. Phùng Trung Nghĩa).
   - *Đề tài*: *"Nghiên cứu và phát triển phương pháp tiếp cận dựa trên cấu trúc và thống kê trong dịch tự động ngôn ngữ ký hiệu Việt Nam"*.
   - *Nội dung xác thực*: Xác lập mô hình chuyển đổi cú pháp (Syntax Transformation) hai chiều giữa câu tiếng Việt và chuỗi ký hiệu VSL (bao gồm luật đảo trật tự động từ, từ phủ định, câu nghi vấn và khôi phục từ chức năng).
   - *Nguồn*: [GUST (61267)](https://gust.edu.vn/vn/thong-tin-dong-gop-moi-cua-luan-an/thong-tin-tom-tat-ve-nhung-dong-gop-moi-cua-luan-an-tien-si-nghien-cuu-va-phat-trien-phuong-phap-tiep-can-dua-tren-cau-truc-va-thong-ke-trong-dich-tu-dong-ngon-ngu-ky-hieu-viet-nam/61267) | [Tóm tắt Luận án PDF](https://gust.edu.vn/media/30/uftai-ve-tai-day30072.pdf) | [Semantic Scholar](https://www.semanticscholar.org/paper/Some-issues-on-syntax-transformation-in-Vietnamese-Bich-DiepNguyen/fb79f7d1f8a8b0256e3194a4d156993f4dc7be9d).
2. **Tạp chí Khoa học Giáo dục Việt Nam (VNIES — Tập 18, Số 12, trang 67–73)**:
   - *Bài báo*: *"Phát triển câu ngôn ngữ kí hiệu từ thành phần nòng cốt"*.
   - *Nội dung xác thực*: Phân tích thực nghiệm cấu trúc câu khẳng định đơn giản trong Ngôn ngữ Ký hiệu ở Việt Nam tuân theo trật tự Chủ ngữ + Bổ ngữ + Vị ngữ (SOV), đối lập với trật tự SVO của tiếng Việt.
   - *Nguồn*: [VNIES PDF (khdg_-_tap_18_so_12_bai_12_-_67-73.pdf)](http://vjes.vnies.edu.vn/sites/default/files/khdg_-_tap_18_so_12_bai_12_-_67-73.pdf).
3. **Cơ sở lý thuyết Sign-to-Gloss-to-Text trong Dịch máy Ký hiệu (ACL Anthology / JHU)**:
   - *Công trình*: Zhang et al., *"Improving Sign Language Gloss Translation with Low-Resource Machine Translation"* & Moryossef et al. (2021), *"Data Augmentation for Sign Language Gloss Translation"*.
   - *Nội dung xác thực*: Định nghĩa tường minh 3 đặc trưng của chuỗi Gloss: (1) Lemmatization (từ gốc không biến hình), (2) Function-word omission (lược bỏ giới từ/trợ từ), và (3) Topicalization & Post-positioned question words (đảo trật tự từ nhấn mạnh và đưa từ hỏi về cuối câu).
   - *Nguồn*: [ACL Anthology 2021.mtsummit-at4ssl.1](https://aclanthology.org/2021.mtsummit-at4ssl.1) | [JHU Paper PDF](https://www.cs.jhu.edu/~xzhan138/papers/SLMT_Book_G2T.pdf).

**Kết luận cho buổi bảo vệ/demo ngày mai**:
- Trong phạm vi **MVP Nhận diện Ký hiệu Độc lập (Isolated SLR — 1 từ/lượt)**: Luồng chuẩn là `Video → Sign-to-Gloss (SL-GCN) → Gloss ID (0..399) → Pre-generated MP3 Lookup`. Việc chuẩn bị sẵn 400 file MP3 là một **tối ưu hóa kỹ thuật (Pre-computed Audio Caching)** thay cho bộ tổng hợp TTS thời gian thực, chứ hoàn toàn không thay thế cho mô-đun nhận dạng `Sign-to-Gloss`.

---

### 1.2. Vấn đề 2: Tại sao quay cố định 4 giây không cắt đoạn dư thừa làm giảm chất lượng đầu vào, và lựa chọn phương pháp cắt ranh giới (Boundary Segmentation)

#### A. Bằng chứng toán học trong mã nguồn hiện tại
Trong [slgcn_xy_adapter.py](../deployment/slgcn_feature_trial/vendor/slgcn_xy_adapter.py#L80), hàm `build_from_raw()` chuẩn bị tensor `150` frames theo chính sách đóng băng lúc huấn luyện:
```python
index = np.arange(150) % T if T < 150 else np.arange(150)
```
- **Trên tập huấn luyện VSL400** (kiểm chứng từ [index_qc.csv](../deployment/slgcn_feature_trial/reference/training_qc/index_qc.csv)): Các video mẫu đã được cắt sát điểm bắt đầu và kết thúc ký hiệu, có độ dài $T \in [45, 79]$ frames (trung vị $\approx 63$ frames, tương đương $2.0\text{--}2.5\text{ giây}$). Khi đưa qua `np.arange(150) % T`, ký hiệu tích cực được **lặp tuần hoàn 2 đến 3 lần** lấp đầy 150 frames.
- **Trên webcam thực tế (`demo.py` quay cố định 4.0 giây)**:
  - Người dùng thường mất $0.5\text{--}0.8\text{s}$ đầu để đưa tay lên, thực hiện ký hiệu trong $1.8\text{--}2.2\text{s}$, và hạ tay xuống nghỉ trong $1.0\text{--}1.5\text{s}$ cuối.
  - Khi hạ tay ra khỏi khung hình ở đầu và cuối clip, chính sách `edge_policy = "nan"` ([training_config.json](../deployment/slgcn_smoke/training_config.json#L186)) giữ nguyên các frame trống này là `NaN` rồi gán bằng `0` trong tensor `bone`.
  - Hệ quả: Với $T \approx 118$ frames (ở 30 FPS), có tới $40\%\text{--}60\%$ số frame là frame chết (tay ngoài khung hoặc đứng yên), và phép lặp `np.arange(150) % 118` chỉ lặp lại 32 frame đầu tiên (vốn là lúc chưa kịp giơ tay lên) thay vì lặp lại phần lõi của ký hiệu.

#### B. So sánh các phương pháp cắt ranh giới ký hiệu (Sign Boundary Detection)

| Tiêu chí | Phương pháp 1: Máy trạng thái Động học & Vị trí Cổ tay (Kinematic + Wrist-Height FSM) | Phương pháp 2: Cửa sổ trượt thuần túy (Pure Sliding Window) | Phương pháp 3: Lai 2 tầng (Kinematic Boundary Proposal + Multi-Crop / Server GPU) |
| :--- | :--- | :--- | :--- |
| **Nguyên lý** | Dùng trực tiếp chuỗi đặc trưng từ `mediapipe_extractor`: (1) Mask hiện diện bàn tay $M_t$, (2) Độ cao cổ tay so với vai $y_{\text{wrist}, t}$ trong hệ tọa độ thân người, (3) Vận tốc dịch chuyển cổ tay $v_t = \|\mathbf{w}_t - \mathbf{w}_{t-1}\|_2$ và gia tốc $a_t = |v_t - v_{t-1}|$. Xác định điểm khởi phát ($t_{\text{start}}$) khi tay đi vào vùng ký và điểm kết thúc ($t_{\text{end}}$) khi tay hạ xuống vùng nghỉ hoặc rời khung. | Trượt cửa sổ độ dài $W \in \{60, 75\}$ frames với bước nhảy $S \in \{10, 15\}$ trên toàn bộ video; chạy `prepare_arrays` + `SL-GCN` cho từng cửa sổ và lọc bằng ngưỡng xác suất $\max p(y) > \tau$ kết hợp Non-Maximum Suppression (NMS). | Tầng 1 dùng Kinematic FSM để cắt bỏ khoảng nghỉ và đề xuất các đoạn ứng viên $[t_s, t_e]$. Tầng 2 lấy $K=3$ cửa sổ quanh $[t_s, t_e]$ (chặt, vừa, rộng) đưa vào `SL-GCN` và lấy trung bình xác suất (Test-Time Augmentation). |
| **Chi phí tính toán (đo thực tế từ `report.json`)** | **$< 1\text{ ms}$ trên CPU** (chỉ tính toán mảng NumPy trên đặc trưng đã trích xuất). | Lưu ý quan trọng: MediaPipe (`~6–8s`) chỉ cần chạy **1 lần duy nhất** cho cả video. Phần chạy lặp lại cho $N$ cửa sổ là `adapter` (`0.012s`) + `SL-GCN forward` (`0.35s` trên CPU, `< 0.005s` trên GPU). Với 10 cửa sổ: tốn thêm `~3.6s` trên CPU hoặc `< 0.05s` trên Server GPU. | Tốn thêm `~0.7s` trên CPU (với 3 crops) hoặc `< 0.02s` trên Server GPU. |
| **Ưu điểm** | - Khôi phục phân phối độ dài $T_{\text{active}} \approx 50\text{--}75$ frames giống hệt tập train VSL400.<br>- Tách được chuỗi nhiều ký hiệu độc lập liên tiếp nếu người ký có nhịp hạ tay/nghỉ ngắn giữa các từ.<br>- Chạy tức thì ngay trên laptop/Pi 4. | - Không phụ thuộc giả định người dùng phải hạ tay xuống hoàn toàn giữa hai từ liên tiếp. | - Độ chính xác cao nhất, chống chịu tốt với sai số cắt biên $\pm 5$ frames.<br>- Dễ dàng triển khai trên CPU cục bộ (3 crops) hoặc đẩy lên Server/Colab GPU. |
| **Nhược điểm & Rủi ro** | - Nếu chỉ dùng ngưỡng vận tốc $v_t$, các ký hiệu có nhịp "giữ tĩnh bàn tay" (hold phase) ở giữa từ có thể bị cắt nhầm. **Khắc phục**: Bắt buộc kết hợp điều kiện **Vị trí cổ tay cao hơn ngưỡng nghỉ ($y_{\text{wrist}} < y_{\text{rest}}$)** — chừng nào tay còn giơ trong vùng ký trước ngực/mặt thì không cắt dù $v_t \approx 0$. | - Dễ sinh dự đoán giả (False Positives) ở đoạn chuyển tiếp giữa 2 ký hiệu (movement epenthesis) vì Softmax 400 lớp vẫn có thể gán xác suất cao cho một lớp ngẫu nhiên. | - Cần hiệu chỉnh ngưỡng $y_{\text{rest}}$ và $v_{\text{thresh}}$ trên 5–10 video mẫu trước khi khóa cấu hình. |

**Khuyến nghị kiến trúc**:
1. **Cho buổi Demo ngày mai (1 ký hiệu/lượt trong 4s)**: Áp dụng **Tầng 1 (Auto-Trimming bằng Kinematic + Wrist-Height FSM)** ngay sau bước `extract_video()` để cắt bỏ các frame trống đầu/cuối trước khi đưa vào `prepare_arrays()`. Có công tắc bật/tắt (`--trim-idle`) để so sánh trực tiếp A/B với pipeline gốc.
2. **Cho bài toán Chuỗi các ký hiệu độc lập (Sequential Isolated Signs)**: Áp dụng **Phương pháp 3 (Hybrid)**: dùng Kinematic + Wrist-Height FSM để tách video dài thành $K$ đoạn ký hiệu ứng viên (khi người ký hạ tay/dừng nhịp giữa các từ), sau đó chạy `SL-GCN` (kèm multi-crop nếu chạy trên máy mạnh/Server GPU) trên từng đoạn.

---

### 1.3. Vấn đề 3: Chẩn đoán thực nghiệm từ Log hệ thống — Tại sao suy luận Webcam thực tế kém hơn lý thuyết?

Phân tích trực tiếp **15 bản ghi thực nghiệm webcam** trong `slr-app/MVP/outputs/desktop_demo/*/report.json` đối chiếu với clip chuẩn `014159.mp4` và bảng QC tập huấn luyện (`index_qc.csv`) cho thấy **5 nguyên nhân định lượng trực tiếp**:

| Chỉ số kỹ thuật | Clip chuẩn VSL400 (`014159.mp4`) & Tập Train (`index_qc.csv`) | 13/15 lượt quay Webcam bị lỗi (`outputs/desktop_demo`) | 2/15 lượt quay Webcam thành công (`160926` & `161011`) | Nguyên nhân gốc rễ trong mã nguồn |
| :--- | :--- | :--- | :--- | :--- |
| **`missing_after_pct`** *(Tỷ lệ điểm khớp bị mất/loại bỏ sau repair)* | **`0.0% – 17.7%`** (`014159.mp4`: **`4.39%`**) | **`48.3% – 72.2%`** (Mất từ một nửa đến gần 3/4 dữ liệu xương!) | **`3.1% – 11.5%`** | Trong [slgcn_xy_adapter.py](../deployment/slgcn_feature_trial/vendor/slgcn_xy_adapter.py#L35-L38), toàn bộ 10 khớp của bàn tay bị xóa thành `NaN` nếu `handedness_valid == False`. Mà trong [handedness.py](../deployment/feature_extract/src/extraction/handedness.py#L88-L89), `handedness_valid` chỉ bằng `True` khi cổ tay Pose có `visibility > 0.3` VÀ khoảng cách giữa cổ tay Hand với cổ tay Pose $\le 0.15$. Khi ngồi sát màn hình laptop, khuỷu/cổ tay dễ khuất mép dưới (`visibility <= 0.3`) hoặc kích thước người chiếm khung quá lớn làm khoảng cách chuẩn hóa $> 0.15$, khiến cả bàn tay bị loại bỏ dù MediaPipe Hands vẫn bắt được! |
| **`decoded_frames`** *(Số frame thu được trong 4 giây)* | **`45 – 79` frames** (cắt sát hành động ở 25–30 FPS) | **`57 – 60` frames** trong 11/15 lượt ($\approx 14.8\text{ FPS}$) | **`119` frames** ($\approx 29.8\text{ FPS}$) | Khi ánh sáng phòng yếu, webcam tự động tăng thời gian phơi sáng (Auto-Exposure), làm tốc độ khung hình tụt từ `30 FPS` xuống `15 FPS`. Vì `prepare_clip.py` không nội suy lại thời gian (`No time resampling`), cử chỉ quay ở 15 FPS bị tua nhanh gấp đôi trong không gian tích chập thời gian (`block_size = 41`) của SL-GCN. |
| **`geometry_blocked`** *(Số frame bị chặn bởi `wrist_threshold = 1.0`)* | **`0` frames** (trung vị) | Lên tới **`19` frames** (lượt `082705`) | **`0` frames** | Khi ngồi quá gần góc rộng webcam, biến dạng phối cảnh hoặc gán nhầm cổ tay làm khoảng cách cổ tay vượt quá `1.0 × shoulder_width`, kích hoạt bộ chặn `geometry_block` xóa trắng toàn bộ 27 khớp của frame đó. |
| **Xác suất dự đoán `Top-1 Softmax`** | **`0.997`** (`Dài`) | **`0.249 – 0.476`** (Nhiễu, phân tán) | **`0.681`** (`Trường Cao đẳng`) & **`0.950`** (`Khăn quàng cổ`) | Khi `missing_after_pct` giảm xuống $< 15\%$ và FPS đạt chuẩn `~30 FPS` (`119` frames), mô hình SL-GCN lập tức khôi phục độ tự tin cao (`0.68 – 0.95`). |

#### Cơ chế "Mô hình nhìn thời gian bằng số tấm ảnh" & Ràng buộc `No time resampling`
Mô hình học sâu đồ thị thời gian (Spatial-Temporal Graph Convolutional Network - SL-GCN) **không nhận thức thời gian vật lý bằng đơn vị giây ($t$)**, mà nhận thức thời gian hoàn toàn thông qua **chỉ số khung hình rời rạc ($k \in [0, \dots, T-1]$)**:
1. **Phân phối nhịp điệu trong tập huấn luyện VSL400**:
   - Dữ liệu chuẩn được quay cố định ở tốc độ **`25 – 30 FPS`**.
   - Một cử chỉ hoàn chỉnh kéo dài trung bình $2.0\text{--}2.5\text{ giây}$ tương đương với **`50 đến 60 tấm ảnh liên tiếp`**. Các bộ lọc tích chập thời gian 1D (Temporal Convolution với kích thước kernel $K_t=9$) đã học được phân phối vận tốc và biến thiên góc xương khớp dựa trên bước nhảy $\Delta t \approx 33\text{--}40\text{ ms}$ giữa hai ảnh liên tiếp.
2. **Ràng buộc đóng băng trong mã nguồn ([prepare_clip.py:185](../deployment/slgcn_feature_trial/prepare_clip.py#L185))**:
   - Khóa chính sách ghi rõ:
     ```json
     "temporal_policy": "Frozen training policy: repeat indices modulo T below150; first150 above150 only with explicit opt-in. No time resampling."
     ```
   - Pipeline **hoàn toàn không có thuật toán nội suy thời gian (No time resampling / linear interpolation)** để bù đắp hoặc chèn thêm khung hình khi FPS giảm. Mảng tensor chỉ đơn thuần xếp chồng các frame trích xuất thực tế kế tiếp nhau.
3. **Hiện tượng "Tua nhanh gấp đôi" khi thiếu sáng**:
   - Khi ánh sáng phòng yếu, cảm biến webcam tự động tăng thời gian phơi sáng (Auto-Exposure), kéo tốc độ khung hình tụt từ $30\text{ FPS}$ xuống $\approx 15\text{ FPS}$ ($57\text{--}60$ frames / 4 giây).
   - Một cử chỉ $2.0\text{ giây}$ lúc này chỉ thu được **`30 tấm ảnh`** thay vì $60$ tấm ảnh.
   - Do không có cơ chế bù ảnh, khi đưa 30 tấm ảnh này thẳng vào mô hình, dưới "mắt nhìn" của các bộ lọc thời gian trong SL-GCN, **người ký như đang chuyển động với tốc độ nhanh gấp đôi bình thường**, phá vỡ toàn bộ đặc trưng quỹ đạo và vận tốc đã học $\to$ Softmax bị phân tán và sụt giảm độ tự tin nghiêm trọng.
4. **Hai Hướng Thí Nghiệm Khắc Phục (Chi tiết tại [03_CAMERA_SETUP_AND_CONFUSION_AUDIT_PLAN.md](03_CAMERA_SETUP_AND_CONFUSION_AUDIT_PLAN.md#L20-L50))**:
   - **Hướng 1 (Phần mềm - Tiền xử lý)**: Khôi phục nhịp thời gian bằng nội suy tuyến tính (Linear Interpolation) $T \to 2 \times T$ trên đặc trưng sau trích xuất MediaPipe mà không can thiệp checkpoint.
   - **Hướng 2 (Phần cứng / Camera driver)**: Khóa cố định 30 FPS trong OpenCV thông qua `CAP_PROP_AUTO_EXPOSURE = 0.25`, `CAP_PROP_EXPOSURE = -5`, `CAP_PROP_FPS = 30` kết hợp tăng cường độ rọi sáng trực diện.

---

## 2. Đề Xuất Cấu Trúc Thư Mục Chuẩn (Lớp 1 — Codebase Organization)

Để giữ nguyên tính bất biến của `deployment/` (không làm hỏng kiểm tra SHA-256) và tổ chức mã nguồn sạch sẽ cho AI Agent, cấu trúc mở rộng trong `slr-app/MVP/` được quy hoạch như sau:

```text
slr-app/MVP/
├── deployment/                          # [FROZEN - KHÔNG CHỈNH SỬA] Trọng số, extractor, adapter có khóa SHA-256
├── desktop_mvp/                         # [PRODUCTION MVP] Kiosk server, UI và kiểm thử tích hợp
│   ├── demo.py
│   ├── demo.html
│   ├── check_clip.py
│   ├── record_webcam.py
│   ├── test_demo_server.py
│   └── verify_transitions.js
├── diagnostics/                         # [NEW - CHẨN ĐOÁN & TRỰC QUAN HÓA]
│   ├── inspect_clip_qc.py               # Phân tích chi tiết từng frame: pose/hand mask, handedness_valid, wrist_distance
│   ├── render_diagnostic_video.py       # Vẽ overlay đa khung (Raw Image + Body Norm + L/R Hand Local + Timeline Mask)
│   └── benchmark_demo_words.py          # Chạy kiểm thử hàng loạt clip webcam & xuất bảng Golden Demo Words
├── segmentation/                        # [NEW - CẮT RANH GIỚI KÝ HIỆU]
│   ├── boundary_detector.py             # Cắt frame dư thừa đầu/cuối (Auto-Trimming) bằng Kinematic + Wrist-Height FSM
│   ├── sequence_splitter.py             # Tách video dài chứa chuỗi ký hiệu độc lập thành nhiều đoạn
│   └── test_segmentation.py             # Unit tests & invariant checks cho thuật toán cắt đoạn
└── plans/                               # [NEW - KẾ HOẠCH ĐIỀU PHỐI MULTI-AGENT]
    ├── 00_MASTER_INDEX_AND_ARCHITECTURE.md
    ├── 01_EMPIRICAL_DIAGNOSIS_AND_VISUALIZER_PLAN.md
    ├── 02_TEMPORAL_SEGMENTATION_AND_TRIMMING_PLAN.md
    ├── 03_CAMERA_SETUP_AND_CONFUSION_AUDIT_PLAN.md
    ├── 04_GOLDEN_DEMO_WORDS_AND_CONFUSION_REPORT.md
    ├── 05_POSTURE_FRAMING_AND_HANDS_FREE_INTERACTION.md
    └── 06_EMPIRICAL_PROOF_TRIMMING_AND_DOMAIN_MISMATCH.md
```

---

## 3. Bản Đồ Điều Phối Các File Kế Hoạch Cho Antigravity Agent (`/boost` / `/teamwork`)

| Thứ tự ưu tiên | File kế hoạch | Mục tiêu cụ thể | Chế độ Agent khuyên dùng |
| :--- | :--- | :--- | :--- |
| **Bước 1 (Làm ngay cho Demo ngày mai)** | [01_EMPIRICAL_DIAGNOSIS_AND_VISUALIZER_PLAN.md](01_EMPIRICAL_DIAGNOSIS_AND_VISUALIZER_PLAN.md) | Xây dựng công cụ vẽ overlay đa ô (Raw + Normalized Body/Hands + Mask Timeline) và phân tích toàn bộ các video `webcam_*.avi` đã quay để chỉ ra chính xác frame nào mất điểm khớp. | `DeepCoder` subagent hoặc `/boost` |
| **Bước 2 (Đã hoàn tất kiểm toán Drive)** | [03_CAMERA_SETUP_AND_CONFUSION_AUDIT_PLAN.md](03_CAMERA_SETUP_AND_CONFUSION_AUDIT_PLAN.md) & [04_GOLDEN_DEMO_WORDS_AND_CONFUSION_REPORT.md](04_GOLDEN_DEMO_WORDS_AND_CONFUSION_REPORT.md) | Chuẩn hóa khoảng cách/góc máy/ánh sáng (`missing_after_pct < 15%`, `FPS ≈ 30`), tổng hợp bảng **Platinum / Golden Demo Words** và danh sách **Confusion Pairs / Blacklist** từ 3,714 mẫu Test. | Thực nghiệm cùng người dùng + `research` subagent |
| **Bước 3 (ĐÃ HOÀN TẤT 100% — Tách đoạn & Chuỗi từ)** | [02_TEMPORAL_SEGMENTATION_AND_TRIMMING_PLAN.md](02_TEMPORAL_SEGMENTATION_AND_TRIMMING_PLAN.md) & [EXPERIMENT_REPORT.md](../outputs/segmentation_experiments/EXPERIMENT_REPORT.md) | Triển khai hoàn tất `boundary_detector.py` và `sequence_splitter.py`. Thực nghiệm trên 26 clip chứng minh Method 1 FSM tăng +0.1932 Softmax trên 7 clip có frame thừa, đạt 100% Recall trên chuỗi liên tục 431 frames trong 0.78ms (nhanh gấp 5.4× và sạch 0 FP so với Sliding Window). | Sẵn sàng tích hợp `--trim-idle` vào Kiosk |
| **Bước 4 (Chuẩn hóa Tư thế & Kích hoạt Rảnh tay)** | [05_POSTURE_FRAMING_AND_HANDS_FREE_INTERACTION.md](05_POSTURE_FRAMING_AND_HANDS_FREE_INTERACTION.md) | Giải quyết triệt để Domain Shift Đứng vs. Ngồi, triệt tiêu vòng lặp chạy đi chạy lại bấm nút bằng kịch bản Wizard of Oz / Clicker từ xa, và lộ trình Gesture/Voice Trigger. | Thực thi vận hành Kiosk |
| **Bước 5 (Bằng chứng Thực nghiệm Lệch miền & Active Trimming)** | [06_EMPIRICAL_PROOF_TRIMMING_AND_DOMAIN_MISMATCH.md](06_EMPIRICAL_PROOF_TRIMMING_AND_DOMAIN_MISMATCH.md) | Lưu trữ đầy đủ phân tích 3 tầng hệ thống, thí nghiệm bơm frame nghỉ P1 vs. P2, số liệu sửa sai thành công trên 3 clip webcam thực tế và bộ 4 artifact trực quan hóa (dashboard + 3 biểu đồ). | Dữ liệu nghiệm thu khoa học |
