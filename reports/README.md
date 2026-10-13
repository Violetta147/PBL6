# Báo cáo demo B01–B04

Mở [DEMO_BUOI_01_04.md](DEMO_BUOI_01_04.md) ở chế độ đọc của Obsidian. Các đường phân cách tạo khối trình bày, không có nhãn số slide; đây vẫn là Markdown, chưa xuất PowerPoint hoặc kiểm tra chế độ trình chiếu của một plugin.

- [PIPELINES_BUOI_01_04.md](PIPELINES_BUOI_01_04.md): luồng từ nguồn audio đến báo cáo, file/component dùng chung, nhánh Pi và B05 dự kiến.
- [DIEM_CHUA_CHAT_BUOI_01_04.md](DIEM_CHUA_CHAT_BUOI_01_04.md): lỗi phép so và giới hạn kết luận, có đính chính C0-base/Pi chưa đầy đủ.
- `figures/`: hai biểu đồ chất lượng, mỗi hình có PNG/SVG; `sources.json` lưu nguồn/hash và đúng 12 giá trị phần trăm.
- `diagrams/`: bốn nguồn Mermaid tương ứng các sơ đồ nhúng trong hai tài liệu. Nét đứt chỉ phần dự kiến hoặc chưa thực hiện.

Sinh lại biểu đồ từ CSV có sẵn, trong workspace PBL6 có môi trường plotting:

```powershell
& data/stt_venv/Scripts/python.exe reports/generate_demo_figures.py
```

Script không chạy ASR, không thay kết quả thí nghiệm và không ghi đè các tài liệu Markdown. Nội dung demo vẫn chỉnh được trực tiếp.

## Kiểm tra ngày 13/10/2026

Script plotting đã thực thi; code compile đạt. Hai PNG đã xem trực tiếp: nhãn và số không bị cắt, chữ tiếng Việt đọc được. Kiểm tra hash nguồn/generator/hình và 12 giá trị WER_ws/CER khớp CSV; 28 liên kết local trong ba tài liệu demo/pipeline/audit tồn tại. Transcript mẫu pilot và self20 đối chiếu JSONL/CSV; các thời gian Pi đối chiếu summary/raw. Bản demo có 13 đường phân cách, ba block Mermaid, không có tiêu đề “slide số”. Nội dung Mermaid nhúng khớp nguồn `.mmd`, fence đóng đủ; chưa trực tiếp quan sát renderer Mermaid trong Obsidian, không coi việc kiểm tra nguồn là kiểm tra trình chiếu.

Bản demo trước khi chuyển bố cục đã được sao lưu vào thư mục ignored `data/document_backups/`. Các chỉnh sửa hỏi–đáp của người thực hiện được giữ nguyên; các câu trả lời mới được commit riêng. Không chạy lại model, thay manifest/scorer, mở test, hoặc cập nhật kế hoạch 7 buổi trong lần tạo báo cáo này.

C0 Whisper-base trên Pi mới có smoke một câu; tiny là khảo sát bổ sung. Hai chính sách nạp/phạm vi thời gian chưa đồng nhất, nên báo cáo không biểu diễn tỷ lệ tăng tốc hoặc khẳng định đã hoàn tất benchmark đối chứng.

Git giữ byte các figure/receipt và LF của script/nguồn Mermaid để hash không đổi do EOL Windows. Khoảng trắng cuối dòng có chủ đích trong Markdown (hard break) và SVG do Matplotlib sinh được giữ; diff check bỏ kiểm tra riêng blank-at-eol, vẫn kiểm tra phần lỗi còn lại.

Kiểm tra cuối: 31 liên kết local trong bốn tài liệu tồn tại; bốn nguồn Mermaid có endpoint cạnh được định nghĩa (chưa phải kiểm tra renderer đầy đủ). Kiểm tra blob Git ban đầu phát hiện SVG bị đổi EOL khi stage trước khi có attributes; đã stage lại theo attributes và xác minh cả script cùng bốn hình PNG/SVG trong index khớp SHA-256 receipt. Không sửa hình hoặc số liệu để khớp hash.
