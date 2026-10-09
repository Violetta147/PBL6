import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_asr


class QwenGpuPolicyTests(unittest.TestCase):
    def test_explicit_cpu_fails_before_reading_manifest_or_writing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'result.jsonl'
            result = subprocess.run([sys.executable, str(Path(run_asr.__file__)),
                                     '--model', 'qwen', '--device', 'cpu',
                                     '--manifest', str(Path(tmp) / 'missing.csv'),
                                     '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('CPU fallback is disabled', result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix('.run.json').exists())

    def test_auto_without_cuda_never_loads_qwen(self):
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(run_asr, 'ROOT', Path(tmp)), patch.dict(sys.modules, {'torch': fake_torch}):
                with self.assertRaisesRegex(ValueError, 'GPU-only'):
                    run_asr.load_backend('qwen', 'auto', 2)

    def test_other_cpu_baselines_remain_allowed(self):
        run_asr.require_qwen_gpu('whisper', 'cpu', False)
        run_asr.require_qwen_gpu('zipformer', 'cpu', False)


if __name__ == '__main__':
    unittest.main()
