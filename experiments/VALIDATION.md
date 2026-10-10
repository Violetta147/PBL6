# Kiểm tra thực hành B01–B03 — 10/10/2026

Mã và notebook đã được tạo; trạng thái inference được ghi riêng trong output thực tế, không suy từ việc test mã thành công.

- `data/stt_venv/Scripts/python.exe -m unittest discover -s experiments/tests -v`: 11 test pass, không skip. Có đáp án S/D/I tính tay, NFC/dấu/chữ số, nhãn rỗng, trọng số toàn tập, giữ lỗi inference, đối chiếu edit distance với JiWER, parser 6/7 cột và chuyển float WAV thành PCM16 mà không đổi raw. Ba test mới xác nhận Qwen CPU bị chặn trước khi đọc manifest/ghi output, `auto` thiếu CUDA không nạp Qwen, và hai baseline CPU vẫn được phép.
- `python experiments/make_notebooks.py`: B01 9 cell, B02 12 cell, B03 17 cell; JSON được sinh hợp lệ và toàn bộ code cell compile được. Đây là kiểm tra cấu trúc, chưa chứng minh chạy Colab thành công.
- `python experiments/make_qwen_notebook.py`: notebook Drive riêng 12 cell, code compile được. Người thực hiện đã chạy trên Colab; output chứng minh mount Drive và Qwen GPU A100 hoàn tất 100/100. Gói ZIP SHA-256 khớp receipt, runner/scoring/manifest hash khớp signature; hai baseline được dùng lại có hash trùng nguồn. Chưa xác nhận người thực hiện đã nghe audio.
- `prepare.py` chạy trên dữ liệu thật: 10 pilot, 111,54 giây; 100 dev, 1.198,20 giây. Tất cả bản dẫn xuất mono16kHz PCM16 có hash. 200 test chỉ lưu ID, không đưa audio/reference test vào gói.
- Môi trường local riêng `data/stt_venv`, dùng torch CPU sẵn có. CPU đã kiểm tra: Intel i5-7200U, 2 core/4 logical processor. Một số package không dùng trong thí nghiệm được kế thừa từ Python gốc; không sử dụng seleniumbase để điều khiển Chrome.

Whisper pilot 10/10 và cả ba model dev 100/100 đều có `finished=true`. `verify_results.py` kiểm tra đủ ID, hash audio/reference và tính lại điểm bằng JiWER độc lập; bốn run đạt trong `verification.json`. Bảng ba model sinh lại local trùng hoàn toàn summary Colab. Qwen WER_ws 0,09760457633178406, CER 0,06277056277056277. Chưa chạy lại inference khi nhập kết quả. Nghe lỗi và 20 câu tự thu còn thiếu; không đánh dấu hoàn thành cả ba buổi ở thời điểm này.
