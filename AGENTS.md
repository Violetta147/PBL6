# Hướng dẫn agent cho PBL6

## Điểm duyệt

Dừng ở bước cần người dùng duyệt. Tiếp tục các phần độc lập đã được phép.

- **SLR:** xin duyệt trước khi thay ngưỡng tách đoạn hoặc tiền xử lý đầu vào SL-GCN.
- **Dữ liệu và mô hình:** xin duyệt trước khi thao tác với dữ liệu gốc trên Google Drive, huấn luyện lại hoặc thay trọng số `gcnCkpt.pt`.
- **Golden Demo Set:** dùng kết quả người ký thử trực tiếp trước camera để đề xuất bộ từ. Chỉ chốt sau khi người dùng duyệt.
- **Bàn giao:** xin duyệt trước khi đưa thay đổi vào demo chính thức, production hoặc tạo commit. Sau khi được duyệt, tạo commit cho từng thay đổi hoàn chỉnh với thông điệp mô tả rõ.

## Thay đổi và kiểm chứng

1. **Chọn vị trí.** Trước khi tạo file code, notebook hoặc Markdown, nêu vị trí và trách nhiệm của file. Khi lập kế hoạch nhiều mô-đun cho SLR, dùng `slr-app/MVP/plans/`. Mỗi kế hoạch ghi đầu vào, đầu ra, file được phép sửa và lệnh kiểm chứng.
2. **Kiểm tra xác định.** Với Python, chạy `python -m py_compile <file.py>`. Với TypeScript trong `stt-app/`, chạy `npm run build` hoặc `npm run typecheck` (`tsc --noEmit`) tùy phạm vi. Với bundle SLR, chạy `verify_bundle()` từ `slr-app/MVP/deployment/slgcn_feature_trial/prepare_clip.py` và chạy `verify_reference.py` trong cùng thư mục để đối chiếu mẫu tham chiếu. Dùng đầu ra của công cụ để kết luận về cú pháp, kiểu dữ liệu và mã băm.
3. **Xác minh hành vi.** Chạy kiểm thử liên quan đến đầu vào và đầu ra đã thay đổi theo bảng bên dưới. Cập nhật tài liệu và kiểm thử liên quan trong cùng thay đổi chức năng. Ghi các kiểm tra đã chạy và kết quả trước khi đề xuất commit.

## SLR và STT

**SLR.** Trong `slr-app/MVP/`, giữ `deployment/` bất biến theo SHA-256, bao gồm checkpoint, `feature_extract/`, `slgcn_feature_trial/` và `label_map_v1.json`. Đặt mã kiosk, ghi clip và kiểm thử tích hợp trong `desktop_mvp/`. Đặt phân tích landmark và cặp nhầm lẫn trong `diagnostics/`, thuật toán tìm biên và tách chuỗi trong `segmentation/`. Dùng `local_data/` cho clip mẫu, clip quay thử và âm thanh `tts/0.mp3..399.mp3`. Dùng `outputs/` cho báo cáo chạy thử. Git bỏ qua clip `*.avi` trong `local_data/` và các đầu ra thực nghiệm.

Chạy các lệnh SLR từ `slr-app/MVP/`.

| Phần thay đổi | Kiểm tra |
| --- | --- |
| Máy chủ hoặc trạng thái kiosk | `python -u desktop_mvp/test_demo_server.py` |
| Chuyển trạng thái DOM hoặc giao diện | `node desktop_mvp/verify_transitions.js` |
| Đường nhận dạng, trọng số hoặc tiền xử lý | Kiểm tra bundle và chạy `python -X utf8 desktop_mvp/check_clip.py local_data/014159.mp4 --expected "Dài" --expected-frames 59` |

**STT.** Khi làm trong `stt-app/`, đọc [hướng dẫn của phân hệ](stt-app/AGENTS.md) trước khi sửa mã. Chạy lệnh TypeScript từ thư mục đó.

## Viết và tra cứu

- Mở đầu bằng kết quả hoặc việc cần làm. Dùng gạch đầu dòng hoặc bảng khi cần đối chiếu nhiều điều kiện.
- Với tài liệu học thuật, dùng thuật ngữ chính xác và gắn kết luận với bằng chứng. Chỉ đưa trích dẫn, số liệu và tên tác giả đã kiểm chứng. Khi tài liệu và mã nguồn cục bộ thiếu căn cứ, ghi “Cần kiểm chứng nguồn thực tế” và nêu từ khóa tra cứu. Trong slide, dùng “nhóm” hoặc “nhóm chúng em”, nêu hành động và mục đích. Dùng “nhóm dự định…” cho việc chưa chốt.
- Dùng `search_web` hoặc công cụ tìm kiếm hiện có để kiểm chứng nhanh. Dùng Tavily khi có và cần đọc sâu nhiều nguồn. Khi cần thao tác trên web động, dùng `browser` subagent nếu có sẵn và được phép. Nếu không, dùng công cụ trình duyệt hiện có.
