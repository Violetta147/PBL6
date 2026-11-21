# PBL6 — nghiên cứu STT tiếng Việt cho kính thông minh

> **[BÀN GIAO MỚI NHẤT CHO ĐỒNG ĐỘI & AI AGENT — ĐỌC TẠI ĐÂY NẾU BẠN MỚI PULL VỀ LÀM TIẾP]:** Xem [HANDOFF_TEAMMATE_M2_PI.md](HANDOFF_TEAMMATE_M2_PI.md) để nắm toàn bộ kiến trúc M2.2 + nhánh tối ưu realtime **`perf/streaming-onnx`** (SL-GCN ONNX `0.74s` trên Pi + Streaming Extraction 1 luồng `0.49s–0.77s` + 3 điểm cần tinh chỉnh tiếp), cách cài môi trường, kết nối **SSH / TightVNC (`:5900`)** vào **Raspberry Pi 4B**, chạy **Vision Backend (`:8767`)** và đồng bộ code bằng `-FastSync`. Kiến trúc & các quyết định đã chốt (`1A, 2A, 3A, 4A, 5B`) nằm tại [docs/PBL6_DECISION_AND_ARCHITECTURE.md](docs/PBL6_DECISION_AND_ARCHITECTURE.md).

> Giữ dự án STT tại thư mục C hiện tại. Hạn hoàn thành là thứ Năm 05/11/2026. Dùng [kế hoạch hiện tại](STT_PLAN_1_WEEK.md), [đặc tả Settings/phụ đề/IoT](STT_SYSTEM_SPEC.md), [bàn giao năm ca nối tiếp](STT_SHIFT_HANDOFF.md), [BOM tổng thể](STT_BOM.md) và [kiểm kê bằng chứng](experiments/inventory_20261102/README.md). Các tài liệu cũ bên dưới giữ vai trò lịch sử và tra cứu; không tự động là phạm vi hiện tại.

## Tài liệu định hướng hiện tại

[Thực hành buổi 1–3](experiments/README.md) chứa mã dùng chung, ba notebook và manifest chọn mẫu. Xem output/run metadata để phân biệt mã đã chuẩn bị với model đã chạy; dữ liệu tự thu cần bản ghi thật và nhãn đã nghe kiểm tra.

[Kế hoạch lean: 7 tuần, 7 buổi demo](PLAN_DEMO_STT_7_BUOI.md) là nơi bắt đầu: chạy baseline → học cách chấm và so ba model → đo Pi → thử micro → báo cáo kết quả. Mỗi tuần một buổi gặp thầy, với công việc vừa đủ để học và demo.

[Đặc tả lean ASR trên Pi 4, phiên bản 2.0](SPEC_ASR_PI4_RESEARCH_20261009.md) tập trung vào Whisper-base, Zipformer-30M và Qwen3-ASR-0.6B; WER/CER, tốc độ/RAM và demo thu âm → chữ. Dùng model có sẵn, baseline đủ tốt thì giữ. Một notebook, script/CLI Pi khi cần và báo cáo ngắn là đủ; tích hợp kính và phần mở rộng làm sau nếu sẵn sàng.

[Ghi chú khái niệm](REVIEW_CONCEPTS_20261009.md) là tài liệu tra ngắn khi thực hành. [Trang đặc tả cũ](SPEC_STT_SMART_GLASSES.md) dẫn về phạm vi hiện hành; các bản chi tiết trước đây còn trong Git. [Kiểm tra bộ tài liệu](VALIDATION_SPEC_ASR_PI4_20261009.md) phân biệt kế hoạch với kết quả đã đo. Không bắt buộc làm đủ 35 bước ML hoặc tự huấn luyện STT.

Các mục dưới đây giữ nguồn, phiên bản và cách khôi phục dataset đã lưu. Đây là kho tham khảo, không phải danh sách corpus cần dùng hết. Phần lean chỉ cần subset FLEURS và bộ tự thu nhỏ.

## FLEURS `vi_vn`

