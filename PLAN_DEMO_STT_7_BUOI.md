# Kế hoạch lean: 7 buổi học và demo STT

Phiên bản 2.0 — cập nhật tiến độ 10/10/2026. Một người phụ trách STT, một buổi gặp thầy mỗi tuần, còn bảy tuần. Buổi 1 là lần gặp tiếp theo; chưa có ngày cụ thể. Kết quả đã chạy và phần còn thiếu được ghi tại [tiến độ thực hành](experiments/PROGRESS.md).

Mục tiêu là học cách dùng model có sẵn, so sánh có căn cứ và tìm phương án cho Pi 4. Làm theo [đặc tả lean](SPEC_ASR_PI4_RESEARCH_20261009.md); kiến thức cần tra ở [ghi chú khái niệm](REVIEW_CONCEPTS_20261009.md). Không cần hoàn thiện một sản phẩm lớn trước khi có thứ để demo.

## Nhịp làm việc mỗi tuần

Chọn một đầu ra nhỏ, làm cho chạy được, lưu output rồi tập demo khoảng 3–5 phút. Trình bày: tuần này thêm gì → cho thấy kết quả → một lỗi/điều học được → bước tiếp theo. Video ngắn và bảng đã lưu là dự phòng khi mạng/thiết bị lỗi; luôn nói rõ live hay ghi trước. Không lấy output người khác hoặc dữ liệu mock làm kết quả model của nhóm.

Giữ một notebook so sánh, script/CLI Pi khi cần, một bảng kết quả và ghi chú tiến độ ngắn. Chưa cần UI, dashboard hoặc báo cáo riêng từng stage. Mỗi thay đổi mã hoàn chỉnh cập nhật tài liệu/test, chạy kiểm tra liên quan rồi commit theo `AGENTS.md`.

## Bảy buổi

| Buổi | Phần mới đem demo | Thử nghiệm |
|---|---|---|
| B01 | Một audio tiếng Việt → text bằng Whisper | T1 |
| B02 | Whisper và Zipformer trên cùng audio, cùng WER/CER | T2, phần đầu |
| B03 | Thêm Qwen3-ASR, hoàn thành bảng so sánh ba model trên dev | T2, hoàn tất |
| B04 | Model nhỏ chạy trên Pi, có số đo tốc độ/RAM | T3 |
| B05 | Thu micro → chữ và xem lỗi trong điều kiện thực tế | T4 |
| B06 | Bảng đánh giá cuối trên test và xác nhận cấu hình Pi | T5 |
| B07 | Demo cơ bản, kết luận lựa chọn, báo cáo ngắn | Tổng hợp |

Buổi 1–5 dùng pilot/dev để học và điều chỉnh. Test chỉ dùng đánh giá sau khi chốt ở cuối buổi 5. Câu trình diễn thầy nói trực tiếp là minh họa, không tự trở thành điểm benchmark.

## B01 — Chạy một câu qua baseline

- [x] Chọn 10 audio FLEURS train; kiểm tra transcript và input.
- [x] Chạy C0 Whisper-base, lưu text và model/môi trường; lần đã đo dùng CPU laptop do Computer Use/Colab lỗi, notebook Colab có sẵn để chạy lại.
- [ ] Nghe một mẫu, đối chiếu nhãn/output, tính một WER bằng tay; kiểm kê Pi/micro.

**Demo:** phát audio và hiện text do model tạo. Chỉ ra model nhận đúng/sai ở đâu. **Xong khi:** chạy lại được, output có lưu và giải thích được audio → model → text. Chưa cần Pi inference hoặc bộ chấm hoàn chỉnh trong buổi đầu.

## B02 — So hai model và học cách chấm

- [x] Viết hàm chuẩn hóa/scorer chung; kiểm tra dấu tiếng Việt, lỗi chèn/xóa/thay và nhãn rỗng bằng đáp án tính tay.
- [x] Chạy C0/C1 trên 100 FLEURS dev đã chọn cố định; giữ đủ output/status.
- [ ] Thu và kiểm tra khoảng 20 câu dev của nhóm, ghi điều kiện và người/phiên; chuẩn bị kế hoạch test tách biệt.

