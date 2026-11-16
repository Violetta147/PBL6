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

### 8.12. Thử offline giữ đủ pha mở tay trong hai lượt Cảm ơn (16/11/2026)

Người ký đã duyệt phép thử A/B. Chạy lại hai video với cùng bộ trích điểm, bước chuẩn bị đầu vào và checkpoint SL-GCN đã kiểm tra mã băm. A dùng đoạn mặc định sau đệm và được đưa vào mô hình riêng dù kiosk loại vì ngắn. B giữ cùng khung bắt đầu và kéo dài đến sau pha mở tay quan sát được. Ở clip `024619`, tư thế nghỉ hoàn toàn chưa thấy tại khung cuối của bảng ảnh. Các khoảng `[đầu, cuối)` dùng chỉ số khung gốc từ 0.

| Clip | A, đoạn ngắn | Hạng và điểm Cảm ơn ở A | B, đủ pha mở | Hạng và điểm Cảm ơn ở B |
| --- | --- | --- | --- | --- |
| `024431` | `[77,95)`, 18 khung, nhãn đầu **Cầu lông** | Hạng 4, 0,81% | `[77,106)`, 29 khung | **Hạng 1, 99,63%** |
| `024619` | `[63,82)`, 19 khung, nhãn đầu **Nói chuyện** | Hạng 12, 0,012% | `[63,95)`, 32 khung | **Hạng 1, 84,47%** |

- Phần nối thêm có **0 khung với điểm bàn tay dùng được** ở cả hai clip. Tính mỗi khung nguồn một lần sau lọc và sửa dữ liệu, số điểm tay giữ nguyên **220 điểm trên 11 khung** ở `024431`, và **260 điểm trên 13 khung** ở `024619`. Riêng pha đưa và giữ tay ra trước còn điểm tay ở **2/13** và **1/13** khung tương ứng. Giữ đủ thời đoạn sửa được nhãn ở cả hai clip dù không bổ sung điểm bàn tay. Phép thử chưa phân lập ảnh hưởng riêng của chuyển động thân người và việc lặp đoạn theo độ dài trong bộ chuẩn bị đầu vào.
- Ghép kết quả B vào đúng vị trí theo thời gian và giữ nguyên các nhãn còn lại cho ra **Khăn quàng cổ → Cảm ơn → Rửa mặt** và **Khăn quàng cổ → Cảm ơn → Khăn quàng cổ → Cảm ơn**. Hai chuỗi này đúng với mô tả khi dùng biên chọn từ ảnh. Chạy lại kiosk mặc định vẫn tái hiện biên và dự đoán cũ. Chạy lại A sau B cho đầu vào và 400 điểm đầu ra giống hệt lần A đầu.
- Phép thử ở mục 8.13 kiểm tra cách giữ đoạn khi bộ dò bàn tay mất dấu giữa động tác, cùng các chuỗi vốn đúng và clip múa ngẫu nhiên `024009`.

[Báo cáo A/B và kết quả ghép theo biên chọn từ ảnh](../outputs/segmentation_experiments/webcam_two_thanks_crop_ab_20261116T040914Z.json).

### 8.13. Thử offline giữ đoạn khi mất dấu bàn tay (16/11/2026)

**Đầu vào.** Bảy chuỗi hai ký hiệu đã có nhãn, ba chuỗi dài `024431`, `024619`, `030632` và hai lượt không ký. Dùng số khung trên mỗi giây ghi trong báo cáo kiosk cho AVI và giá trị do bộ giải mã đọc từ MP4 cho các clip Windows Camera. Hai clip phát hiện lỗi dùng để đặt giả thuyết, nên phép đo là đối chiếu trên tập đã có. Dùng cùng đặc trưng trích từ từng clip cho cả hai phương án.

