# Bản đồ pipeline B01–B04 và file dùng chung

Sơ đồ luồng logic từ nguồn audio đến báo cáo; không phải mọi node tương ứng một tiến trình độc lập. Mỗi nhánh chạy theo manifest riêng. Reference được đọc để chấm, không truyền làm đầu vào nhận dạng.

## Từ nguồn dữ liệu đến báo cáo

```mermaid
flowchart TB
    RF["FLEURS gốc + transcript"] --> PRE["prepare.py<br/>chọn ID, xuất WAV mono 16 kHz"]
    RS["M4A Galaxy M15<br/>nhãn đã nghe xác nhận"] --> PS["WAV mono 16 kHz<br/>metadata người / phiên / điều kiện"]
    subgraph DATA["WAV và manifest đã chốt"]
        P["Pilot: FLEURS train 10<br/>pilot.csv"]
        F["FLEURS dev100<br/>fleurs_dev100.csv"]
        S["Self dev20<br/>self_dev20.csv"]
    end
    subgraph RUN["Các nhánh đã chạy - từng manifest là một run riêng"]
        W["Whisper-base<br/>openai-whisper / laptop CPU"]
        Z["Zipformer INT8<br/>sherpa-onnx / laptop CPU"]
        Q["Qwen 0.6B<br/>Transformers / Colab A100"]
        PI["Pi 4 / self dev20<br/>nhánh chi tiết bên dưới"]
    end
    PRE --> P
    PRE --> F
    PS --> S
    P --> W
    F --> W
    F --> Z
    F --> Q
    S --> W
    S --> Z
    S --> Q
    S --> PI
    W --> R["Transcript gốc + metadata<br/>B01, B02, B03, B04/results"]
    Z --> R
    Q --> R
    PI --> R
    R --> A["Chấm / kiểm tra dùng chung<br/>common.py + verify_results.py + JiWER"]
    M["Reference + ID/hash từ manifest<br/>chỉ dùng đối chiếu, không đưa nhãn vào ASR"] --> A
    A --> T["Bảng riêng theo dataset và cấu hình<br/>summary.csv / comparison.csv"]
    T --> REPORT["reports/DEMO_BUOI_01_04.md<br/>biểu đồ + số đo + giới hạn"]
    classDef shared fill:#e6f1f7,stroke:#236b8e,color:#17354a;
    class P,F,S,M,A,T shared;
```

| Thành phần dùng chung | File hoặc thư mục thực tế | Vai trò |
|---|---|---|
| Chuẩn bị FLEURS | [prepare.py](../experiments/prepare.py) | Chọn ID và khôi phục WAV pilot/dev; không huấn luyện |
| FLEURS pilot | [pilot.csv](../experiments/manifests/pilot.csv), data/derived/stt_b01_b03/train | 10 câu train cho B01 |
| FLEURS dev | [fleurs_dev100.csv](../experiments/manifests/fleurs_dev100.csv), data/derived/stt_b01_b03/dev | Cùng 100 WAV cho ba model |
| Self dev20 | [self_dev20.csv](../experiments/manifests/self_dev20.csv), data/self_recorded/dev | Cùng 20 WAV cho B02/B03/B04 |
| Runner laptop/Colab | [run_asr.py](../experiments/run_asr.py) | Nạp backend một lần/run; lần lượt nhận dạng WAV |
| Scorer | [common.py](../experiments/common.py) | NFC/chuẩn hóa và WER_ws/CER, được gọi trong runner |
| Audit | [verify_results.py](../experiments/verify_results.py) | ID/reference/audio hash; chấm lại bằng scorer và JiWER |
| Kết quả tự thu laptop | [B02/results/self_dev20](../experiments/B02/results/self_dev20/summary.csv) | Baseline đã lưu, B03 tái sử dụng; không chạy lại trên Colab |
| Kết quả Qwen/so ba model | [B03/results](../experiments/B03/results/summary.csv), [self_dev20](../experiments/B03/results/self_dev20/summary.csv) | Qwen GPU + bảng hợp nhất cùng dữ liệu |

