"""Render the reviewed communication diagrams; preserve previous Downloads exports."""

from pathlib import Path
import argparse
import json
import math
import shutil
from datetime import datetime
from html import escape

from PIL import Image, ImageDraw, ImageFont

BG = '#171b22'
PANEL = '#1d2530'
BOX = '#073653'
LINE = '#7394a8'
TEXT = '#edf5fa'
MUTED = '#b7ccd9'
ACCENT = '#75c7dd'
FONT = Path('C:/Windows/Fonts/segoeui.ttf')


class Diagram:
    def __init__(self, title, subtitle, height=2000, width=1800):
        self.width, self.height = width, height
        self.image = Image.new('RGB', (width, height), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                    f'<title>{escape(title)}</title>', f'<rect width="100%" height="100%" fill="{BG}"/>']
        self.nodes = {}
        self.edges = []
        self.routes = []
        self.text(70, 40, title, size=38, color=TEXT)
        self.text(70, 100, subtitle, size=25, color=MUTED)

    def text(self, x, y, value, size=27, color=TEXT, center=False):
        font = ImageFont.truetype(str(FONT), size)
        for line in value.split('\n'):
            width = self.draw.textlength(line, font=font)
            left = x - width / 2 if center else x
            assert left >= 10 and left + width <= self.width - 10, (line, left, width)
            assert y + size + 7 <= self.height, (line, y)
            self.draw.text((left, y), line, font=font, fill=color)
            self.svg.append(f'<text x="{left:.1f}" y="{y + size}" fill="{color}" font-family="Segoe UI, sans-serif" font-size="{size}">{escape(line)}</text>')
            y += size + 10

    def panel(self, x, y, w, h, title):
        self.draw.rounded_rectangle((x, y, x+w, y+h), radius=24, fill=PANEL, outline=LINE, width=1)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="24" fill="{PANEL}" stroke="{LINE}"/>')
        self.text(x+25, y+16, title, size=27, color=ACCENT)

    def box(self, key, x, y, w, h, value, size=27, fill=BOX):
        assert key not in self.nodes
        assert x >= 15 and x+w <= self.width-15 and y+h <= self.height-15
        self.nodes[key] = {'rect': [x, y, w, h], 'text': value}
        self.draw.rounded_rectangle((x, y, x+w, y+h), radius=20, fill=fill, outline=LINE, width=2)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="{fill}" stroke="{LINE}" stroke-width="2"/>')
        lines = []
        font = ImageFont.truetype(str(FONT), size)
        for paragraph in value.split('\n'):
            current = ''
            for word in paragraph.split():
                candidate = (current+' '+word).strip()
                if self.draw.textlength(candidate, font=font) > w-42:
                    assert current, word
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            lines.append(current)
        total = len(lines)*(size+10)
        assert total <= h-20, (key, total, h)
        self.text(x+w/2, y+(h-total)/2-2, '\n'.join(lines), size=size, center=True)

    def anchor(self, key, side):
        x, y, w, h = self.nodes[key]['rect']
        return {'top': (x+w/2, y), 'bottom': (x+w/2, y+h),
                'left': (x, y+h/2), 'right': (x+w, y+h/2)}[side]

    def arrow(self, source, target, start='bottom', end='top', via=(), label=None, label_xy=None):
        pts = [self.anchor(source, start), *via, self.anchor(target, end)]
        self.edges.append([source, target, label])
        self.routes.append((source, target, pts))
        self.draw.line(pts, fill=LINE, width=3)
        x, y = pts[-1]
        px, py = pts[-2]
        angle = math.atan2(y-py, x-px)
        tip = [(x, y), (x-15*math.cos(angle-.45), y-15*math.sin(angle-.45)),
               (x-15*math.cos(angle+.45), y-15*math.sin(angle+.45))]
        self.draw.polygon(tip, fill=LINE)
        coordinates = ' '.join(f'{a},{b}' for a,b in pts)
        triangle = ' '.join(f'{a},{b}' for a,b in tip)
        self.svg += [f'<polyline points="{coordinates}" fill="none" stroke="{LINE}" stroke-width="3"/>',
                     f'<polygon points="{triangle}" fill="{LINE}"/>']
        if label:
            assert label_xy
            self.text(*label_xy, label, size=23, color=MUTED)

    def chain(self, keys):
        for a,b in zip(keys, keys[1:]):
            self.arrow(a,b)

    def save(self, target, backup_dir):
        target.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ('.png', '.svg'):
            prior = target.with_suffix(suffix)
            if prior.exists():
                backup_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(prior, backup_dir/prior.name)
        self.image.save(target.with_suffix('.png'))
        target.with_suffix('.svg').write_text('\n'.join(self.svg+['</svg>']), encoding='utf-8')
        with Image.open(target.with_suffix('.png')) as check:
            check.verify()
        return {'file': target.name, 'size': [self.width,self.height], 'nodes': self.nodes, 'edges': self.edges}