**Phương án nối qua mất dấu.** Sau ít nhất bốn khung liên tiếp được bộ tách mặc định đánh dấu đang ký, thử giữ đoạn nếu mất dấu bàn tay nhưng cổ tay từ bộ dò thân người vẫn ở vùng ký và có chuyển động trong 0,25 giây đầu. Chỉ nối các khung thiếu tay liên tiếp có cổ tay trong vùng ký, tối đa 1,8 giây tính theo FPS và làm tròn đến số khung gần nhất. Bộ tách mặc định quyết định lúc đóng đoạn. Điểm khớp và checkpoint giữ như cũ.

**Phương án chỉ khôi phục một đoạn ngắn.** Chọn sau khi phép thử đầu cho qua clip múa ngẫu nhiên và nối quá cuối đoạn `024619`. Chỉ áp dụng khi mặc định tìm được ít nhất hai đoạn thô, đúng một đoạn bị loại vì ngắn, và các đoạn còn lại đủ điều kiện nhận dạng. Kéo dài đoạn ngắn qua đúng chuỗi khung được hỗ trợ liên tiếp, rồi thêm đệm trong phạm vi giữa hai đoạn kế cận. Giữ nguyên biên và nhãn của các đoạn còn lại. Khi thủ tục không đủ điều kiện, dùng kết quả mặc định. Điều kiện đúng một đoạn có thể bỏ lỡ lượt mất nhiều đoạn, và cần đo trên tập độc lập do quy tắc được chọn sau khi xem lỗi.

**Đầu ra và kiểm chứng.** Lưu biên, số khung được nối, nhãn và trạng thái cho qua từng clip. Chấm đủ ký hiệu đúng thứ tự, so số đoạn thô với số ký hiệu đã biết và đếm clip không ký được cho qua. So kết quả mặc định với báo cáo trước để phát hiện sai lệch khi chạy lại. Kiểm tra hồi quy tập trung vào bốn chuỗi mặc định đã đúng và hai lượt không ký.

Chạy từ `slr-app/MVP/`. `$cameraRoll` trỏ tới thư mục chứa các MP4 thử nghiệm của Windows Camera.

```powershell
python -m py_compile segmentation/compare_hand_dropout.py
python -B -u -X utf8 segmentation/compare_hand_dropout.py --camera-roll $cameraRoll
```

| Cấu hình | Chuỗi 2 ký hiệu đúng | Chuỗi 3–4 ký hiệu đúng | Lượt không ký được cho qua |
| --- | ---: | ---: | ---: |
| Mặc định | 4/7 | 0/3 | 0/2 |
| Nối qua mất dấu trên mọi đoạn | 4/7 | 1/3 | 1/2 |
| Chỉ khôi phục đúng một đoạn ngắn | 4/7 | 2/3 | 0/2 |

- Nối trên mọi đoạn sửa đúng `024431`, nhưng nối `024619` tới khung 100 sau đệm và nhận **Cầu lông** ở đoạn cần ra **Cảm ơn**. Nó cũng kéo dài cả hai đoạn ngắn của clip múa ngẫu nhiên `024009`, khiến clip được cho qua với bốn nhãn.
- Phương án chỉ khôi phục một đoạn ngắn tìm biên tự động `[77,108)` ở `024431` và `[63,95)` ở `024619`. SL-GCN trả **Cảm ơn** đứng đầu với điểm 99,98% và 84,47%, tương ứng. Hai chuỗi 3 và 4 ký hiệu đúng đủ thứ tự. Các đoạn khác trong hai lượt giữ nguyên từ lần chạy mặc định. `030632` vẫn có 5 đoạn thô cho 4 ký hiệu và nhầm **Cảm ơn** cuối thành **Nói chuyện**. Số chuỗi có ít đoạn thô hơn số ký hiệu là 2/10 ở cả ba phương án, đều là hai ca hai ký hiệu đã gộp từ mặc định.
- Chạy lại mặc định khớp biên, nhãn, trạng thái và điểm dự đoán đầu trong dung sai 0,00001 trên cả 12 báo cáo cũ. Với phương án chỉ khôi phục một đoạn ngắn, kiểm tra quy tắc trên cả 12 clip, kiểm tra mã băm từng clip và chạy lại mô hình ở hai đoạn đủ điều kiện. Mười clip còn lại trả nguyên kết quả mặc định. Kiểm tra riêng điều kiện cần có đoạn đã bắt đầu, tín hiệu chuyển động, giới hạn thời gian và điểm dừng khi cổ tay rời vùng ký.
- Kết quả ưu tiên cách khôi phục một đoạn ngắn để kiểm tra tiếp trên phiên quay độc lập. Quy tắc chọn từ chính tập đã xem, trong đó chỉ có một clip múa ngẫu nhiên. Kiosk vẫn dùng bộ tách mặc định.

