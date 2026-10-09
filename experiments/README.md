# Thực hành buổi 1–3

Mã dùng chung nằm tại đây; mỗi buổi có một notebook và thư mục `results` riêng. Không training. Dữ liệu lớn và model ở `data/` được Git bỏ qua. Kết quả chỉ được coi là đã đo khi có JSONL và `.run.json` từ lần chạy thật.

**Để chạy tiếp ngay:** mở `B03_Qwen_Colab_GPU.ipynb` tại `My Drive/Seventh Semester/PBL6/STT_B01_B03`, chọn GPU rồi chạy các ô theo thứ tự. Notebook đọc gói ZIP và hai baseline đã đo từ Drive, chỉ chạy thêm Qwen, ghi từng prediction và bảng kết quả vào `runs/qwen_gpu_...`. Nếu runtime ngắt, nhập tên lần chạy cũ vào `RUN_NAME` để tiếp tục. Không cần tải lại ZIP qua hộp thoại upload. `make_qwen_notebook.py` tạo notebook này; ba notebook bên dưới vẫn phục vụ học từng buổi từ đầu.

1. `python experiments/prepare.py`: chọn seed 42, khôi phục 10 WAV train pilot và 100 WAV dev, lưu 200 ID test mà không khôi phục WAV/nhãn test vào gói Colab.
2. Mở notebook B01/B02/B03 trong Colab, chọn GPU, upload `data/derived/stt_b01_b03_package.zip` khi được hỏi. B03 có thể chạy cả ba buổi; output vẫn tách theo buổi. Colab Pro cấp GPU nào thì ghi GPU đó.
3. Tải ZIP kết quả bằng cell cuối; giữ output, metadata môi trường và bảng. Không ngắt runtime trước khi tải.
4. Thu 20 câu dev thật theo `B02/THU_AM.md`, tạo manifest bằng `import_self.py`, rồi chạy phần dữ liệu tự thu của B03. Chưa có audio thì mục này vẫn chưa hoàn thành.

Whisper và Zipformer có thể chạy CPU local. Qwen chỉ chạy GPU Colab: dùng `run_asr.py --model qwen --manifest ... --output ... --device cuda`. Runner từ chối Qwen CPU, kể cả khi `auto` không tìm thấy CUDA. Mỗi run có manifest/scoring/code hash. Chạy lại cùng cấu hình tiếp tục các mẫu chưa ghi; dùng đường dẫn output mới nếu đổi mã/cấu hình. Run đã ghi lỗi không tự âm thầm chạy lại hoặc bỏ lỗi. Tốc độ local/Colab không phải số đo Pi.

WAV nguồn FLEURS là IEEE float. `prepare.py` cần `soundfile==0.14.0` và tạo bản dẫn xuất PCM16 mono16kHz để các backend dùng cùng audio. Không resample hoặc thay header giả; rate giữ nguyên. Manifest lưu hash của cả nguồn lẫn bản dẫn xuất, archive raw không đổi.

Qwen tải vào `local_dir` theo revision để không cần quyền tạo symlink; backend dùng PyTorch, tắt import TensorFlow/Flax không cần thiết. Lần CPU đã dừng theo yêu cầu người thực hiện, giữ 6 prediction trong `B03/attempts/cancelled_cpu/`; không dùng lần chạy dở này trong bảng kết quả. Lần GPU dùng output mới.

Sau khi sửa mã hoặc thêm audio tự thu đã kiểm tra, dùng `python experiments/prepare.py --package-only` để tạo lại gói Colab, không khôi phục raw lần nữa. Gói chỉ đưa audio dev tự thu vào khi manifest đã có consent/label_verified và hash khớp. Kết quả/attempt/progress được lưu riêng, không đi vào gói đầu vào. `package_receipt.json` ghi kích thước, CRC và hash gói hiện tại.

Kiểm tra: `python -m unittest discover -s experiments/tests -v`. `jiwer==4.0.0` cung cấp kiểm tra độc lập cho khoảng cách edit. Notebook JSON và code cell được kiểm tra khi chạy `make_notebooks.py`.

Nguồn runtime: [Whisper](https://github.com/openai/whisper), [Zipformer ONNX](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/zipformer-transducer-models.html), [Qwen3-ASR](https://huggingface.co/Qwen/Qwen3-ASR-0.6B). Phiên bản package được ghim; các phụ thuộc thực tế và checkpoint hash/revision được lưu trong metadata. FLEURS: [google/fleurs](https://huggingface.co/datasets/google/fleurs), revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`, CC BY 4.0. Đây là đánh giá nội bộ subset, không phải điểm XTREME-S chính thức.
