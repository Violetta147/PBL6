"""Create the Drive notebook: run Qwen on GPU and reuse completed CPU baselines."""
import json
from pathlib import Path
from make_notebooks import markdown, code, GPU

ROOT = Path(__file__).resolve().parents[1]


def main():
    cells = [
        markdown('# B03 — Qwen trên Colab GPU\n\nChọn **Runtime → Change runtime type → GPU**, rồi chạy các ô theo thứ tự. Notebook tải Qwen3-ASR-0.6B pretrained, không huấn luyện. Whisper và Zipformer đã có kết quả CPU trên cùng 100 câu dev: notebook đọc lại các kết quả đó, chỉ chạy thêm Qwen. Không suy tốc độ trên Pi từ bảng này. Khi mount Drive, bạn tự cấp quyền trong hộp thoại Colab.'),
        code(GPU),
        markdown('## 1. Đọc dữ liệu từ Drive\n\nGói đầu vào nằm trong `My Drive/Seventh Semester/PBL6/STT_B01_B03`. Output Qwen được ghi từng câu trực tiếp vào thư mục `runs` trên Drive. Nếu runtime ngắt, điền tên thư mục lần chạy cũ vào `RUN_NAME` để tiếp tục; giữ nguyên gói mã và cấu hình. Để trống thì tạo lần chạy mới.'),
        code('''from google.colab import drive
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, subprocess, sys, zipfile
drive.mount('/content/drive')
DRIVE_ROOT = Path('/content/drive/MyDrive/Seventh Semester/PBL6/STT_B01_B03')
ROOT = Path('/content/PBL6')
RUN_NAME = ''  # Điền tên qwen_gpu_... đã in ở lần chạy trước để tiếp tục.
if not RUN_NAME:
    RUN_NAME = globals().get('_active_run_name') or 'qwen_gpu_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
if Path(RUN_NAME).name != RUN_NAME or RUN_NAME in ['.', '..']:
    raise ValueError('RUN_NAME phải là tên thư mục, không phải đường dẫn.')
_active_run_name = RUN_NAME
RUN_DIR = DRIVE_ROOT / 'runs' / RUN_NAME
RUN_DIR.mkdir(parents=True, exist_ok=True)
package = DRIVE_ROOT / 'stt_b01_b03_package.zip'
receipt = json.loads((DRIVE_ROOT / 'experiments/package_receipt.json').read_text(encoding='utf-8'))
digest = hashlib.sha256(package.read_bytes()).hexdigest()
if digest != receipt['sha256']:
    raise ValueError('Gói Drive chưa đồng bộ đủ hoặc hash không khớp; không chạy với dữ liệu này.')
stamp = RUN_DIR / 'input_receipt.json'
if stamp.exists() and json.loads(stamp.read_text())['sha256'] != digest:
    raise ValueError('Gói mã đã thay đổi; dùng RUN_NAME mới để giữ lần chạy cũ.')
stamp.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
with zipfile.ZipFile(package) as archive:
    if archive.testzip() is not None:
        raise ValueError('ZIP lỗi CRC')
    for name in archive.namelist():
        if not (ROOT / name).resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Unsafe ZIP path')
    archive.extractall(ROOT)
sys.path.insert(0, str(ROOT / 'experiments'))
BASELINES = DRIVE_ROOT / 'experiments/B02/results'
for model in ['whisper', 'zipformer']:
    for suffix in ['.jsonl', '.run.json']:
        source = BASELINES / f'{model}_dev{suffix}'
        if not source.is_file():
            raise FileNotFoundError(f'Thiếu baseline đã đo: {source}')
        shutil.copy2(source, RUN_DIR / source.name)
def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)
print('Lần chạy:', RUN_NAME)
print('Kết quả được lưu tại:', RUN_DIR)
print('Đầu vào:', digest)
'''),
        markdown('## 2. Cài runtime và kiểm tra mã\n\nÔ này cài thư viện vào máy ảo Colab. GPU đã được kiểm tra trước khi cài hoặc tải checkpoint; không có đường chạy Qwen CPU.'),
        code("run('-m', 'pip', 'install', 'qwen-asr==0.0.6', 'transformers==4.57.6', 'soundfile==0.14.0', 'jiwer==4.0.0')\nrun('-m', 'unittest', 'discover', '-s', ROOT / 'experiments/tests', '-v')\n"),
        markdown('## 3. Chạy Qwen trên 100 câu dev\n\nCheckpoint được ghim revision; ngôn ngữ Vietnamese, batch 1. Mỗi dòng tiến độ là một prediction đã ghi xuống Drive. Chạy lại ô này với cùng RUN_DIR sẽ tiếp tục câu chưa xử lý. Không mở test để chọn model.'),
        code("run(ROOT / 'experiments/run_asr.py', '--model', 'qwen',\n    '--manifest', ROOT / 'experiments/manifests/fleurs_dev100.csv',\n    '--output', RUN_DIR / 'qwen_dev.jsonl', '--device', 'cuda')\n"),
        markdown('## 4. Kiểm tra và so sánh\n\nChỉ lập bảng khi đủ 100/100 ID và metadata hoàn thành. WER_ws dùng khoảng trắng; CER giữ dấu sau NFC, bỏ khoảng trắng. Cả ba kết quả dùng cùng nhãn và hash audio. Whisper/Zipformer CPU và Qwen GPU có thể so chất lượng; thời gian chạy thuộc các môi trường khác nhau. FLEURS có thể có trong dữ liệu pretrained, nên cần bảng tự thu riêng trước khi kết luận cho tình huống dùng kính.'),
        code('''from verify_results import verify
manifest = ROOT / 'experiments/manifests/fleurs_dev100.csv'
paths = [RUN_DIR / f'{model}_dev.jsonl' for model in ['whisper', 'zipformer', 'qwen']]
checks = [verify(path, manifest) for path in paths]
(RUN_DIR / 'verification.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
run(ROOT / 'experiments/summarize.py', '--manifest', manifest,
    '--runs', *paths, '--output-dir', RUN_DIR)
import pandas as pd
from IPython.display import Audio, display
display(pd.read_csv(RUN_DIR / 'summary.csv'))
print('Đã lưu prediction, metadata, verification, summary và comparison vào:', RUN_DIR)
'''),
        markdown('## 5. Nghe và giải thích lỗi\n\nNghe 3–5 câu, đọc reference cùng ba prediction, rồi ghi lỗi về dấu, tên riêng, chữ số hoặc chữ lặp. Ô dưới đưa ba câu có WER Qwen cao nhất để bắt đầu. Chưa có 20 WAV tự thu thật nên notebook này hoàn thành phần FLEURS của B03; phần tự thu và kết luận cuối vẫn còn. Sau khi chạy, gửi tên RUN_NAME cho Codex để đọc kết quả qua Drive.'),
        code("import pandas as pd\nfrom IPython.display import Audio, display\nif 'RUN_DIR' not in globals() or 'ROOT' not in globals():\n    raise RuntimeError('Chạy ô 1 để mở Drive và đặt RUN_NAME của lần đã lưu; không cần chạy lại ô Qwen.')\ncomparison = pd.read_csv(RUN_DIR / 'comparison.csv')\nfor _, row in comparison.sort_values('qwen_WER_ws', ascending=False).head(3).iterrows():\n    display(Audio(filename=str(ROOT / row['audio_path'])))\n    display(row[['id', 'reference', 'whisper_prediction', 'zipformer_prediction', 'qwen_prediction']])\nprint('RUN_NAME:', RUN_DIR.name)\n")
    ]
    for i, cell in enumerate(cells):
        cell['id'] = f'qwen-gpu-{i:02d}'
        if cell['cell_type'] == 'code':
            compile(''.join(cell['source']), f'qwen:cell{i}', 'exec')
    notebook = dict(cells=cells, metadata=dict(accelerator='GPU',
                    colab=dict(name='B03_Qwen_Colab_GPU.ipynb'),
                    kernelspec=dict(display_name='Python 3', language='python', name='python3'),
                    language_info=dict(name='python')), nbformat=4, nbformat_minor=5)
    output = ROOT / 'experiments/B03/B03_Qwen_Colab_GPU.ipynb'
    output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{output.name}: {len(cells)} cells; code compiles')


if __name__ == '__main__':
    main()
