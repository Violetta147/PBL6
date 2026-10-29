# Sơ đồ giao tiếp cập nhật ngày 29/10/2026

## Hành vi và phạm vi đã chốt

- Nhấn Phát chuyển nội dung vùng soạn sang bản dành cho lần phát, đồng thời xóa vùng soạn. Bản phát độc lập với nội dung mới. Dừng phát ngừng bộ phát và audio chờ của lần đó, không xóa bản nháp mới.
- Sơ đồ 03 chứa phần mềm bên trong ranh giới Pi và ngoại vi theo chức năng. Chưa cố định mẫu micro, màn hình hoặc thiết kế điện. ESP32 tách sang sơ đồ 09.
- Sơ đồ 04 đặt các mốc LSTM, SPOTER với pipeline cũ và ablation preprocessing mới trong bối cảnh phát triển. Cả nhánh ký hiệu và lời nói có bước chốt cấu hình trước test. Đây là quy trình, không phải bảng xác nhận hoàn thành.
- Sơ đồ 05b đặt baseline nhóm và pipeline mới của Minh cạnh nhau theo bảy hàng tương ứng. `none` tắt augmentation nhưng vẫn dùng preprocessing mới. Mỗi run có trọng số riêng; vị trí các khối là mức chức năng, không khẳng định mọi phép augmentation có cùng thứ tự lệnh.

## Nguồn đối chiếu

- `C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/SLR/tmp/evidence/VSL400_LSTM_baseline.ipynb.txt`: temporal config, build_input_tensor, mô hình và output test lưu sẵn.
- `C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/SLR/my_read/baseline_provenance/source/repair.py`: nội suy từng chiều feature, gap tối đa 5 theo cấu hình, chính sách biên nearest.
- `C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/SLR/my_read/baseline_provenance/source/resample.py`: nội suy feature float theo đoạn hợp lệ; cờ boolean lấy nearest; bảo toàn khoảng thiếu chưa sửa.
- `C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/SLR/minh_read/TOM_TAT_SPOTER_AUGMENTATION_ERROR_ANALYSIS_CSLR.md`: geometry 49 điểm, preprocessing mới, bốn run và giới hạn diễn giải.
- `C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/SLR/minh_read/SPOTER_Note_v1.md`: SPOTER điều chỉnh dùng cache 64×128 của baseline.
- Các quyết định của người dùng trong chat: flush khi nhấn Phát, ESP32 tách riêng, phần cứng chưa xác định được mô tả theo chức năng.

## Xuất ảnh và kiểm tra

Chạy bằng Python có Pillow, từ thư mục gốc project:

```powershell
python reports/diagrams/test_communication_diagrams.py
python reports/diagrams/export_communication_diagrams.py --output 'C:/Users/LAPTOP T&T/Downloads'
```

Xuất PNG và SVG cho ảnh 02, 03, 04, 05b và 09. Khi đã có file cùng tên, sao lưu trước vào thư mục `diagram-backups-<timestamp>` trong thư mục đích. Các ảnh 01, 05 gốc, 06–08 không nằm trong lần xuất này.

Kiểm tra tự động: text nằm trong khung và canvas; connector không xuyên khối không liên quan; luồng chuyển bản phát và vùng soạn độc lập; nhánh hoàn tất và nhánh dừng phát; ranh giới phần mềm Pi và ESP32 riêng. Mỗi PNG được mở kiểm tra cấu trúc; SVG có cùng nội dung. Kiểm tra trực quan từng ảnh sau render.

Kết quả ngày 29/10/2026: 3 bài kiểm tra đạt; cả 5 PNG xuất thành công và mở kiểm tra cấu trúc. Đã xem trực tiếp từng ảnh để kiểm tra tiếng Việt và bố cục; sửa các đường đi qua khối / chú thích trước lần xuất cuối. Ảnh 02–04 trước khi ghi đè được lưu trong `C:/Users/LAPTOP T&T/Downloads/diagram-backups-20261029-122021`. File `diagrams-validation-20261029.json` tại Downloads ghi tên ảnh, kích thước, nội dung khối và quan hệ.
