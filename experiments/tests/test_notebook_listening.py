"""Regression: listening cell runs without imports from the previous cell."""
import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

NOTEBOOK = Path(__file__).resolve().parents[1] / 'B03/B03_Qwen_Colab_GPU.ipynb'


class ListeningCellTests(unittest.TestCase):
    def test_saved_results_play_without_previous_cell_imports(self):
        import numpy as np
        import soundfile as sf
        from IPython.display import Audio
        notebook = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        code = ''.join(notebook['cells'][-1]['source'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'saved_run'
            output.mkdir()
            sf.write(root / 'sample.wav', np.zeros(160, dtype='float32'), 16000, subtype='PCM_16')
            fields = ['id', 'audio_path', 'reference', 'whisper_prediction',
                      'zipformer_prediction', 'qwen_prediction', 'qwen_WER_ws']
            long_text = 'má đi học ' * 100 + 'END_OF_FULL_TRANSCRIPT'
            with (output / 'comparison.csv').open('w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                for i in range(4):
                    writer.writerow(dict(id=str(i), audio_path='sample.wav', reference=long_text,
                                         whisper_prediction='ma', zipformer_prediction='má',
                                         qwen_prediction='má', qwen_WER_ws=i / 10))
            namespace = {'ROOT': root, 'RUN_DIR': output}
            captured = []
            output_text = io.StringIO()
            with patch('IPython.display.display', side_effect=captured.append), redirect_stdout(output_text):
                exec(compile(code, 'listening-cell', 'exec'), namespace)
            self.assertEqual(len([item for item in captured if isinstance(item, Audio)]), 3)
            printed = output_text.getvalue()
            self.assertEqual(printed.count(long_text), 3)
            self.assertLess(printed.index('ID: 3'), printed.index('ID: 2'))
            self.assertLess(printed.index('ID: 2'), printed.index('ID: 1'))
            for label in ['Nhãn chuẩn', 'Whisper', 'Zipformer', 'Qwen']:
                self.assertEqual(printed.count(label + ':'), 3)

    def test_missing_workspace_explains_how_to_open_saved_results(self):
        notebook = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        with self.assertRaisesRegex(RuntimeError, 'RUN_NAME'):
            exec(''.join(notebook['cells'][-1]['source']), {})
