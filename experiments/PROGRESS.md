# Tiến độ thực tế B01–B03 — 10/10/2026

Mục tiêu vẫn là hoàn thành cả ba buổi theo kế hoạch. Mã đã chuẩn bị không đồng nghĩa mọi thí nghiệm đã xong.

| Phần | Bằng chứng hiện có | Phần còn thiếu |
|---|---|---|
| B01 | Whisper-base trên CPU laptop: 10/10 pilot; JSONL, metadata và summary đã lưu | Người thực hiện nghe audio và trình diễn; micro/màn hình chưa xác nhận |
| B02 | Scorer 8 test pass; Whisper và Zipformer cùng 100/100 dev; bảng hai model đã lưu | 20 bản ghi dev thật và demo nghe/đối chiếu |
| B03 | Notebook và runner Qwen3-ASR-0.6B Transformers, checkpoint ghim revision | Chạy Qwen GPU, bảng ba model, bảng tự thu và nghe 3–5 lỗi |

Gói trên Drive: `G:/My Drive/Seventh Semester/PBL6/STT_B01_B03/stt_b01_b03_package.zip`, 29.279.189 byte, SHA-256 `553bc7ab73c1bdb0b113ee06685b3dbc1043834e0a1fbca4fca1373ede729964`. Hash đọc lại bản G khớp local, CRC ZIP đạt. Gói chứa 110 WAV dẫn xuất và mã/notebook; không có WAV hoặc reference test.

Baseline pilot là phần train dùng kiểm tra luồng, không phải bảng dev: WER_ws 36,875%, CER 20,3883%, 320 đơn vị reference và 1.133 ký tự. Không dùng điểm pilot để xếp hạng trên dev.

Runtime local không phải Pi/Colab. Kết quả đo trên CPU laptop và các run Colab tương lai cần giữ metadata riêng. Test chưa chạy. Audio tự thu chưa có; template câu gợi ý không phải nhãn đã được kiểm tra.

FLEURS dev100, cùng 2.797 đơn vị reference và 9.702 ký tự: Whisper-base WER_ws 49,3743%, CER 33,9208%; Zipformer ONNX INT8 WER_ws 7,5080%, CER 5,3494%. Cả hai hoàn tất 100/100 trên CPU laptop. Đây là so sánh checkpoint/runtime trên subset nội bộ, không phải điểm XTREME-S chính thức. C1 liệt kê FLEURS trong nguồn huấn luyện, nên không kết luận mức chênh này là khả năng tổng quát trên dữ liệu hoàn toàn mới; cần bảng tự thu riêng.

Qwen sẽ thử CPU laptop nếu Computer Use không thao tác Colab được. Đây là thay đổi nơi chạy để tiếp tục thí nghiệm chất lượng, không phải số đo GPU/Pi. Notebook GPU vẫn giữ để chạy lại khi Colab sử dụng được.