[Báo cáo phép thử nối qua mất dấu](../outputs/segmentation_experiments/hand_dropout_20261116T041914Z.json) · [Báo cáo đối chiếu cả ba cấu hình](../outputs/segmentation_experiments/hand_dropout_guarded_20261116T042209Z.json).

### 8.14. Đối chiếu trên phiên quay lúc 11 giờ (16/11/2026)

Phiên này có ba lượt ở chế độ chuỗi (`110216`, `110403`, `110546`). Mỗi clip có SHA-256 khác toàn bộ 12 clip dùng để chọn quy tắc. Hai lượt quay chế độ một ký hiệu cùng phiên nằm ngoài phép thử. Dùng thời lượng và FPS đo lúc quay trong báo cáo kiosk. So bộ tách mặc định với quy tắc chỉ khôi phục một đoạn ngắn ở mục 8.13, giữ checkpoint và các ngưỡng đã dùng trong phép thử đó.

Chấm theo thứ tự ký do người ký xác nhận. Lượt có ký đúng khi bộ tách cho qua và trả đủ nhãn theo đúng thứ tự. Lượt không ký đúng khi hệ thống từ chối. Các clip chưa xác nhận nội dung vẫn dùng được để kiểm tra hai cấu hình có trả cùng kết quả và quy tắc có cơ hội kích hoạt hay không.

Chạy lại với checkpoint và hai mẫu tham chiếu đã kiểm tra. Biên, trạng thái cho qua, nhãn và điểm của kiosk mặc định khớp báo cáo gốc trong dung sai 0,00001. Cả ba clip đều ở khoảng 29,5–29,8 FPS. Mỗi clip có đúng hai đoạn thô và hai đoạn được nhận dạng. Đoạn ngắn nhất trong sáu đoạn là 51 khung sau đệm. Quy tắc khôi phục không kích hoạt lần nào và trả nguyên kết quả mặc định trên cả ba clip. Cần clip độc lập có đúng một đoạn bị loại vì ngắn để kiểm chứng tác dụng khôi phục.

Người ký xác nhận cả ba lượt đều là **Khăn quàng cổ → Cảm ơn**. Hai cấu hình cùng đạt **0/3 chuỗi đúng** và **2/6 vị trí nhãn đúng**. Có hai đoạn ở mỗi clip, nhưng cả ba vị trí của Cảm ơn đều sai. Chưa đối chiếu biên với video gốc để xác định đoạn đưa vào mô hình có chứa trọn ký hiệu hay không.

| Clip | Kết quả theo thứ tự ở cả hai cấu hình |
| --- | --- |
| `110216` | Khăn quàng cổ → Chạy |
| `110403` | Không nghe lời → Tháng mười một |
| `110546` | Khăn quàng cổ → Tháng |

Hai lượt **một ký hiệu** được chấm riêng theo báo cáo kiosk gốc. `110720` là lượt không ký nhưng nhận **Màu xanh da trời**. `110739` là **Cảm ơn** nhưng nhận **Cháu**. Lượt không ký này xác nhận lỗi báo nhầm ở chế độ một ký hiệu. Phép chấm chế độ chuỗi chưa có lượt không ký của phiên này.