def composition():
    d = Diagram('02 · Soạn gloss và phát tiếng nói', 'Hai luồng phối hợp qua vùng soạn; thao tác Phát chuyển nội dung sang bản phát rồi xóa vùng soạn.', 2200)
    d.panel(60,170,800,1590,'A · THU KÝ HIỆU VÀ SOẠN NỘI DUNG')
    d.panel(940,170,800,1590,'B · PHÁT ÂM THANH')
    left = [
        ('ready','Sẵn sàng thu lượt ký hiệu\nNgười dùng nhấn Bắt đầu'),
        ('capture','Thu một lượt ký hiệu\nNhấn Kết thúc để đóng dữ liệu lượt'),
        ('recognize','Nhận dạng → hiện gloss ứng viên\nGloss: nhãn chữ của ký hiệu dự đoán'),
        ('review','Người dùng kiểm tra\nGiữ / Làm lại / Bỏ kết quả'),
        ('draft','Vùng soạn\nGiữ các gloss; cho phép xóa hoặc chỉnh'),
        ('transfer','Nhấn Phát khi vùng soạn có nội dung\nChuyển nội dung sang bản phát\nvà xóa vùng soạn trong một thao tác'),
        ('newdraft','Vùng soạn trống để nhận nội dung mới\nNội dung mới chờ lần nhấn Phát tiếp theo')]
    for i,(k,t) in enumerate(left):
        d.box(k,100,245+i*205,720,155,t)
    d.chain([x[0] for x in left])
    right=[('snapshot','Bản văn bản dành cho lần phát hiện tại\nĐộc lập với vùng soạn mới'),
           ('tts','Tổng hợp tiếng nói từ bản phát'),
           ('play','Bộ phát phát âm thanh ra loa\nGiao diện vẫn nhận thao tác'),
           ('request','Người dùng nhấn Dừng phát\nỨng dụng gửi yêu cầu dừng'),
           ('stop','Bộ phát dừng\nHủy audio còn chờ của lần phát này'),
           ('idle','Bộ phát trở về trạng thái rảnh\nKhông xóa nội dung mới trong vùng soạn')]
    for i,(k,t) in enumerate(right):
        d.box(k,980,450+i*205,720,155,t)
    d.chain([x[0] for x in right])
    d.arrow('transfer','snapshot','right','left',via=[(900,1347),(900,527)])
    d.arrow('play','idle','right','right',via=[(1720,937),(1720,1552)])
    d.text(1020,1660,'Đường vòng: phát xong → bộ phát rảnh.',size=23,color=MUTED)
    d.text(100,1690,'Thêm ký hiệu / Làm lại → thu lượt tiếp theo.',size=23,color=MUTED)
    d.text(100,1730,'Bỏ kết quả / Hủy lượt thu → sẵn sàng.',size=23,color=MUTED)
    d.box('rule',80,1810,1640,155,'Vùng soạn tiếp tục nhận nội dung trong khi loa phát.\nNhận dạng và phát là hai tác vụ phối hợp; cần đo khả năng chạy đồng thời khi tích hợp.',size=27,fill=PANEL)
    d.text(95,2000,'Đường âm thanh: chính sách thu micro khi loa phát được xác định khi tích hợp.',size=26,color=MUTED)
    d.text(95,2050,'Kiểm thử khử tiếng vọng là việc phát triển hệ thống, không phải bước của mỗi lượt phát.',size=26,color=MUTED)
    return d