**Demo:** cùng một audio hiện hai transcript và cách tính WER/CER; mở bảng dev, chỉ một khác biệt đáng chú ý. **Xong khi:** hai model được chấm cùng dữ liệu/quy tắc. Nếu chưa đủ nhãn tự thu, hoàn thành trước khi chốt cấu hình ở B05.

## B03 — Thử model mới và hoàn thành so sánh

- [x] Chạy C2 Qwen3-ASR-0.6B trên Colab A100 bằng Transformers; đủ 100/100 cùng subset dev, output và metadata đã lưu.
- [x] Chấm ba model trên 100 FLEURS dev; chấm lại bằng JiWER khớp, bảng ba model đã lưu.
- [ ] Chấm ba model trên 20 câu tự thu dev, giữ bảng riêng; audio thật chưa có.
- [ ] Nghe 3–5 lỗi, ghi model nào đáng thử trên Pi; dùng điểm dev, không mở test để chọn.

**Demo:** ba transcript cạnh nhau và bảng chất lượng; [kịch bản B03](experiments/B03/DEMO.md) có năm audio để nghe. Trên dev đã đo, Zipformer WER_ws 7,5080%, Qwen 9,7605%, Whisper-base 49,3743%. Giải thích model mới năm 2026 giúp nghiên cứu điều gì, không mặc định nó thắng hoặc phải chạy trên Pi. **Xong khi:** có bảng ba model, output từng mẫu và nhận xét có căn cứ; bảng tự thu vẫn cần trước chốt B05.

Nếu C2 không chạy được sau khoảng một ngày xử lý môi trường, dùng PhoASR thay thế theo đặc tả và ghi lý do. Không dành tuần này mở thêm nhiều model/vLLM hoặc sửa môi trường không phục vụ inference cơ bản.

## B04 — Đưa model nhỏ lên Pi

- [ ] Chạy C0/C1 với runtime có sẵn trên Pi; nếu C0 quá chậm, thử tiny dự phòng.
- [ ] Dùng 20 tệp dev cố định, hai lượt; ghi thời gian/RTF, RAM và nhiệt, phân biệt thời gian nạp model.
- [ ] Chọn ứng viên demo; với backend đổi giữa Colab và Pi, kiểm tra vài output và ghi khác biệt.

**Demo:** Pi xử lý WAV thật, hiện text và bảng tốc độ/RAM. **Xong khi:** có kết quả từ Pi, biết cấu hình dùng gì và chọn bằng số đo. Tốc độ WAV chưa được gọi là đạt xử lý hội thoại liên tục.

Nếu Pi vướng cài đặt, dùng output/video đã chạy thành công nếu có; nếu chưa, báo lỗi thực tế và demo phần tệp trên máy tính. Cắt mọi phần mở rộng để ưu tiên Pi, không trình bày xử lý ngoài Pi như xử lý cục bộ.

## B05 — Thử micro và các trường hợp thực tế

- [ ] Dùng ví dụ micro + VAD có sẵn, hiện final trên terminal/màn hình; chưa cần partial hay kính thật.
- [ ] Thử 5–10 phút: câu ngắn, nghỉ, ồn, số/phủ định. Dùng dev để xem lỗi do model, mức thu hay chia đoạn; chỉ chỉnh đơn giản khi cần.
- [ ] Hoàn tất 30–50 câu tự thu test và khoảng 2 phút không có lời nói; chốt model/runtime/scoring/VAD và các ID test trước B06.

**Demo:** nói vào micro và thấy chữ; cho thấy một trường hợp khó cùng nhận xét. **Xong khi:** luồng cơ bản hoạt động, giới hạn được ghi và cấu hình cuối đã chốt. Có thể dùng nhận từng lượt nếu chưa theo kịp nói liên tục.