[Báo cáo chạy lại ba lượt độc lập](../outputs/segmentation_experiments/hand_dropout_independent_11h_20261116T042643Z.json) · [Kết quả chấm năm lượt theo nhãn người ký xác nhận](../outputs/segmentation_experiments/webcam_11h_scored_20261116T042935Z.json).

### 8.15. Tiêu chí dừng thí nghiệm chuỗi đã duyệt (16/11/2026)

Trên 10 chuỗi mới dùng để đánh giá, ít nhất **9/10** được nhận đủ và đúng thứ tự. Chế độ chuỗi phải từ chối cả **5/5 lượt không ký**. Ghi nhãn và thứ tự trước khi đối chiếu dự đoán. Khi đạt đồng thời hai điều kiện, báo **[ĐÃ ĐẠT TIÊU CHÍ]** kèm số lượt đúng và số lượt không ký bị nhận nhầm. Phiên 11 giờ hiện có **0/3 chuỗi đúng**. Tiêu chí này áp dụng cho chế độ chuỗi.

### 8.16. Đối chiếu pha mở tay của ba lượt Cảm ơn lúc 11 giờ (16/11/2026)

Lấy một ảnh mỗi 10 khung nguồn, khoảng 0,34 giây giữa hai ảnh. Gemini 4 Hydrogen Low đọc ảnh theo số khung mà chưa được cung cấp nhãn hay biên của kiosk. Đối chiếu quan sát đó với ảnh và biên đã lưu. Mốc động tác là xấp xỉ do ảnh lấy thưa. Chỉ số khung bắt đầu từ 0 và khoảng `[a,b)` không tính khung `b`.

| Clip | Biên kiosk đưa vào mô hình | Pha giữ lòng bàn tay mở quan sát trên ảnh | Quan sát |
| --- | --- | --- | --- |
| `110216` | `[281,332)` | Khoảng 330–380, hạ tay vào khoảng 390–400 | Biên kết thúc ngay đầu pha giữ. Khung 370 và 380 còn thấy hai lòng bàn tay hướng ra trước. |
| `110403` | `[183,274)` | Khoảng 230–260, tay rút lại ở khung 270 | Có đủ pha mở và giữ tay nhìn thấy trên ảnh. |
| `110546` | `[204,295)` | Khoảng 250–280, tay rút lại ở khung 290 | Có đủ pha mở và giữ tay nhìn thấy trên ảnh. |

[Ảnh khung 110216](../outputs/segmentation_experiments/webcam_110216_sequence_frames.png) · [Ảnh khung 110403](../outputs/segmentation_experiments/webcam_110403_sequence_frames.png) · [Ảnh khung 110546](../outputs/segmentation_experiments/webcam_110546_sequence_frames.png).

Đếm dữ liệu gốc của bộ dò bàn tay và điểm tay còn dùng được sau lọc/sửa trong đoạn kiosk. Mỗi khung nguồn được tính một lần. Chạy lại tái hiện biên mặc định trên cả ba clip.

| Clip | Khoảng kiểm tra | Số khung trong đoạn kiosk | Khung không có tay ngay từ bộ dò, tính trên toàn khoảng | Khung có điểm của cả hai tay sau chuẩn bị đầu vào, tính trong đoạn kiosk |
| --- | --- | ---: | ---: | ---: |
| `110216` | `[330,385)` | 2/55 | 50/55 | 0/2 |
| `110403` | `[230,261)` | 31/31 | 0/31 | 13/31 |
| `110546` | `[250,281)` | 31/31 | 0/31 | 31/31 |

