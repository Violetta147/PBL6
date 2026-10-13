"""Build a separate GPU notebook for the confirmed self dev20 recordings."""
import json
from pathlib import Path
from make_notebooks import code, markdown

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = '''from google.colab import drive
from pathlib import Path
import csv, hashlib, json, shutil, subprocess, sys, zipfile
drive.mount('/content/drive')
DRIVE_ROOT = Path('/content/drive/MyDrive/Seventh Semester/PBL6/STT_B01_B03')
ROOT = Path('/content/PBL6_SELF_DEV20')
RUN_NAME = 'self_dev20_qwen_v1'  # Giữ nguyên để tiếp tục hoặc xem lần đã lưu.
if Path(RUN_NAME).name != RUN_NAME or RUN_NAME in ['', '.', '..']:
    raise ValueError('RUN_NAME phải là một tên thư mục.')
package = DRIVE_ROOT / 'self_dev20_package.zip'
receipt = json.loads((DRIVE_ROOT / 'experiments/self_dev20_package_receipt.json').read_text(encoding='utf-8'))
digest = hashlib.sha256(package.read_bytes()).hexdigest()
if digest != receipt['sha256']:
    raise ValueError('Gói self dev20 chưa đồng bộ đủ hoặc hash không khớp.')
RUN_DIR = DRIVE_ROOT / 'runs' / RUN_NAME
stamp = RUN_DIR / 'input_receipt.json'
if stamp.exists() and json.loads(stamp.read_text(encoding='utf-8'))['sha256'] != digest:
    raise ValueError('Gói đầu vào khác lần đã lưu; chọn RUN_NAME mới.')
with zipfile.ZipFile(package) as archive:
    if archive.testzip() is not None:
        raise ValueError('ZIP lỗi CRC')
    for name in archive.namelist():
        if not (ROOT / name).resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Unsafe ZIP path')
    archive.extractall(ROOT)
manifest = ROOT / 'experiments/manifests/self_dev20.csv'
with manifest.open(encoding='utf-8', newline='') as file:
    rows = list(csv.DictReader(file))
expected_ids = {f'self/dev/{i:02d}' for i in range(1, 21)}
if len(rows) != 20 or {r['id'] for r in rows} != expected_ids:
    raise ValueError('Gói phải chứa đúng 20 câu self dev chính.')
if any(r['consent'] != 'yes' or r['label_verified'] != 'yes' for r in rows):
    raise ValueError('Thiếu xác nhận nhãn hoặc đồng ý sử dụng audio.')
RUN_DIR.mkdir(parents=True, exist_ok=True)
stamp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
for model in ['whisper', 'zipformer']:
    for suffix in ['.jsonl', '.run.json']:
        source = ROOT / f'experiments/B02/results/self_dev20/{model}{suffix}'
        target = RUN_DIR / source.name
        if target.exists():
            if target.read_bytes() != source.read_bytes():
                raise ValueError(f'Baseline đã lưu khác gói: {target}')
        else:
            shutil.copy2(source, target)
sys.path.insert(0, str(ROOT / 'experiments'))
def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)
print('Lần chạy:', RUN_NAME)
print('Kết quả:', RUN_DIR)
print('Đầu vào self dev20:', digest)
'''


