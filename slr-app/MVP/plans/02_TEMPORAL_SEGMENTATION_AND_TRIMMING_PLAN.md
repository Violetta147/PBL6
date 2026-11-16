# Kế Hoạch Mô-đun 02: Cắt Ranh Giới Ký Hiệu (Sign Boundary Detection) Cho Từ Đơn & Chuỗi Ký Hiệu Độc Lập

## 1. Mục Tiêu Kỹ Thuật
1. **Chế độ 1 — Auto-Trimming cho 1 ký hiệu/lượt (`boundary_detector.py`)**: Tự động phát hiện điểm bắt đầu ($t_{\text{start}}$) và điểm kết thúc ($t_{\text{end}}$) của hành động ký hiệu bên trong cửa sổ quay 4 giây, loại bỏ các frame chờ ở đầu/cuối trước khi đưa vào `prepare_arrays()`.
2. **Chế độ 2 — Multi-Sign Sequence Segmentation (`sequence_splitter.py`)**: Nhận một video dài trong đó người ký thực hiện tuần tự nhiều ký hiệu độc lập (có nhịp hạ tay hoặc dừng nghỉ giữa các từ), tự động tách thành danh sách các đoạn $[t_s^{(k)}, t_e^{(k)}]$ và suy luận ra chuỗi Gloss $(g_1, g_2, \dots, g_K)$.
3. **Chế độ 3 — Tùy chọn Multi-Crop / Sliding Window trên Server/Cloud GPU**: Cung cấp hàm lấy mẫu đa cửa sổ quanh biên $[t_s, t_e]$ để tăng độ bền vững (Test-Time Augmentation) khi chạy trên máy trạm hoặc Colab/Server GPU.

---

## 2. Công Thức Toán Học & Máy Trạng Thái Hữu Hạn (Kinematic + Wrist-Height FSM)

Đặt $T$ là tổng số khung hình của video đã trích xuất qua `extract_video()`. Tại mỗi khung hình $t \in \{0, \dots, T-1\}$:

### 2.1. Các tín hiệu đặc trưng (Trích xuất trực tiếp từ `result.arrays`)
1. **Tín hiệu hiện diện bàn tay hợp lệ ($H_t \in \{0, 1\}$)**:
   $$H_t = \mathbb{I}\big(\text{detection\_masks}[t, 2] \lor \text{detection\_masks}[t, 3]\big)$$
2. **Độ cao cổ tay chuẩn hóa theo vai ($Y_t \in \mathbb{R}$)**:
   Trong hệ tọa độ `upper_body` (gốc tại trung điểm hai vai, trục $y$ hướng xuống dưới theo tọa độ ảnh chuẩn hóa cho độ rộng vai `shoulder_width`):
   - Khi hai tay buông thõng ở tư thế nghỉ: tọa độ $y$ của cổ tay lớn ($y > y_{\text{rest}}$, thường $y_{\text{rest}} \approx 1.15\text{--}1.30$ lần độ rộng vai tính từ trung điểm hai vai xuống).
   - Khi ít nhất một tay nâng lên vùng thực hiện ký hiệu (trước ngực, cổ hoặc mặt):
     $$Y_t = \min_{s \in \{\text{left}, \text{right}\}} y_{\text{wrist}, s}(t)$$
     Tay nằm trong vùng ký hiệu tích cực (Active Signing Zone) khi $H_t = 1$ hoặc $Y_t \le y_{\text{rest}}$.
3. **Năng lượng vận tốc và gia tốc cổ tay ($V_t, A_t$)**:
   Với vị trí cổ tay $\mathbf{w}_{s}(t) \in \mathbb{R}^2$ (lấy từ `left_palm_body[t, 0]` và `right_palm_body[t, 0]`, hoặc fallback sang `upper_body[t, 5:7]`):
   $$V_t = \max_{s \in \{L, R\}} \|\mathbf{w}_s(t) - \mathbf{w}_s(t-1)\|_2, \quad A_t = |V_t - V_{t-1}|$$
   Làm mượt tín hiệu bằng bộ lọc trung vị/trung bình trượt cửa sổ $w = 3$: $\tilde{V}_t = \text{MedianFilter}(V_t, 3)$.

### 2.2. Quy tắc xác định trạng thái Khung hình Tích cực (`is_signing_frame[t]`)
Một khung hình $t$ được coi là thuộc pha thực hiện ký hiệu (`ACTIVE`) nếu thỏa mãn:
$$\text{Active}(t) \iff \Big(H_t = 1 \land Y_t \le y_{\text{rest}}\Big) \lor \Big(H_t = 1 \land \tilde{V}_t \ge \theta_{\text{vel}}\Big)$$
- **Lý do kết hợp cả $Y_t \le y_{\text{rest}}$ VÀ $\tilde{V}_t \ge \theta_{\text{vel}}$**:
  - Nếu người ký thực hiện ký hiệu có pha **giữ tĩnh tay trước ngực/mặt** (ví dụ: ký hiệu chỉ số, giữ hình dạng bàn tay trong $0.5\text{s}$), lúc đó $\tilde{V}_t \approx 0$ nhưng tay vẫn đang ở vùng cao ($Y_t \le y_{\text{rest}}$), nên thuật toán **không bị cắt nhầm giữa chừng**.
  - Chỉ khi người ký **hạ cả hai tay xuống vùng nghỉ ($Y_t > y_{\text{rest}}$ hoặc tay ra khỏi khung $H_t = 0$) VÀ vận tốc giảm ($\tilde{V}_t < \theta_{\text{vel}}$)** trong liên tiếp $K_{\text{off}}$ frames thì ký hiệu mới kết thúc.

### 2.3. Thuật toán Cắt Ranh Giới
1. **Với video Từ Đơn (Single-Sign Auto-Trimming trong 4s)**:
   - Tìm đoạn liên thông dài nhất (sau khi lấp các khoảng trống ngắn $\le 5$ frames) có $\text{Active}(t) = \text{True}$: $[t_0, t_1]$.
   - Mở rộng vùng đệm biên an toàn (boundary margin) $\Delta = 3$ frames hai đầu để bảo toàn pha khởi phát/kết thúc nhẹ:
     $$t_{\text{start}} = \max(0, t_0 - \Delta), \quad t_{\text{end}} = \min(T, t_1 + \Delta)$$
   - **Bảo vệ an toàn (Fallback Invariant)**: Nếu $t_{\text{end}} - t_{\text{start}} < L_{\min}$ (mặc định $L_{\min} = 24$ frames $\approx 0.8\text{s}$), giữ nguyên toàn bộ clip gốc $[0, T)$ để không bao giờ làm hỏng clip ngắn.
   - Khi cắt mảng `features` từ $[0, T)$ về $[t_{\text{start}}, t_{\text{end}})$, giữ nguyên tính tăng nghiêm ngặt của `frame_indices` và `timestamps` để vượt qua 100% các kiểm tra `validate_features()` trong `prepare_clip.py`.