- `110216` có **53/55 khung** của khoảng giữ tay nằm ngoài đoạn đưa vào mô hình. Đoạn mặc định dài **51 khung**, nên quy tắc chỉ cứu đoạn dưới 20 khung không tác động. Trong hai khung kiểm tra còn lọt vào đoạn, cả hai đều thiếu dữ liệu tay ngay từ bộ dò.
- `110403` và `110546` đều còn ít nhất một tay dùng được ở **31/31** khung kiểm tra. Riêng `110546` có cả hai tay trong cả 31 khung và vẫn bị dự đoán là **Tháng**. Có đủ điểm để dùng không xác nhận tọa độ chính xác. Chưa xác định nguyên nhân của nhãn sai trên hai clip đã giữ được pha mở tay.
- Mục 8.17 đối chiếu hai biên của `110216`. Giữ `110546` làm ca chẩn đoán riêng cho lỗi xảy ra dù pha mở đã nằm trong đoạn và có điểm của hai tay.

[Báo cáo dữ liệu tay theo khung](../outputs/segmentation_experiments/webcam_11h_thanks_boundary_audit_20261116T043351Z.json).

### 8.17. Thử offline giữ hết pha mở tay ở 110216 (16/11/2026)

Người ký đã duyệt so A là đoạn kiosk `[281,332)` với B là đoạn kéo đến khung nghỉ `[281,400)`. Cả hai dùng cùng đặc trưng trích một lần và cùng checkpoint. Kiểm tra mã băm video, checkpoint và hai mẫu tham chiếu. Khớp Top-5 của A với báo cáo kiosk trong dung sai 0,00001. Chạy lại A sau B cho đầu vào và toàn bộ 400 điểm mô hình giống hệt lần A đầu.

| Đoạn | Nhãn đứng đầu | Hạng và điểm của Cảm ơn | Khung có điểm bàn tay sử dụng được |
| --- | --- | --- | ---: |
| A `[281,332)`, 51 khung | Chạy, 54,00% | Hạng 10, 0,49% | 40/51 |
| B `[281,400)`, 119 khung | Lạnh, 16,33% | Hạng 5, 9,06% | 50/119 |

- B thêm 68 khung, trong đó 10 khung có điểm tay dùng được và cả 10 chỉ còn một tay. Riêng 55 khung kiểm tra ở pha giữ lòng bàn tay mở, B có 9 khung còn điểm một tay. Không có khung nào trong pha đó còn điểm cả hai tay.
- Kéo dài đoạn làm Cảm ơn tăng hạng nhưng Top-1 vẫn sai. Nếu thay riêng đoạn thứ hai bằng kết quả B, chuỗi sẽ là **Khăn quàng cổ → Lạnh**. Số chuỗi đúng của phiên 11 giờ vẫn là 0/3 ngay cả khi dùng biên chọn bằng mắt cho clip này.
- Mục 8.18 kiểm tra ảnh hưởng của mật độ khung trên `110546`, nơi pha mở tay có đủ dữ liệu tay.

[Báo cáo A/B 110216](../outputs/segmentation_experiments/webcam_110216_thanks_crop_ab_20261116T043643Z.json).

### 8.18. Thử offline mật độ khung trên 110546 (16/11/2026)

Người ký đã duyệt so ba đầu vào trên biên `[204,295)` của Cảm ơn. A giữ toàn bộ khung. B lấy các khung nguồn chẵn trong đoạn và C lấy các khung nguồn lẻ, cùng mật độ khoảng 14,88 khung/giây. Trích điểm một lần trên video gốc. Giữ mốc thời gian, điểm và cờ chất lượng của từng khung được chọn. Cả ba dùng cùng checkpoint và cách chuẩn bị đầu vào. Kết quả A khớp Top-5 kiosk trong dung sai 0,00001. Chạy lại A sau B/C cho đầu vào và toàn bộ 400 điểm mô hình giống hệt lần đầu.

