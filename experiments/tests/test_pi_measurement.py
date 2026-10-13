"""Timing math uses fixtures; actual benchmark outputs must come from Pi."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from B04.run_zipformer_pi import speed_stats, peak_rss_mib
from B04.run_whisper_cpp_pi import cli_command


class PiMeasurementTests(unittest.TestCase):
    def test_whisper_cli_preserves_paths_and_forces_vietnamese_cpu(self):
        command = cli_command('bin/whisper-cli', 'models/ggml-base.bin',
                              'audio with spaces/a.wav', 'result with spaces/01')
        self.assertEqual(command[command.index('-f') + 1], 'audio with spaces/a.wav')
        self.assertEqual(command[command.index('-of') + 1], 'result with spaces/01')
        self.assertEqual(command[command.index('-l') + 1], 'vi')
        self.assertIn('-ng', command)
        self.assertEqual(command[command.index('-t') + 1], '2')

    def test_rtf_total_weights_audio_duration(self):
        rows = [dict(id='a', status='ok', elapsed_s=1, duration_s=2),
                dict(id='b', status='ok', elapsed_s=1, duration_s=20)]
        result = speed_stats(rows)
        self.assertAlmostEqual(result['RTF_total'], 2 / 22)
        self.assertAlmostEqual(result['RTF_median'], (0.5 + 0.05) / 2)
        self.assertEqual(result['inference_seconds'], 2)

    def test_missing_failed_or_invalid_timing_does_not_become_zero(self):
        for row in [dict(id='a', status='error', elapsed_s=None, duration_s=2),
                    dict(id='a', status='ok', elapsed_s=None, duration_s=2),
                    dict(id='a', status='ok', elapsed_s=1, duration_s=0),
                    dict(id='a', status='ok', elapsed_s=float('nan'), duration_s=2)]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                speed_stats([row])
        duplicate = dict(id='a', status='ok', elapsed_s=1, duration_s=2)
        with self.assertRaises(ValueError):
            speed_stats([duplicate, duplicate])

    def test_gnu_time_peak_kib_is_reported_as_mib(self):
        self.assertEqual(peak_rss_mib('\tMaximum resident set size (kbytes): 262144\n'), 256)
        with self.assertRaises(ValueError):
            peak_rss_mib('No memory value available')


if __name__ == '__main__':
    unittest.main()
