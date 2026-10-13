# Tiến độ thực tế B01–B03 — cập nhật 13/10/2026

Mục tiêu vẫn là hoàn thành cả ba buổi theo kế hoạch. Mã đã chuẩn bị không đồng nghĩa mọi thí nghiệm đã xong.

Cập nhật 13/10: đã nhận bốn M4A thật (hai câu ở phòng ngủ và cùng hai câu ở cà phê), sao lưu bản gốc và chuyển sang WAV mono 16 kHz PCM16. Người thực hiện xác nhận đã nghe nhãn của cả bốn; hai phiên cùng Samsung Galaxy M15, ứng dụng ghi âm có sẵn, khoảng cách xấp xỉ 30 cm. Metadata/điều kiện chi tiết ở `B02/self_recorded_inventory.csv`, manifest ở `manifests/self_dev_pairs4.csv`. Whisper-base và Zipformer đều chạy đủ 4/4 CPU laptop, điểm được kiểm tra lại bằng JiWER: WER_ws lần lượt 13,8889% và 0%; CER 7,8947% và 0%. Output, metadata, bảng từng phiên và kiểm tra tại `B02/results/self_dev_pairs4/`. Qwen chưa chạy bộ bốn này; self dev20 chưa đủ. Bốn bản chỉ gồm hai câu đơn giản đọc hai lần, không đủ kết luận về chất lượng tổng quát hoặc tác động riêng của tiếng ồn. Gói FLEURS đầu vào và các kết quả cũ được giữ nguyên.

| Phần | Bằng chứng hiện có | Phần còn thiếu |
|---|---|---|
| B01 | Whisper-base trên CPU laptop: 10/10 pilot; JSONL, metadata và summary đã lưu | Người thực hiện nghe audio và trình diễn; micro/màn hình chưa xác nhận |
| B02 | 13 test pass; Whisper và Zipformer cùng 100/100 FLEURS dev; đã nhận và chuẩn hóa bốn bản tự thu, nhãn được người thực hiện nghe xác nhận | Câu 03–20 của bộ dev tự thu và bảng đủ 20 câu |
| B03 | Qwen Colab A100 hoàn tất 100/100 dev; bảng ba model được chấm lại độc lập; người thực hiện xác nhận đã nghe và đối chiếu ba câu lỗi | Bảng 20 câu tự thu; hai câu đối chiếu Qwen tốt hơn vẫn chưa xác nhận đã nghe |

Gói trên ổ Drive G: `G:/My Drive/Seventh Semester/PBL6/STT_B01_B03/stt_b01_b03_package.zip`, 29.291.600 byte, SHA-256 `e154ef97a09cc332b180cf04f884b2d41faa475b711115c44ab3fecf0316f7f2`. Hash đọc lại bản G khớp local, CRC ZIP đạt. Gói chứa 110 WAV dẫn xuất và mã/notebook; không có WAV hoặc reference test. Notebook riêng đã được chép vào thư mục gốc `STT_B01_B03`; hash bản G khớp nguồn. Đồng bộ cloud được kiểm tra riêng, không suy từ việc chép ổ G.

Baseline pilot là phần train dùng kiểm tra luồng, không phải bảng dev: WER_ws 36,875%, CER 20,3883%, 320 đơn vị reference và 1.133 ký tự. Không dùng điểm pilot để xếp hạng trên dev.

Whisper/Zipformer được đo trên CPU laptop, Qwen trên GPU Colab; metadata được giữ riêng. Chưa có số đo Pi. Test chưa chạy. Đã có hai câu tự thu ở hai phiên (bốn bản ghi), người thực hiện xác nhận nhãn ngày 13/10; chưa đủ bộ self dev20. Các câu còn lại trong template vẫn chỉ là gợi ý.

FLEURS dev100, cùng 2.797 đơn vị reference và 9.702 ký tự: Whisper-base WER_ws 49,3743%, CER 33,9208%; Zipformer ONNX INT8 WER_ws 7,5080%, CER 5,3494%. Cả hai hoàn tất 100/100 trên CPU laptop. Đây là so sánh checkpoint/runtime trên subset nội bộ, không phải điểm XTREME-S chính thức. C1 liệt kê FLEURS trong nguồn huấn luyện, nên không kết luận mức chênh này là khả năng tổng quát trên dữ liệu hoàn toàn mới; cần bảng tự thu riêng.

