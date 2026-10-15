---
marp: true
theme: default
size: 16:9
paginate: false
lang: vi
title: Nhận dạng tiếng Việt trên Raspberry Pi 4
backgroundImage: url('themes/dut/content.png')
footer: PBL6 · Báo cáo tiến độ STT
style: |
  section {
    font-family: Arial, sans-serif;
    color: #14364e;
    font-size: 29px;
    line-height: 1.4;
    padding: 42px 64px 128px;
    justify-content: flex-start;
    background-size: cover;
  }
  h1 { font-size: 52px; line-height: 1.16; }
  h2 { color: #075486; font-size: 39px; line-height: 1.2; margin: 0 0 26px; }
  p { margin: 0 0 22px; }
  strong { color: #075486; }
  a { color: #075486; text-decoration: underline; }
  table { display: table; width: 100%; font-size: 25px; margin: 15px 0 22px; }
  th { color: #075486; background: #e8f1f6; }
  th, td { padding: 13px 17px; border-color: #b7c9d5; }
  tr:nth-child(2n) { background: #f3f7fa; }
  footer { left: 64px; bottom: 97px; color: #526777; font-size: 16px; }
  section.cover { color: white; padding: 174px 68px 130px 340px; }
  section.cover h1 { color: #ffe600; margin: 0 0 22px; }
  section.cover strong, section.cover p { color: white; }
  section.cover p { font-size: 26px; margin: 0 0 21px; }
  section.cover footer { display: none; }
  section.chart h2 { margin-bottom: 8px; }
  section.chart p { font-size: 24px; margin: 0 0 10px; }
  section.chart img { display: block; height: 400px; width: auto; margin: auto; }
  section.flow img { display: block; width: 100%; height: 360px; object-fit: contain; }
  section.flow p { font-size: 26px; }
  section.next img { display: block; width: 100%; height: 235px; object-fit: contain; }
  section.formula p:first-of-type { margin: 20px 0 35px; padding: 20px 22px; background: #e8f1f6; font-size: 34px; }
  section.example table { max-width: 800px; font-size: 27px; }
  section.references p { font-size: 25px; }
---

<!-- _class: cover -->

<!-- _backgroundImage: url('themes/dut/cover.png') -->

# Nhận dạng tiếng Việt trên Raspberry Pi 4

**Báo cáo tiến độ STT**

Phần phụ đề cho đề tài hỗ trợ giao tiếp bằng kính thông minh.

Nguyễn Hữu Minh Quân  
GVHD: TS. Ninh Khánh Duy

<!--
Báo cáo phần STT do Nguyễn Hữu Minh Quân thực hiện; thông tin GVHD lấy từ mẫu người dùng cung cấp. Mở đầu: “Em phụ trách phần nhận dạng tiếng nói tiếng Việt cho hướng kính thông minh. Bốn buổi đầu giúp em hiểu đầu ra của model, so các cấu hình có sẵn và thử ứng viên trên Pi thật. Hiện mới chạy được WAV thành chữ; phần audio liên tục và hiển thị còn là bước tiếp theo.”

Phạm vi là đề tài học tập, một người thực hiện. Chưa huấn luyện lại, chưa có bản kính hoàn chỉnh, chưa triển khai cho người dùng. Số liệu trong deck lấy từ kết quả đã lưu ngày 13/10/2026; tạo slide ngày 15/10/2026 không tạo kết quả benchmark mới.

Đây là file trình chiếu mới. reports/DEMO_BUOI_01_04.md vẫn giữ vai trò tài liệu giải thích và tra cứu.
-->

---

## Bài toán và phạm vi

Phần STT cần chuyển lời nói tiếng Việt thành chữ để hiển thị phụ đề.

Câu hỏi hiện tại là cấu hình có sẵn nào cho ít lỗi và chạy được trên Pi 4. Đề tài chưa huấn luyện lại model; trước hết thử WAV, sau đó mới nhận audio đến dần.

<!--
Baseline là cấu hình ban đầu để đối chiếu. B01 dùng Whisper-base trên 10 câu pilot từ FLEURS train, chỉ inference, không huấn luyện. B02 so Whisper-base và Zipformer trên FLEURS dev100. B03 thêm Qwen trên cùng dev100, sau đó so cả ba trên self dev20. B04 đo Pi.

Đây là bốn mốc nội dung, không khẳng định đã trình bày đủ bốn buổi với supervisor. B04 có kết quả Zipformer nhưng chưa hoàn tất đối chiếu Whisper-base/Pi. C0 là Whisper-base, C1 là Zipformer trong kế hoạch.
-->

---

## Model và runtime

ASR là bài toán nhận dạng tiếng nói thành văn bản. Model đã học mối liên hệ giữa âm thanh và chữ; runtime là phần mềm thực thi model.

| Cấu hình | Nơi chạy |
|---|---|
| Whisper-base / openai-whisper | CPU laptop |
| Zipformer-30M INT8 / sherpa-onnx | CPU laptop và Pi |
| Qwen3-ASR-0.6B / Transformers | A100 trên Colab |

<!--
Whisper-base là baseline đa ngôn ngữ, Zipformer là ứng viên tiếng Việt nhỏ cho CPU; Qwen là model mới để đối chiếu. Các hệ thống khác checkpoint, dữ liệu train, kích cỡ và runtime, chưa cô lập riêng kiến trúc. Nguồn: cấu hình từng run và Hugging Face Audio Course.
-->

---

<!-- _class: flow -->

## Thiết kế thí nghiệm

![Các nhánh xử lý và thành phần dùng chung](figures/slides_overview.svg)

Ba cấu hình nhận cùng WAV và được chấm theo cùng nhãn, cùng quy tắc. Nhãn chuẩn chỉ dùng để đối chiếu đầu ra.

<!--
Giải thích từ trái sang phải: chuẩn bị audio và danh sách mẫu; chạy model trên thiết bị phù hợp; lưu chữ model sinh ra; đối chiếu nhãn chuẩn; tổng hợp kết quả. Nhánh Pi chỉ nhận self dev20, nhánh laptop/Colab nhận dev100 và self20. Pilot riêng ở B01 chỉ dùng Whisper-base.

“Dùng chung” là cùng nội dung/phiên bản đã kiểm tra hash. Colab/Pi nhận bản sao qua ZIP, không dùng chung một đường dẫn vật lý. Manifest chứa ID, đường dẫn, nhãn và metadata. Scorer nằm trong runner, rồi verify_results.py chấm lại bằng JiWER để kiểm tra.

Nguồn sơ đồ Mermaid: diagrams/slides_overview.mmd. Nhúng SVG đã render để slide không phụ thuộc khả năng hiển thị Mermaid của trình xem.
-->

---

<!-- _class: formula -->

## Cách tính WER_ws

**WER_ws = (S + D + I) / N × 100%**

S là số đơn vị bị thay, D bị xóa, I bị chèn. N là số đơn vị trong nhãn chuẩn.

Ở đây mỗi đơn vị được tách bằng khoảng trắng, thường là một tiếng trong tiếng Việt. Chưa dùng bộ tách từ.

<!--
WER_ws dùng tổng số lỗi thay/xóa/chèn chia tổng đơn vị reference trên tập, không lấy trung bình đơn giản từng câu. Có thể vượt 100% nếu chèn nhiều. Reference rỗng cần kiểm tra riêng; không chia cho 0. Nguồn: experiments/common.py và https://jitsi.github.io/jiwer/usage/.
-->

---

<!-- _class: formula -->

## Cách tính CER

**CER = (S_c + D_c + I_c) / C × 100%**

Các lỗi được đếm theo ký tự; C là số ký tự của nhãn chuẩn sau bỏ khoảng trắng.

Nhãn và đầu ra cùng chuẩn hóa NFC, chữ thường và dấu câu. Dấu tiếng Việt vẫn được giữ.

<!--
S_c, D_c, I_c là lỗi thay/xóa/chèn theo ký tự. Quy tắc bỏ khoảng trắng là quy tắc của dự án. NFC gom các biểu diễn Unicode tương đương; không sửa nội dung. Ví dụ riêng cọ nhận thành cộ: 1/1 tiếng sai và 1/2 ký tự sai, WER_ws 100%, CER 50%. Đây là minh họa, không phải điểm corpus. Code trả về tỷ lệ 0–1, slide nhân 100 để hiển thị phần trăm.
-->

---

<!-- _class: example -->

## Đối chiếu lỗi nhận dạng · B01

| Nhãn chuẩn | Whisper |
|---|---|
| cây | cái |
| cọ | cộ |
| lá | là |
| nhọn | nhỏ |

Mẫu này có **4 lỗi thay trên 13 đơn vị**, nên WER_ws là **30,77%**.

[Nghe câu mẫu](../data/derived/stt_b01_b03/train/18182759805207678941.wav)

<!--
Demo: phát đoạn audio, chỉ bốn cặp in đậm rồi giải thích phép chia. Người thực hiện đã nghe và xác nhận nhãn của mẫu này. Không nói đã nghe toàn bộ pilot.

WER_ws = (thay thế + xóa + chèn) / số đơn vị reference. Ở đây có bốn thay thế, không chèn/xóa, reference có 13 đơn vị. Tiếng Việt tách bằng khoảng trắng thường tương ứng “tiếng”, chưa phải từ ghép đã tách từ. CER bỏ khoảng trắng khi chấm.

Cả pilot 10 câu: WER_ws 36,88%, CER 20,39%. Không lấy điểm pilot để thay dev. Chấm toàn tập bằng tổng lỗi / tổng đơn vị, không lấy trung bình đơn giản WER từng câu.

Chuẩn hóa chung: Unicode NFC, chữ thường, dấu câu thành khoảng trắng, gộp khoảng trắng. Giữ dấu tiếng Việt và transcript gốc; không có bước sửa nội dung. Nguồn: ../experiments/B01/results/summary.csv, ../experiments/common.py.
-->

---

<!-- _class: chart -->

## Chất lượng trên FLEURS · B02–B03

![Kết quả ba cấu hình trên FLEURS dev100](figures/fleurs_dev100.png)

Zipformer có điểm lỗi thấp nhất trên 100 câu này. Biểu đồ so chất lượng, chưa so tốc độ CPU với GPU.

<!--
Vì sao chọn ba cấu hình: Whisper-base là baseline đa ngôn ngữ quen thuộc; Zipformer-30M INT8 là ứng viên tiếng Việt nhỏ chạy CPU; Qwen3-ASR-0.6B là hướng model mới để đối chiếu. Dùng model có sẵn giúp tập trung học đánh giá và tích hợp trong thời gian đề tài.

B02 đã chạy hai baseline CPU laptop; B03 dùng lại đúng output ấy, thêm Qwen GPU. Model mới không mặc nhiên tốt hơn trên bộ đang chấm. Các giá trị WER_ws/CER: Whisper 49,37%/33,92%; Zipformer 7,51%/5,35%; Qwen 9,76%/6,28%. Mỗi model 100/100, reference 2.797 đơn vị và 9.702 ký tự.

Cấu hình: Whisper-base multilingual / openai-whisper / CPU laptop; Zipformer-30M RNNT ONNX INT8 / sherpa-onnx / CPU laptop; Qwen3-ASR-0.6B bfloat16 / qwen-asr Transformers / A100 Colab. Khác trọng số, quy mô, dữ liệu train, runtime và giải mã nên chưa cô lập riêng tác động kiến trúc.

Giới hạn cần trả lời nếu hỏi: Zipformer liệt kê FLEURS trong nguồn train; chưa đủ thông tin split/ID để xác nhận có trùng các câu dev. Không gọi đây là phép đánh giá chắc chắn trên dữ liệu chưa thấy. Đổi sang public test cũng không tự chứng minh độc lập với pretraining.

Nguồn: ../experiments/B03/results/summary.csv. Hình đọc CSV đã lưu; receipt: figures/sources.json. Chỉ so chất lượng; không so thời gian GPU với CPU.
-->

---

<!-- _class: chart -->

## Chất lượng trên audio tự thu · B03

![Kết quả ba cấu hình trên audio tự thu](figures/self_dev20.png)

20 câu do một người đọc bằng Galaxy M15, cách khoảng 30 cm: 2 câu phòng ngủ, 18 câu cà phê. Bộ nhỏ nên chưa đại diện hội thoại thực tế.

<!--
Vì sao thêm self dev20: FLEURS là lời đọc từ bộ public; audio tự thu kiểm tra thêm thiết bị và tiếng nền gần điều kiện thực hành. Không gộp điểm hai bộ thành một hoặc suy ra “cà phê dễ hơn FLEURS”, vì nội dung, độ dài và người nói khác nhau.

Nhãn 20 câu đã được người thực hiện nghe xác nhận. 181 đơn vị reference, 607 ký tự. Whisper: 50/181 = WER_ws 27,62%, CER 17,79%. Zipformer: 1/181 = 0,55%, CER 0,16%. Qwen: 2/181 = 1,10%, CER 1,32%. Hai bản cà phê 01–02 đối chiếu thêm không nằm trong bộ chính.

Điểm thấp vẫn có lỗi: câu 20, reference “Kết quả trên máy tính chưa phải kết quả trên kính.”; Qwen sinh “cách quả trên máy tính chưa phải cách quả trên kính”, sai hai lần kết/cách. Zipformer đúng câu này nhưng sai gốc/góc ở câu 14. Nếu cần nghe lỗi, mở ../data/self_recorded/dev/self_20.wav và ../experiments/B03/results/self_dev20/comparison.csv. Chưa ghi nhận người thực hiện đã nghe lỗi Qwen câu 20 riêng.

Chỉ một người đọc, chưa đại diện hội thoại nhiều người. Các câu ở hai môi trường khác nội dung, chưa cô lập tác động nhiễu. Chữ hoa/thường không tạo chênh lệch điểm vì cùng chuẩn hóa khi chấm.

Nguồn: ../experiments/B03/results/self_dev20/summary.csv. Kết quả hỗ trợ chọn ứng viên tạm thời, chưa phải test cuối.
-->

---

<!-- _class: formula -->

## Đọc số đo thời gian

**RTF = thời gian xử lý / thời lượng audio**

RTF dưới 1 nghĩa là xử lý tệp nhanh hơn thời lượng của tệp ấy. Phải ghi rõ thời gian có gồm nạp model và đọc/ghi hay không.

RTF chưa cho biết người dùng phải chờ bao lâu để thấy phụ đề.

<!--
RTF inference Zipformer = tổng inference / tổng audio. R1 = 10,278388288 / 84,1599375 = 0,1221292291. Không trung bình đơn giản RTF từng tệp. Độ trễ phụ đề cần mốc đo riêng, ví dụ cuối lời nói đến phụ đề cuối; gồm chốt đoạn, hàng đợi và hiển thị. Chưa có số này. Peak RSS là RAM cao nhất toàn tiến trình, gồm runtime và nạp. 1 MiB = 2^20 byte.
-->

---

## Tài nguyên trên Pi · B04

**Pi 4B 8 GB, CPU hai luồng.** Mỗi lượt nạp model một lần rồi xử lý 20 WAV, tổng 84,160 giây audio.

| Lượt | Nhận dạng | Cả runner | RAM cao nhất |
|---|---:|---:|---:|
| r1 | 10,278 s | 14,644 s | 199,06 MiB |
| r2 | 10,226 s | 14,578 s | 198,32 MiB |

Transcript giống laptop 20/20 câu ở cả hai lượt.

<!--
Vì sao đo Pi: điểm chất lượng trên laptop/GPU chưa trả lời model có dùng được trên phần cứng mục tiêu hay không. Pi dùng cùng gói Zipformer/hash như laptop, sherpa-onnx 1.13.8, Python 3.13.5, OS aarch64. Nạp model một lần mỗi lượt, xử lý lần lượt 20 WAV. Hai lượt không phải 40 mẫu độc lập.

Thời gian inference bỏ nạp model và đọc WAV. Wall cả runner gồm khởi động, nạp, đọc, chấm trong runner và ghi; không gồm audit JiWER chạy sau. Nạp model 3,742/3,735 s đã nằm trong wall. RTF inference = inference / 84,1599375 s = 0,1221/0,1215, không phải latency từ lúc người nói kết thúc đến khi hiện chữ. Peak RSS gồm runtime và lúc nạp. Cache hệ điều hành có thể ấm. throttled=0x0 trước/sau.

WER_ws 0,55%, CER 0,16%, 20/20 mỗi lượt. Nguồn: ../experiments/B04/results/zipformer_summary.csv và ../experiments/B04/results/zipformer_r1/measurement.json. Lệnh demo một WAV đã có tại ../experiments/B04/DEMO.md. Không chạy lại inference để làm slide.
-->

---

## Nhận xét kết quả

Zipformer là ứng viên để tích hợp tiếp: cho ít lỗi trên hai bộ dev và đã chạy được trên Pi.

Kết quả mới đúng với các cấu hình và mẫu đã thử. Bộ tự thu chỉ có một người; FLEURS chưa xác minh độc lập với dữ liệu huấn luyện của checkpoint.

<!--
Không quy chênh lệch cho riêng kiến trúc, INT8 hoặc số luồng. Zipformer liệt kê FLEURS trong nguồn train nhưng chưa xác minh split/ID trùng. Một và hai lỗi trên self20 chưa đủ chứng minh ưu thế tổng quát. Đây là dev thăm dò, chưa phải test cuối.
-->

---

## Phần còn thiếu

Whisper-base trên Pi mới thử một câu, chưa chạy đủ 20 câu. Tiny là khảo sát thêm, không thay baseline base.

Hai nhánh Pi khác cách nạp model và phạm vi thời gian. Chưa thể dùng số hiện tại để báo nhanh hơn bao nhiêu lần.

<!--
Phân biệt hai câu hỏi: chọn cấu hình thực dụng để thử tích hợp và nghiên cứu chỉ khác kiến trúc. Các kết quả hiện tại phục vụ câu hỏi đầu. Chưa chứng minh Zipformer là kiến trúc tốt nhất hoặc INT8 là nguyên nhân điểm tốt.

Giải thích thiếu sót B04 nếu thầy hỏi: Whisper-base trên Pi mới smoke một WAV, wall 20,869 s / audio 5,355 s. Sau đó đã chạy Whisper-tiny/whisper.cpp đủ self20 x hai lượt, WER_ws 41,99%, CER 26,36%, tổng wall 172,807/171,309 s. Tiny thay checkpoint nên chỉ là khảo sát bổ sung, không thay C0-base.

Adapter Whisper mở CLI và nạp lại model mỗi WAV; Zipformer nạp một lần mỗi lượt. Whisper báo wall có nạp/đọc/ghi, còn Zipformer có số inference riêng. Không chia những số khác phạm vi để tuyên bố tỷ lệ tăng tốc. Đây là thiếu sót phép đo, không phải yêu cầu của kiến trúc Whisper. Chậm vẫn là kết quả cần ghi nhận khi giữ baseline.

Kế hoạch v3.0 đã giữ C0-base/Pi đầy đủ và phép so tốc độ đồng nhất ở trạng thái chưa hoàn tất. Nếu tiếp tục so baseline, dùng cùng self20/Pi/hai luồng, nạp một lần và cùng phạm vi timing; lưu lỗi hoặc timeout thay vì âm thầm thay checkpoint.

Chưa đo Qwen trên Pi. Chỉ kết luận bản Qwen đang dùng chạy GPU theo phạm vi đã chọn, không kết luận mọi bản Qwen đều không chạy được trên Pi. Chưa kiểm tra input không lời nói, nên false_captions_per_minute còn trống, không phải 0.
-->

---

<!-- _class: next -->

## Hướng tích hợp

![Pipeline dự kiến, chưa triển khai](figures/slides_next.svg)

Audio đến dần cần được chốt thành đoạn để đưa vào ASR. Model giữ trong RAM thay vì nạp lại mỗi câu.

Pi chưa có micro; bước đầu dùng replay WAV theo thời gian thực.

<!--
Vì sao chuyển sang pipeline: WAV đã chia sẵn chưa trả lời audio đến liên tục sẽ cho chữ lúc nào. Replay đưa từng khối audio theo nhịp thời gian thực để kiểm tra luồng; không thay kiểm tra micro thật.

VAD là phát hiện hoạt động giọng nói, giúp tách phần có nói; endpoint là quyết định chốt đoạn. Chỉ thêm khối này khi cần để chốt audio đầu vào cho ASR offline. Giữ model trong RAM, đặt lại trạng thái đoạn theo API. Ghép các khối này chưa biến checkpoint offline thành streaming ASR nguyên sinh.

Tất cả mũi tên nét đứt chỉ phần dự kiến. Chưa có kết quả VAD, replay, độ trễ phụ đề hoặc hiển thị trên kính. Trước mắt hiển thị text trên màn hình để kiểm tra. Chưa cần thêm model, fine-tuning hay bộ sửa lỗi văn bản tự động.

Nguồn sơ đồ Mermaid: diagrams/slides_next.mmd. Nguồn kế hoạch: ../PLAN_DEMO_STT_7_BUOI.md.
-->

---

## Công việc tiếp theo

| Mã | Nội dung dự kiến |
|---|---|
| B05 | Nhận audio đến dần, hiển thị chữ |
| B06 | Thử audio mới, đo lỗi, độ trễ và RAM |
| B07 | Demo toàn luồng, tổng hợp kết quả |

Trước mắt cần hoàn thành luồng audio thành phụ đề trên Pi, rồi kiểm tra trên dữ liệu mới.

<!--
Gợi ý trình bày 3–5 phút: mở mục tiêu và lộ trình thật ngắn, chỉ sơ đồ luồng; phát mẫu B01 khoảng 15–20 giây; giải thích hai biểu đồ và quyết định tạm; nêu kết quả Pi cùng giới hạn; kết thúc bằng đầu ra cụ thể của B05. Nếu chạy Pi trước lớp, dùng lệnh trong ../experiments/B04/DEMO.md sau khi đã tập thử. Đừng biến phần trình bày thành đọc hết các ghi chú.

B06 theo kế hoạch: bộ mới nhỏ khoảng 30–50 câu và khoảng hai phút không lời nói nếu khả thi. Chốt cấu hình trước khi xem bộ mới; đo từ cuối lời nói đến phụ đề cuối, ghi rõ phạm vi và lỗi. Public FLEURS test200 là phần bổ sung, không chặn hoàn thiện pipeline. B04 vẫn còn việc đo C0-base/Pi và phép so đồng nhất; ưu tiên pipeline không xóa việc còn thiếu này.

Tài liệu tra cứu:
- ../reports/DEMO_BUOI_01_04.md: giải thích chi tiết, các pipeline và giới hạn.
- ../mynotes/TONG_QUAN_VA_HOI_DAP_STT_BUOI_01_04.md: hỏi đáp.
- ../PLAN_DEMO_STT_7_BUOI.md: kế hoạch v3.0.
- ../experiments/B04/DEMO.md: thao tác demo Pi.
- ../experiments/B03/results/summary.csv và ../experiments/B03/results/self_dev20/summary.csv: chất lượng.
- ../experiments/B04/results/zipformer_summary.csv và whisper_summary.csv: số đo từng cấu hình Pi.

Cách mở: file Markdown dùng Marp với trang 16:9 và dấu --- để ngắt trang. Bản HTML cùng tên là bản xem trình chiếu, dùng phím mũi tên. Trong Obsidian có thể thử lệnh Start presentation của core plugin Slides; bố cục tùy renderer, chưa xác minh trên Obsidian. HTML là bản đã render để kiểm tra bố cục. Giữ Markdown, HTML và thư mục figures cạnh nhau khi sao chép. Ghi chú nằm trong comment HTML, không xuất hiện trên trang chiếu.
-->

---

<!-- _class: references -->

## Tài liệu và minh chứng

[1] Hugging Face, [Audio Course: mô hình ASR](https://huggingface.co/learn/audio-course/en/chapter5/asr_models).

[2] Google, [FLEURS dataset card](https://huggingface.co/datasets/google/fleurs).

[3] JiWER, [cách chấm và đối chiếu lỗi](https://jitsi.github.io/jiwer/usage/).

Kết quả đã lưu: [FLEURS](../experiments/B03/results/summary.csv), [audio tự thu](../experiments/B03/results/self_dev20/summary.csv), [Pi](../experiments/B04/results/zipformer_summary.csv).

<!--
Nguồn hình chất lượng: reports/figures/sources.json. Nguồn nền DUT: reports/themes/dut/source.json, lấy nguyên ảnh từ mẫu Canva do người dùng cung cấp; không khẳng định đây là chuẩn báo cáo bắt buộc của trường. Tài liệu giải thích chi tiết giữ tại reports/DEMO_BUOI_01_04.md. Chỉ hai định dạng để so sánh: Marp và core Slides của Obsidian.
-->
