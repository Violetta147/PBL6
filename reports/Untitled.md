nạp audio vào ram là do ai làm?
-> Code Python trong `experiments/run_asr.py` gọi `soundfile.read()` để đọc WAV thành mảng số float32 trong RAM. Với nhánh Whisper/Pi, chính chương trình `whisper-cli` đọc WAV được truyền qua tham số `-f`.
gồm xử lý trong runtime là sao nhỉ?
-> Là các bước từ mảng âm thanh đến chữ: trích đặc trưng, chạy mạng neural và giải mã. Code bấm giờ quanh lời gọi nhận dạng, nên đo cả các bước ấy trong runtime, không chỉ riêng phép tính của mạng neural.
Thời gian xử lý có gồm nạp model và đọc/ghi hay không trong pipeline?
-> Tùy số đo: `elapsed_s` trong `run_asr.py` không gồm nạp model, đọc WAV, chấm và ghi file. Wall cả runner Zipformer có gồm các bước đó; wall CLI Whisper/Pi gồm nạp model, đọc WAV và ghi text nhưng không gồm chấm/ghi JSONL của code gọi CLI.
elapse_s code snippet?
-> Tên đúng là `elapsed_s`. Đoạn sau trích từ `experiments/run_asr.py`; đọc WAV nằm trước mốc bắt đầu, chấm và ghi JSONL nằm sau mốc kết thúc:

```python
audio, rate = sf.read(audio_path, dtype='float32')
if rate != 16000 or audio.ndim != 1:
    raise ValueError('Expected mono 16kHz audio, resample before inference')
record['duration_s'] = len(audio) / rate
synchronize()
start = time.perf_counter()
record['prediction'] = infer(audio).strip()
synchronize()
record.update(elapsed_s=time.perf_counter() - start, status='ok')
```

`synchronize()` chờ GPU hoàn tất khi chạy CUDA, để không dừng timer lúc GPU vẫn đang xử lý; trên CPU hàm này không cần chờ GPU.
Nếu mô tả thành khối cái quy trình đo đạc RTF này bạn sẽ ghi như nào?
-> Với Zipformer/Pi hiện tại:

```text
[Bắt đầu wall cả runner]
  → Khởi động Python/runtime → Nạp model một lần
  → Với mỗi WAV: kiểm tra hash → Đọc vào RAM
    → [Bắt đầu elapsed_s] → Nhận dạng → [Kết thúc elapsed_s]
    → Chấm với reference → Ghi kết quả
  → Hoàn tất runner → [Kết thúc wall]
  → Kiểm chứng lại kết quả bằng JiWER

RTF nhận dạng = tổng elapsed_s / tổng thời lượng WAV
RTF cả runner = wall cả runner / tổng thời lượng WAV
```

tại sao lại có chấm và ghi "Khởi động, nạp model, đọc WAV, nhận dạng, chấm và ghi" cho ZIpformer?
-> Vì timer wall bao quanh cả chương trình thí nghiệm `run_asr.py`, mà chương trình này vừa nhận dạng, vừa tính điểm với nhãn chuẩn và lưu JSONL/metadata. Chấm là phục vụ đánh giá, không phải bước cần thiết để tạo phụ đề; lần kiểm chứng JiWER riêng chạy sau timer wall.

Khởi động là khởi động cái gì?
-> Là tạo tiến trình chạy chương trình, khởi động Python và nhập các thư viện/runtime cần dùng. Không phải bật nguồn hay khởi động lại Raspberry Pi.
Wav ở đâu mà đọc, được load chưa?
-> WAV đã chuẩn bị nằm trên bộ nhớ lưu trữ của máy chạy; manifest chỉ đường dẫn đến từng file. Ví dụ trên Pi là `/home/pi/PBL6_STT_B04_20261013/data/self_recorded/dev/self_01.wav`. File có sẵn trên bộ nhớ lưu trữ chưa có nghĩa là mảng audio đã nằm trong RAM; runner đọc lần lượt từng WAV trước khi bắt đầu timer nhận dạng.
Không tính thời gian xử lý chuẩn bị wav sao?
-> Không tính trong các số RTF hiện tại. Chuyển M4A sang WAV và chuẩn bị FLEURS đã làm trước thí nghiệm; nếu đo một pipeline nhận M4A hoặc micro trực tiếp thì cần xác định và đo thêm các bước xử lý đầu vào tương ứng.
ghi text mỗi tệp ở đây là sao "Khởi động, nạp model, đọc WAV, nhận dạng và ghi text mỗi tệp" Whisper?
-> Mỗi lần gọi `whisper-cli` xử lý một WAV và xuất transcript ra một file `.txt`, chẳng hạn `01.txt`, nhờ tùy chọn `-otxt`. Sau khi CLI kết thúc, code Python mới đọc text ấy, chấm điểm và ghi JSONL; phần sau không nằm trong timer CLI.