def build_notebook():
    original = ROOT / 'experiments/B03/B03_Qwen_Colab_GPU.ipynb'
    notebook = json.loads(original.read_text(encoding='utf-8'))
    cells = notebook['cells']
    cells[0] = markdown('# B03 — Qwen trên self dev20\n\nChọn GPU rồi chạy các ô theo thứ tự. Bộ này gồm 20 câu tự thu đã nghe kiểm tra nhãn: 2 câu phòng ngủ, 18 câu cà phê; không phải FLEURS. Hai baseline CPU đã đo được dùng lại, chỉ chạy Qwen GPU. Hai bản cà phê đối chiếu câu 01–02 không nằm trong bộ chính. Không huấn luyện; test vẫn đóng.')
    cells[2] = markdown('## 1. Mở bộ tự thu trên Drive\n\nGiữ tên `self_dev20_qwen_v1` để tránh tạo nhiều lần chạy khi bấm lại ô. Chỉ đổi tên khi chủ động làm lần khác. Workspace và output riêng, không ghi đè notebook/kết quả FLEURS. Để xem kết quả đã có, chạy ô này rồi ô nghe cuối; không cần chạy lại Qwen hoặc giữ GPU sau khi đã lưu xong.')
    cells[3] = code(BOOTSTRAP)
    cells[4] = markdown('## 2. Cài runtime và kiểm tra hai baseline\n\nDùng phiên bản runtime Qwen như lần FLEURS. Kiểm tra nhãn, hash và điểm hai baseline trước khi chạy thêm model; không chạy lại Whisper/Zipformer trên Colab.')
    cells[5] = code("run('-m', 'pip', 'install', 'qwen-asr==0.0.6', 'transformers==4.57.6', 'soundfile==0.14.0', 'jiwer==4.0.0')\nfrom verify_results import verify\nmanifest = ROOT / 'experiments/manifests/self_dev20.csv'\nfor model in ['whisper', 'zipformer']:\n    print(verify(RUN_DIR / f'{model}.jsonl', manifest))\n")
    cells[6] = markdown('## 3. Chạy Qwen trên 20 câu tự thu\n\nChỉ dùng CUDA. Giữ cùng checkpoint/revision và ngôn ngữ Vietnamese như lần FLEURS. Prediction được ghi từng câu xuống Drive; chạy lại cùng cấu hình chỉ tiếp tục phần thiếu, lần hoàn tất không inference lại.')
    cells[7] = code("print('So sánh Qwen với hai baseline trên cùng self dev20; không dùng kết quả FLEURS thay vào.')\nrun(ROOT / 'experiments/run_asr.py', '--model', 'qwen',\n    '--manifest', ROOT / 'experiments/manifests/self_dev20.csv',\n    '--output', RUN_DIR / 'qwen.jsonl', '--device', 'cuda')\n")
    cells[8] = markdown('## 4. Chấm và lưu bảng ba model\n\nChỉ tổng hợp khi đủ 20/20 ID mỗi run. Giữ cùng nhãn và scorer; JiWER kiểm tra độc lập. Đây là bộ dev nhỏ của một người, không phải test độc lập; phân bố 2 phòng ngủ/18 cà phê không dùng kết luận riêng tác động tiếng ồn. Bảng thời gian GPU/CPU không phải số đo Pi.')
    cells[9] = code("import json\nimport pandas as pd\nfrom IPython.display import display\nfrom verify_results import verify\nmanifest = ROOT / 'experiments/manifests/self_dev20.csv'\npaths = [RUN_DIR / f'{model}.jsonl' for model in ['whisper', 'zipformer', 'qwen']]\nchecks = [verify(path, manifest) for path in paths]\n(RUN_DIR / 'verification.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')\nrun(ROOT / 'experiments/summarize.py', '--manifest', manifest, '--runs', *paths, '--output-dir', RUN_DIR)\ndisplay(pd.read_csv(RUN_DIR / 'summary.csv'))\nprint('Đã lưu bảng self dev20 tại:', RUN_DIR)\n")
    cells[10] = markdown('## 5. Nghe đối chiếu\n\nĐọc đầy đủ reference và ba prediction. Ba mẫu dưới được chọn theo WER Qwen cao nhất để xem lỗi, không đại diện toàn bộ tập. Sau khi chạy, gửi tên lần `self_dev20_qwen_v1` cho Codex kiểm tra kết quả trên Drive. Chưa có số đo Pi hoặc test.')
    notebook['metadata']['colab']['name'] = 'B03_Self_dev20_Qwen_GPU.ipynb'
    for i, cell in enumerate(cells):
        cell['id'] = f'qwen-self-{i:02d}'
        if cell['cell_type'] == 'code':
            cell.update(execution_count=None, outputs=[])
            compile(''.join(cell['source']), f'self-dev20:cell{i}', 'exec')
    return notebook


def main():
    output = ROOT / 'experiments/B03/B03_Self_dev20_Qwen_GPU.ipynb'
    output.write_text(json.dumps(build_notebook(), ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{output.name}: 12 cells; code compiles; not executed on Colab yet')


if __name__ == '__main__':
    main()