Qwen3-ASR-0.6B hoàn tất 100/100 cùng dev trên Colab A100-SXM4-40GB, bfloat16, Transformers: WER_ws 9,7605%, CER 6,2771%. Lần chạy `qwen_gpu_20261010_023946` ngày 10/10/2026 có signature code/scoring/manifest khớp gói đầu vào; hai baseline sao vào lần Colab có hash trùng output local. Chấm lại bằng JiWER khớp; bảng được sinh lại local trùng summary Colab. Prediction và metadata ở `B03/results`, nguồn/hash ở `source.json`, bảng ba model ở `summary.csv` và `comparison.csv`. So theo số lỗi từng câu: Qwen thấp hơn Zipformer ở 18 câu, cao hơn ở 46 và bằng ở 36; đây là thống kê mô tả, chưa kiểm định ý nghĩa thống kê. Dùng [DEMO.md](B03/DEMO.md) để chuẩn bị buổi học. Ngày 10/10/2026, người thực hiện xác nhận đã nghe và đối chiếu ba câu lỗi: 4767212356465567922, 14301804876253465717 và 5380420816515716433. Xác nhận này chỉ áp dụng cho ba mẫu, không phải toàn bộ nhãn dev100. Thời điểm 10/10 chưa có audio tự thu; bốn bản nhận ngày 13/10 được ghi riêng ở đầu tài liệu. Zipformer là ứng viên để thử trên Pi; chưa có bằng chứng phụ đề đạt chất lượng mong muốn. Chưa cần fine-tune trước khi có bảng tự thu và số đo Pi.

Theo yêu cầu người thực hiện, Qwen chỉ chạy GPU Colab. Đã dừng tiến trình CPU và kiểm tra không còn worker Qwen CPU. Sáu prediction đã tạo được giữ tại `B03/attempts/cancelled_cpu/`, trạng thái chưa hoàn thành; không tổng hợp thành kết quả dev100. Runner chặn Qwen CPU và chặn `auto` chuyển sang CPU khi không có CUDA. Lỗi thao tác Colab không phải lý do khởi động lại Qwen CPU.

Lần tải Qwen CPU đầu tiên kết thúc lỗi `WinError 1314` khi thư viện Hugging Face tạo symlink; chưa có prediction. Metadata lỗi được giữ trong `B03/attempts`. Đã sửa sang tải `local_dir` bằng tệp thường, giữ revision, và dùng PyTorch mà không import TensorFlow/Flax không cần thiết. Không đổi quyền hoặc cài đặt bảo mật Windows.

Người thực hiện đã chạy notebook `B03_Qwen_Colab_GPU.ipynb` trên Drive. Kết quả ghi trực tiếp vào `STT_B01_B03/runs/qwen_gpu_20261010_023946`, không cần tự tải ZIP output. Output cần thiết đã lưu; có thể ngắt runtime A100 sau khi xem/nghe các ô demo. Qwen CPU đã dừng nhưng việc xóa môi trường và checkpoint local bị kiểm duyệt tự động chặn với lý do `blocked by policy`; các tệp lớn vẫn còn trên máy, chưa giải phóng dung lượng. Không ghi nhận việc dọn các thư mục đó là đã hoàn thành.

Đã kiểm tra notebook trên cloud bằng metadata và liệt kê thư mục: [B03_Qwen_Colab_GPU.ipynb](https://drive.google.com/file/d/1MkjzmgwXEQkD-WgvKIR9sSljATfdphnW/view?usp=drivesdk). Gói ZIP và bốn tệp prediction/metadata baseline đều có trên Drive. Đã xóa ba file trùng do đồng bộ và upload: một ZIP, một receipt, một notebook; giữ notebook có MIME Colab và gói đầu vào hiện tại. Bản audio rời trên Drive vẫn còn vì công cụ xóa file không nhận URL thư mục.

Các mục local không cần cho lần chạy GPU, còn chờ xóa thủ công (đường dẫn tương đối từ thư mục PBL6): `data/stt_qwen_venv` (519 MB), `data/models/Qwen3-ASR-0.6B` (1.881 MB), `data/models/huggingface/models--Qwen--Qwen3-ASR-0.6B` (1.881 MB), ba tệp `data/logs/qwen_cpu_*`. Tổng khoảng 4,28 GB; không xóa toàn bộ `data` vì vẫn chứa raw, WAV đã chọn và runtime của hai baseline.
