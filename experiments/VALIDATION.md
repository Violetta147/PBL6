# Kiểm tra thực hành B01–B03 — 10/10/2026

Mã và notebook đã được tạo; trạng thái inference được ghi riêng trong output thực tế, không suy từ việc test mã thành công.

- `data/stt_venv/Scripts/python.exe -m unittest discover -s experiments/tests -v`: 8 test pass, không skip. Có đáp án S/D/I tính tay, NFC/dấu/chữ số, nhãn rỗng, trọng số toàn tập, giữ lỗi inference, đối chiếu edit distance với JiWER, parser 6/7 cột và chuyển float WAV thành PCM16 mà không đổi raw.
- `python experiments/make_notebooks.py`: B01 9 cell, B02 12 cell, B03 17 cell; JSON được sinh hợp lệ và toàn bộ code cell compile được. Đây là kiểm tra cấu trúc, chưa chứng minh chạy Colab thành công.
- `prepare.py` chạy trên dữ liệu thật: 10 pilot, 111,54 giây; 100 dev, 1.198,20 giây. Tất cả bản dẫn xuất mono16kHz PCM16 có hash. 200 test chỉ lưu ID, không đưa audio/reference test vào gói.
- Môi trường local riêng `data/stt_venv`, dùng torch CPU sẵn có. CPU đã kiểm tra: Intel i5-7200U, 2 core/4 logical processor. Một số package không dùng trong thí nghiệm được kế thừa từ Python gốc; không sử dụng seleniumbase để điều khiển Chrome.

Whisper pilot 10/10, Whisper dev 100/100 và Zipformer dev 100/100 đã kết thúc với `finished=true`; bảng hai model đã tổng hợp. `verify_results.py` kiểm tra đủ ID, hash audio/reference và tính lại điểm bằng JiWER độc lập; kết quả ở `verification.json`. Qwen/Colab, nghe lỗi và 20 câu tự thu vẫn cần kiểm tra thực tế. Không đánh dấu hoàn thành cả ba buổi ở thời điểm này.
