# Kế hoạch đánh giá cải tiến nhận dạng trên VSL400 và kiosk

## Phạm vi đã xác minh

VSL400 công bố 74.259 clip ký hiệu đơn từ 28 người ký, quay đồng thời ở ba góc. Metadata mô tả mỗi clip bằng một mã ký hiệu và người ký. Các clip góc trước trong split của PBL6 hỗ trợ đo khả năng phân loại một ký hiệu đã được cắt của người ký chưa gặp khi huấn luyện. Metadata và split hiện có thiếu chuỗi ký hiệu tự nhiên có nhãn theo thứ tự, khoảng chuyển tiếp và lượt không ký để chấm đầu cuối kiosk. [Mô tả dữ liệu VSL400 gốc](https://zenodo.org/records/17943574)

| Split dự án | Clip góc trước | Người ký | Số lớp |
| --- | ---: | ---: | ---: |
| Train | 17.326 | 18 | 400 |
| Validation | 3.712 | 4 | 400 |
| Test | 3.714 | 4 | 400 |

Manifest cục bộ có 24.752 mã clip duy nhất. Ba split không trùng người ký. Cả 24.752 dòng ghi FPS là 25. Đối chiếu mã SHA-256 của cả ba CSV chia tập với cấu hình train và báo cáo test. Toàn bộ bộ ba mã clip, người ký và nhãn của test khớp giữa manifest, bảng kiểm tra đầu vào và bảng dự đoán. Checkpoint kiosk khớp mã băm của checkpoint dùng trong báo cáo test. [Cấu hình gốc](../deployment/slgcn_smoke/training_config.json) · [Báo cáo train và validation](../deployment/slgcn_feature_trial/reference/training_result.json) · [Báo cáo test gốc](../deployment/slgcn_feature_trial/reference/test_metrics.json)

SL-GCN bone 2D chọn epoch 52 bằng validation (**90,517% Top-1**). Chấm lại bảng dự đoán lưu sẵn cho test được **3.325/3.714 đúng Top-1 (89,526%)**, **3.581/3.714 đúng Top-5 (96,419%)** và **Macro-F1 90,374%**. Đây là đối soát kết quả đã lưu. Đã chạy kiểm tra mã băm bundle và đối chiếu đúng hai mẫu đầu vào tham chiếu của train. [Lệnh và dữ liệu tham chiếu](../deployment/slgcn_feature_trial/README.md)

## Một hướng cải tiến ưu tiên

**Huấn luyện SL-GCN chịu thay đổi nhịp ký.** Trên train, tạo biến thể nhanh/chậm nhẹ của cùng đoạn bằng lấy mẫu theo thời gian trên đặc trưng sẵn có, giữ nhãn và đồng bộ cờ chất lượng với từng khung được chọn. Giữ cách sửa mất điểm và giới hạn của adapter. Dùng cùng kiến trúc, split và quy trình train để đo riêng tác động của thay đổi này. Chốt một lịch tăng cường trên train trước khi đối chiếu validation. Những đoạn webcam đủ pha mở tay vẫn có thể đổi nhãn khi mật độ khung thay đổi. Train hiện dùng dữ liệu ghi 25 FPS trong khi webcam đã có lượt khoảng 7,45, 15 và 30 FPS. Dữ liệu này đưa ra giả thuyết rằng mô hình nhạy với nhịp đầu vào. [Chẩn đoán webcam](02_TEMPORAL_SEGMENTATION_AND_TRIMMING_PLAN.md#818-thử-offline-mật-độ-khung-trên-110546-16112026)

1. **Chọn trên train/validation.** So checkpoint gốc với đúng một ứng viên. Chọn epoch bằng validation. Chấm theo cặp trên cùng 3.712 clip ở nhịp gốc và trên một bản đối chứng nhịp khác được định trước từ chính validation. Bản đối chứng đo nhạy với lấy mẫu, còn webcam đo ảnh hưởng của phiên quay thực. Báo Top-1 và Macro-F1. Mốc sàng lọc đề xuất cần chốt trước khi chạy: Top-1 ở đối chứng nhịp khác tăng ít nhất 1 điểm phần trăm và Top-1 ở nhịp gốc không giảm. Nếu hụt mốc, dừng ứng viên mà chưa chấm test.
2. **Khóa ứng viên rồi so test một lần.** Cùng 3.714 mã clip, thứ tự nhãn và điều kiện đầu vào gốc. Ghi Top-1, Top-5, Macro-F1, số clip sửa đúng, số clip đổi từ đúng sang sai và kết quả theo bốn người ký. Nếu Top-1 hoặc Macro-F1 giảm, dừng ứng viên theo mốc đề xuất. Khi hai số bằng gốc, báo giữ chất lượng VSL400. Chỉ báo tăng accuracy trên test VSL400 khi có chênh lệch đo được. Giữ test ngoài việc chọn lịch tăng cường, epoch hoặc cách suy luận.
3. **Chấm đầu cuối kiosk trên tập mới.** Cố định ứng viên và bộ tách trước khi quay hoặc xem đầu ra. Ghi thứ tự và nhãn không ký trước. Chạy hai cấu hình trên cùng clip. Báo số chuỗi đúng đủ và đúng thứ tự, cùng số lượt không ký bị nhận nhầm. Mốc đã duyệt là **ít nhất 9/10 chuỗi mới đúng** và **0/5 lượt không ký bị cho qua**. Hai chuỗi sai hoặc một lượt không ký bị cho qua đã đủ để xác định cấu hình cố định hụt mốc. Chỉ báo `[ĐÃ ĐẠT TIÊU CHÍ]` khi đạt cả hai trên tập đánh giá. Tập quay cũ tiếp tục dùng để phân tích lỗi, gồm cả các ca sửa được bằng cắt tay hoặc lấy khung chẵn/lẻ.

Nếu đánh giá riêng bộ tách, giữ cùng bộ phân loại ở hai cấu hình. Dùng chuỗi ghép từ clip ký hiệu đơn để kiểm tra cắt, thứ tự và khả năng chịu khoảng nghỉ có chủ đích. Báo đó là benchmark ghép riêng vì khoảng nối do người thử tạo và không mô tả chuyển động nối tự nhiên. Báo cáo ghép cũ có 4/4 đoạn tìm được nhưng chỉ 3/4 nhãn đúng với bộ tách mặc định. Số đoạn tìm được và số chuỗi nhận đúng là hai phép đo khác nhau. [Báo cáo mô phỏng ghép chuỗi](../outputs/segmentation_experiments/EXPERIMENT_REPORT.md)

## Đầu vào, đầu ra và phạm vi thực hiện

- Đầu vào là split đã khóa, đặc trưng train/validation hiện có, checkpoint đối chứng và bảng dự đoán test đã lưu. Chỉ truy cập đặc trưng và chạy huấn luyện sau khi được duyệt. Tập webcam đánh giá mới cần thu sau khi đã chốt cấu hình. Các lượt không ký cần có cả yên và có chuyển động thông thường.
- Lưu script và cấu hình thử mới dưới `diagnostics/`, lưu manifest và kết quả thử ở `outputs/`. Giữ `deployment/`, dữ liệu gốc và trọng số hiện hành. Lưu seed, mã băm split, cấu hình, checkpoint ứng viên, phiên bản phần mềm, bảng dự đoán và các mẫu bị lỗi. Đối chiếu mọi video theo định danh trước khi tính chênh lệch.
- Kiểm tra đã chạy từ `slr-app/MVP/deployment/slgcn_feature_trial/` bằng môi trường `pbl6_slr`: `python -B -c "from prepare_clip import verify_bundle; verify_bundle()"` và `python -B verify_reference.py`. Kiểm tra cú pháp bằng `python -m py_compile` khi có script mới. Nghiệm thu đường kiosk với `python -u desktop_mvp/test_demo_server.py` khi đến bước tích hợp đã duyệt.
