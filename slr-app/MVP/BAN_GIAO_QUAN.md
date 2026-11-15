# Bàn giao MVP cho Quân

## Việc làm trước

Mở demo bằng clip mẫu để kiểm tra môi trường. Sau đó chỉnh giao diện và luồng thao tác cho màn 7 inch (1024 × 600). Khoa phụ trách đo màn hình và vẽ vỏ.

## Chạy trên Windows

Mở PowerShell tại thư mục MVP vừa giải nén. Dùng Python 3.11 64-bit. Nếu máy chưa có môi trường riêng, chạy ba lệnh này:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "numpy==2.4.6" "opencv-contrib-python==4.11.0.86" "mediapipe==0.10.14"
.\.venv\Scripts\python.exe -m pip install "torch==2.7.0+cpu" --index-url https://download.pytorch.org/whl/cpu
```

Thử trên clip mẫu, không cần webcam:

```powershell
.\.venv\Scripts\python.exe -X utf8 desktop_mvp/demo.py --clip local_data/014159.mp4
```

Chờ **Sẵn sàng** → bấm **Bắt đầu** → kết quả mong đợi **Dài** → bấm **Xác nhận & phát** để nghe. Để quay bằng webcam, dừng bằng Ctrl+C rồi chạy:

```powershell
.\.venv\Scripts\python.exe -X utf8 desktop_mvp/demo.py --camera 1
```

Nếu mở nhầm webcam, thử đổi chỉ số. Trong trang, **R** bắt đầu/thử lại, **F** xác nhận/phát. Webcam đếm ngược 3 giây rồi quay khoảng 4 giây và tự dừng.

## Sửa ở đâu

| Tệp / thư mục | Vai trò |
| --- | --- |
| `desktop_mvp/demo.html` | Giao diện, nút bấm, phím tắt và phát tiếng. Bắt đầu chỉnh ở đây. |
| `desktop_mvp/demo.py` | Điều phối webcam, các trạng thái và trả kết quả cho giao diện. |
| `desktop_mvp/check_clip.py` | Chạy MediaPipe → chuẩn bị đầu vào → SL-GCN. |
| `deployment/` | Mô hình, mã tiền xử lý, bảng nhãn và dữ liệu đối chứng. Các tệp được kiểm tra hash khi khởi động. |

## Khi gửi lại cho Khoa

- Kiểm tra toàn màn hình 1024 × 600, chữ đọc được và nút bấm nằm trong khung. Người ký thao tác được từ vị trí ký bằng R/F.
- Thử hai lượt liên tiếp. Chỉ phát tiếng sau xác nhận, bấm **Thử lại** phải bỏ kết quả cũ.
- MVP nhận một ký hiệu mỗi lượt. MP3 tiếng Việt có sẵn cho **Dài, Cảm ơn, Nước, Xin lỗi**. Các nhãn này có âm thanh sẵn, còn kết quả nhận dạng từ webcam cần kiểm tra từng nhãn.
- Gửi lại danh sách tệp đã sửa, ảnh giao diện và kết quả thử. Clip tự quay và log được tạo trên máy chạy demo.