Bộ dữ liệu FLEURS `vi_vn` được tải từ [google/fleurs](https://huggingface.co/datasets/google/fleurs) vào `data/raw/fleurs/vi_vn/`. Đây là bản gốc gồm `train.tsv`, `dev.tsv`, `test.tsv` và ba tệp `audio/{train,dev,test}.tar.gz`; chưa giải nén hoặc biến đổi âm thanh. Thư mục `data/` được Git bỏ qua để không đưa dữ liệu vào commit.

- Phiên bản nguồn: commit `70bb2e84b976b7e960aa89f1c648e09c59f894dd` của kho Hugging Face, tải ngày 25/09/2026.
- Giấy phép: [CC BY 4.0](https://huggingface.co/datasets/google/fleurs) theo dataset card. Khi sử dụng, ghi nguồn và trích dẫn bài báo FLEURS theo dataset card.
- Split gốc: `train` 2.994 dòng, `dev` 361 dòng, `test` 857 dòng. Trong thư viện Hugging Face, `dev` tương ứng `validation`.
- Metadata TSV gốc có 10 dòng chỉ gồm 6 cột thay vì 7 (`train`: 4, `test`: 6); giữ nguyên bản nguồn. Khi viết bộ đọc dữ liệu, kiểm tra độ rộng từng dòng trước khi gán tên cột.
- Vai trò theo [đặc tả lean](SPEC_ASR_PI4_RESEARCH_20261009.md): chọn cố định 100 mẫu dev và 200 mẫu test, bổ sung 20 câu tự thu dev và 30–50 câu test. Báo đúng subset đã chạy; giữ test ngoài quá trình chọn cấu hình. Một số checkpoint có thể đã dùng FLEURS khi huấn luyện, nên không mặc định benchmark này hoàn toàn chưa được model thấy.

Các tệp âm thanh nén có SHA-256 chính thức (LFS OID của kho nguồn):

| Tệp | Byte | SHA-256 |
|---|---:|---|
| `audio/train.tar.gz` | 1.607.278.457 | `016a568afc1909cfaf9efb1a2fc2f1d3311e646d9b52d05dc2e84ac0c17c34ce` |
| `audio/dev.tar.gz` | 214.500.592 | `8821a394c99069409b3ce7bb5cd14b10b709f2ee2fea16f42b4701e1cc9ef673` |
| `audio/test.tar.gz` | 544.139.865 | `b359261216ef14b8eea159abce794e270c2a0be903218cf1e1e8f7c7c1565b5c` |

Git blob SHA-1 của TSV trên kho nguồn, đã đối chiếu bằng `git hash-object`: `train.tsv` `f88141e2bc80f1942d5939819da120264f7eeed6`, `dev.tsv` `f2f5a9207bb010193e298b302495ed76e3ce5782`, `test.tsv` `5e6d9d0bb2252181c78080eb80d5c0af09b5c42f`.

Để tải lại một tệp, dùng URL dạng `https://huggingface.co/datasets/google/fleurs/resolve/70bb2e84b976b7e960aa89f1c648e09c59f894dd/data/vi_vn/<tên-tệp>?download=true`. Cấu trúc và tên tệp trong `data/raw/fleurs/vi_vn/` trùng đường dẫn `data/vi_vn/` trên nguồn. Kiểm tra SHA-256 bằng `Get-FileHash data/raw/fleurs/vi_vn/audio/test.tar.gz -Algorithm SHA256` (đổi tên tệp cho các split khác). Có thể đọc trực tiếp TSV và kho tar.gz; chỉ giải nén split cần dùng để tiết kiệm dung lượng.

Bản lưu trên Google Drive nằm tại `G:\My Drive\Seventh Semester\PBL6\dataset\FLEURS_vi_vn_70bb2e84.zip` (2.368.837.561 byte, SHA-256 `405d169c0fe07b97168a5a6b08987946aa682955bd998987ee2900be21c92496`). ZIP có sáu tệp nguồn giữ nguyên cấu trúc dưới `FLEURS_vi_vn/`, cùng `SOURCE_INFO.txt` và `SOURCE_SHA256SUMS.txt`; toàn bộ tám entry đã được đọc lại để kiểm tra CRC và kích thước. Checksum của ZIP cũng được lưu cạnh archive trong `FLEURS_vi_vn_70bb2e84.zip.sha256.txt`.

## ViMD

Toàn bộ [ViMD Dataset](https://huggingface.co/datasets/nguyendv02/ViMD_Dataset) được tải vào `D:\PBL6\dataset\ViMD_Dataset` và đóng gói để lưu tại `G:\My Drive\Seventh Semester\PBL6\dataset\ViMD_Dataset_3a5b301`. Dữ liệu gốc không được đưa vào Git.

- Phiên bản nguồn: commit `3a5b30157034e7eadd5c75fae1a820c6f9383398`, tải ngày 25/09/2026.
- Giấy phép khai báo trên dataset card: CC BY-NC-ND 4.0. Chỉ sử dụng trong phạm vi nghiên cứu phù hợp với giấy phép; không phân phối bản biến đổi khi chưa xác minh quyền.
- Bản gốc: 132 tệp, 59.828.312.520 byte; gồm 103 shard `train`, 13 shard `valid`, 14 shard `test`, `README.md` và `.gitattributes`.
- Bản lưu Drive: 13 ZIP train, 2 ZIP validation, 2 ZIP test và 1 ZIP metadata. Mỗi ZIP độc lập, dùng chế độ lưu không nén lại và giữ nguyên các tệp Parquet.
- `SOURCE_SHA256SUMS.txt` trong thư mục Drive chứa SHA-256 chính thức của 130 shard LFS và SHA-256 của hai tệp metadata. `SOURCE_INFO.txt` ghi revision và cách khôi phục.
- Vai trò tham khảo/mở rộng: phân tích sai số theo vùng/tỉnh khi có câu hỏi cụ thể. Không cần khôi phục ViMD cho kế hoạch lean. Nguồn phát thanh địa phương không thay thế audio tự thu qua micro thực tế.

Khi khôi phục, giải nén tất cả ZIP train/valid/test vào cùng một thư mục, sau đó giải nén `ViMD_metadata.zip`. Giữ nguyên split gốc; không dùng test để chọn model, tinh chỉnh, tạo prompt hoặc xây từ điển sửa lỗi. Đối chiếu file đã giải nén với `SOURCE_SHA256SUMS.txt` trước khi chạy thí nghiệm.

## VIVOS 1.0

Bản gốc [VIVOS 1.0](https://zenodo.org/records/7068130) được tải về `D:\PBL6\dataset\VIVOS_1.0\vivos.tar.gz`, đóng gói không nén lại thành `D:\PBL6\dataset\VIVOS_1.0_Zenodo_7068130.zip`, rồi lưu tại `G:\My Drive\Seventh Semester\PBL6\dataset\VIVOS_1.0_Zenodo_7068130.zip`. Dữ liệu gốc không được đưa vào Git.

- Phiên bản nguồn: VIVOS 1.0, DOI `10.5281/zenodo.7068130`, tải ngày 26/09/2026.
- Giấy phép: CC BY-NC-SA 4.0; trang nguồn nêu corpus chỉ dùng cho mục đích học thuật.
- Tệp nguồn `vivos.tar.gz`: 1.474.408.300 byte; MD5 chính thức `72972a8b14050f3f11ea7c3debabd7af`; SHA-256 đã tính `147477f7a7702cbafc2ee3808d1c142989d0dbc8d9fce8e07d5f329d5119e4ca`.
- Gói Drive: 1.474.409.282 byte; SHA-256 `2e1236bd5284504555fbbabd31f102482c6c44ab342709f889d3c5ad296b544b`. Hash đọc lại từ ổ G trùng bản trên D.
- ZIP chứa nguyên vẹn `vivos.tar.gz`, `SOURCE_INFO.txt` và `CHECKSUMS.txt`; tệp âm thanh chưa được giải nén hoặc biến đổi.
- Vai trò dự phòng: lời đọc nhỏ để kiểm tra pipeline nếu cần. Kế hoạch lean không bắt buộc thêm VIVOS vào bảng so sánh; nguồn này không thay thế audio tự thu.

Khi sử dụng, giải nén ZIP rồi kiểm tra `vivos.tar.gz` theo `CHECKSUMS.txt` trước khi giải nén corpus. Giữ split gốc; không dùng test để chọn mô hình, prompt, từ điển sửa lỗi hoặc cấu hình tiền xử lý.

## VietSuperSpeech

Toàn bộ [VietSuperSpeech](https://huggingface.co/datasets/thanhnew2001/VietSuperSpeech) được tải vào `D:\PBL6\dataset\VietSuperSpeech_git` và lưu trên Google Drive tại [VietSuperSpeech_cbf624ae](https://drive.google.com/drive/folders/1iK8ye-gBiUCRR1m6bAS1X7DdcQXncJcd), tương ứng `G:\My Drive\Seventh Semester\PBL6\dataset\VietSuperSpeech_cbf624ae`. Dữ liệu gốc không được đưa vào Git của dự án.

- Phiên bản nguồn: commit `cbf624ae9b30e1c2793a27e95b262115c69601f3` của kho Hugging Face, tải ngày 27–28/09/2026.
- Giấy phép ghi trong README của nguồn: MIT. Âm thanh được trích từ các nguồn video; quyền đối với nội dung gốc chưa được kiểm tra riêng.
- Bản nguồn tại commit này có 118.264 tệp, trong đó 118.260 tệp Git LFS, tổng cộng 62.619.407.773 byte. Nhãn phiên âm được tạo bằng mô hình Zipformer-30M-RNNT-6000h theo README của nguồn, nên cần xem là nhãn máy và kiểm tra chất lượng trước khi dùng.
- Bản lưu Drive gồm 15 ZIP (`VietSuperSpeech_cbf624ae_part01-of-15.zip` đến `part15-of-15.zip`) và 15 tệp `.sha256.txt` tương ứng; tổng dung lượng ZIP là 62.688.053.113 byte. Mỗi ZIP độc lập, lưu tệp dưới tiền tố `VietSuperSpeech/` và chứa `SOURCE_INFO.txt`, `FILE_SHA256SUMS.txt` riêng. Thư mục Drive còn có `SOURCE_SHA256SUMS.txt` tổng hợp 118.264 dòng và checksum của manifest này.
- Khi đóng gói, SHA-256 của từng tệp LFS được so với OID nguồn. SHA-256 của từng ZIP đã được đối chiếu sau khi chép sang ổ G. Google Drive đã liệt kê đủ 15 ZIP và 15 checksum; kiểm tra cấu trúc ZIP cho thấy đủ 118.264 đường dẫn tệp nguồn, không trùng và không thiếu manifest.
- Vai trò: lưu làm nguồn nghiên cứu sau này, không cần trong kế hoạch lean dùng inference pretrained. Nhãn máy chưa kiểm tra không dùng làm tập đánh giá chính, đặc biệt khi chấm chính Zipformer tạo nhãn.

Để khôi phục, tải đủ 15 ZIP rồi giải nén tất cả vào cùng một thư mục. Trước khi giải nén, kiểm tra SHA-256 của mỗi ZIP theo tệp `.sha256.txt` cùng tên. Sau khi giải nén, đối chiếu dữ liệu trong thư mục `VietSuperSpeech/` với `SOURCE_SHA256SUMS.txt` tổng hợp; các tệp `FILE_SHA256SUMS.txt` trùng tên ở mỗi ZIP nên sẽ ghi đè nhau nếu giải nén tất cả vào cùng chỗ. Giữ nguyên `train.json`, `dev.json` và cấu trúc `audio/` của bản nguồn.
