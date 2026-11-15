# Thử chuyển đặc trưng sang đầu vào SL-GCN bone cũ

Gói này chỉ chuẩn bị đầu vào, chưa nạp model hoặc nhận dạng ký hiệu.
Nguồn Drive chỉ được đọc; các bản sao và kết quả thử nằm trong thư mục này.

## Đúng nguồn nào?

Nguồn: SLGCN_bone_adapt_v1/runs/stage2_20261015_004947_10dd94/
full/trainval_v3_seed42_60ep_v1. Huấn luyện đủ 60 epoch, chọn epoch52 bằng validation.
Checkpoint SHA256 cd742dadd5b6d7aa1e4c742d618c78a9f616cfda7a6d5d968e14996f4f2e544f
trùng bản đã smoke-test trên Pi. Test offline 89,5261%, chưa phải accuracy camera.

Hai file vendor được sao nguyên byte từ source của run huấn luyện hoàn chỉnh.
SHA256 của chúng khớp config huấn luyện; hai bản trùng tên trên Drive đã được so sánh
và có nội dung giống nhau. Không chạy lại notebook hoặc mã huấn luyện đã tải.
Các cờ candidate/subset trong adapter_policy là metadata kế thừa từ thí nghiệm trước;
trạng thái run hoàn chỉnh phải xem reference/training_result.json và test_metrics.json.

## Chuyển như thế nào?

1. Nhận feature chuẩn hóa CŨ, preprocessing1.1.0; không nhận raw v3 của Revamped.
2. Tái dựng tọa độ trong hệ thân, chọn 7 điểm thân +10 điểm mỗi tay =27 điểm.
3. Dùng nguyên quality gate/repair: gap nội bộ ngắn<=5, không lấp mép, không sửa qua
   vùng bị loại vì chất lượng. Ngưỡng cổ tay1,0 theo độ rộng vai là heuristic của dự án.
4. Theo chính sách huấn luyện cũ: dưới150 frame thì lặp chuỗi theo chỉ số modulo T.
   Với121 frame, lấy121 frame rồi lặp29 frame đầu. Không nội suy thời gian lên150 frame.
   Trên150 frame sẽ dừng, chỉ lấy150 frame đầu nếu có --allow-training-truncation rõ ràng.
5. Chuyển tọa độ khớp thành bone, đặt0 ở bone thiếu theo mask, center root trên frame hợp lệ.
6. Đầu vào cuối: float32, (1,2,150,27,1) = batch, X/Y, thời gian, điểm, người.

## Kiểm chứng đã chuẩn bị

- Hai TRAIN sample014615 và020536 từ QC cũ, không phải tập test.
- So sánh trực tiếp bone, toàn bộ masks/provenance với cache36 sample đã lưu từ trước.
- Kiểm tra hash file nguồn/cache bằng manifest lịch sử; không dùng output mới làm đáp án.
- Kiểm tra input sau centering với công thức áp dụng trên cache cũ.
- Bài thử regression kiểm tra schema mới bị từ chối, Inf/hình học sai, cắt chuỗi cần opt-in,
  và các mảng nguồn giữ nguyên. Không có train/validation/test accuracy mới.

## Chạy trên Pi sau khi người dùng đồng ý

Chép cả thư mục này vào ~/pbl6_edge_islr/slgcn_feature_trial rồi chạy:

```bash
"$HOME/pbl6_edge_islr/.venv/bin/python" "$HOME/pbl6_edge_islr/slgcn_feature_trial/prepare_clip.py"
```

Lệnh mặc định đọc ../feature_extract/latest_result.json để tìm lần xuất feature trên Pi.
Chỉ dùng NumPy có sẵn. Trước xử lý camera, kiểm tra bundle và hai mẫu TRAIN tham chiếu.
Lưu vào results/<UTC>/input_tensor.npy, adapter_debug.npz và metadata.json;
latest_result.json chỉ trỏ tới kết quả mới. Không sửa feature, video hoặc checkpoint cũ.

Trên laptop có thể truyền --features đường dẫn features_raw.npz. Phải có metadata.json
và capture_read_complete_seconds.npy bên cạnh, như bộ4 file đã chép từ Pi.

## Giới hạn cần giữ rõ

Hai mẫu đối chiếu đạt không chứng minh toàn dataset tương đương. Chưa có forward thật
từ tensor này, CPU/GPU logit parity, accuracy ký hiệu camera hay độ trễ end-to-end.
Clip121 frame chỉ là clip kiểm tra tư thế/chuyển động, không có nhãn ký hiệu.
Timestamps header0..4s và read-completion thực tế khoảng0,056..8,009s được giữ riêng;
gói dùng chính sách số frame của training, chưa giải quyết chênh lệch tốc độ quan sát.
Các thời điểm lặp theo chỉ số không phải timeline liên tục mới. Capture read-completion
không phải thời điểm phơi sáng cảm biến. Không gọi đây là dataset raw của Revamped.
