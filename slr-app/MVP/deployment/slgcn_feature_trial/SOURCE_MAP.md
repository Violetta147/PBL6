# Bản đồ tài nguyên SL-GCN bone cũ

Đối chiếu ngày04/11/2026; chỉ đọc tài nguyên Drive/Colab.

## Hai đường dẫn có vai trò khác nhau

- Notebook: https://colab.research.google.com/drive/1QN6E4MWz8e8zfIvgeeEAbAk7fEx4Ta-Z
  Tên SLGCN_bone_VSL400_Colab.ipynb. Có15 ô, trong đó14 ô code.
  Tất cả14 ô code hiện tại có nguyên nội dung trong bản audit notebook trước đây.
  Notebook là quy trình thực hiện; không cần chạy lại các cell để triển khai checkpoint.
- Thư mục kết quả: https://drive.google.com/drive/folders/1DqNyXoOtxtVN-MDaO9idE1rnnrVQPVeU
  Đây là SLGCN_bone_adapt_v1. Nhánh gốc là runs/stage2_20261015_004947_10dd94/.

## Đọc theo thứ tự này

| Vị trí bên trong run stage2 | Vai trò |
|---|---|
| full/trainval_v3_seed42_60ep_v1/config.json | Cấu hình của lần train đủ60 epoch; số lớp/điểm, nguồn adapter, temporal/quality policy và hash |
| full/.../result.json | Xác nhận hoàn thành; checkpoint tốt nhất ở epoch52, chọn bằng validation |
| full/.../source/slgcn_xy_adapter.py + team_repair.py | Chính xác phép chuyển dữ liệu đã dùng cho model này |
| full/.../source/cell08_pilot_cache_v1.py | Kiểm tra feature, tái dựng hình học, cache, masks và prepare_input |
| full/.../source/cell09_pilot_train_v1.py + cell11_full_train_v1.py | Định nghĩa cấu hình/model và mã huấn luyện |
| full/.../source/official/ | Mã model/graph SL-GCN tại commit đã chốt |
| full/.../best.pt và checkpoints/best_epoch_052.pt | Checkpoint tốt nhất; hash giống bản trên Pi |
| full/.../test_once_v1/test_metrics.json | Kết quả test offline3714 mẫu: Top1=89,5261%; không phải accuracy camera |
| inputs/label_map_v1.json + split_v1/ | Ánh xạ400 nhãn và phân chia train/validation/test |
| cache/subset_quality_v3_022031_55854f/ | Cache36 mẫu TRAIN ở giai đoạn QC; gói này đối chiếu2 mẫu với cache này |
| qc/cell02_005640_dcc1f3/raw_npz/ | Bản sao feature nguồn của các mẫu QC, dùng để kiểm tra phép chuyển |
| pilot/ + sanity/ + các cache subset đời trước | Lịch sử thử nghiệm/kiểm tra; không tự chọn checkpoint hoặc adapter bất kỳ ở đây |
| config/resume_latest.json | Trạng thái nối phiên từ giai đoạn cũ; có cờ chưa được cập nhật. Không dùng riêng file này để kết luận full training chưa hoàn thành |

## Định danh để tránh lấy nhầm

Full run: https://drive.google.com/drive/folders/1fzqTYr_JYvuQwZHcGPRnb8UXH0M4pXyo

Checkpoint SHA256:
cd742dadd5b6d7aa1e4c742d618c78a9f616cfda7a6d5d968e14996f4f2e544f

Adapter SHA256:
d4ef152c29aab4986fff558a105abfdf3382055dd9c2e90b1d2aee158c8f5bd8

Repair SHA256:
065fd21c4179524805d580ee1036f8a8f62096a85e73c1f24bca001023ea1bbe

Các filename source bị lặp đôi trong full/source đã được so nội dung byte: adapter trùng
nhau, repair trùng nhau và hash khớp config. Không lựa chọn chỉ dựa vào ngày sửa hoặc tên.

Đây không phải SLGCN_temporal_sampling_v1 đã dừng, cũng không phải pipeline raw mới của
PBL6_Revamped. Không huấn luyện lại, không sửa Drive hoặc notebook trong lần kiểm tra này.