**WAV dùng chung không có nghĩa cùng đường dẫn vật lý.** ZIP chuyển bản sao qua Drive/Colab/Pi. Receipt/hash kiểm tra nội dung và manifest; các ZIP có thể khác hash vì chứa thêm model/code/metadata khác nhau. Gói Pi chứa model Zipformer; Whisper GGML được tải riêng. Không dùng lại tên checkpoint để thay cho kiểm tra file/hash.

## Nhánh Pi và chỗ phép so chưa đồng nhất

```mermaid
flowchart TB
    S["Cùng self dev20 + manifest<br/>sao sang Pi qua ZIP, kiểm tra hash"]
    subgraph ACTUAL["Đã chạy trên Pi 4 / CPU hai luồng"]
        Z["Zipformer INT8<br/>cùng gói model/hash như laptop"]
        ZRUN["Nạp một lần mỗi lượt<br/>20 WAV tuần tự x 2 lượt"]
        ZOUT["zipformer_r1 / zipformer_r2<br/>inference + wall + RAM + transcript"]
        B["Whisper-base / whisper.cpp<br/>smoke một WAV"]
        T["Whisper-tiny / whisper.cpp<br/>khảo sát bổ sung"]
        TRUN["Mỗi WAV mở CLI mới, nạp lại<br/>20 WAV tuần tự x 2 lượt"]
        TOUT["whisper_tiny_r1 / whisper_tiny_r2<br/>wall CLI + RAM + transcript"]
    end
    S --> Z
    Z --> ZRUN --> ZOUT
    S --> B
    B -->|"đã chuyển tiny do chậm"| T
    S --> T
    T --> TRUN --> TOUT
    B -.-> GAP["C0-base/Pi còn thiếu<br/>chưa chạy đủ cùng self dev20"]
    ZOUT --> A["Cùng scorer + audit<br/>chấm riêng từng checkpoint/run"]
    TOUT --> A
    A --> LIMIT["Chất lượng có bảng theo cấu hình<br/>tốc độ chưa cùng chính sách nạp/phạm vi"]
    classDef gap fill:#fff0da,stroke:#bc6b13,color:#653908;
    class GAP,LIMIT gap;
```

| Nhánh | Mã thực thi | Bằng chứng |
|---|---|---|
| Zipformer Pi | [run_zipformer_pi.py](../experiments/B04/run_zipformer_pi.py) gọi runner chung | [measurement r1](../experiments/B04/results/zipformer_r1/measurement.json) |
| Whisper Pi | [run_whisper_cpp_pi.py](../experiments/B04/run_whisper_cpp_pi.py) gọi CLI upstream | [tiny r1](../experiments/B04/results/whisper_tiny_r1/measurement.json), [base smoke](../experiments/B04/results/whisper_base_smoke/measurement.json) |

Zipformer Pi giữ cùng gói model/hash như laptop. Whisper Pi thay runtime; tiny còn thay checkpoint so với base laptop. Hai lượt lặp không bổ sung người/câu mới. C0-base đầy đủ/Pi và phép đo tốc độ cùng chính sách nạp chưa hoàn tất.

## B05 là kế hoạch, không phải kết quả đã chạy

```mermaid
flowchart LR
    AUDIO["Replay WAV theo thời gian thực<br/>micro khi có thiết bị"]
    VAD["VAD / chốt đoạn nếu cần<br/>nạp một lần khi khởi động"]
    ASR["ASR giữ trong RAM<br/>nhận từng đoạn audio"]
    TEXT["Hiện text<br/>lưu thời gian và lỗi"]
    AUDIO -.-> VAD -.-> ASR -.-> TEXT
    classDef planned fill:#f6f7f9,stroke:#6b7280,stroke-dasharray:5 5,color:#374151;
    class AUDIO,VAD,ASR,TEXT planned;
```

Nét đứt = dự kiến. Có thể ghép VAD với ASR offline, không đồng nghĩa ASR có streaming nguyên sinh. VAD không phải bước bắt buộc cho mọi backend; chỉ thêm nếu phù hợp cách chốt đoạn đã chọn. Chưa triển khai pipeline này hoặc ghi nhận demo với thầy.