def hardware():
    d=Diagram('03 · Phần cứng và giám sát hệ thống','Khối phần mềm nằm trong Pi; thiết bị thu, hiển thị và phát nối với Pi theo chức năng.',2050)
    d.box('power',70,170,1660,110,'Nguồn DC ổn định và phân phối điện theo tải từng nhánh\nCấp điện cho Pi và các ngoại vi theo yêu cầu của từng thiết bị',size=27,fill=PANEL)
    d.panel(70,530,1660,750,'RASPBERRY PI 4B · PHẦN MỀM CHẠY TRÊN PI')
    d.box('app',550,605,700,120,'Ứng dụng giao tiếp và điều phối\nThu dữ liệu · xử lý thao tác · quản lý trạng thái')
    d.box('models',550,810,700,150,'Nhận dạng ký hiệu · nhận dạng lời nói (ASR)\nTổng hợp tiếng nói từ chữ (TTS)\nModel và phần mềm thực thi được chọn')
    d.box('ui',130,1050,700,150,'Giao diện sử dụng\nVùng bản chép lời + vùng soạn\nBắt đầu / Kết thúc / Giữ / Phát / Dừng phát')
    d.box('agent',970,1050,700,150,'Tác vụ giám sát và cấu hình\nĐọc thông số, trạng thái; nhận và kiểm tra cấu hình\nBáo kết quả đã áp dụng hoặc lý do từ chối',size=25)
    d.arrow('app','models')
    d.arrow('app','ui','left','top',via=[(480,665)])
    d.arrow('app','agent','right','top',via=[(1320,665)])
    d.box('cam',130,335,700,130,'Camera\nVideo → Pi để thu lượt ký hiệu')
    d.box('mic',970,335,700,130,'Thiết bị thu âm\nÂm thanh số → Pi để thu lời người đối thoại')
    d.box('speaker',970,1370,700,150,'Đầu ra âm thanh → loa\nLoa có khuếch đại\nhoặc ampli + loa phù hợp')
    d.box('screen',130,1370,700,150,'Màn hình và cảm ứng\nPi → hình ảnh hiển thị\nThao tác chạm → giao diện trên Pi')
    d.box('tb',130,1660,1540,150,'ThingsBoard CE · nền tảng giám sát\nNhận / lưu dữ liệu → dashboard người vận hành\nGửi cấu hình xuống tác vụ giám sát trên Pi',size=26,fill=PANEL)
    d.arrow('cam','models','bottom','left',via=[(480,500),(85,500),(85,885)])
    d.arrow('mic','models','bottom','right',via=[(1320,500),(1700,500),(1700,885)])
    d.arrow('models','speaker','bottom','top',via=[(900,990),(1740,990),(1740,1320),(1320,1320)])
    d.arrow('ui','screen')
    d.arrow('screen','ui','left','left',via=[(100,1445),(100,1125)])
    d.arrow('agent','tb','bottom','top',via=[(1320,1250),(900,1250)])
    d.arrow('tb','agent','right','right',via=[(1760,1735),(1760,1125)])
    d.text(140,1570,'MQTT: Pi gửi thông số, trạng thái, heartbeat.',size=23,color=MUTED)
    d.text(980,1570,'Nhận cấu hình; báo kết quả áp dụng.',size=23,color=MUTED)
    d.box('note',70,1870,1660,125,'Màn hình phục vụ người dùng; dashboard phục vụ người vận hành.\nHeartbeat không thay thế kiểm tra chức năng. Nhánh ESP32 được trình bày ở sơ đồ 09.',size=26,fill=PANEL)
    return d


