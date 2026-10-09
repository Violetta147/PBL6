# Biên bản kiểm tra đặc tả ASR trên Pi 4

Ngày 09/10/2026. Đối tượng là [bản đặc tả mới](SPEC_ASR_PI4_RESEARCH_20261009.md) và phần dẫn đường cập nhật trong [README](README.md). Đây là kiểm tra tài liệu và dữ liệu nguồn phục vụ lập kế hoạch, chưa phải kết quả thực nghiệm ASR.

## Phạm vi nguồn đã rà soát

Đã đọc nội dung của cả chín task được người dùng tham chiếu: Trend 2025-2026; Tìm dataset bổ sung cho PBL6; Concepts; All Stagé; HuggingFace ASR course; Bài tập STT; Machine learning pipelines and Scientific Workflow; labeling; Khởi tạo Git và tạo AGENTS.md. Với `labeling`, đã đọc các trang lịch sử để lấy quy trình nhãn và giới hạn nguồn. Đã đọc thêm các trang chia sẻ Stage 3–5 và bài tập lớp được dẫn từ task, kết hợp tài liệu xuất hiện có trong workspace.

Hai hình Concepts dùng đường dẫn nội bộ không được xác minh riêng. Kiến trúc của đặc tả mới không phụ thuộc hình đó. Thông tin chat được xem là bối cảnh học tập; không tái sử dụng bảng WER hoặc tuyên bố trong chat như số đo của PBL6.

Đã đối chiếu nguồn chính thức của Whisper/whisper.cpp, sherpa-onnx và model card Zipformer, Qwen3-ASR, PhoASR, PhoWhisper, Parakeet tiếng Việt và Parakeet TDT v3; tham khảo công bố Cohere, Whisper-Streaming/SimulStreaming, khóa Audio Hugging Face, JiWER, tài liệu Raspberry Pi và FAQ Colab. Các liên kết được đặt cạnh nội dung tương ứng trong đặc tả. Danh mục corpus ngoài giao thức chính giữ trạng thái khảo sát; không tuyên bố đã xác minh mới toàn bộ giấy phép hoặc nhãn của mọi corpus.

Cấu hình Pi, laptop, Colab Pro/250 credits, Drive 5 TB và home server HDD 1 TB lấy từ thông tin người dùng cung cấp. Chưa kiểm tra tài khoản Colab, quota Drive hoặc đăng nhập thiết bị/server. Không đưa serial Pi vào tài liệu vì không cần cho thí nghiệm.

## Kết quả kiểm tra tài liệu

- Đủ 22 mục chính, năm stage và 35 bước liên tiếp; mỗi bước có cách áp dụng cho inference pretrained hoặc phương án thay thế phù hợp.
- Đủ ba ứng viên chính C0/C1/C2, tiny dự phòng và danh mục mở rộng có giới hạn; phân biệt model, artifact, runtime, precision và môi trường chạy.
- Có sáu thí nghiệm E0–E5, lịch bảy tuần, dev/test, cách khóa cấu hình, tiêu chí dừng và phương án khi runtime/thiết bị không đáp ứng.
- Có giao thức WER_ws/CER tiếng Việt, nhãn rỗng, inference thất bại, coverage, WER toàn luồng, RAM/nhiệt, timestamp và các cấp độ đo hiển thị.
- Có hợp đồng caption để nối với SLR, quy tắc partial/final và UTF-8; phần cải tiến STT là tùy chọn theo yêu cầu mới của giảng viên.
- Các code fence cân bằng; hai khối JSON parse thành công; đoạn Python minh họa parse bằng `ast.parse` thành công. Đây là kiểm tra cú pháp, không xác nhận package/API đã chạy.
- Các liên kết Markdown đến tệp trong kho được kiểm tra tồn tại. Chín liên kết task không trùng ID. Các đường dẫn/cấu trúc script tương lai được đánh dấu là kế hoạch.
- `git diff --check` và kiểm tra nội dung mới không phát hiện lỗi khoảng trắng hoặc ký tự thay thế Unicode. Cảnh báo LF/CRLF của cấu hình Git trên Windows không phải lỗi nội dung.

Không thêm bộ unit test giả cho thay đổi chỉ tài liệu. Các kiểm thử cần có khi triển khai mã đã được quy định ở mục 15 của đặc tả.

## Kiểm tra FLEURS và bảo toàn tài liệu cũ

Đọc lại TSV bằng Python `csv.reader(delimiter='\t')`, giữ nguyên bản nguồn:

| Split | Số bản ghi | Dòng 7 cột | Dòng 6 cột |
|---|---:|---:|---:|
| train | 2.994 | 2.990 | 4 |
| dev | 361 | 361 | 0 |
| test | 857 | 851 | 6 |

Các dòng 6 cột có trường văn bản chứa chuỗi literal `\t`, nên cần parser có quy tắc thay vì bỏ mẫu. Đặc tả cho phép dùng trường transcript nguyên bản thứ ba nhất quán và tự chuẩn hóa để chấm. Chưa viết parser hoặc giải nén audio trong thay đổi này.

SHA-256 của `SPEC_STT_SMART_GLASSES.md` trước và sau thay đổi trùng nhau:

```text
bed8267bdd674754d4ec0dc524c3c4fa4ad7b39075d5b6ad4279e5ca313bfa9b
```

Các bản lưu dataset trên Drive đã được kiểm tra sự hiện diện/kích thước để định hướng sử dụng. Các kiểm tra CRC/hash toàn bộ archive được ghi trong README từ các đợt tải trước; không chạy lại việc đọc hàng chục GB archive ở lần soạn đặc tả này.

## Những gì chưa được thực hiện

Chưa tải checkpoint mới, cài runtime trên Pi/Colab, chạy inference, huấn luyện, thu audio, đo WER/CER, đo hiệu năng Pi hoặc thử màn hình/kính. Các ngưỡng kỹ thuật trong đặc tả là mục tiêu đề xuất; mọi bảng kết quả còn ghi “chưa đo”. Các lệnh Bash và đoạn Python là hướng dẫn khởi đầu cần xác nhận trong môi trường đích.

Thay đổi được giới hạn ở bản đặc tả mới, biên bản này và phần dẫn đường/role FLEURS trong README. Giữ nguyên đặc tả cũ, tài liệu rà soát khái niệm, dữ liệu và các file export chưa được theo dõi. Commit chỉ chứa ba tệp tài liệu của thay đổi; chưa push remote.
