# Hai câu tự thu ở hai phiên — 13/10/2026

Bốn bản ghi thật, không phải bộ 20 câu hoàn chỉnh. Người thực hiện đã nghe và xác nhận reference; nhãn không được lấy từ prediction. Cả hai phiên dùng Samsung Galaxy M15, ứng dụng ghi âm có sẵn, cách miệng khoảng 30 cm. Điều kiện thực tế và hash audio ở `../../self_recorded_inventory.csv`; manifest cố định ở `../../../manifests/self_dev_pairs4.csv`.

| Phiên | Whisper-base WER_ws | Zipformer WER_ws | Số bản mỗi model |
|---|---:|---:|---:|
| Phòng ngủ, điều hòa phía trên chạy | 11,1111% | 0% | 2/2 |
| Cà phê, tiếng nền do người thực hiện mô tả | 16,6667% | 0% | 2/2 |
| Tổng bốn bản | 13,8889% | 0% | 4/4 |

Whisper ở phòng ngủ nhận “Tòi” thay “Tôi”, “1” thay “một”; ở cà phê nhận “phục đề” thay “phụ đề”, “chặn” thay “chậm” và “hộp” thay “một”. Khác cách viết “1/một” vẫn tính lỗi theo scorer hiện tại. Zipformer khớp cả bốn sau chuẩn hóa chữ hoa/dấu câu. Chưa có Qwen trên bộ này; không dùng output Qwen của FLEURS thay vào. Điểm 0% chỉ áp dụng bốn bản, hai câu đơn giản; không chứng minh model hoàn hảo. Hai phiên là hai lần nói khác nhau, chưa tách riêng tác động tiếng ồn.

`comparison.csv` chứa reference và hai prediction từng bản; `summary.csv` là tổng hợp, `summary_by_session.csv` tách phiên. JSONL và `.run.json` giữ output/config/môi trường thực tế. `verification.json` ghi kiểm tra độc lập bằng JiWER; `conversion_verification.json` ghi việc chuẩn hóa audio. Bản M4A và WAV nằm trong `data/self_recorded/` local và `STT_B01_B03/self_recorded/` trên Drive, không đưa audio vào Git. Không có WAV/reference test trong lần đo này.

Bước tiếp theo: thu câu 03–20 theo template để hoàn thành self dev20, kiểm tra nhãn, rồi chấm ba model trên đúng bộ đó; Qwen chỉ chạy GPU Colab. Hai bản cà phê ở đây được giữ làm đối chiếu thêm, không thay câu 03–20.