def research():
    d=Diagram('04 · Nghiên cứu, đánh giá và triển khai','Đọc hai nhánh từ trên xuống, sau đó hội tụ ở triển khai và kiểm thử trên Pi.',2290)
    d.panel(60,170,810,1210,'A · NHẬN DẠNG KÝ HIỆU')
    d.panel(930,170,810,1210,'B · NHẬN DẠNG LỜI NÓI')
    a=[('sdata','Video + nhãn + người ký + góc quay\nChia train / validation / test theo mục tiêu'),
       ('sbase','Baseline LSTM của nhóm\nPipeline feature cũ → input 64 × 128'),
       ('sold','SPOTER dùng pipeline cũ của baseline\nMốc trước khi đổi preprocessing'),
       ('snew','Preprocessing mới của Minh\nnone / temporal_sampling / frame_drop / joint_mask'),
       ('sval','Dùng validation chọn checkpoint / cấu hình\nPhân biệt so model, preprocessing và augmentation'),
       ('stest','Chốt lựa chọn → đánh giá test\nLưu checkpoint + preprocessing tương ứng')]
    b=[('adata','FLEURS + audio tự thu + bản chép lời chuẩn\nTách dev / test theo người hoặc phiên phù hợp'),
       ('aprep','Chuẩn bị audio đúng yêu cầu mô hình\nManifest: bảng kê mẫu, đường dẫn và nhãn'),
       ('arun','Suy luận bằng mô hình có sẵn\nWhisper-base / Zipformer / Qwen3-ASR'),
       ('ascore','Prediction đối chiếu reference để chấm\nWER theo khoảng trắng + CER\nReference chỉ đưa vào bộ chấm'),
       ('adev','Chọn model / runtime / cấu hình trên dev\nRuntime: phần mềm nạp và thực thi mô hình'),
       ('atest','Chốt lựa chọn → đánh giá test\nLưu model + runtime + cấu hình tương ứng')]
    for x, seq in [(100,a),(970,b)]:
        for i,(key,txt) in enumerate(seq):
            d.box(key,x,245+i*180,730,135,txt,size=25)
        d.chain([k for k,t in seq])
    d.box('measure',310,1450,1180,125,'Đo trên Raspberry Pi\nThời gian, RAM từng khối và toàn luồng; xác định cấu hình triển khai')
    d.arrow('stest','measure',via=[(465,1415),(900,1415)])
    d.arrow('atest','measure',via=[(1335,1415),(900,1415)])
    d.box('integrate',310,1630,1180,125,'Tích hợp giao diện\nThu → nhận dạng → kiểm tra → hiển thị / soạn / phát')
    d.box('e2e',310,1810,1180,125,'Kiểm thử sử dụng thực tế\nĐộ trễ, dừng phát, âm thanh, thao tác và nhiều lượt chạy liên tục')
    d.box('report',310,1990,1180,125,'Ghi kết quả và giới hạn → chốt phạm vi phiên bản\nPhân loại vấn đề: dữ liệu / preprocessing / model / runtime / giao diện')
    d.chain(['measure','integrate','e2e','report'])
    d.text(100,2170,'Vấn đề mới → quay lại đúng bước liên quan; cấu hình sửa tiếp được chọn trên dev / validation.',size=25,color=MUTED)
    d.text(100,2215,'Sơ đồ mô tả quy trình. Dữ liệu test đã dùng để cải tiến không còn là phép đánh giá độc lập.',size=25,color=MUTED)
    return d


def baseline():
    d=Diagram('05b · Baseline nhóm đối chiếu bốn run của Minh','Cùng hàng = cùng vai trò. Khác biệt chính: xử lý feature đã có hay xử lý tọa độ rồi tính lại feature.',2330)
    d.panel(60,170,810,1760,'BASELINE LSTM CỦA NHÓM · PIPELINE CŨ')
    d.panel(930,170,810,1760,'MINH · PIPELINE MỚI CHO BỐN RUN SPOTER')
    left=[
        '1 · Dữ liệu đầu vào đã trích\nNPZ: hand-local, body, palm-body,\nquan hệ hình học, scale và cờ phát hiện',
        '2 · Giữ các nhóm feature đã tính\nTay local và thân vẫn ở biểu diễn riêng\nKhông tái dựng thành 49 điểm chung ở bước này',
        '3 · Sửa khoảng mất trên từng nhóm feature\nNội suy gap ngắn tối đa 5 khung\nBiên dùng giá trị hợp lệ gần nhất theo cấu hình',
        '4 · Nội suy từng nhóm về 64 khung\nCả tọa độ, khoảng cách và scale đã có\nCờ phát hiện lấy theo thời điểm gần nhất',
        '5 · Ghép feature đã xử lý\n124 giá trị hình học + 4 cờ phát hiện\nKhông tính lại quan hệ hình học từ tọa độ chung',
        '6 · Tensor X: 64 × 128\nNaN / Inf còn lại được thay bằng 0\nkhi tạo đầu vào mô hình',
        '7 · LSTM một chiều, 2 lớp, hidden 256\nTrạng thái cuối → LayerNorm → Dropout\n→ Linear phân loại 400 ký hiệu']
    right=[
        '1 · Dữ liệu đầu vào đã trích\nCác nhóm tọa độ / feature đã lưu\nKhông cần trích lại video bằng MediaPipe',
        '2 · Tái dựng tọa độ chung theo thân\n49 điểm = 7 điểm thân + 21 điểm mỗi tay\nDùng thông tin tọa độ và scale đã lưu',
        '3 · Sửa khoảng mất trên tọa độ tái dựng\nXử lý geometry trước khi tạo lại feature\nGiữ quy tắc missing theo cấu hình',
        '4 · Bốn run độc lập, khác quy tắc biến đổi\nnone: đều 64; temporal: jitter vị trí mẫu\nframe_drop: bỏ khung; joint_mask: che điểm tay',
        '5 · Chuẩn hóa và tính lại feature từ geometry\nTọa độ, khoảng cách và scale theo cùng dữ liệu\nBốn run đều tắt body augmentation và Gaussian',
        '6 · Tensor X: 64 × 128\nCùng kích thước với baseline\nnhưng giá trị bên trong có thể khác',
        '7 · SPOTER: chiếu 128 → 108\nEncoder 6 lớp → decoder 6 lớp + class query\n→ Linear phân loại 400 ký hiệu']
    for x,seq,prefix in [(100,left,'b'),(970,right,'m')]:
        keys=[]
        for i,t in enumerate(seq):
            key=f'{prefix}{i+1}'; keys.append(key)
            d.box(key,x,245+i*235,730,185,t,size=25)
        d.chain(keys)
    d.box('difference',70,1980,1660,145,'KHÁC NHAU Ở THỨ TỰ TÍNH\nCũ: tính khoảng cách → nội suy khoảng cách. Mới: nội suy tọa độ → tính khoảng cách.\nHai phép này thường không cho cùng kết quả, dù cùng tạo input 64 × 128.',size=27,fill=PANEL)
    d.text(95,2160,'none = tắt augmentation, vẫn dùng toàn bộ preprocessing mới và vẫn huấn luyện SPOTER.',size=26,color=TEXT)
    d.text(95,2210,'SPOTER low-LR trước đó dùng pipeline cũ ở cột trái; không phải run none ở cột phải.',size=26,color=MUTED)
    d.text(95,2260,'Các khối biểu diễn vai trò xử lý; thứ tự chi tiết augmentation phụ thuộc từng kỹ thuật.',size=25,color=MUTED)
    return d


