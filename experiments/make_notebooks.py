"""Build the three teaching notebooks from the same small runner."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def markdown(text):
    return dict(cell_type='markdown', metadata={}, source=text.splitlines(keepends=True))


def code(text):
    return dict(cell_type='code', metadata={}, execution_count=None, outputs=[], source=text.splitlines(keepends=True))


BOOTSTRAP = '''from pathlib import Path
import sys, zipfile, subprocess
ROOT = Path('/content/PBL6')
if not (ROOT / 'experiments/common.py').exists():
    # Upload stt_b01_b03_package.zip from the computer; no Drive login required.
    from google.colab import files
    uploaded = files.upload()
    package = next(name for name in uploaded if name.endswith('.zip'))
    with zipfile.ZipFile(package) as archive:
        for name in archive.namelist():
            target = (ROOT / name).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                raise ValueError('Unsafe ZIP path')
        archive.extractall(ROOT)
sys.path.insert(0, str(ROOT / 'experiments'))
from common import read_csv, read_jsonl, score
def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)
print('Workspace:', ROOT)
'''

GPU = '''import torch, platform
print('Python:', platform.python_version())
print('CUDA:', torch.cuda.is_available())
print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')
if not torch.cuda.is_available():
    raise RuntimeError('Chọn Runtime > Change runtime type > GPU rồi chạy lại.')
'''

INSTALL = '''run('-m', 'pip', 'install', {packages})
run('-m', 'unittest', 'discover', '-s', ROOT / 'experiments/tests', '-v')
'''

PILOT = '''run(ROOT / 'experiments/run_asr.py', '--model', 'whisper',
    '--manifest', ROOT / 'experiments/manifests/pilot.csv',
    '--output', ROOT / 'experiments/B01/results/whisper_pilot.jsonl', '--device', 'cuda')
'''

DEV = '''for model in ['whisper', 'zipformer']:
    run(ROOT / 'experiments/run_asr.py', '--model', model,
        '--manifest', ROOT / 'experiments/manifests/fleurs_dev100.csv',
        '--output', ROOT / f'experiments/B02/results/{model}_dev.jsonl',
        '--device', 'cuda' if model == 'whisper' else 'cpu')
run(ROOT / 'experiments/summarize.py',
    '--manifest', ROOT / 'experiments/manifests/fleurs_dev100.csv',
    '--runs', ROOT / 'experiments/B02/results/whisper_dev.jsonl', ROOT / 'experiments/B02/results/zipformer_dev.jsonl',
    '--output-dir', ROOT / 'experiments/B02/results')
'''

QWEN = '''run(ROOT / 'experiments/run_asr.py', '--model', 'qwen',
    '--manifest', ROOT / 'experiments/manifests/fleurs_dev100.csv',
    '--output', ROOT / 'experiments/B03/results/qwen_dev.jsonl', '--device', 'cuda')
run(ROOT / 'experiments/summarize.py',
    '--manifest', ROOT / 'experiments/manifests/fleurs_dev100.csv',
    '--runs', ROOT / 'experiments/B02/results/whisper_dev.jsonl',
              ROOT / 'experiments/B02/results/zipformer_dev.jsonl',
              ROOT / 'experiments/B03/results/qwen_dev.jsonl',
    '--output-dir', ROOT / 'experiments/B03/results')
'''

SELF = '''# Only run on actual, listened-to recordings. Do not substitute synthetic speech.
self_manifest = ROOT / 'experiments/manifests/self_dev20.csv'
if self_manifest.exists():
    for model in ['whisper', 'zipformer', 'qwen']:
        run(ROOT / 'experiments/run_asr.py', '--model', model,
            '--manifest', self_manifest,
            '--output', ROOT / f'experiments/B03/results/{model}_self_dev.jsonl',
            '--device', 'cpu' if model == 'zipformer' else 'cuda')
    run(ROOT / 'experiments/summarize.py', '--manifest', self_manifest,
        '--runs', *[ROOT / f'experiments/B03/results/{model}_self_dev.jsonl' for model in ['whisper', 'zipformer', 'qwen']],
        '--output-dir', ROOT / 'experiments/B03/results/self_recorded')
else:
    print('CHƯA ĐO dữ liệu tự thu: cần 20 WAV thật và nhãn đã nghe kiểm tra.')
'''

SAVE = '''import shutil
from google.colab import files
# Contains real predictions, environment and summaries; excludes model weights.
export = Path('/content/PBL6_results_B01_B03')
export.mkdir(exist_ok=True)
for stage in ['B01', 'B02', 'B03']:
    source = ROOT / f'experiments/{stage}/results'
    if source.exists():
        shutil.copytree(source, export / stage, dirs_exist_ok=True)
shutil.copytree(ROOT / 'experiments/manifests', export / 'manifests', dirs_exist_ok=True)
archive = shutil.make_archive(str(export), 'zip', export)
files.download(archive)
print('Lưu ZIP vào G:/My Drive/Seventh Semester/PBL6/STT_B01_B03 sau khi tải.')
'''


def main():
    for stage, title in [('B01', 'Một audio → Whisper → text'), ('B02', 'Hai model và cách chấm'), ('B03', 'Ba model trên cùng dev')]:
        cells = [markdown(f'# {stage}: {title}\n\nDùng model pretrained, không training. Notebook chưa có kết quả cho đến khi các cell chạy thật.\n\nChọn GPU trong Runtime. Khi được hỏi, upload `stt_b01_b03_package.zip`. Dữ liệu: 10 FLEURS train pilot và 100 FLEURS dev cố định, seed 42. Không chạy test.\n\nB03 có thể chạy cả ba buổi từ đầu; các output vẫn được tách B01/B02/B03. Không so thời gian Zipformer CPU với Whisper/Qwen GPU như cùng thiết bị.'), code(BOOTSTRAP)]
        packages = ["'openai-whisper==20250625'", "'soundfile==0.14.0'", "'jiwer==4.0.0'"]
        if stage != 'B01':
            packages.append("'sherpa-onnx==1.13.8'")
        if stage == 'B03':
            packages.append("'qwen-asr==0.0.6'")
        cells += [code(INSTALL.format(packages=', '.join(packages))), code(GPU)]
        cells += [markdown('## B01: chạy baseline\n\nAudio là đầu vào; reference chỉ để chấm. Mỗi lần chạy lưu prediction và trạng thái từng mẫu. Thời gian nạp model được ghi riêng.\n\nPi hiện có: Pi 4B 8GB, OS 13 Trixie aarch64. Micro/màn hình: chưa xác nhận.'), code(PILOT)]
        cells += [code("from IPython.display import Audio, display\nrows = read_jsonl(ROOT / 'experiments/B01/results/whisper_pilot.jsonl')\nr = rows[0]\ndisplay(Audio(filename=str(ROOT / r['audio_path'])))\nprint('Reference:', r['reference'])\nprint('Prediction:', r['prediction'])\nprint('Scorer:', score(r['reference'], r['prediction']))\nprint('Ví dụ tính tay (minh họa): tôi đi học → tôi học: D=1, N=3, WER_ws=1/3')\n")]
        if stage != 'B01':
            cells += [markdown('## B02: Whisper và Zipformer\n\nWER_ws tách bằng khoảng trắng, gần mức âm tiết tiếng Việt. CER đếm Unicode code point sau NFC, bỏ khoảng trắng. Cả reference và prediction dùng cùng chuẩn hóa, giữ dấu và chữ số. Điểm toàn tập là tổng lỗi/tổng độ dài nhãn. Inference lỗi giữ status và tính dự đoán rỗng, không loại mẫu.'), code(DEV), code("import pandas as pd\ndisplay(pd.read_csv(ROOT / 'experiments/B02/results/summary.csv'))\ndisplay(pd.read_csv(ROOT / 'experiments/B02/results/comparison.csv').head(3))\n")]
        if stage == 'B03':
            cells += [markdown('## B03: thêm Qwen3-ASR-0.6B\n\nBackend Transformers, checkpoint revision được ghim trong runner. Chạy cùng 100 dev; không chọn lại câu sau khi xem output. FLEURS có thể xuất hiện trong dữ liệu pretrained, nên bảng này không chứng minh model chưa thấy benchmark.'), code(QWEN), code("import pandas as pd\ndisplay(pd.read_csv(ROOT / 'experiments/B03/results/summary.csv'))\ncomparison = pd.read_csv(ROOT / 'experiments/B03/results/comparison.csv')\ndisplay(comparison.head(5))\n# Nghe 3–5 lỗi, đọc reference và ba prediction trước khi viết nhận xét.\nfor _, row in comparison.sort_values('whisper_WER_ws', ascending=False).head(3).iterrows():\n    display(Audio(filename=str(ROOT / row['audio_path'])))\n    display(row[['id', 'reference', 'whisper_prediction', 'zipformer_prediction', 'qwen_prediction']])\n"), markdown('## Audio tự thu: bảng riêng\n\nCần 20 câu thật đã kiểm tra nhãn. Đọc `B02/THU_AM.md`; dùng `import_self.py` để kiểm tra và tạo manifest. Nếu chưa có, phần này còn thiếu; không gọi FLEURS là dữ liệu tự thu.'), code(SELF)]
        cells += [markdown('## Lưu kết quả\n\nChạy cell này trước khi ngắt runtime. Dữ liệu đã lưu là bằng chứng; notebook có mã nhưng chưa chạy không phải kết quả. Không dùng điểm Colab để kết luận tốc độ trên Pi.'), code(SAVE)]
        notebook = dict(cells=cells, metadata=dict(colab=dict(name=f'{stage}_STT.ipynb'),
                        kernelspec=dict(display_name='Python 3', language='python', name='python3'),
                        language_info=dict(name='python')), nbformat=4, nbformat_minor=5)
        for i, cell in enumerate(cells):
            cell['id'] = f'{stage.lower()}-{i:02d}'
        output = ROOT / f'experiments/{stage}/{stage}_STT.ipynb'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding='utf-8')
        for i, cell in enumerate(cells):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), f'{output.name}:cell{i}', 'exec')
        print(f'{output.name}: {len(cells)} cells; code compiles')


if __name__ == '__main__':
    main()
