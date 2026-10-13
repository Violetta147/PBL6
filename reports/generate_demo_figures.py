"""Plot saved B03 scores only; does not run ASR or alter experiment outputs."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/figures'
SOURCES = [
    ('fleurs_dev100', 'experiments/B03/results/summary.csv', 100,
     'FLEURS tiếng Việt · dev100', '2.797 đơn vị reference · 9.702 ký tự'),
    ('self_dev20', 'experiments/B03/results/self_dev20/summary.csv', 20,
     'Audio tự thu · self dev20', '1 người · 2 phòng ngủ / 18 cà phê · 181 đơn vị · 607 ký tự'),
]
ORDER = ['whisper', 'zipformer', 'qwen']
LABELS = ['Whisper-base\nCPU laptop', 'Zipformer-30M INT8\nCPU laptop', 'Qwen3-ASR-0.6B\nA100 / Colab']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'svg.fonttype': 'none', 'axes.titleweight': 'bold'})
    receipt = {'purpose': 'Saved quality metrics; not a latency comparison or independent test',
               'generator_sha256': digest(__file__), 'figures': []}
    for name, relative, count, title, subtitle in SOURCES:
        source = ROOT / relative
        with source.open(encoding='utf-8', newline='') as file:
            rows = list(csv.DictReader(file))
        assert len(rows) == 3 and {r['model'] for r in rows} == set(ORDER)
        by_model = {r['model']: r for r in rows}
        rows = [by_model[name] for name in ORDER]
        assert all(int(r['total']) == int(r['completed']) == count for r in rows)
        assert all(r['split'] == 'dev' for r in rows)
        assert len({(r['reference_units'], r['reference_chars']) for r in rows}) == 1
        values = {metric: [100 * float(r[metric]) for r in rows] for metric in ['WER_ws', 'CER']}
        fig, ax = plt.subplots(figsize=(10, 4.6), layout='constrained')
        fig.set_facecolor('#ffffff')
        positions = np.arange(3)
        for offset, metric, color in [(-0.19, 'WER_ws', '#236b8e'), (0.19, 'CER', '#d17834')]:
            bars = ax.bar(positions + offset, values[metric], width=0.34, color=color, label=metric, zorder=3)
            ax.bar_label(bars, labels=[f'{v:.2f}%' for v in values[metric]], padding=5, fontsize=11)
        ax.set_xticks(positions, LABELS)
        ax.set_ylabel('Tỷ lệ lỗi (%) · thấp hơn là tốt hơn')
        ax.set_ylim(0, max(max(v) for v in values.values()) * 1.28)
        ax.set_title(title, loc='left', fontsize=17, pad=40)
        ax.text(0, 1.075, subtitle, transform=ax.transAxes, fontsize=10, color='#4b5563')
        ax.legend(loc='upper right', frameon=False, ncol=2)
        ax.set_axisbelow(True)
        ax.grid(axis='y', color='#e5e7eb')
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.tick_params(axis='both', length=0, pad=10)
        outputs = []
        for extension in ['png', 'svg']:
            path = OUTPUT / f'{name}.{extension}'
            fig.savefig(path, dpi=180, facecolor=fig.get_facecolor())
            outputs.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path)})
        plt.close(fig)
        receipt['figures'].append({'source': relative, 'source_sha256': digest(source),
                                  'records_per_model': count, 'model_order': ORDER,
                                  'percent_values': values, 'outputs': outputs})
    (OUTPUT / 'sources.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Created two quality charts (PNG + SVG) and source receipt; no inference.')


if __name__ == '__main__':
    main()