2. **Với video Chuỗi Từ Độc Lập (Multi-Sign Sequence Segmentation)**:
   - Chạy máy trạng thái 3 pha (`REST` $\to$ `SIGNING` $\to$ `COOLDOWN`) trên chuỗi $\text{Active}(t)$:
     - Chuyển `REST` $\to$ `SIGNING` khi có $\ge K_{\text{on}} = 4$ frames liên tiếp $\text{Active}(t) = \text{True}$.
     - Chuyển `SIGNING` $\to$ `REST` (đóng 1 từ) khi có $\ge K_{\text{off}} = 8$ frames liên tiếp ($\approx 0.27\text{s}$ ở 30 FPS) người ký hạ tay xuống vùng nghỉ ($\text{Active}(t) = \text{False}$).
   - Mỗi đoạn $[t_{\text{start}}^{(k)}, t_{\text{end}}^{(k)}]$ có độ dài $\ge L_{\min} = 20$ frames được trích xuất thành một sub-feature dict và đưa qua `prepare_arrays()` $\to$ `SL-GCN` để nhận diện từ thứ $k$.

---

## 3. Phạm Vi File & Tích Hợp Không Phá Hủy
- **File tạo mới**:
  - `slr-app/MVP/segmentation/__init__.py`
  - `slr-app/MVP/segmentation/boundary_detector.py` (chứa `slice_feature_arrays(arrays, start, end)` và `trim_single_sign(arrays, cfg)`)
  - `slr-app/MVP/segmentation/sequence_splitter.py` (chứa `split_sign_sequence(arrays, cfg)` và CLI chạy nhận diện chuỗi từ từ 1 video dài)
  - `slr-app/MVP/segmentation/test_segmentation.py`
- **Tích hợp có cờ bật/tắt vào `check_clip.py` / `demo.py` (Sau khi qua Human Review)**:
  - Thêm tham số tùy chọn `trim_idle: bool = False` vào `ClipRecognizer.recognize()` (mặc định `False` để bảo toàn hành vi cũ 100% cho các bài test hiện tại; bật qua cờ `--trim-idle` khi chạy demo webcam).

---

## 4. Kiểm Chứng Tự Động (Harness Layer 3 — Verification)
```powershell
cd slr-app/MVP
python -m py_compile segmentation/boundary_detector.py segmentation/sequence_splitter.py segmentation/test_segmentation.py
python -X utf8 segmentation/test_segmentation.py
```
- **Các thuộc tính bất biến (Invariants) bắt buộc phải kiểm thử trong `test_segmentation.py`**:
  1. `validate_features(sliced_arrays)` trong `prepare_clip.py` phải PASS 100% sau khi cắt đoạn.
  2. Trên clip chuẩn `014159.mp4` (vốn đã được cắt gọn từ tập VSL400), `trim_single_sign` phải giữ lại $\ge 85\%$ số frame và dự đoán Top-1 vẫn là `"Dài"` với `softmax > 0.99`.
  3. Trên chuỗi ghép nhân tạo gồm 3 lần lặp của `014159.mp4` xen kẽ 20 frames nghỉ (tay hạ xuống / NaN), `split_sign_sequence` phải tách ra chính xác **3 đoạn** và cả 3 đoạn đều nhận diện đúng nhãn `"Dài"`.

---

## 5. Trạng Thái Hoàn Tất 100% & Báo Cáo Thực Nghiệm Định Lượng

Toàn bộ module đã được hiện thực hóa, kiểm thử đơn vị hồi quy và đánh giá thực nghiệm toàn diện trên 26 video `local_data/`. Chi tiết lưu tại [EXPERIMENT_REPORT.md](../outputs/segmentation_experiments/EXPERIMENT_REPORT.md).

### 5.1. Tóm tắt kết quả Thực nghiệm 1: Cắt biên tự động Ký hiệu đơn (16 clips hợp lệ)
- **Trên 7 clips thực tế có frame thừa**: Tỷ lệ mất khớp giảm từ $49.60\%$ xuống $32.70\%$ ($-16.90\%$), Softmax trung bình tăng từ $0.4745$ lên **$0.6677$ ($+0.1932$)**.
- **Bảo toàn pha giữ tĩnh (Hold Phase)**: Method 1 (Kinematic + Wrist-Height FSM) đạt **$100.0\%$**, trong khi phương pháp chỉ dùng vận tốc (Velocity-Only) chỉ đạt $39.5\%$ (gây mất khớp và ép kích hoạt fallback ở $9/16$ clips).
- **Độ trễ thuật toán FSM**: Chỉ **$0.636\text{--}0.782\text{ ms}$**; giảm tổng thời gian Adapter + SL-GCN từ $264.33\text{ ms}$ xuống $241.34\text{ ms}$.

### 5.2. Tóm tắt kết quả Thực nghiệm 2: Tách chuỗi ký hiệu liên tục (T = 431 frames, 4 từ)
- **Method 1 (Kinematic + Wrist-Height FSM)**: Bắt đúng **$4/4$ ký hiệu ($100\%$ Recall)**, **$0$ Báo động giả (FP = 0)**, $\text{Mean IoU} = 0.923$, sai số biên trung bình $3.0$ frames, tổng thời gian $814\text{ ms}$.
- **Method 2 (Pure Sliding Window)**: Tốn $5,142\text{ ms}$ ($6.3\times$ thời gian), sinh ra **$3$ False Positives nghiêm trọng** do Softmax 400 lớp ảo giác trên khoảng nghỉ giữa các từ.
- **Method 3 (Hybrid FSM + 3-Crop TTA)**: Cùng Recall $4/4$ nhưng tốn $3,297\text{ ms}$ ($3\times$ thời gian model).

### 5.3. Gia cố 7 trường hợp biên (Edge-Case Hardening)
Đã vượt qua $100\%$ ($5/5$ test suites chính + $15/15$ bài kiểm thử hồi quy):
1. Khóa không cho tight-crop cắt vào các đoạn đã bật `fallback_triggered=True`.
2. Tự động chia nhỏ đoạn quá dài ($> 150$ frames) để tương thích ngưỡng cứng `max_frames = 150`.
3. Căn giữa cửa sổ Fallback quanh tâm cử động khi $T > 150$ frames.
4. Triệt tiêu cảnh báo `RuntimeWarning` bằng kiểm tra `np.isfinite` trên hiệu tọa độ liên tiếp.
5. Chuẩn hóa mô phỏng khoảng nghỉ mất tay (`mode="dropped"`).
6. Bắt `ValueError` khi cấu hình sai lệch tham số.
7. Bắt ngoại lệ trong `sliding_window_infer` bảo vệ luồng chạy.

**Quyết định tích hợp**: Sử dụng **Method 1 (`kinematic_wrist_fsm`)** làm cấu hình sản xuất mặc định cho buổi Demo Kiosk.


## 6. Chuyển động nối từ và cách kiểm chứng trên webcam