Nếu chưa có micro, replay WAV theo tốc độ thực qua cùng VAD/ASR và gọi đúng là replay. Giữ phần demo tệp ở B04 chạy được. Màn hình kính chỉ nối nếu đã sẵn sàng và không làm chậm đánh giá.

## B06 — Đánh giá cuối

- [ ] Chạy ba model trên 200 FLEURS test cố định và 30–50 câu tự thu test với quy tắc đã chốt; giữ cả lỗi/timeout.
- [ ] Chấm bản model/runtime thực sự chọn trên Pi bằng tập tự thu test; ghi backend riêng nếu khác Colab.
- [ ] Thử micro/replay cuối 5–10 phút và audio không có lời nói; tổng hợp chất lượng, tốc độ/RAM, khoảng chờ và lỗi.

**Demo:** bảng test và vài lỗi thật, kèm clip chạy Pi. Giải thích phương án chọn và phần chưa đáp ứng. **Xong khi:** bảng có đúng tập, số mẫu, cấu hình/thiết bị và bằng chứng; chưa đạt một chỉ số vẫn được báo cáo trung thực.

Không lấy lỗi test để sửa rồi gọi bản sau là đánh giá độc lập. Nếu run ngắt, tiếp tục phần thiếu với cùng cấu hình; báo bảng một phần đúng trạng thái. Không cần chạy toàn bộ benchmark lại trên lớp hoặc làm thống kê suy luận phức tạp.

## B07 — Demo và báo cáo điều đã học

- [ ] Viết cách khởi động notebook/CLI và kiểm tra một lượt nhỏ chạy lại được.
- [ ] Hoàn thiện báo cáo khoảng 4–6 trang: mục tiêu, model/dữ liệu, cách đo, kết quả, lỗi, lựa chọn và giới hạn.
- [ ] Chuẩn bị demo 3–5 phút, video dự phòng và bảng kết quả lưu trên laptop; bàn giao mã/output.

**Demo:** micro → text, hoặc chế độ từng lượt với giới hạn rõ; mở bảng để giải thích vì sao chọn model. **Xong khi:** có pipeline cơ bản, kết quả kiểm tra được và báo cáo khớp output. Không cần chứng minh đã làm kính hoàn chỉnh hoặc thuật toán mới.

## Việc song song và cách giảm tải

Kiểm tra/mượn micro từ B01. Thu dev ở B02, test từ B04 và hoàn tất trước chốt B05; ưu tiên người khác nhau giữa dev/test, nếu không thì tách phiên và ghi giới hạn. Lưu output và vài dòng ghi chú sau mỗi lượt thử, không đợi tuần cuối. Bảng/log là bằng chứng nghiên cứu; vài câu đẹp để demo không thay thế toàn tập đánh giá.

Khi chậm, bỏ model mở rộng, partial và phần tích hợp kính chưa có. Giữ ba việc: so model, đo Pi và demo audio → chữ. Không bắt buộc đủ 35 bước ML, stress test nhiều lượt, khoảng tin cậy, giao thức phụ đề riêng hoặc nhiều lớp phần mềm.

## Theo dõi ngắn gọn

- [ ] B01: baseline chạy được.
- [ ] B02: hai model và scorer chung.
- [ ] B03: bảng dev ba model.
- [ ] B04: số đo Pi.
- [ ] B05: micro và cấu hình chốt.
- [ ] B06: kết quả test.
- [ ] B07: demo/báo cáo cuối.

Sau mỗi buổi, thêm vài dòng: commit/notebook nào, kết quả mới, vị trí output, lỗi và phản hồi thầy. Không cần một bộ báo cáo tiến độ riêng. Khi làm với Codex có thể yêu cầu: “Thực hiện B01 theo kế hoạch lean, kiểm tra phần đã có, làm phần tối thiểu, thử và commit; chưa làm sang B02.”
