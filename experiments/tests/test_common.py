import csv
import io
import json
import sys
import tempfile
import unittest
import unicodedata
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import aggregate, edit_counts, normalize, read_fleurs, score


class ScoringTests(unittest.TestCase):
    def test_normalization_preserves_accents_digits(self):
        self.assertEqual(normalize('  TÔI, có 25 quả! '), 'tôi có 25 quả')
        self.assertEqual(normalize(unicodedata.normalize('NFD', 'Má')), 'má')
        self.assertNotEqual(normalize('má'), normalize('ma'))

    def test_hand_counted_substitution_deletion_insertion(self):
        self.assertEqual(score('tôi đi học', 'tôi học')['deletions'], 1)
        self.assertAlmostEqual(score('tôi đi học', 'tôi học')['WER_ws'], 1 / 3)
        self.assertEqual(score('tôi đi học', 'tôi đi chơi')['substitutions'], 1)
        self.assertEqual(score('tôi học', 'tôi đi học')['insertions'], 1)
        self.assertEqual(score('má', 'ma')['CER'], .5)

    def test_empty_reference_is_not_divided_by_zero(self):
        self.assertIsNone(score('', 'chữ sai')['WER_ws'])
        self.assertEqual(score('tôi học', '')['WER_ws'], 1)
        result = aggregate([dict(reference='', prediction='chữ sai', status='ok', duration_s=30)])
        self.assertIsNone(result['WER_ws'])
        self.assertEqual(result['false_captions_per_minute'], 2)

    def test_corpus_weighting_and_failed_inference(self):
        rows = [dict(reference='a b c', prediction='a b c', status='ok'),
                dict(reference='d', prediction='fake text from failed run', status='error')]
        result = aggregate(rows)
        self.assertEqual(result['WER_ws'], .25)
        self.assertEqual(result['completed'], 1)
        self.assertEqual(result['total'], 2)

    def test_edit_distance_matches_independent_jiwer(self):
        try:
            import jiwer
        except ImportError:
            self.skipTest('Optional independent check: pip install jiwer==4.0.0')
        for ref, hyp in [('tôi đi học', 'tôi học'), ('ma má 25', 'má ma hai mươi lăm'), ('', 'a'), ('a b', ''), ('a a b', 'b a b a')]:
            self.assertEqual(edit_counts(ref.split(), hyp.split())['errors'],
                             jiwer.process_words(ref, hyp).substitutions + jiwer.process_words(ref, hyp).deletions + jiwer.process_words(ref, hyp).insertions)


class DataTests(unittest.TestCase):
    def test_six_and_seven_column_rows_keep_raw_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'dev.tsv'
            with path.open('w', encoding='utf-8', newline='') as file:
                csv.writer(file, delimiter='\t').writerows([
                    ['1', 'a.wav', 'Má đi học.', 'má đi học', 'chars', '16000', 'FEMALE'],
                    ['2', 'b.wav', 'Tôi ở đây.', 'tôi ở đây', '16000', 'MALE']])
            rows = read_fleurs(path, 'dev')
            self.assertEqual([r['reference'] for r in rows], ['Má đi học.', 'Tôi ở đây.'])
            self.assertEqual(rows[1]['id'], 'fleurs/dev/b.wav')

    def test_bad_filename_and_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'dev.tsv'
            path.write_text('1\t../a.wav\tref\tx\tx\tx\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                read_fleurs(path, 'dev')
            path.write_text(('1\ta.wav\tref\tx\tx\tx\n') * 2, encoding='utf-8')
            with self.assertRaises(ValueError):
                read_fleurs(path, 'dev')


class AudioPreparationTests(unittest.TestCase):
    def test_float_source_is_preserved_and_derivative_is_pcm16(self):
        import tarfile
        import numpy as np
        import soundfile as sf
        import prepare
        from common import sha256
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.wav'
            sf.write(source, np.array([0, .25, -.25, .5], dtype='float32'), 16000, subtype='FLOAT')
            original_hash = sha256(source)
            archive = root / 'train.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                tar.add(source, arcname='train/a.wav')
            with patch.object(prepare, 'ROOT', root):
                rows = prepare.extract_selected(archive, [dict(filename='a.wav')], root / 'derived')
            derivative = root / rows[0]['audio_path']
            self.assertEqual(sf.info(derivative).subtype, 'PCM_16')
            self.assertEqual(sf.info(derivative).samplerate, 16000)
            self.assertEqual(sha256(source), original_hash)
            self.assertEqual(rows[0]['source_audio_sha256'], original_hash)
            self.assertEqual(rows[0]['audio_sha256'], sha256(derivative))
            self.assertEqual(rows[0]['duration_s'], 4 / 16000)


if __name__ == '__main__':
    unittest.main()