- **Quan sát 15/11/2026.** Clip `23_04_20` cho hai đoạn tự động và đúng chuỗi **Khăn quàng cổ → Cảm ơn**. Clip `23_04_34` chỉ cho một đoạn `[3,145)` và trả **Khăn quàng cổ**. Khi lấy riêng phần Cảm ơn bằng tay ở `[17,62)`, cùng mô hình trả **Cảm ơn** hạng 1 với điểm 0,9634. Kết quả cho thấy tách đoạn là một điểm nghẽn ở clip thứ hai. Cần xem tín hiệu theo từng khung để xác định tại sao đoạn bị gộp.
- **Giả thuyết.** Chuyển động đưa tay đến vị trí bắt đầu của ký hiệu kế tiếp (movement epenthesis) có thể xuất hiện tự nhiên trong chuỗi. Động tác chỉnh tư thế hoặc chạm nút là nguồn chuyển động ngoài lượt ký. Cần giữ chuyển động mang nghĩa ở đầu và cuối ký hiệu, đặc biệt pha mở tay ra trước của Cảm ơn. Bộ tách hiện đóng đoạn khi thấy đủ khung không hoạt động liên tiếp, nên khoảng hạ tay có thể chưa được ghi nhận thành ranh giới.
- **Đề xuất kiểm chứng.** Đánh dấu thủ công các pha ký, nghỉ và chuyển tiếp trên hai clip. Vẽ theo thời gian vị trí và tốc độ cổ tay, trạng thái phát hiện tay và `active_raw`. So biên tự động với biên thủ công trên cùng clip và cùng mô hình. Thử hai thứ tự từ với nhịp nghỉ rõ và nhịp nối tự nhiên. Ghi số đoạn trước khi chia theo giới hạn độ dài, số lượt gộp/tách thừa và số chuỗi đúng đủ từ, đúng thứ tự.
- **Hướng xử lý.** Với demo hai từ, thử hướng dẫn hạ tay nghỉ rõ giữa hai ký hiệu. Sau đó, nếu được duyệt, đối chiếu bộ tách hiện tại với tín hiệu nghỉ theo thời gian thực (mili giây) kết hợp vị trí, chuyển động và chất lượng điểm khớp. Làm mượt thời gian có thể giảm nhiễu ngắn, nhưng cần đo cả lỗi làm mất đoạn ngắn hoặc gộp hai ký hiệu.
- **Hướng học từ dữ liệu thực tế.** Fine-tune bộ phân loại từ đơn trên clip đã cắt quay đúng điều kiện triển khai có thể giúp giảm lỗi nhãn. Để xử lý biên khi ký liền, có thể học bộ phát hiện pha ký/chuyển tiếp từ video chuỗi có nhãn biên, hoặc huấn luyện mô hình nhận dạng chuỗi với CTC (căn chỉnh khung hình với thứ tự nhãn mà không cần ghi mốc từng từ). Giữ người ký hoặc phiên quay độc lập để đánh giá. Các hướng này là đề xuất, chưa chạy và cần duyệt trước khi sửa tiền xử lý hoặc huấn luyện.

