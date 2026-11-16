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

**Thử đưa đầu vào về nhịp 25 FPS với checkpoint hiện có.** Ưu tiên phép thử này trước huấn luyện. Train VSL400 ghi 25 FPS. Ở webcam, một đoạn đủ pha mở tay vẫn đổi nhãn khi mật độ khung đổi. Dùng một quy tắc chọn khung theo thời gian, với đích 25 FPS lấy từ manifest train và giữ biên đoạn. Mỗi mốc chọn khung nguồn gần nhất, giữ nguyên tọa độ và cờ chất lượng của khung đó. Với đầu vào VSL400 vốn 25 FPS, đi thẳng qua cấu hình gốc. Bước thử đầu giới hạn ở nguồn nhanh hơn 25 FPS, vì nguồn chậm cần một giả thuyết riêng về dữ liệu thiếu. Dùng FPS thu đo được khi AVI ghi tốc độ danh định khác tốc độ thực. [Chẩn đoán webcam](02_TEMPORAL_SEGMENTATION_AND_TRIMMING_PLAN.md#818-thử-offline-mật-độ-khung-trên-110546-16112026)

1. **Chốt từ train, kiểm tra trên validation.** Xác minh quy tắc 25 FPS để nguyên tensor ở nhịp gốc. So đối chứng và ứng viên theo cặp trên bản mô phỏng nguồn nhanh hơn 25 FPS của validation đã chốt trước, cùng một checkpoint. Báo Top-1 và Macro-F1 riêng cho nhịp gốc và bản mô phỏng. Mốc sàng lọc đề xuất là tăng ít nhất 1 điểm phần trăm Top-1 ở bản mô phỏng, cùng đầu vào và kết quả ở nhịp gốc. Hụt mốc thì dừng ứng viên trước khi mở test. Các clip webcam cũ có thể dùng để kiểm tra kỹ thuật và tìm lỗi.
2. **Khóa ứng viên rồi so test một lần.** Dùng cùng 3.714 mã clip, thứ tự nhãn và dữ liệu 25 FPS gốc. Kiểm tra nhánh đi thẳng và đối chiếu Top-1, Top-5, Macro-F1, số clip sửa đúng, số clip đổi từ đúng sang sai và kết quả theo người ký. Nhánh này dự kiến giữ nguyên dự đoán trên VSL400 gốc. Chênh lệch cần điều tra trước khi sang kiosk. Bước test ở đây kiểm tra không suy giảm trên VSL400 gốc. Giữ test ngoài việc chọn phương pháp lấy mẫu hoặc tốc độ đích.
3. **Chấm đầu cuối kiosk trên tập mới.** Cố định ứng viên và bộ tách trước khi quay hoặc xem đầu ra. Ghi thứ tự và nhãn không ký trước. Chạy hai cấu hình trên cùng clip. Báo số chuỗi đúng đủ và đúng thứ tự, cùng số lượt không ký bị nhận nhầm. Mốc đã duyệt là **ít nhất 9/10 chuỗi mới đúng** và **0/5 lượt không ký bị cho qua**. Hai chuỗi sai hoặc một lượt không ký bị cho qua đã đủ để xác định cấu hình cố định hụt mốc. Chỉ báo `[ĐÃ ĐẠT TIÊU CHÍ]` khi đạt cả hai trên tập đánh giá. Tập quay cũ tiếp tục dùng để phân tích lỗi, gồm cả các ca sửa được bằng cắt tay hoặc lấy khung chẵn/lẻ.

Nếu đánh giá riêng bộ tách, giữ cùng bộ phân loại ở hai cấu hình. Dùng chuỗi ghép từ clip ký hiệu đơn để kiểm tra cắt, thứ tự và khả năng chịu khoảng nghỉ có chủ đích. Báo đó là benchmark ghép riêng vì khoảng nối do người thử tạo và không mô tả chuyển động nối tự nhiên. Báo cáo ghép cũ có 4/4 đoạn tìm được nhưng chỉ 3/4 nhãn đúng với bộ tách mặc định. Số đoạn tìm được và số chuỗi nhận đúng là hai phép đo khác nhau. [Báo cáo mô phỏng ghép chuỗi](../outputs/segmentation_experiments/EXPERIMENT_REPORT.md)

## Đầu vào, đầu ra và phạm vi thực hiện

- Đầu vào là split đã khóa, đặc trưng validation hiện có, checkpoint đối chứng và bảng dự đoán test đã lưu. Thử thay đổi đầu vào SL-GCN sau khi được duyệt. Có thể chạy suy luận cục bộ trên CPU. Nếu cache validation chỉ có trên Drive, cần nhận bản sao được phép dùng hoặc chạy đối chứng trong notebook có quyền truy cập. Tập webcam đánh giá mới cần thu sau khi đã chốt cấu hình. Các lượt không ký cần có cả yên và có chuyển động thông thường.
- Lưu script và cấu hình thử mới dưới `diagnostics/`, lưu manifest và kết quả thử ở `outputs/`. Giữ `deployment/`, dữ liệu gốc và trọng số hiện hành. Lưu mã băm split, cấu hình, mã băm checkpoint, phiên bản phần mềm, bảng dự đoán và các mẫu bị lỗi. Đối chiếu mọi video theo định danh trước khi tính chênh lệch.
- Kiểm tra đã chạy từ `slr-app/MVP/deployment/slgcn_feature_trial/` bằng môi trường `pbl6_slr`: `python -B -c "from prepare_clip import verify_bundle; verify_bundle()"` và `python -B verify_reference.py`. Kiểm tra cú pháp bằng `python -m py_compile` khi có script mới. Nghiệm thu đường kiosk với `python -u desktop_mvp/test_demo_server.py` khi đến bước tích hợp đã duyệt.

Huấn luyện với biến thể nhịp nhanh/chậm trên train là phương án dự phòng. Cân nhắc sau khi biết kết quả suy luận với checkpoint hiện tại. Nếu chọn hướng đó, xin duyệt riêng và áp dụng quy trình chọn trên train/validation, khóa ứng viên rồi so một lần trên test gốc. GPU A100 có thể dùng ở bước huấn luyện nếu được chọn.

## Kết quả thử offline lấy mẫu 25 FPS (16/11/2026)

Thử trên ba clip webcam đã phân tích từ phiên 11 giờ. Nhãn xác nhận của cả ba là **Khăn quàng cổ → Cảm ơn**. Giữ sáu đoạn kiosk đã lưu và checkpoint gốc. Chạy trích xuất một lần mỗi clip và tái lập đủ thứ tự Top-5 của cả sáu đoạn trước khi so sánh. Ước lượng thời gian của khung nguồn bằng FPS trung bình đo lúc thu (29,55–29,79 FPS). Đặt mốc 25 FPS từ đầu từng đoạn đến thời điểm khung nguồn cuối và chọn khung nguồn gần nhất với mỗi mốc. Khi khoảng cách bằng nhau, chọn khung đến sau.

| Clip | Giữ mọi khung | Lấy mẫu về 25 FPS |
| --- | --- | --- |
| `110216` | Khăn quàng cổ → Chạy | Khăn quàng cổ → Chạy |
| `110403` | Không nghe lời → Tháng mười một | Không nghe lời → Nói chuyện |
| `110546` | Khăn quàng cổ → Tháng | Khăn quàng cổ → Quả chuối |
| Đúng cả chuỗi | 0/3 | 0/3 |
| Đúng theo vị trí | 2/6 | 2/6 |

Hai mẫu train tham chiếu ở 25 FPS cho tensor và Top-5 giống hệt đối chứng. Kiểm tra cú pháp, mã băm bundle và đối chiếu tham chiếu đều đạt. Luồng nhận dạng gốc nhận đúng **Dài** trên clip `014159.mp4` (59 khung). [Script](../diagnostics/compare_temporal_sampling.py) · [Báo cáo A/B](../outputs/temporal_sampling_25fps/20261116T051658_953363Z/report.json)

**Quyết định sau phép thử:** hạ ưu tiên ứng viên 25 FPS. Với các đoạn này, thay đổi nhịp chưa sửa được nhãn nào. Riêng đoạn `110216` vẫn thiếu 53/55 khung trong pha giữ lòng bàn tay theo đối chiếu biên trước đó. Chưa chạy validation thay đổi nhịp, test VSL400 hay đánh giá kiosk mới. Chưa tìm thấy đặc trưng gốc của validation trong hai thư mục cục bộ đã rà (MVP và bản sao báo cáo VSL400). Chưa cần chạy notebook hoặc dùng GPU A100 cho kết quả này.