def esp32():
    d=Diagram('09 · Nhánh ESP32 và ngoại vi mở rộng','Phương án firmware tách riêng; chức năng cụ thể của nút, LED và cảm biến được xác định khi tích hợp.',1450)
    d.box('io',120,220,650,160,'Nút nhấn và LED\nNút → sự kiện; lệnh → LED\nChức năng ứng dụng cần được phân công')
    d.box('sensor',1030,220,650,160,'Cảm biến mở rộng\nKhoảng cách / điện áp / dòng điện\nChọn theo yêu cầu đo cụ thể')
    d.box('esp',550,540,700,180,'ESP32\nFirmware đọc ngoại vi, xử lý nút\nđiều khiển LED và đóng gói trạng thái')
    d.box('pi',550,890,700,180,'Raspberry Pi\nNhận sự kiện / số đo từ ESP32\nGửi lệnh theo giao thức đã thống nhất')
    d.arrow('io','esp',via=[(445,465),(900,465)])
    d.arrow('sensor','esp',via=[(1355,465),(900,465)])
    d.arrow('esp','pi',label='Serial: dữ liệu và trạng thái',label_xy=(950,770))
    d.arrow('pi','esp','left','left',via=[(420,980),(420,630)],label='Lệnh điều khiển',label_xy=(100,785))
    d.box('note',120,1190,1560,160,'Nguồn và mức điện áp giao tiếp được kiểm tra theo linh kiện thực tế.\nNhánh này được tích hợp khi có vai trò cụ thể; luồng giao tiếp chính trên Pi phát triển độc lập.',size=28,fill=PANEL)
    return d


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    backup=args.output/('diagram-backups-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    pages=[('02-quy-trinh-soan-gloss-va-phat-tieng-noi.png',composition()),
           ('03-kien-truc-phan-cung-va-giam-sat-he-thong.png',hardware()),
           ('04-quy-trinh-huan-luyen-danh-gia-va-trien-khai.png',research()),
           ('05b-baseline-nhom-doi-chieu-4-run-minh.png',baseline()),
           ('09-nhanh-esp32-va-ngoai-vi-mo-rong.png',esp32())]
    # Validate all layouts before replacing any export.
    report=[page.save(args.output/name,backup) for name,page in pages]
    log=args.output/'diagrams-validation-20261029.json'
    log.write_text(json.dumps({'backup':str(backup),'pages':report},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'exported':[p['file'] for p in report],'backup':str(backup),'validation':str(log)},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