| Mẫu | Số khung | Nhãn đứng đầu và điểm | Cảm ơn xếp hạng | Khung có điểm hai tay trong pha giữ tay |
| --- | ---: | --- | ---: | ---: |
| A, toàn bộ, 29,76 khung/giây | 91 | Tháng, 34,63% | 11 (0,92%) | 31/31 |
| B, khung nguồn chẵn | 46 | Cảm ơn, 95,01% | 1 | 16/16 |
| C, khung nguồn lẻ | 45 | Cảm ơn, 81,68% | 1 | 15/15 |

- Cả hai cách lấy thưa đều sửa nhãn **Cảm ơn** ở biên cố định. Giữ kết quả **Khăn quàng cổ** ở đoạn đầu và thay riêng nhãn đoạn hai bằng B hoặc C cho đúng chuỗi của `110546` trong đối chiếu offline.
- Việc lấy thưa thay đổi số khung và số lần đoạn được lặp để chuẩn bị đầu vào 150 khung của SL-GCN. Tác dụng riêng của mật độ khung và cách lặp chưa được tách trong phép thử này. Kết quả đo trên một đoạn với điểm trích từ video khoảng 30 FPS, vì vậy chưa đánh giá việc quay trực tiếp ở 15 FPS hay số chuỗi đúng khi áp dụng toàn lượt.
- Mục 8.19 mở rộng phép thử lấy thưa cho cả hai đoạn của ba clip phiên 11 giờ.

[Báo cáo đối chiếu mật độ khung trên 110546](../outputs/segmentation_experiments/webcam_110546_thanks_sampling_20261116T043859Z.json).

### 8.19. Thử offline mật độ khung trên cả ba chuỗi lúc 11 giờ (16/11/2026)

Người ký đã duyệt áp dụng phép thử trên cả sáu đoạn của `110216`, `110403`, `110546`. Giữ nguyên biên kiosk và dùng cùng đặc trưng trích một lần từ mỗi clip. Đối chiếu ba đầu vào cho từng đoạn: đầy đủ, khung nguồn chẵn, khung nguồn lẻ. Kiểm tra mã băm video và checkpoint, hai mẫu tham chiếu, Top-5 mặc định của từng đoạn và kết quả phép thử trước trên đoạn `110546`. Cả ba chuỗi đã được người ký xác nhận là **Khăn quàng cổ → Cảm ơn**.

| Clip | Giữ toàn bộ khung | Khung nguồn chẵn | Khung nguồn lẻ |
| --- | --- | --- | --- |
| `110216` | Khăn quàng cổ → Chạy | Khăn quàng cổ → Cầu lông | Khăn quàng cổ → Chạy |
| `110403` | Không nghe lời → Tháng mười một | Hát → Tháng | Gió → Cảm ơn |
| `110546` | Khăn quàng cổ → Tháng | **Khăn quàng cổ → Cảm ơn** | **Khăn quàng cổ → Cảm ơn** |
| Chuỗi đúng đủ và đúng thứ tự | 0/3 | 1/3 | 1/3 |
| Vị trí nhãn đúng | 2/6 | 3/6 | 4/6 |

- Cả hai cách lấy thưa giữ nguyên hai vị trí **Khăn quàng cổ** vốn đúng. `110403` chỉ nhận đúng **Cảm ơn** khi lấy khung lẻ. Kết quả giữa khung chẵn và khung lẻ chưa đủ ổn định để chọn lệch một khung làm mặc định. Thử nghiệm giữ nguyên biên cắt và chưa đo lượt không ký.
- `110216` vẫn sai khi giữ biên kiosk và lấy thưa. Phép thử tiếp theo cần duyệt: giữ biên đầy đủ `[281,400)` của `110216` theo mục 8.17 và đối chiếu cả hai cách lấy thưa với đầu vào đầy đủ. Mục tiêu kiểm tra việc kết hợp giữ trọn pha mở với giảm mật độ khung có sửa nhãn trên ca vốn sai với từng cách riêng hay không.

[Báo cáo đối chiếu cả sáu đoạn](../outputs/segmentation_experiments/webcam_11h_sequence_sampling_20261116T044244Z.json).
