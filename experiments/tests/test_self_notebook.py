"""Verify the self dev20 bootstrap with fixture ZIPs, without GPU inference."""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from make_self_notebook import BOOTSTRAP, build_notebook


class SelfNotebookTests(unittest.TestCase):
    def package(self, drive, bad_id=False, unsafe=False):
        (drive / 'experiments').mkdir(parents=True)
        text = io.StringIO()
        writer = csv.DictWriter(text, fieldnames=['id', 'consent', 'label_verified'])
        writer.writeheader()
        for i in range(1, 21):
            writer.writerow(dict(id='self/dev/cafe/01' if bad_id and i == 1 else f'self/dev/{i:02d}',
                                 consent='yes', label_verified='yes'))
        package = drive / 'self_dev20_package.zip'
        with zipfile.ZipFile(package, 'w') as archive:
            archive.writestr('experiments/manifests/self_dev20.csv', text.getvalue())
            for model in ['whisper', 'zipformer']:
                for suffix in ['.jsonl', '.run.json']:
                    archive.writestr(f'experiments/B02/results/self_dev20/{model}{suffix}',
                                     f'fixture {model}{suffix}')
            if unsafe:
                archive.writestr('../outside.txt', 'fixture')
        receipt = {'sha256': hashlib.sha256(package.read_bytes()).hexdigest()}
        (drive / 'experiments/self_dev20_package_receipt.json').write_text(json.dumps(receipt), encoding='utf-8')
        return package

    def bootstrap(self, drive, root):
        google = ModuleType('google')
        colab = ModuleType('google.colab')
        colab.drive = SimpleNamespace(mount=lambda path: None)
        source = BOOTSTRAP.replace('/content/drive/MyDrive/Seventh Semester/PBL6/STT_B01_B03', drive.as_posix())
        source = source.replace('/content/PBL6_SELF_DEV20', root.as_posix())
        namespace = {}
        with patch.dict(sys.modules, {'google': google, 'google.colab': colab}), redirect_stdout(io.StringIO()):
            exec(compile(source, 'self-bootstrap', 'exec'), namespace)
        return namespace

    def test_rerun_keeps_same_run_and_preserves_saved_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            drive, root = Path(tmp) / 'drive', Path(tmp) / 'workspace'
            self.package(drive)
            first = self.bootstrap(drive, root)
            prediction = first['RUN_DIR'] / 'qwen.jsonl'
            prediction.write_text('saved prediction', encoding='utf-8')
            second = self.bootstrap(drive, root)
            self.assertEqual(first['RUN_DIR'], second['RUN_DIR'])
            self.assertEqual(prediction.read_text(encoding='utf-8'), 'saved prediction')
            baseline = first['RUN_DIR'] / 'whisper.jsonl'
            baseline.write_text('different baseline', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Baseline'):
                self.bootstrap(drive, root)
            self.assertEqual(baseline.read_text(encoding='utf-8'), 'different baseline')

    def test_tampered_package_fails_before_creating_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            drive, root = Path(tmp) / 'drive', Path(tmp) / 'workspace'
            package = self.package(drive)
            package.write_bytes(package.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'hash'):
                self.bootstrap(drive, root)
            self.assertFalse((drive / 'runs').exists())

    def test_wrong_prompt_ids_and_path_traversal_are_rejected(self):
        for options, message in [({'bad_id': True}, '20'), ({'unsafe': True}, 'Unsafe ZIP')]:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                drive, root = Path(tmp) / 'drive', Path(tmp) / 'workspace'
                self.package(drive, **options)
                with self.assertRaisesRegex(ValueError, message):
                    self.bootstrap(drive, root)
                self.assertFalse((Path(tmp) / 'outside.txt').exists())
                self.assertFalse((drive / 'runs').exists())

    def test_changed_input_cannot_reuse_saved_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            drive, root = Path(tmp) / 'drive', Path(tmp) / 'workspace'
            self.package(drive)
            run = drive / 'runs/self_dev20_qwen_v1'
            run.mkdir(parents=True)
            stamp = run / 'input_receipt.json'
            stamp.write_text(json.dumps({'sha256': 'different input'}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'RUN_NAME'):
                self.bootstrap(drive, root)
            self.assertEqual(json.loads(stamp.read_text(encoding='utf-8'))['sha256'], 'different input')

    def test_actual_gpu_cell_rejects_cpu_and_all_cells_compile(self):
        notebook = build_notebook()
        source = ''.join(notebook['cells'][1]['source'])
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        with patch.dict(sys.modules, {'torch': fake_torch}), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'GPU'):
                exec(compile(source, 'self-gpu-cell', 'exec'), {})
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), 'self-notebook', 'exec')
                self.assertEqual(cell['outputs'], [])


if __name__ == '__main__':
    unittest.main()
