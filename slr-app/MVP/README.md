# PBL6 MVP

Prototype nhận dạng một ký hiệu từ video bằng SL-GCN trên CPU. Chạy các lệnh ở thư mục dự án bằng Python 3.11.

    py -3.11 -X utf8 desktop_mvp/check_clip.py local_data/014159.mp4 --expected "Dài" --expected-frames 59
    py -3.11 desktop_mvp/record_webcam.py

Bấm R trong cửa sổ xem trước để đếm ngược và quay 4 giây. Q để thoát. Nếu mở nhầm webcam, thử thêm --camera 1. Kết quả nhận dạng lưu dưới outputs/desktop_clip_checks. Lượt tự quay ghi nhãn dự kiến, cần xác nhận động tác trước khi tính độ chính xác.

Môi trường đã kiểm tra trên Windows: Python 3.11.9, NumPy 2.4.6, OpenCV 4.11.0, MediaPipe 0.10.14 và PyTorch 2.7.0+cpu.

## Demo trên laptop

Cắm Aioneus, đóng ứng dụng đang giữ webcam rồi chạy từ PowerShell:

    py -3.11 -X utf8 desktop_mvp/demo.py --camera 1

Trình duyệt mở tại http://127.0.0.1:8765. Chờ trạng thái Sẵn sàng, giữ vai và hai tay trong khung, bấm Bắt đầu và thực hiện một ký hiệu sau khi đếm ngược. Mỗi lần quay khoảng 4 giây. Nhấn R để bắt đầu hoặc thử lại, F để xác nhận và phát. Bạn cũng có thể dùng các nút trên màn hình. Ctrl+C trong PowerShell để dừng. Nếu xem trước mở nhầm camera, khởi động lại với chỉ số camera phù hợp.

Để thử với clip đã có, dùng `--clip local_data/014159.mp4` thay cho `--camera 1`. Video webcam lưu ở `local_data`, báo cáo của ứng dụng lưu ở `outputs/desktop_demo`.

Âm thanh tiếng Việt cho Dài, Cảm ơn, Nước và Xin lỗi nằm trong local_data/tts, theo mã nhãn của checkpoint. Đây là tệp MP3 tạo sẵn bằng Microsoft Edge TTS (vi-VN-HoaiMyNeural). Ứng dụng phát tệp cục bộ tương ứng với kết quả sau khi người dùng xác nhận. Với nhãn khác, trình duyệt dùng giọng tiếng Việt cục bộ nếu có.

## Tệp nhận qua kênh chia sẻ của nhóm

- local_data/014159.mp4 — clip VSL400 59 khung hình, nhãn Dài.
- deployment/slgcn_smoke/gcnCkpt.pt — checkpoint SL-GCN epoch 52.
- deployment/slgcn_feature_trial/reference/ — tệp cấu hình và dữ liệu đối chứng đúng theo bundle_manifest.json.
- deployment/handoff_assets/label_map_v1.json — bảng 400 nhãn.

Chia sẻ các tệp theo quyền sử dụng dataset và trọng số. Giữ byte gốc của các tệp dưới deployment để SHA-256 khớp.


