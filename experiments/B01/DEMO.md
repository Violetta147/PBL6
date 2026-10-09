# Demo B01: một audio → text → đếm lỗi

Lần chạy thật dùng Whisper-base đa ngôn ngữ trên CPU i5-7200U, `openai-whisper==20250625`, language `vi`, task `transcribe`, temperature 0, không nối ngữ cảnh giữa các đoạn. 10/10 pilot có output, tổng WER_ws 36,875% và CER 20,3883%. Đây là pilot lấy từ train để học luồng, không phải điểm dev hay test.

Mở [WAV mẫu](../../data/derived/stt_b01_b03/train/18182759805207678941.wav) rồi đọc nhãn và kết quả. Người thực hiện cần nghe lại; tài liệu này đối chiếu văn bản đã lưu, chưa chứng nhận kiểm tra bằng tai.

**Reference:** Những cây này nhìn giống cây cọ nhỏ có tán lá sắc nhọn.

**Whisper:** Những cái này nhìn giống cây cộ nhỏ có tán là sắc nhỏ.

Sau chuẩn hóa chữ thường/dấu câu, reference có 13 đơn vị cách nhau bằng khoảng trắng. Bốn thay thế là `cây → cái`, `cọ → cộ`, `lá → là`, `nhọn → nhỏ`; không chèn hoặc xóa. WER_ws của câu là `(4 + 0 + 0)/13 = 30,7692%`. Dấu tiếng Việt vẫn tham gia chấm, nên `cọ` và `cộ` khác nhau.

Demo 3–5 phút: phát WAV → cho thấy audio đi vào model → mở prediction thật → đếm bốn lỗi → giải thích bước tiếp theo là chấm chung cho hai model. Bản chép lời tham chiếu không được truyền vào model. Các số đo/metadata đầy đủ ở [results](results/summary.csv).