Nguồn phương pháp: [Xử lý chuyển động nối từ trong nhận dạng liên tục](https://pubmed.ncbi.nlm.nih.gov/20075472/), [Sign Language Transformers và CTC](https://arxiv.org/abs/2003.13830), [Khoảng cách giữa video từ điển và ký liên tục](https://link.springer.com/article/10.1007/s11263-022-01589-6).


### 6.1. Kiểm tra tín hiệu nghỉ trên ba clip webcam thật (15/11/2026)

Chạy cùng bộ tách và mô hình SL-GCN trên cả ba clip. Video đều xấp xỉ 15 FPS. Tín hiệu `active_raw` đánh dấu một khung là đang ký khi có tay và cổ tay ở vùng ký hoặc chuyển động vượt ngưỡng. Cấu hình mặc định đóng đoạn sau 8 khung liên tiếp có `active_raw = False` (khoảng 0,53 giây ở 15 FPS). Các khoảng khung dưới đây tính từ 0 và loại trừ đầu mút phải.

| Clip | Chuỗi quan sát | Khoảng liên tiếp bộ tách coi là nghỉ ở vùng nối | Đầu ra tự động |
| --- | --- | --- | --- |
| `23_04_20` | Khăn quàng cổ → Cảm ơn | `[79,111)`, 32 khung (~2,13 giây) | 2 đoạn, đúng đủ thứ tự. Điểm Top-1 lần lượt 0,99995 và 0,96915. |
| `23_04_34` | Cảm ơn → Khăn quàng cổ | Từ khung 53 đến trước khung 75, chuỗi nghỉ dài nhất là `[56,59)`, 3 khung (~0,20 giây). | 1 đoạn, Khăn quàng cổ (0,82350). Cảm ơn hạng 15 trong đoạn gộp, nhưng đứng hạng 1 (0,96340) trên đoạn cắt tay `[17,62)`. |
| `23_13_00` | Cảm ơn → Khăn quàng cổ | `[60,86)`, 26 khung (~1,73 giây) | 2 đoạn. `[19,63)` là Cảm ơn (0,99354), `[83,151)` là Khăn quàng cổ (0,99992). |

- Trong clip bị gộp, tín hiệu nghỉ xen kẽ với các khung phát hiện tay ở vùng ký. Chẳng hạn các khung 59, 61, 63 và 65–66 đều bật lại `active_raw`. Theo quy tắc hiện tại, các khung này đặt lại bộ đếm nghỉ. Ở clip mới, khoảng nghỉ liên tục đủ dài để đóng đoạn đầu. Đây là nguyên nhân trực tiếp ở tầng tách đoạn trên các clip đã kiểm tra. Chưa xác định riêng phần ảnh hưởng của động tác thực tế, sai số điểm khớp và tốc độ thu hình.
- Hai chuỗi đảo thứ tự đã nhận đúng tự động khi có khoảng nghỉ rõ. Với demo có hướng dẫn, lấy đó làm kịch bản thử lại. Với nhịp nối tự nhiên, ưu tiên thử một bộ tách chịu được vài khung hoạt động xen kẽ trong khoảng nghỉ, dùng thời lượng theo mili giây và kiểm tra cả trường hợp cắt nhầm giữa một ký hiệu. Tập kiểm tra cần có cả các ký hiệu giữ tay tĩnh như Cảm ơn. Chưa thay đổi ngưỡng hay mã.

## 7. Điểm chưa giải quyết sau tổng duyệt webcam (16/11/2026)

| Điểm còn mở | Bằng chứng hiện có | Cách kiểm tra tiếp |
| --- | --- | --- |
| Kiosk lấy ít khung hơn ứng dụng Camera | Kiosk ghi 29 khung/4 giây và 97 khung/13 giây ở 640 × 480, khoảng 7,3–7,5 FPS. AVI ghi 30 FPS trong header. Ứng dụng Camera tạo MP4 1280 × 720 khoảng 15 FPS. Các lượt sau vẫn 97 khung. | Đo FPS theo đồng hồ và giữ cố định ánh sáng, tư thế, khung hình khi đối chiếu cấu hình thu. Cần xác định phần ảnh hưởng của chế độ webcam, phơi sáng và vòng lặp ghi/xem trước. Báo cáo kiosk mới có `capture.observed_fps`. |
| Có đoạn bị mất và đoạn đủ dài vẫn nhầm nhãn | 4 clip lỗi tổng cộng có 6 đoạn bị loại ở 12–19 khung sau khi thêm đệm. Chạy riêng 6 đoạn cho các nhãn khác Cảm ơn/Khăn quàng cổ. Trong các lượt đã giữ đủ 2 đoạn, Cảm ơn từng bị xếp sau Khô/Cầu lông. | Gán nhãn từ và biên thật cho từng đoạn khó trước khi tính độ chính xác. So tách tự động với biên đối chứng, dùng cùng checkpoint. Hiện chưa tách riêng ảnh hưởng của biên, chuyển động nhòe, mất điểm khớp và biến thể động tác. |
| Đứng yên sinh nhãn | Clip đứng yên `01_54_02` sinh một đoạn **Máy giặt**. Quy tắc đầu ra của chế độ chuỗi đã từ chối lượt đó. | Kiểm tra thêm đứng yên, pha chỉnh tư thế, người ngoài khung và giữ tay tĩnh. Đếm cả nhãn mô hình sinh ra và chuỗi được kiosk chấp nhận. |
| Độ dài chuỗi, tập từ và tiếng loa ngoài thực tế | Đã xác nhận hiển thị trực tiếp hai thứ tự hai từ. Nút kết thúc thủ công đã qua kiểm thử phần mềm. Chưa có số liệu chuỗi dài trên webcam, nhiều người ký hoặc xác nhận loa từ người thử. | Sau khi cấu hình thu và cắt đoạn được chọn, đánh giá trên phiên quay mới có nhãn, gồm chuỗi từ ba ký hiệu trở lên và nhiều từ/người ký. Ghi thời gian từ lúc kết thúc quay đến khi có kết quả, số chuỗi đúng đủ từ và kiểm tra phát loa. |

Nguồn cục bộ: [Kết quả tổng duyệt năm clip](../outputs/segmentation_experiments/webcam_demo_acceptance_20261115_185814.json), [kiểm tra lại biên](../outputs/segmentation_experiments/live_boundary_recheck_20261115_192932.json), [suy luận trên đoạn ngắn bị loại](../outputs/segmentation_experiments/live_dropped_interval_diagnosis_20261116.json). Lỗi HTTP `WinError 10053` đã có kiểm thử xử lý ngắt kết nối khi gửi ảnh xem trước. Nếu xuất hiện lại sau khi khởi động lại kiosk, đối chiếu yêu cầu HTTP và thời điểm `Report:` trước khi quy lỗi nhận dạng.

## 8. Đối chiếu offline phương pháp #32 (16/11/2026)

Chạy `segmentation/compare_timed_rest.py` trong môi trường `pbl6_slr` với `--camera-roll` trỏ vào thư mục clip. Mỗi clip chỉ trích MediaPipe một lần. Ba cấu hình dùng cùng đầu ra đó và cùng checkpoint.

| Cấu hình | Chuỗi đúng đủ nhãn và thứ tự trên 5 clip tham chiếu | Trên 2 clip quay sau |
| --- | ---: | ---: |
| Mặc định, 8 khung nghỉ liên tiếp và tối thiểu 20 khung/đoạn | 2/5 | 2/2 |
| Quy đổi hai ngưỡng trên theo thời lượng tương đương ở 15 FPS | 2/5 | 2/2 |
| #32, quy đổi thời lượng và chịu ngắt quãng ngắn | 3/5 | 2/2 |

- #32 cho phép nối khoảng nghỉ qua đợt hoạt động ngắn cỡ 130 ms nếu một cửa sổ 800 ms chứa tối thiểu 500 ms nghỉ quan sát được. Các mốc được làm tròn theo FPS của clip. Clip tham chiếu `23_04_34` chuyển từ **Khăn quàng cổ** thành đúng **Cảm ơn → Khăn quàng cổ**.
- Cả ba cấu hình trả đúng ba clip từ đơn trong phép thử gọi bộ tách. Clip đứng yên vẫn sinh dự đoán **Máy giặt**, và quy tắc cửa ra của kiosk từ chối clip cho cả ba cấu hình.
- Với bốn clip live 97 khung chưa có nhãn thật theo đoạn, hai cấu hình dựa trên thời lượng cho qua các lượt mà mặc định từ chối. Các nhãn mới gồm Kính lúp, Nói chuyện, Chạy và Cái đèn. Cần gán nhãn biên thật trước khi xác định số đoạn khôi phục đúng và số nhãn phát sinh sai.
- Giữ cấu hình mặc định của kiosk. Mức tăng 2/5 → 3/5 thuộc tập tham chiếu có ca đã dùng để đề xuất biến thể. Hai chuỗi quay sau đều đúng ở cả ba cấu hình. Cần thêm clip có nhãn trong điều kiện 7,5 FPS để đo hiệu quả ở cấu hình webcam thực tế.

[JSON đối chiếu 15 clip](../outputs/segmentation_experiments/timed_rest_32_20261115T194319Z.json).

### 8.1. Ba clip quay chuỗi dài bằng nút kết thúc thủ công

Người ký đã xác nhận nội dung từng clip. Clip `024009` là mẫu âm tính có chuyển động, không có ký hiệu đích. Clip `024431` có **Khăn quàng cổ → Cảm ơn → động tác chà mặt giống Rửa mặt**. Dùng **Rửa mặt** để đối chiếu luồng demo theo mô tả, chưa coi động tác này là mẫu VSL400 chuẩn. Clip `024619` lặp **Khăn quàng cổ → Cảm ơn** hai lần. Không có lượt **Dài** trong ba clip theo nhãn đã xác nhận.

| Clip | Thời gian quay | Mặc định (đoạn thô → đoạn có nhãn) | #32 (đoạn thô → đoạn có nhãn) |
| --- | ---: | ---: | ---: |
| `024009`, 214 khung | 28,70 giây | 4 → 2, từ chối | 5 → 4, từ chối |
| `024431`, 183 khung | 24,56 giây | 3 → 2, từ chối | 4 → 4, cho qua |
| `024619`, 199 khung | 26,70 giây | 4 → 3, từ chối | 6 → 6, cho qua |

- FPS đo theo đồng hồ là 7,45–7,46 ở cả ba clip. Kiosk đã ghi vượt 13 giây. Trong cấu hình mặc định, số đoạn sau lọc nhỏ hơn số đoạn thô nên kiosk yêu cầu thử lại. Thông báo “Cần ít nhất hai ký hiệu” chưa phân biệt được lý do này.
- Ở clip `024619`, chuẩn hóa thời lượng đơn thuần tăng số đoạn thô từ 4 lên 5. Thêm xử lý ngắt quãng của #32 tăng lên 6. Các biên bị tách thêm nằm trong những đoạn cũ `[112,144)` và `[165,191)`. Với các lượt được mô tả gồm ba hoặc bốn từ, đầu ra sáu nhãn là dấu hiệu cắt thừa. Việc kiosk cho qua thêm lượt chưa chứng minh nhận dạng tốt hơn.
- So với nhãn đã xác nhận, mặc định bỏ **Cảm ơn** ở `024431` và bỏ lần **Cảm ơn** thứ nhất ở `024619`. #32 cho qua cả hai nhưng chuỗi đều sai. Kết quả đúng đủ chuỗi là 0/2 cho cả ba cấu hình. Mẫu âm tính có chuyển động bị từ chối ở cả ba cấu hình; bên trong vẫn sinh 2 nhãn ở mặc định và 4 nhãn ở mỗi biến thể.
- Chưa đưa #32 vào kiosk. Giữ ba clip làm đối chứng có nhãn. Ưu tiên xác định nguyên nhân tốc độ webcam khoảng 7,45 FPS và gán biên từng động tác trước vòng đối chiếu mới.
- Bản thử cục bộ đã phân biệt các lý do từ chối. Với ba báo cáo chuỗi dài cũ, thông báo mới nêu số đoạn tìm thấy và số đoạn đủ dài, lần lượt là 4/2, 3/2 và 4/3. Ba lượt vẫn ở trạng thái thử lại. Đây là thay đổi thông báo, không thay đổi cách tách, nhận dạng hoặc chấp nhận lượt.

[JSON đối chiếu ba clip chuỗi dài](../outputs/segmentation_experiments/timed_rest_32_20261115T195122Z.json).

### 8.2. Kiểm tra giả thuyết chênh lệch FPS

- Kiosk mở webcam qua DirectShow và yêu cầu 640 × 480 ở 30 FPS. Mã không ghi kết quả từng lệnh đặt cấu hình hoặc định dạng luồng thiết bị đã thương lượng. Ứng dụng Camera ghi MP4 1280 × 720 với tốc độ trung bình khoảng 15 FPS. Hai bên dùng cấu hình khác nhau và chưa có phép đo dưới cùng điều kiện ánh sáng. 30 FPS trong header AVI là tốc độ khai báo cho tệp phát lại.
- Mã kiosk thực hiện đọc camera, tạo JPEG xem trước và ghi AVI trên cùng vòng lặp. Nhận dạng chỉ bắt đầu khi đã đóng tệp. Kiểm tra cục bộ trên 199 khung 640 × 480 của clip `024619` cho thời gian tạo JPEG chất lượng 75 cộng ghi MJPG trung vị **4,97 ms** và P95 **5,59 ms** mỗi khung. Phép đo dùng tệp tạm và khung đã giải mã, không gồm driver, streaming xem trước hoặc tải đồng thời của kiosk. Chu kỳ thu 7,45 FPS tương đương khoảng **134 ms/khung**. Chi phí hai khâu mã hóa/ghi riêng lẻ khó giải thích phần lớn khoảng này trong điều kiện đã đo.
- Giả thuyết ưu tiên là nhịp cấp khung từ chế độ thu mà driver chọn, có thể chịu ảnh hưởng của chế độ bù thiếu sáng. Tài liệu Kế hoạch 03 và 05 mô tả khả năng này. Chưa có log định dạng capture, thời gian từng lệnh `read()` và trạng thái điều khiển phơi sáng để quy nguyên nhân cho Auto Exposure.
- Phép thử xác định tiếp theo dùng cùng thiết bị và ánh sáng. Đếm khung theo đồng hồ khi chỉ gọi `read()` qua DirectShow ở cấu hình hiện tại, rồi đo lại với vòng lặp ghi/xem trước. Nếu chỉ đọc vẫn quanh 7,45 FPS, đối chiếu cấu hình 1280 × 720 / 15 FPS và backend khác, giữ các yếu tố khác cố định. Nếu chỉ đọc đạt khoảng 15 FPS, đo từng bước trong vòng kiosk để tìm chỗ hụt.

Tài liệu kỹ thuật: [OpenCV VideoCapture](https://docs.opencv.org/4.11.0/d8/dfe/classcv_1_1VideoCapture.html), [Windows Auto Exposure Priority](https://learn.microsoft.com/en-us/windows-hardware/drivers/stream/ksproperty-cameracontrol-auto-exposure-priority).

### 8.3. Tốc độ phát AVI và lượt kiosk sau khi bật đèn

- Kiosk ghi FPS mà OpenCV báo vào header AVI. Trên clip `024431`, 183 khung được thu trong 24,56 giây (7,45 FPS), nhưng header khai báo 30 FPS nên trình phát chỉ mất 6,10 giây, nhanh khoảng 4,03 lần. Thay mốc phát lại sẽ khôi phục thời lượng hiển thị xấp xỉ, không tạo thêm khung thu được.
- Clip `030632`, quay sau khi bật đèn, ghi 378 khung trong 25,328 giây (**14,92 FPS thực đo**). Header vẫn 30 FPS, tương đương 12,60 giây phát (nhanh khoảng 2,01 lần). Mức tăng FPS xảy ra trong cùng kiosk. Đây là bằng chứng bổ sung cho giả thuyết phơi sáng, chưa có đối chứng cùng bố trí và đo trạng thái điều khiển phơi sáng để kết luận.
- Nhãn người ký xác nhận là **Khăn quàng cổ → Cảm ơn → Khăn quàng cổ → Cảm ơn**. Kiosk trả thêm **Vòng tay** và đoán nhãn cuối là **Nói chuyện**. Ảnh lấy theo biên cho thấy đoạn `[253,275)` giữ hai tay bắt chéo trước cổ, nhiều khả năng thuộc phần cuối của Khăn quàng cổ lần hai. Đoạn `[311,356)` chứa động tác đưa tay từ miệng ra trước của Cảm ơn lần cuối. Cần đánh dấu biên trên toàn video để xác nhận. Tổng xử lý 33,41 giây, trong đó MediaPipe mất 31,93 giây.

[Báo cáo kiosk lượt bật đèn](../outputs/desktop_demo/20261115T200731_161984Z/report.json).

- Đã tạo [bản AVI xem đúng nhịp](../outputs/segmentation_experiments/webcam_030632_xem_dung_nhip.avi) cho clip 030632. Bản sao khai báo tốc độ phát **14,924 FPS**, suy ra từ 378 khung và thời gian quay 25,328 giây. Kiểm tra giải mã cho thấy **378/378 khung giống từng pixel** với clip gốc. Bản sao dùng để xem và ghi chú, với các khung phát cách đều theo FPS trung bình, do log không có thời gian thu từng khung. Dữ liệu đầu vào của kiosk vẫn là clip gốc. [Cấu trúc thời gian AVI](https://learn.microsoft.com/en-us/windows/win32/directshow/avi-riff-file-reference)

### 8.4. Kiểm tra lại biên trên clip 030632

- Chạy lại 378 khung với cùng bộ trích xuất và SL-GCN. Cấu hình mặc định tái hiện chính xác cả năm đoạn thô và năm nhãn của kiosk. Quy đổi thời lượng đơn thuần cho cùng kết quả. #32 vẫn tách thừa và đổi **Cảm ơn** lần đầu từ đúng thành **Nói chuyện**.
- Lấy một đoạn liên tục `[213,278)` bao trọn hai phần bị tách của **Khăn quàng cổ** lần hai. Mô hình trả đúng **Khăn quàng cổ** với điểm khoảng **0,99995**. Đây là bằng chứng cắt thừa ảnh hưởng một từ trong clip này. Đoạn ghép được chọn sau khi xem lại clip nên không phải kết quả của một bộ tách tự động mới.
- **Cảm ơn** lần cuối vẫn ra **Nói chuyện** ở cả ba biên đã thử: `[308,359)` của kiosk, `[311,356)` bỏ đệm, và `[302,367)` mở rộng. **Cảm ơn** lên hạng hai ở đoạn rộng nhưng điểm chỉ khoảng 0,009. Riêng các điều chỉnh biên này chưa khôi phục được nhãn đúng.
- So dữ liệu tay của hai lần **Cảm ơn** trong cùng clip. Tay trái qua cả bước phát hiện và kiểm tra gán bên ở **30/53 khung** trong đoạn đúng `[127,180)` và **16/51 khung** trong đoạn sai `[308,359)`. Số khung tìm thấy tay trái nhưng không gán bên đáng tin tăng từ **7** lên **16**. Cả hai tay đều không qua đồng thời hai bước kiểm tra trên **21 khung liên tiếp `[333,354)`** ở lượt sai, trùng vùng động tác đưa tay ra trước quan sát được khi xem khung 337 và 346. Điều này xác định dữ liệu tay bị hụt ở đoạn sai. Chưa có đối chứng xác định nguyên nhân hụt hoặc chứng minh khôi phục dữ liệu tay sẽ sửa nhãn.
- Giữ bộ tách và tiền xử lý của kiosk. Phép thử tách được hai việc cần xử lý: giữ liền pha cuối của **Khăn quàng cổ**, và tìm nguyên nhân mất dữ liệu tay ở **Cảm ơn** lần cuối.

[Kết quả chạy lại và cắt tay](../outputs/segmentation_experiments/live_030632_boundaries_20261115T201819Z.json).

### 8.5. Đối chiếu hình ảnh và bước gán tay ở hai lần Cảm ơn

- AGY CLI với Gemini 4 Hydrogen Low mở được video gốc. Khi đọc AVI trực tiếp, công cụ trả một ảnh mỗi giây phát nên bỏ qua pha chuyển động ngắn. Để đối chiếu chi tiết, dùng ảnh từ đúng số khung gốc. Các mốc `11,10–11,77 s` theo header AVI 30 FPS tương ứng khoảng `22,31–23,65 s` theo FPS thu trung bình 14,92. Đây là mốc ước lượng theo tốc độ trung bình, vì clip không có thời điểm thu lưu riêng cho từng khung.
- Ghi dữ liệu ngay trước và sau bước ghép bàn tay với cổ tay trong một lần chạy chẩn đoán cục bộ. Bước này giữ nguyên kết quả trả về. Chạy lại khớp 30/53 và 16/51 khung tay trái dùng được đã ghi ở mục 8.4. Trong 21 khung mất dấu `[333,354)`, MediaPipe Hands không tìm thấy bàn tay ở **5 khung**. Ở **16 khung** còn lại, nó tìm được ít nhất một bàn tay nhưng vị trí đó cách mọi cổ tay đủ tin cậy mà MediaPipe Pose tìm được xa hơn mức cho phép. Khoảng cách nhỏ nhất mỗi khung nằm trong khoảng 0,157–0,214 trên hệ tọa độ ảnh chuẩn hóa, ngưỡng hiện tại là 0,15.
- Điểm tin cậy thấp nhất mà Pose báo cho hai cổ tay là khoảng 0,946 trong 16 khung có tay. Kết quả khoanh vùng sự bất đồng về **vị trí** giữa bộ tìm bàn tay và bộ tìm cổ tay trên thân người. Điểm tin cậy của Pose không xác nhận cổ tay được đặt đúng chỗ.
- Ảnh đối chiếu dùng toàn bộ khung hình, với dòng ghi thời gian đặt phía dưới phần ảnh. Gemini xác nhận ở pha đưa tay ra trước, khung 339–351 của lần sau cho thấy tay thấp hơn, nằm sát mép dưới và khó thấy cổ tay hơn khung 157–169 của lần đầu. Ảnh cho thấy sự khác biệt về tư thế trong khung. Chưa xác định được cổ tay nằm ngoài hình hay bị che, cũng chưa xác định bên phát hiện nào đặt sai vị trí. Bước tiếp theo là vẽ chồng vị trí mà hai bộ phát hiện trả về lên các khung có khoảng cách lớn. Chưa thay ngưỡng hoặc tiền xử lý.

[Ảnh so hai pha đưa tay](../outputs/segmentation_experiments/webcam_030632_thanks_transition.png) · [Bản ghi từng khung](../outputs/segmentation_experiments/webcam_030632_hand_trace_20261115T203327Z.json).

- Đã vẽ chồng hai loại điểm lên đủ 21 khung gốc từ 333 đến 353. Ô vuông xanh là cổ tay từ bộ dò thân người. Chấm tròn vàng là điểm cổ tay từ từng bàn tay phát hiện được. Đường đứt nối cặp có khoảng cách nhỏ nhất. Năm khung thiếu chấm vàng vì bộ dò bàn tay không trả kết quả. Trong 16 khung còn lại, ngay cả cặp gần nhất cũng vượt ngưỡng ghép. Ảnh thể hiện hai phép đo của phần mềm; vị trí cổ tay thật chưa được đánh dấu độc lập.

[Ảnh đủ 21 khung](../outputs/segmentation_experiments/webcam_030632_21_khung_co_tay.png) · [Ảnh phóng to 3 khung](../outputs/segmentation_experiments/webcam_030632_3_khung_chi_tiet.png) · [Tọa độ dùng để vẽ](../outputs/segmentation_experiments/webcam_030632_toa_do_21_khung.json).

- Người ký khoanh hai vùng cổ tay trên khung 344 nguyên bản (640 × 480). Lấy tâm vòng khoanh ước lượng từ ảnh gửi trong chat, điểm do bộ dò thân người trả về cách vùng tham chiếu khoảng **107 px ở cả hai bên ảnh**. Điểm do bộ dò bàn tay trả về cách tâm vòng khoảng **23 px ở bên trái ảnh** và **10 px ở bên phải ảnh**. Đây là đối chiếu với vùng người ký đánh dấu trong một khung, không phải biên đo chuẩn cho tất cả 16 khung. Kết quả ủng hộ nhận định bộ dò thân người đặt cổ tay lệch trong khung 344 và bước ghép đã loại dữ liệu bàn tay dù điểm từ bộ dò bàn tay gần vùng tham chiếu hơn. [Khung 344 nguyên bản](../outputs/segmentation_experiments/webcam_030632_khung_344_goc.png)

### 8.6. Kiểm tra dữ liệu còn giữ được và đề xuất phép thử offline

- Chạy bộ trích xuất hiện tại mà không thay cấu hình. Cả **16 khung 337–352** còn đủ tọa độ bàn tay được gán tạm là **tay trái**. Ba khung **343–345** còn đủ dữ liệu của cả tay phải, tổng cộng 19 lượt bàn tay theo khung. Các điểm gán tạm cho tay trái đều ở phía phải ảnh, các điểm gán tạm cho tay phải ở phía trái ảnh. Điều này cho thấy gán tạm nhất quán theo phía ảnh trong đoạn đã xem; chưa xác nhận trái/phải thật của từng khung.
- Cả 19 lượt bàn tay có dữ liệu đều không qua kiểm tra gán bên hiện tại. Mã trích xuất vẫn giữ được hình bàn tay, vị trí lòng bàn tay theo thân và hệ số kích thước. Bộ chuyển đầu vào SL-GCN loại các điểm vì cờ gán bên chưa đạt. Năm khung còn lại không có điểm bàn tay để khôi phục theo cách này.
- Đối chứng với cùng biên: **Cảm ơn** lần đầu `[127,180)` vẫn đúng; lần cuối `[308,359)` vẫn ra **Nói chuyện**. Chưa chạy một phương án giữ lại dữ liệu bị loại.
- **Phép thử đề xuất, cần duyệt trước khi chạy:** giữ nguyên biên `[308,359)`, dùng ba cấu hình trên cùng dữ liệu đã trích. A giữ chuẩn hiện tại. B dùng lại dữ liệu gán tạm ở ba khung có cả hai tay, trong đó có khung 344 đã khoanh tay. C dùng lại các tay gán tạm trong cả 16 khung có dữ liệu. Giữ nguyên mô hình và bước loại tọa độ bất thường. Đối chiếu nhãn đứng đầu, thứ hạng của **Cảm ơn**, lỗi gán nhầm bên và dữ liệu còn thiếu. Nếu có tín hiệu cải thiện, xác nhận trên ca đúng và clip không có ký hiệu trước khi cân nhắc tích hợp. Phép thử chỉ thực hiện offline.

[Bản kiểm kê những điểm còn dùng được cho phép thử](../outputs/segmentation_experiments/webcam_030632_hand_recovery_audit_20261115T205521Z.json).

### 8.7. Kết quả thử offline khôi phục dữ liệu tay (16/11/2026)

Cùng đoạn **Cảm ơn lần cuối** `[308,359)` (51 khung gốc) và checkpoint đã kiểm tra mã băm. Phương án B/C chỉ đổi cờ gán bên từ chưa đạt sang đạt cho các tay đã có dữ liệu trong bản sao bộ đặc trưng. Giữ nguyên kiểm tra hình học, sửa dữ liệu thiếu và bộ phân loại. Kiểm tra lại đầu vào mặc định sau phép thử cho kết quả giống chính xác trước khi thử.

| Phương án | Điểm tay lấy lại ở khung gốc | Tỷ lệ thiếu điểm sau lọc và sửa | Nhãn đứng đầu | Hạng của Cảm ơn |
| --- | ---: | ---: | --- | ---: |
| A. Giữ nguyên | 0 | 42,12% | Nói chuyện | 47 |
| B. Giữ lại điểm của hai tay ở khung 343–345 | 60 (30 trái, 30 phải) | 37,76% | Nói chuyện | 77 |
| C. Giữ lại điểm tay có sẵn ở khung 337–352 | 190 (160 trái, 30 phải) | 25,42% | Tham ăn | 54 |

- Tất cả điểm được giữ lại trong hai phương án đều qua kiểm tra hình học và có mặt trong dữ liệu đưa vào mô hình. Tỷ lệ thiếu điểm tính trên các điểm của cả thân và tay trong 51 khung, mỗi khung tính một lần. Năm khung ngoài dải 337–352 vẫn không có điểm tay gốc để lấy lại.
- Giữ thêm dữ liệu làm giảm số điểm bị thiếu nhưng không sửa nhãn **Cảm ơn**. Phương án C thay nhãn sai **Nói chuyện** bằng **Tham ăn**. Chỉ thử trên một lần ký, chưa thể kết luận về các lần ký khác hay nguồn sai lệch trái/phải. Kiosk tiếp tục dùng phương án A.

[Báo cáo phép thử ba phương án](../outputs/segmentation_experiments/webcam_030632_hand_recovery_offline_20261115T205931Z.json).

### 8.8. Đối chứng Cảm ơn và Tham ăn bằng mẫu VSL400 (16/11/2026)

- Dùng trình trích xuất và checkpoint hiện tại để chạy lại clip `007412` (**Cảm ơn**) và `007538` (**Tham ăn**). Hai clip là các mẫu tập test của người ký 010, đã có nhãn từ dữ liệu nguồn. Cả hai trả đúng nhãn đứng đầu; bước chuẩn bị đầu vào có đủ các điểm tay sau khi sửa dữ liệu thiếu. Trong báo cáo test của cùng checkpoint, **Cảm ơn đúng 8/8**, **Tham ăn đúng 7/8** (ca sai sang **Nhà**), và **Nói chuyện đúng 8/8**. Hai mẫu chạy lại thuộc chính bộ test, không phải dữ liệu bổ sung độc lập.
- Cùng lúc chạy lại hai lần **Cảm ơn** ở clip 030632. Lần đầu là **Cảm ơn**. Lần cuối là **Nói chuyện**. Xét đoạn tay đã đưa ra trước dựa trên ảnh đối chiếu, ở khung **157–169** của lần đúng có **8/13 khung** với ít nhất một tay qua bước kiểm tra gán bên. Ở khung **339–351** của lần sai có **0/13 khung** đạt. Riêng khoảng này ở lần đúng cũng không có khung nào dùng được cả hai tay đồng thời. Vì vậy dữ liệu chỉ cho thấy sự khác nhau giữa còn được ít nhất một tay và mất cả hai tay ở pha quan sát; chưa chứng minh rằng thiếu dữ liệu là nguyên nhân duy nhất của lỗi nhãn.
- **Phép thử đề xuất, chưa chạy:** dùng đoạn **Cảm ơn** lần đầu `[127,180)` làm đối chứng, rồi thử đánh dấu thiếu các điểm tay trên bản sao ở đúng 13 khung **157–169**. So sánh nhãn với đầu vào nguyên bản, giữ nguyên biên và trọng số. Mục tiêu kiểm tra việc mất dấu ở pha đưa tay có đủ làm một đoạn đang đúng trở thành sai hay không. Cần duyệt trước vì biến thể thay đổi dữ liệu đầu vào SL-GCN.

[Kết quả bốn lượt chạy đối chứng](../outputs/segmentation_experiments/thanks_eating_reference_20261115T210855Z.json) · [Bảng kết quả test đã lưu](../outputs/drive_audit/per_class_test_results.csv) · [Bản ghi từng khung của hai lần Cảm ơn](../outputs/segmentation_experiments/webcam_030632_hand_trace_20261115T203327Z.json).

### 8.9. Thử offline ẩn dữ liệu tay ở pha đưa tay ra trước (16/11/2026)

- Đối chứng trên lần **Cảm ơn** nhận đúng, đoạn `[127,180)` của clip 030632. Phương án thử chỉ tắt cờ gán bên cho cả hai tay trong khung **157–169** trên bản sao, giữ tọa độ gốc, biên đoạn, kiểm tra hình học và checkpoint. Kiểm tra đầu vào mặc định khớp trước và sau phép thử.
- Ở 13 khung này, số khung có ít nhất một tay dùng được giảm từ **8 xuống 0** sau khi chuẩn bị đầu vào. Số điểm tay dùng được giảm từ 80 xuống 0 trong khoảng đó. Trên toàn đoạn 53 khung, tỷ lệ điểm tay thiếu tăng từ **36,79% lên 45,28%**.
- **Cảm ơn** vẫn đứng đầu. Điểm của mô hình giảm từ **60,66% xuống 48,78%**. **Nói chuyện** từ hạng 2 xuống hạng 3, chưa tái hiện lỗi ở lần ký cuối.
- Mất 13 khung ở pha đã chọn làm mô hình bớt chắc nhưng chưa đủ đổi nhãn trong lần ký đối chứng. Lần ký lỗi có 21 khung liên tiếp mất cả hai tay ở khoảng đã đo. Phép thử hiện tại chưa kiểm tra khoảng mất dài hơn hoặc sự khác nhau ở các pha khác. Kiosk giữ nguyên.

[Báo cáo phép thử ẩn dữ liệu tay](../outputs/segmentation_experiments/webcam_030632_thanks_mask_157_169_20261115T211333Z.json).

### 8.10. Đo thời gian từng bước sau khi quay (16/11/2026)

Đo một lần trên clip 030632 có 378 khung, sau khi đã nạp mô hình. Bộ đo chỉ ghi thời gian gọi các hàm. Đầu ra giữ nguyên năm đoạn thô và năm dự đoán, với điểm khớp báo cáo kiosk gốc trong dung sai 0,00001. Tổng thời gian chạy lại là **30,23 giây**; báo cáo kiosk gốc của clip này là **33,41 giây**.

| Bước | Thời gian đo |
| --- | ---: |
| Dò bàn tay | 14,95 giây |
| Dò điểm trên thân người | 12,99 giây |
| Đọc khung đã lưu | 0,71 giây |
| Các bước trích xuất còn lại | 0,37 giây |
| Tách đoạn, chuẩn bị dữ liệu và chạy SL-GCN | 1,22 giây, trong đó SL-GCN 1,17 giây |

Hai bước dò tay và dò thân người chiếm khoảng **92% thời gian xử lý sau khi quay** trong lần đo. Bước dò mặt không được gọi. Số liệu xác định chỗ nên đo khi thử giảm thời gian chờ; chưa đo tốc độ nếu chạy hai bộ dò song song hoặc bắt đầu dò trong khi quay.

[Báo cáo đo từng bước](../outputs/segmentation_experiments/webcam_030632_latency_profile_20261115T212533Z.json).

### 8.11. Ưu tiên độ chính xác trên các clip đã có (16/11/2026)

Chấm lại 10 clip có chuỗi và 2 clip không ký dựa trên báo cáo đã lưu. Chuỗi chỉ được tính đúng khi kiosk cho qua, đủ ký hiệu và đúng thứ tự. Bốn clip chưa xác định được nội dung ký nằm ngoài bảng. Nhãn **Rửa mặt** ở `024431` chỉ mô tả động tác người ký xác nhận.

| Cấu hình | Chuỗi 2 ký hiệu đúng | Chuỗi 3–4 ký hiệu đúng | Chuỗi dài sai vẫn được cho qua | Lượt không ký được cho qua |
| --- | ---: | ---: | ---: | ---: |
| Mặc định | 4/7 | 0/3 | 1/3 | 0/2 |
| Quy đổi thời lượng theo FPS | 4/7 | 0/3 | 3/3 | 0/2 |
| #32, quy đổi thời lượng và chịu ngắt quãng | 5/7 | 0/3 | 3/3 | 0/2 |

- Cả sáu chuỗi mặc định sai đều thiếu hoặc nhận nhầm ít nhất một lượt **Cảm ơn**. Tập clip này tập trung vào một người ký và hai nhãn xuất hiện thường xuyên, nên số liệu dùng để chọn ca sửa lỗi.
- Clip múa ngẫu nhiên `024009` bị kiosk từ chối. Hai đoạn nội bộ vẫn nhận **Khăn quàng cổ** (~100%) và **Cảm ơn** (94,72%). Điểm cho **Cảm ơn** trong ca đúng `01_53_21` là 84,68%. Một ngưỡng điểm chung sẽ giữ ca nhầm này nếu nó vẫn giữ ca đúng đó.

[So sánh #32 trên các clip ngắn](../outputs/segmentation_experiments/timed_rest_32_20261115T194319Z.json) · [Ba clip dài khoảng 7,45 FPS](../outputs/segmentation_experiments/timed_rest_32_20261115T195122Z.json) · [Clip 030632 khoảng 14,92 FPS](../outputs/segmentation_experiments/live_030632_boundaries_20261115T201819Z.json).

**Hai lượt Cảm ơn bị cắt hụt.** So ảnh gốc lấy cách một khung với quan sát độc lập từ Gemini. Sau đó chạy lại bộ trích điểm và bộ tách mặc định. Các khoảng `[đầu, cuối)` dùng chỉ số khung gốc từ 0 và loại trừ đầu mút phải.

| Clip | Đoạn tự động trước đệm | Số khung sau đệm | Pha đưa và giữ tay ra trước | Số khung bộ dò không tìm được tay trong pha đó |
| --- | --- | ---: | --- | ---: |
| `024431` | `[80,92)` | 18, dưới mức 20 | `[90,103)` | 11/13 |
| `024619` | `[66,79)` | 19, dưới mức 20 | `[78,91)` | 12/13 |

- Ảnh cho thấy lòng bàn tay mở ở khung **96–100** (`024431`) và **84–90** (`024619`), sau biên tự động ngay cả khi đã thêm đệm. Trong cả hai pha, cả 13 khung đều có cổ tay được ước lượng nằm trong vùng ký. Bộ tách vẫn cần ít nhất một bàn tay được ghi nhận để đánh dấu khung đang ký, nên phần lớn pha mở tay bị xem là nghỉ. Giảm số khung tối thiểu có thể làm đoạn cụt được nhận dạng và vẫn bỏ mất pha mở tay.
- Kiểm tra thêm ngay đầu ra của MediaPipe Hands, trước bước ghép với cổ tay. Tất cả 23 khung thiếu tay trong hai pha đều đã thiếu ở đầu ra bộ dò. Cả ba khung còn lại có tay được giữ và được đánh dấu đang ký. Đây là lỗi khác với 16 khung của clip `030632`, nơi có điểm bàn tay nhưng bước ghép bác bỏ vị trí. Chưa xác định vì sao bộ dò mất dấu trong hai clip này.

[Ảnh theo khung của 024431](../outputs/segmentation_experiments/webcam_024431_kiem_tra_bien.png) · [Ảnh theo khung của 024619](../outputs/segmentation_experiments/webcam_024619_kiem_tra_bien.png) · [Tín hiệu theo khung](../outputs/segmentation_experiments/webcam_two_dropped_thanks_trace_20261116T035528Z.json).

**Phép thử tiếp theo, cần duyệt trước khi chạy.** Trên hai video đã có, chạy cùng SL-GCN với hai khoảng cho mỗi lượt. Khoảng A là đoạn mặc định sau đệm (`[77,95)` và `[63,82)`), được đưa vào riêng để chẩn đoán dù kiosk bỏ qua. Khoảng B bao trọn từ lúc nhấc tay đến sau pha mở (`[77,106)` và `[63,95)`). Mốc clip `024619` bao hết pha mở quan sát được, tư thế nghỉ hoàn toàn chưa thấy ở khung cuối của bảng ảnh. Giữ nguyên mô hình và dữ liệu điểm trong từng khung. Ghi nhãn đứng đầu, hạng của **Cảm ơn** và số khung có điểm tay dùng được. Nếu B sửa nhãn, dùng ca đúng và clip múa ngẫu nhiên để kiểm tra một quy tắc tìm biên tự động trước khi cân nhắc đưa vào kiosk. Nếu B vẫn sai, ưu tiên kiểm chứng chất lượng dữ liệu tay ở pha mở.
