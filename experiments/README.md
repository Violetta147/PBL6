# Thực hành buổi 1–3

Mã dùng chung nằm tại đây; mỗi buổi có một notebook và thư mục `results` riêng. Không training. Dữ liệu lớn và model ở `data/` được Git bỏ qua. Kết quả chỉ được coi là đã đo khi có JSONL và `.run.json` từ lần chạy thật.

1. `python experiments/prepare.py`: chọn seed 42, khôi phục 10 WAV train pilot và 100 WAV dev, lưu 200 ID test mà không khôi phục WAV/nhãn test vào gói Colab.
2. Mở notebook B01/B02/B03 trong Colab, chọn GPU, upload `data/derived/stt_b01_b03_package.zip` khi được hỏi. B03 có thể chạy cả ba buổi; output vẫn tách theo buổi. Colab Pro cấp GPU nào thì ghi GPU đó.
3. Tải ZIP kết quả bằng cell cuối; giữ output, metadata môi trường và bảng. Không ngắt runtime trước khi tải.
4. Thu 20 câu dev thật theo `B02/THU_AM.md`, tạo manifest bằng `import_self.py`, rồi chạy phần dữ liệu tự thu của B03. Chưa có audio thì mục này vẫn chưa hoàn thành.

Chạy local cũng được: cài các thư viện cần cho checkpoint đang chạy rồi dùng `run_asr.py --model whisper|zipformer|qwen --manifest ... --output ... --device cpu|cuda`. Mỗi run có manifest/scoring/code hash. Chạy lại cùng cấu hình tiếp tục các mẫu chưa ghi; dùng đường dẫn output mới nếu đổi mã/cấu hình. Run đã ghi lỗi không tự âm thầm chạy lại hoặc bỏ lỗi. Tốc độ local/Colab không phải số đo Pi.

WAV nguồn FLEURS là IEEE float. `prepare.py` cần `soundfile==0.14.0` và tạo bản dẫn xuất PCM16 mono16kHz để các backend dùng cùng audio. Không resample hoặc thay header giả; rate giữ nguyên. Manifest lưu hash của cả nguồn lẫn bản dẫn xuất, archive raw không đổi.

Qwen tải vào `local_dir` theo revision để không cần quyền tạo symlink trên Windows; không thay đổi Developer Mode/quyền hệ thống. Backend dùng PyTorch, tắt việc import TensorFlow/Flax không cần thiết để giảm RAM. Lần local CPU và lần Colab GPU dùng output riêng; không ghi đè kết quả cũ.

Kiểm tra: `python -m unittest discover -s experiments/tests -v`. `jiwer==4.0.0` cung cấp kiểm tra độc lập cho khoảng cách edit. Notebook JSON và code cell được kiểm tra khi chạy `make_notebooks.py`.

Nguồn runtime: [Whisper](https://github.com/openai/whisper), [Zipformer ONNX](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/zipformer-transducer-models.html), [Qwen3-ASR](https://huggingface.co/Qwen/Qwen3-ASR-0.6B). Phiên bản package được ghim; các phụ thuộc thực tế và checkpoint hash/revision được lưu trong metadata. FLEURS: [google/fleurs](https://huggingface.co/datasets/google/fleurs), revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`, CC BY 4.0. Đây là đánh giá nội bộ subset, không phải điểm XTREME-S chính thức.
