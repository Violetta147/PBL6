# Phân Tích Bản Bàn Giao SLR MVP (Khoa Bàn Giao Cho Quân)

---

## 1. Tổng Quan Gói Bàn Giao

- **Tên gói lưu trữ:** `PBL6_MVP_BanGiao_Quan_20261113_234032.zip`
- **Vị trí giải nén trong Monorepo:** [slr-app/MVP/](file:///C:/Users/LAPTOP%20T&T/VIOLETTA/Documents/ChatGPT/PBL6/slr-app/MVP)
- **Tài liệu hướng dẫn bàn giao:** [BAN_GIAO_QUAN.md](file:///C:/Users/LAPTOP%20T&T/VIOLETTA/Documents/ChatGPT/PBL6/slr-app/MVP/BAN_GIAO_QUAN.md) & [README.md](file:///C:/Users/LAPTOP%20T&T/VIOLETTA/Documents/ChatGPT/PBL6/slr-app/MVP/README.md)
- **Người bàn giao:** Khoa (phụ trách mô hình AI SLR & đo vẽ vỏ phần cứng).
- **Người nhận bàn giao:** Quân (phụ trách giao diện 1024×600 & tích hợp ứng dụng).
- **Mục tiêu:** Cung cấp bản chạy thử nghiệm (MVP) nhận dạng cử chỉ ký hiệu từ video/webcam bằng mô hình SL-GCN chạy trên CPU, phát âm thanh phản hồi (TTS) và sẵn sàng tối ưu cho màn cảm ứng 7 inch (1024 × 600).

---

## 2. Kiến Trúc Kỹ Thuật Module SLR

### A. Mô hình AI & Xử lý khung xương (Skeleton)
- **Mô hình cốt lõi:** **SL-GCN (Spatial-Temporal Graph Convolutional Network)** kết hợp Attention (`decouple_gcn_attn.py`), đồ thị 27 điểm khớp (`sign_27.py`).
- **Trọng số đã huấn luyện (Checkpoint):** `MVP/deployment/slgcn_smoke/gcnCkpt.pt` (dung lượng **~35.4 MB**, epoch 52).
- **Trích xuất đặc trưng (Feature Extraction):**
  - Sử dụng thư viện **MediaPipe (v0.10.14)** để nhận diện các điểm mốc (landmarks) bàn tay trái, bàn tay phải và nửa thân trên (`upper_body`).
  - Chuẩn hóa tọa độ (`normalization.py`) và kiểm tra tính hợp lệ của bàn tay (`handedness.py`).
- **Bảng từ vựng ký hiệu:** `deployment/handoff_assets/label_map_v1.json` gồm 400 nhãn ngôn ngữ ký hiệu tiếng Việt (Dataset VSL400).

### B. Dữ liệu thử nghiệm & Giọng đọc phát âm (TTS)
- **Video clip kiểm thử mẫu:** `local_data/014159.mp4` (59 khung hình, nhãn ký hiệu *"Dài"*).
- **Kho âm thanh TTS tiếng Việt Offline (`local_data/tts/`):**
  - 4 file mẫu ban đầu trong gói bàn giao của Khoa:
    - `local_data/tts/86.mp3`: *"Cảm ơn"*
    - `local_data/tts/95.mp3`: *"Dài"*
    - `local_data/tts/243.mp3`: *"Nước"*
    - `local_data/tts/364.mp3`: *"Xin lỗi"*
  - Đã sinh bổ sung 396 file còn lại qua `desktop_mvp/generate_tts_assets.py` (`gTTS` tiếng Việt, lược chữ trong ngoặc đơn) đạt đủ **`400/400` file `.mp3` (`0.mp3` → `399.mp3`, tổng `2.97 MB`)** để chạy Offline 100%.

### C. Ghi chú kỹ thuật về Lật gương (Mirroring)
- UI hiển thị lật gương (`transform: scaleX(-1)` trên `<img id="preview">` trong `desktop_mvp/demo.html`), trong khi Backend (`desktop_mvp/demo.py`) giữ nguyên frame gốc không lật để khớp `handedness.py` (tập VSL400 non-mirrored).
- Xem phân tích chi tiết tại [CO_CHE_LAT_GUONG_UI_VA_PIPELINE_SLR.md](file:///C:/Users/LAPTOP%20T&T/VIOLETTA/Documents/ChatGPT/PBL6/mynotes/CO_CHE_LAT_GUONG_UI_VA_PIPELINE_SLR.md).

---

## 3. Cấu Trúc Mã Nguồn Trong `slr-app/MVP/`

| Thư mục / Tệp tin | Vai trò chức năng |
| :--- | :--- |
| `desktop_mvp/demo.py` | Máy chủ điều phối webcam, xử lý trạng thái quay video, inference và trả kết quả qua giao diện web `http://127.0.0.1:8765`. |
| `desktop_mvp/demo.html` | Giao diện hiển thị camera xem trước, nút bấm, phím tắt và phát file âm thanh MP3. |
| `desktop_mvp/check_clip.py` | Kịch bản kiểm tra chất lượng suy luận trên một file video MP4 có sẵn. |
| `desktop_mvp/record_webcam.py` | Kịch bản hỗ trợ quay mẫu video từ camera máy tính. |
| `deployment/` | Chứa trọng số mô hình `gcnCkpt.pt`, pipeline trích xuất MediaPipe và cấu hình huấn luyện. |
| `local_data/` | Chứa clip mẫu và file âm thanh phát ra loa. |

---

## 4. Hướng Dẫn Kích Hoạt Môi Trường Chạy Thử Trên Windows

Yêu cầu máy tính có cài sẵn **Python 3.11 (64-bit)**:

```powershell
# 1. Di chuyển vào thư mục SLR MVP
cd "C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6\slr-app\MVP"

# 2. Tạo môi trường ảo và cài đặt thư viện
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "numpy==2.4.6" "opencv-contrib-python==4.11.0.86" "mediapipe==0.10.14"
.\.venv\Scripts\python.exe -m pip install "torch==2.7.0+cpu" --index-url https://download.pytorch.org/whl/cpu

# 3. Thử nghiệm suy luận trên video có sẵn (không cần webcam):
.\.venv\Scripts\python.exe -X utf8 desktop_mvp/demo.py --clip local_data/014159.mp4

# 4. Chạy trực tiếp với Webcam:
.\.venv\Scripts\python.exe -X utf8 desktop_mvp/demo.py --camera 1
```

- **Quy trình tương tác trên màn hình:**
  - Bấm phím **R** (hoặc nút trên màn hình): Đếm ngược 3 giây → Quay cử chỉ khoảng 4 giây → Tự dừng.
  - Mô hình SL-GCN xử lý và trả về từ tiếng Việt dự đoán.
  - Bấm phím **F** (hoặc nút Xác nhận & phát): Hệ thống phát âm thanh tiếng Việt ra loa.

---

## 5. Giải Đáp: Tách Biệt STT và SLR Thì Sau Này Gộp Chung Giao Diện Có Khó Không?

> **Khẳng định:** **Hoàn toàn KHÔNG khó, thậm chí đây là kiến trúc chuẩn xác và sạch đẹp nhất!**

### Lý do kỹ thuật:
1. **Kiến trúc Microservices độc lập:**
   - Luồng **STT** (Next.js/Node.js) chạy lắng nghe cổng `3100`.
   - Luồng **SLR** (Python SL-GCN/OpenCV) chạy dịch vụ webcam tại cổng `8765`.
   - Việc tách biệt giúp nhóm bạn phát triển song song: Quân làm phần Giọng nói (STT) và giao diện không lo xung đột thư viện với Khoa làm phần Thị giác máy tính (SLR - Computer Vision/PyTorch).
2. **Phương án hợp nhất vào cùng 1 màn hình Kiosk (1024 × 600):**
   - Trên giao diện Next.js, chúng ta chỉ cần tạo một component layout chia 2 phần (hoặc 2 tab linh hoạt):
     - **Cột bên trái:** Vùng hiển thị camera thời gian thực từ luồng SLR của Khoa (kết nối stream qua WebSocket/MJPEG từ `8765`).
     - **Cột bên phải:** Vùng hiển thị lịch sử hội thoại và micro thu âm STT hiện tại.
   - Khi luồng SLR nhận dạng xong cử chỉ (ví dụ: *"Cảm ơn"*), Python gửi một sự kiện (qua WebSocket hoặc POST API cục bộ `/api/conversations/[id]/messages`) để tin nhắn tự động xuất hiện vào cùng khung chat STT!
3. **Kết luận:** Tách riêng lúc phát triển là tối ưu nhất. Khi hoàn thiện, việc ghép 2 luồng chỉ mất vài chục dòng code React gọi API nội bộ!
