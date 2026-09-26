# PBL6 — dữ liệu tiếng nói tiếng Việt

## FLEURS `vi_vn`

Bộ dữ liệu FLEURS `vi_vn` được tải từ [google/fleurs](https://huggingface.co/datasets/google/fleurs) vào `data/raw/fleurs/vi_vn/`. Đây là bản gốc gồm `train.tsv`, `dev.tsv`, `test.tsv` và ba tệp `audio/{train,dev,test}.tar.gz`; chưa giải nén hoặc biến đổi âm thanh. Thư mục `data/` được Git bỏ qua để không đưa dữ liệu vào commit.

- Phiên bản nguồn: commit `70bb2e84b976b7e960aa89f1c648e09c59f894dd` của kho Hugging Face, tải ngày 25/09/2026.
- Giấy phép: [CC BY 4.0](https://huggingface.co/datasets/google/fleurs) theo dataset card. Khi sử dụng, ghi nguồn và trích dẫn bài báo FLEURS theo dataset card.
- Split gốc: `train` 2.994 dòng, `dev` 361 dòng, `test` 857 dòng. Trong thư viện Hugging Face, `dev` tương ứng `validation`.
- Metadata TSV gốc có 10 dòng chỉ gồm 6 cột thay vì 7 (`train`: 4, `test`: 6); giữ nguyên bản nguồn. Khi viết bộ đọc dữ liệu, kiểm tra độ rộng từng dòng trước khi gán tên cột.
- Vai trò theo [bản đặc tả](SPEC_STT_SMART_GLASSES.md): FLEURS là benchmark phụ trợ trên lời đọc. Giữ `test` độc lập; không dùng transcript hoặc âm thanh `test` để tinh chỉnh mô hình, prompt hay từ điển sửa lỗi.

Các tệp âm thanh nén có SHA-256 chính thức (LFS OID của kho nguồn):

| Tệp | Byte | SHA-256 |
|---|---:|---|
| `audio/train.tar.gz` | 1.607.278.457 | `016a568afc1909cfaf9efb1a2fc2f1d3311e646d9b52d05dc2e84ac0c17c34ce` |
| `audio/dev.tar.gz` | 214.500.592 | `8821a394c99069409b3ce7bb5cd14b10b709f2ee2fea16f42b4701e1cc9ef673` |
| `audio/test.tar.gz` | 544.139.865 | `b359261216ef14b8eea159abce794e270c2a0be903218cf1e1e8f7c7c1565b5c` |

Git blob SHA-1 của TSV trên kho nguồn, đã đối chiếu bằng `git hash-object`: `train.tsv` `f88141e2bc80f1942d5939819da120264f7eeed6`, `dev.tsv` `f2f5a9207bb010193e298b302495ed76e3ce5782`, `test.tsv` `5e6d9d0bb2252181c78080eb80d5c0af09b5c42f`.

Để tải lại một tệp, dùng URL dạng `https://huggingface.co/datasets/google/fleurs/resolve/70bb2e84b976b7e960aa89f1c648e09c59f894dd/data/vi_vn/<tên-tệp>?download=true`. Cấu trúc và tên tệp trong `data/raw/fleurs/vi_vn/` trùng đường dẫn `data/vi_vn/` trên nguồn. Kiểm tra SHA-256 bằng `Get-FileHash data/raw/fleurs/vi_vn/audio/test.tar.gz -Algorithm SHA256` (đổi tên tệp cho các split khác). Có thể đọc trực tiếp TSV và kho tar.gz; chỉ giải nén split cần dùng để tiết kiệm dung lượng.

## ViMD

Toàn bộ [ViMD Dataset](https://huggingface.co/datasets/nguyendv02/ViMD_Dataset) được tải vào `D:\PBL6\dataset\ViMD_Dataset` và đóng gói để lưu tại `G:\My Drive\Seventh Semester\PBL6\dataset\ViMD_Dataset_3a5b301`. Dữ liệu gốc không được đưa vào Git.

- Phiên bản nguồn: commit `3a5b30157034e7eadd5c75fae1a820c6f9383398`, tải ngày 25/09/2026.
- Giấy phép khai báo trên dataset card: CC BY-NC-ND 4.0. Chỉ sử dụng trong phạm vi nghiên cứu phù hợp với giấy phép; không phân phối bản biến đổi khi chưa xác minh quyền.
- Bản gốc: 132 tệp, 59.828.312.520 byte; gồm 103 shard `train`, 13 shard `valid`, 14 shard `test`, `README.md` và `.gitattributes`.
- Bản lưu Drive: 13 ZIP train, 2 ZIP validation, 2 ZIP test và 1 ZIP metadata. Mỗi ZIP độc lập, dùng chế độ lưu không nén lại và giữ nguyên các tệp Parquet.
- `SOURCE_SHA256SUMS.txt` trong thư mục Drive chứa SHA-256 chính thức của 130 shard LFS và SHA-256 của hai tệp metadata. `SOURCE_INFO.txt` ghi revision và cách khôi phục.
- Vai trò: benchmark phụ trợ để phân tích sai số theo vùng/tỉnh và người nói. Nguồn chủ yếu là chương trình phát thanh địa phương, nên không thay thế bộ hội thoại tự thu trong điều kiện micro, khoảng cách và tiếng ồn thực tế.

Khi khôi phục, giải nén tất cả ZIP train/valid/test vào cùng một thư mục, sau đó giải nén `ViMD_metadata.zip`. Giữ nguyên split gốc; không dùng test để chọn model, tinh chỉnh, tạo prompt hoặc xây từ điển sửa lỗi. Đối chiếu file đã giải nén với `SOURCE_SHA256SUMS.txt` trước khi chạy thí nghiệm.

## VIVOS 1.0

Bản gốc [VIVOS 1.0](https://zenodo.org/records/7068130) được tải về `D:\PBL6\dataset\VIVOS_1.0\vivos.tar.gz`, đóng gói không nén lại thành `D:\PBL6\dataset\VIVOS_1.0_Zenodo_7068130.zip`, rồi lưu tại `G:\My Drive\Seventh Semester\PBL6\dataset\VIVOS_1.0_Zenodo_7068130.zip`. Dữ liệu gốc không được đưa vào Git.

- Phiên bản nguồn: VIVOS 1.0, DOI `10.5281/zenodo.7068130`, tải ngày 26/09/2026.
- Giấy phép: CC BY-NC-SA 4.0; trang nguồn nêu corpus chỉ dùng cho mục đích học thuật.
- Tệp nguồn `vivos.tar.gz`: 1.474.408.300 byte; MD5 chính thức `72972a8b14050f3f11ea7c3debabd7af`; SHA-256 đã tính `147477f7a7702cbafc2ee3808d1c142989d0dbc8d9fce8e07d5f329d5119e4ca`.
- Gói Drive: 1.474.409.282 byte; SHA-256 `2e1236bd5284504555fbbabd31f102482c6c44ab342709f889d3c5ad296b544b`. Hash đọc lại từ ổ G trùng bản trên D.
- ZIP chứa nguyên vẹn `vivos.tar.gz`, `SOURCE_INFO.txt` và `CHECKSUMS.txt`; tệp âm thanh chưa được giải nén hoặc biến đổi.
- Vai trò: benchmark nhỏ trên lời đọc thu trong môi trường yên tĩnh. VIVOS phù hợp để kiểm tra pipeline và so sánh baseline, nhưng không thay thế bộ hội thoại tự thu với khoảng cách, tiếng ồn và thiết bị thực tế.

Khi sử dụng, giải nén ZIP rồi kiểm tra `vivos.tar.gz` theo `CHECKSUMS.txt` trước khi giải nén corpus. Giữ split gốc; không dùng test để chọn mô hình, prompt, từ điển sửa lỗi hoặc cấu hình tiền xử lý.
