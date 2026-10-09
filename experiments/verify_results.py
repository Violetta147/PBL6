"""Audit actual saved predictions against audio, references and independent JiWER."""
import json
from pathlib import Path
from common import aggregate, normalize, read_csv, read_jsonl, score, sha256

ROOT = Path(__file__).resolve().parents[1]


def verify(path, manifest):
    import jiwer
    path = Path(path)
    metadata = json.loads(path.with_suffix('.run.json').read_text(encoding='utf-8'))
    rows = read_jsonl(path)
    expected = {row['id']: row for row in read_csv(manifest)}
    assert metadata['finished'] is True, f'{path}: not finished'
    assert len(rows) == len(expected) == len({row['id'] for row in rows}), f'{path}: counts/duplicates'
    assert {row['id'] for row in rows} == set(expected), f'{path}: ID mismatch'
    assert metadata['signature']['manifest_sha256'] == sha256(manifest), f'{path}: manifest hash'
    for row in rows:
        original = expected[row['id']]
        assert row['reference'] == original['reference'], f'{row["id"]}: reference mismatch'
        assert row['audio_sha256'] == sha256(ROOT / row['audio_path']), f'{row["id"]}: audio hash'
        assert row['audio_sha256'] == original['audio_sha256'], f'{row["id"]}: manifest audio hash'
        recomputed = score(row['reference'], row['prediction'] if row['status'] == 'ok' else '')
        for field in ['WER_ws', 'CER', 'reference_units', 'reference_chars', 'word_errors', 'char_errors']:
            assert row[field] == recomputed[field], f'{row["id"]}: {field}'
    references = [normalize(row['reference']) for row in rows]
    predictions = [normalize(row['prediction']) if row['status'] == 'ok' else '' for row in rows]
    summary = aggregate(rows)
    word = jiwer.process_words(references, predictions)
    char = jiwer.process_characters([text.replace(' ', '') for text in references],
                                   [text.replace(' ', '') for text in predictions])
    assert abs(summary['WER_ws'] - word.wer) < 1e-12, 'Independent corpus WER mismatch'
    assert abs(summary['CER'] - char.cer) < 1e-12, 'Independent corpus CER mismatch'
    return dict(path=str(path.relative_to(ROOT)), verified=True, **summary)


def main():
    runs = [('B01/results/whisper_pilot.jsonl', 'pilot.csv'),
            ('B02/results/whisper_dev.jsonl', 'fleurs_dev100.csv'),
            ('B02/results/zipformer_dev.jsonl', 'fleurs_dev100.csv')]
    qwen = ROOT / 'experiments/B03/results/qwen_dev.jsonl'
    if qwen.exists():
        runs.append(('B03/results/qwen_dev.jsonl', 'fleurs_dev100.csv'))
    checks = [verify(ROOT / 'experiments' / run, ROOT / 'experiments/manifests' / manifest)
              for run, manifest in runs]
    report = ROOT / 'experiments/verification.json'
    report.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
