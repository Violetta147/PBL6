# PBL6 — dữ liệu FLEURS tiếng Việt

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
