"""Combine completed, identical-ID runs without hiding inference failures."""
import argparse
import json
from pathlib import Path
from common import aggregate, read_csv, read_jsonl, write_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--runs', nargs='+', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    expected = {r['id']: r for r in read_csv(args.manifest)}
    summaries, wide = [], {id: dict(id=id, reference=r['reference'], audio_path=r['audio_path']) for id, r in expected.items()}
    for path in args.runs:
        metadata = json.loads(path.with_suffix('.run.json').read_text(encoding='utf-8'))
        rows = read_jsonl(path)
        if not metadata.get('finished') or len(rows) != len(expected) or {r['id'] for r in rows} != set(expected):
            raise ValueError(f'Incomplete or different-ID run: {path}')
        if any(r['reference'] != expected[r['id']]['reference'] or r['audio_sha256'] != expected[r['id']]['audio_sha256'] for r in rows):
            raise ValueError(f'Reference/audio mismatch: {path}')
        summary = dict(model=rows[0]['model'], corpus=rows[0]['corpus'], split=rows[0]['split'],
                       device=metadata['backend']['device'], runtime=metadata['backend']['runtime'], **aggregate(rows))
        summaries.append(summary)
        for row in rows:
            model = row['model']
            wide[row['id']].update({f'{model}_prediction': row['prediction'], f'{model}_status': row['status'],
                                   f'{model}_WER_ws': row['WER_ws'], f'{model}_CER': row['CER']})
    write_csv(args.output_dir / 'summary.csv', summaries)
    write_csv(args.output_dir / 'comparison.csv', wide.values())
    (args.output_dir / 'summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