Wall CLI là sao?
-> CLI là chương trình gọi bằng dòng lệnh. Wall time là thời gian thực trôi qua từ trước lúc gọi đến sau lúc chương trình kết thúc; nó gồm cả thời gian chờ đọc/ghi, không chỉ thời gian CPU tính toán. Ở đây timer còn bao quanh `/usr/bin/time` và thao tác mở/đóng log.

Chừng này là đủ hiểu hết RTF estimate pipeline chưa?
-> Đủ để hiểu cách tính và phạm vi các số RTF của thí nghiệm WAV hiện tại. Đây là phép đo từ thời gian chạy thực, chưa phải đánh giá toàn bộ pipeline phụ đề liên tục.

Còn thiếu gì không?
-> Để so tốc độ, còn cần thống nhất cách nạp model, phạm vi timer và điều kiện chạy. Để đánh giá pipeline kính, còn cần đo chốt đoạn, hàng đợi và thời gian từ cuối lời nói đến khi hiện phụ đề; hiện chưa có các số đó.

Chốt lại là gì, chứ tính bậy bạ không công bằng sao so sánh được?
-> Các số đã đo có ý nghĩa trong phạm vi riêng, nhưng phép so tốc độ giữa hai nhánh Pi chưa đồng nhất: Zipformer nạp một lần cho 20 WAV, Whisper nạp lại mỗi WAV, và timer gồm các việc khác nhau. Vì vậy chưa được dùng chúng để tuyên bố nhanh hơn bao nhiêu lần. Muốn so cấu hình công bằng hơn, dùng cùng Pi, cùng WAV, cùng số luồng, cùng chế độ nạp một lần và cùng mốc đo; ghi rõ checkpoint/runtime và điều kiện cache. Điều đó vẫn là so hai cấu hình cụ thể, chưa cô lập tác động riêng của kiến trúc model.

Tài liệu chứng minh sao không dùng đường dẫn Drive và code trên Drive đã sync với project workspace cũng như hai cái là mới nhất chưa?
-> Chưa thể nói toàn bộ hai nơi đồng bộ hoặc đều mới nhất. Kiểm tra ngày 15/10/2026: 11/16 file Python giống hệt; 5 file chưa có ở cây experiments trên Drive, gồm hai runner Pi, make_self_notebook.py và hai file test. run_asr.py trên Drive khớp local; hai runner Pi local khớp hash ghi trong metadata lần chạy thật. Các bảng summary/comparison FLEURS và self20, cùng hai bảng tổng hợp Pi đã kiểm tra đều khớp; README B04 local đã khác bản Drive. ZIP đầu vào Pi trên Drive có run_asr.py khớp, nhưng không có hai runner đo Pi; không được suy ra chúng đã đồng bộ từ việc ZIP tồn tại.

-> Dẫn workspace giúp mở đúng dòng code và đối chiếu Git. Khi cần chia sẻ với nhóm, nên kèm đường dẫn Drive và định danh lần chạy/hash để tránh nhầm code mới với code đã tạo ra kết quả. G: là ổ Drive gắn trên máy; đối chiếu này chưa xác minh trạng thái cloud độc lập và không thay đổi file trên Drive.

Bằng chứng và đường dẫn:

- [Code nhận dạng trên Drive](<G:/My Drive/Seventh Semester/PBL6/STT_B01_B03/experiments/run_asr.py>) và [code local](<C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/PBL6/experiments/run_asr.py:177>).
- [Runner Zipformer/Pi local](<C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/PBL6/experiments/B04/run_zipformer_pi.py:84>) và [metadata hash runner đo Pi](<C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/PBL6/experiments/B04/results/zipformer_r1/measurement.json>).
- [Runner Whisper/Pi local](<C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/PBL6/experiments/B04/run_whisper_cpp_pi.py:79>) và [metadata hash lần chạy](<C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/PBL6/experiments/B04/results/whisper_tiny_r1/whisper_cpp.run.json>).
- [Kết quả Pi trên Drive](<G:/My Drive/Seventh Semester/PBL6/STT_B01_B03/B04_Pi_results_20261013>), [FLEURS trên Drive](<G:/My Drive/Seventh Semester/PBL6/STT_B01_B03/runs/qwen_gpu_20261010_023946>) và [self20 trên Drive](<G:/My Drive/Seventh Semester/PBL6/STT_B01_B03/runs/self_dev20_qwen_v1>).
- [Đối chiếu từng file và hash](<C:/Users/LAPTOP T&T/VIOLETTA/Documents/ChatGPT/PBL6/reports/DRIVE_SYNC_AUDIT_20261015.json>).

Trong các câu hỏi đã trả lời, có khái niệm nào tương đương inference time không?
-> Có: “thời gian nhận dạng” (`elapsed_s` trong run_asr.py) là inference time theo phạm vi đo của dự án: audio đã ở RAM → transcript. Tổng các elapsed_s của 20 câu được ghi thành `inference_seconds` trong kết quả Zipformer/Pi. Nó gồm trích đặc trưng, chạy mạng neural và giải mã trong runtime, không chỉ riêng forward pass của mạng; không gồm nạp model, đọc WAV, chấm hoặc ghi file. “Cả runner” và “wall CLI” là wall time, không tương đương inference time này.
