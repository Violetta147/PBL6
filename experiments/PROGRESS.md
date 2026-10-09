# Tiến độ thực tế B01–B03 — 10/10/2026

Mục tiêu vẫn là hoàn thành cả ba buổi theo kế hoạch. Mã đã chuẩn bị không đồng nghĩa mọi thí nghiệm đã xong.

| Phần | Bằng chứng hiện có | Phần còn thiếu |
|---|---|---|
| B01 | Whisper-base trên CPU laptop: 10/10 pilot; JSONL, metadata và summary đã lưu | Người thực hiện nghe audio và trình diễn; micro/màn hình chưa xác nhận |
| B02 | 11 test pass; Whisper và Zipformer cùng 100/100 dev; bảng hai model đã lưu | 20 bản ghi dev thật và demo nghe/đối chiếu |
| B03 | Notebook Drive riêng chỉ chạy Qwen GPU, checkpoint ghim revision, dùng lại baseline đã đo | Người thực hiện chạy notebook; bảng ba model, bảng tự thu và nghe 3–5 lỗi |

Gói trên ổ Drive G: `G:/My Drive/Seventh Semester/PBL6/STT_B01_B03/stt_b01_b03_package.zip`, 29.291.600 byte, SHA-256 `e154ef97a09cc332b180cf04f884b2d41faa475b711115c44ab3fecf0316f7f2`. Hash đọc lại bản G khớp local, CRC ZIP đạt. Gói chứa 110 WAV dẫn xuất và mã/notebook; không có WAV hoặc reference test. Notebook riêng đã được chép vào thư mục gốc `STT_B01_B03`; hash bản G khớp nguồn. Đồng bộ cloud được kiểm tra riêng, không suy từ việc chép ổ G.

Baseline pilot là phần train dùng kiểm tra luồng, không phải bảng dev: WER_ws 36,875%, CER 20,3883%, 320 đơn vị reference và 1.133 ký tự. Không dùng điểm pilot để xếp hạng trên dev.

Runtime local không phải Pi/Colab. Kết quả đo trên CPU laptop và các run Colab tương lai cần giữ metadata riêng. Test chưa chạy. Audio tự thu chưa có; template câu gợi ý không phải nhãn đã được kiểm tra.

FLEURS dev100, cùng 2.797 đơn vị reference và 9.702 ký tự: Whisper-base WER_ws 49,3743%, CER 33,9208%; Zipformer ONNX INT8 WER_ws 7,5080%, CER 5,3494%. Cả hai hoàn tất 100/100 trên CPU laptop. Đây là so sánh checkpoint/runtime trên subset nội bộ, không phải điểm XTREME-S chính thức. C1 liệt kê FLEURS trong nguồn huấn luyện, nên không kết luận mức chênh này là khả năng tổng quát trên dữ liệu hoàn toàn mới; cần bảng tự thu riêng.

Theo yêu cầu người thực hiện, Qwen chỉ chạy GPU Colab. Đã dừng tiến trình CPU và kiểm tra không còn worker Qwen CPU. Sáu prediction đã tạo được giữ tại `B03/attempts/cancelled_cpu/`, trạng thái chưa hoàn thành; không tổng hợp thành kết quả dev100. Runner chặn Qwen CPU và chặn `auto` chuyển sang CPU khi không có CUDA. Lỗi thao tác Colab không phải lý do khởi động lại Qwen CPU.

Lần tải Qwen CPU đầu tiên kết thúc lỗi `WinError 1314` khi thư viện Hugging Face tạo symlink; chưa có prediction. Metadata lỗi được giữ trong `B03/attempts`. Đã sửa sang tải `local_dir` bằng tệp thường, giữ revision, và dùng PyTorch mà không import TensorFlow/Flax không cần thiết. Không đổi quyền hoặc cài đặt bảo mật Windows.

Người thực hiện sẽ tự mở và chạy notebook `B03_Qwen_Colab_GPU.ipynb` trên Drive. Kết quả ghi trực tiếp vào `STT_B01_B03/runs/qwen_gpu_...`, không cần tự tải ZIP output. Qwen CPU đã dừng nhưng việc xóa môi trường và checkpoint local bị kiểm duyệt tự động chặn với lý do `blocked by policy`; các tệp lớn vẫn còn trên máy, chưa giải phóng dung lượng. Không ghi nhận việc dọn các thư mục đó là đã hoàn thành.

Đã kiểm tra notebook trên cloud bằng metadata và liệt kê thư mục: [B03_Qwen_Colab_GPU.ipynb](https://drive.google.com/file/d/1MkjzmgwXEQkD-WgvKIR9sSljATfdphnW/view?usp=drivesdk). Gói ZIP và bốn tệp prediction/metadata baseline đều có trên Drive. Đã xóa ba file trùng do đồng bộ và upload: một ZIP, một receipt, một notebook; giữ notebook có MIME Colab và gói đầu vào hiện tại. Bản audio rời trên Drive vẫn còn vì công cụ xóa file không nhận URL thư mục.

Các mục local không cần cho lần chạy GPU, còn chờ xóa thủ công (đường dẫn tương đối từ thư mục PBL6): `data/stt_qwen_venv` (519 MB), `data/models/Qwen3-ASR-0.6B` (1.881 MB), `data/models/huggingface/models--Qwen--Qwen3-ASR-0.6B` (1.881 MB), ba tệp `data/logs/qwen_cpu_*`. Tổng khoảng 4,28 GB; không xóa toàn bộ `data` vì vẫn chứa raw, WAV đã chọn và runtime của hai baseline.
