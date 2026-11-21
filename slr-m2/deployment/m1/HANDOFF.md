# Bàn giao M1 để triển khai nhận dạng trực tiếp ở M2

M1 đã chốt theo quyết định của nhóm. Agent nhận bàn giao có thể bắt đầu triển khai M2 từ mã nguồn và checkpoint trong gói ZIP. M1 đã chạy nhận dạng trên Mac từ video ghi sẵn tới kết quả 07b. Phần còn lại của M1 gồm đánh giá trên video dành riêng và đối chiếu toàn trình với bộ nạp dữ liệu đánh giá của notebook.

## Cấu hình đã chốt

- Hai tay ở tư thế nghỉ liên tục **0,35 giây** để vào trạng thái sẵn sàng hoặc xác nhận kết thúc một ký hiệu. Khi đã sẵn sàng, ít nhất một tay duy trì tư thế hoạt động **0,35 giây** để xác nhận bắt đầu. Mốc bắt đầu được tính từ khung hình hoạt động đầu tiên của khoảng đó.
- Giữ thêm tối đa 0,30 giây trước và 0,20 giây sau chuyển động. Nghỉ đủ 1,5 giây có thể kết thúc lượt ký hiệu hiện tại. Phiên nhận dạng kết thúc bằng nút **Kết thúc phiên**.
- Dùng `deployment/m1/frozen-config.json`. Cấu hình mặc định trong `segmenter.py` khớp tệp này. Lệnh demo ngắn trong README có cấu hình riêng.
- Dùng mô hình SL-GCN bone từ notebook 07b, run `07b_bone_seed42`. Đầu vào gồm 150 vị trí thời gian × 28 nút × 8 kênh. Bộ chuyển đổi lặp clip ngắn, giữ 150 khung đầu của clip dài, và căn tọa độ nút gốc theo cửa sổ đánh giá.
- Checkpoint nằm ở `models/checkpoints/sl_gcn_bone_07b/07b_bone_seed42` cùng bản chụp mã huấn luyện, cấu hình và bảng nhãn. SHA-256 của `best.pt` là `7934805bf89a912bc2d450c83facc19d73a72d5b22beb38189968ff6ff2bbddf`.

## Khởi động từ thư mục gốc sau khi giải nén

Dùng Python 3.11. Nếu lấy mã qua Git, đặt thư mục checkpoint vào đúng đường dẫn ở trên trước khi chạy preflight.

```sh
python3.11 -m venv deployment/.venv-m1
deployment/.venv-m1/bin/python -m pip install -r deployment/m1/requirements.txt
deployment/.venv-m1/bin/python -m deployment.m1 preflight
deployment/.venv-m1/bin/python -m unittest deployment.m1.test_segmenter
```

Để chạy lại M1 trên Mac với video của bạn:

```sh
m1_video="$(osascript -e 'POSIX path of (choose file with prompt "Chọn video ký hiệu")')" &&
  m1_run="$(deployment/.venv-m1/bin/python -m deployment.m1 replay "$m1_video" --config deployment/m1/frozen-config.json)" &&
  deployment/.venv-m1/bin/python -m deployment.m1 serve "$m1_run"
```

Mở http://127.0.0.1:8765/ khi máy chủ đã chạy. Gói bàn giao không chứa video cá nhân, tập dữ liệu hoặc môi trường Python đã cài.

## Việc đầu tiên cho agent M2

1. Chạy preflight và kiểm thử ở trên. Đọc `deployment/m1/segmenter.py` để dùng lại `Config`, `arm_states` và `Segmenter.feed`. Đọc `replay.py` và `inference.py` trong cùng thư mục để nối đúng bộ tiền xử lý và mô hình 07b. Dùng video replay làm mốc đối chiếu khi thay nguồn video bằng camera.
2. Thêm nguồn camera trực tiếp. Đưa khung hình và dấu thời gian tăng dần vào bộ phân đoạn, giữ đủ khung trước khi bắt đầu để tạo phần đệm. Khi đoạn hoàn chỉnh, chuyển clip qua cùng đường tiền xử lý và suy luận như M1. Giữ thứ tự kết quả, kể cả khi hai ký hiệu liên tiếp giống nhau. Hiển thị mỗi gloss khi có kết quả và tiếp tục nhận khung hình trong lúc suy luận.
3. Hỗ trợ nút **Bắt đầu phiên** và **Kết thúc phiên**. Khi bấm kết thúc, dừng nhận khung hình, xử lý nốt các đoạn đã hoàn chỉnh, đánh dấu đoạn đang mở là chưa hoàn chỉnh và chốt lượt ký hiệu còn lại. Giữ kết quả đã nhận dạng trên màn hình. Thử đếm ngược **3–2–1** cho lúc bắt đầu ở bước sau.
4. Kiểm tra trước trên Mac với một video hoặc phiên camera có ba ký hiệu cách nhau bằng tư thế nghỉ. Kiểm tra ký hiệu lặp, giữ tay trên cao, mất dấu cổ tay, và bấm kết thúc giữa chuyển động. Sau đó mới chuyển đường camera và giao diện sang thiết bị đích. Ghi thời gian từ khi người ký kết thúc động tác đến khi gloss xuất hiện để có số đo ban đầu.

Khi người ký tiến về máy, cổ tay có thể ra khỏi khung và trạng thái có thể chuyển sang `UNKNOWN`. Bộ phân đoạn dùng mốc cổ tay của bộ phát hiện dáng người. Kiểm tra trực tiếp với góc máy thật. Động tác tiến lại gần vẫn có thể tạo dự đoán nếu đã thành một đoạn hoàn chỉnh trước khi bấm nút.

## Bằng chứng kiểm tra

Video_03.mov cho ba đoạn hoàn chỉnh có dự đoán trong lần chạy trước. Chạy lại bộ phân đoạn trên tín hiệu dáng người đã lưu với cấu hình chốt 0,35 giây cho cả hai ngưỡng vẫn cho ba đoạn hoàn chỉnh. Kiểm tra này xác nhận kết quả phân đoạn trên mẫu đó. Chưa chạy lại mô hình từ video gốc với cấu hình mới và chưa đánh giá khả năng nhận dạng trực tiếp.
