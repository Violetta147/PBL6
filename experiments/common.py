"""Shared data and scoring rules for the three small ASR experiments."""
import csv
import hashlib
import json
import unicodedata
from pathlib import Path


def normalize(text):
    text = unicodedata.normalize('NFC', text).lower()
    text = ''.join(' ' if unicodedata.category(c).startswith('P') else c for c in text)
    return ' '.join(text.split())


def edit_counts(reference, prediction):
    """Levenshtein S/D/I counts. Ties: substitution, deletion, insertion."""
    previous = [(j, 0, 0, j) for j in range(len(prediction) + 1)]
    for i, ref in enumerate(reference, 1):
        current = [(i, 0, i, 0)]
        for j, hyp in enumerate(prediction, 1):
            if ref == hyp:
                current.append(previous[j - 1])
            else:
                cost, s, d, ins = previous[j - 1]
                sub = (cost + 1, s + 1, d, ins)
                cost, s, d, ins = previous[j]
                delete = (cost + 1, s, d + 1, ins)
                cost, s, d, ins = current[j - 1]
                insert = (cost + 1, s, d, ins + 1)
                current.append(min([sub, delete, insert], key=lambda x: x[0]))
        previous = current
    errors, substitutions, deletions, insertions = previous[-1]
    return dict(errors=errors, substitutions=substitutions, deletions=deletions, insertions=insertions)


def score(reference, prediction):
    ref, hyp = normalize(reference), normalize(prediction)
    words = edit_counts(ref.split(), hyp.split())
    chars = edit_counts(ref.replace(' ', ''), hyp.replace(' ', ''))
    nw, nc = len(ref.split()), len(ref.replace(' ', ''))
    return dict(reference_normalized=ref, prediction_normalized=hyp,
                reference_units=nw, reference_chars=nc,
                word_errors=words['errors'], char_errors=chars['errors'],
                substitutions=words['substitutions'], deletions=words['deletions'],
                insertions=words['insertions'],
                WER_ws=words['errors'] / nw if nw else None,
                CER=chars['errors'] / nc if nc else None)


def aggregate(rows):
    if not rows:
        raise ValueError('No evaluation rows')
    scored = [score(r['reference'], r['prediction'] if r['status'] == 'ok' else '') for r in rows]
    speech = [s for s in scored if s['reference_units']]
    nw, nc = sum(s['reference_units'] for s in speech), sum(s['reference_chars'] for s in speech)
    silence = [(r, s) for r, s in zip(rows, scored) if not s['reference_units']]
    silent_minutes = sum(float(r.get('duration_s', 0)) for r, _ in silence) / 60
    return dict(total=len(rows), completed=sum(r['status'] == 'ok' for r in rows),
                reference_units=nw, reference_chars=nc,
                WER_ws=sum(s['word_errors'] for s in speech) / nw if nw else None,
                CER=sum(s['char_errors'] for s in speech) / nc if nc else None,
                false_captions_per_minute=sum(bool(s['prediction_normalized']) for _, s in silence) / silent_minutes if silent_minutes else None)


def read_fleurs(path, split):
    result = []
    with Path(path).open(encoding='utf-8', newline='') as file:
        for line, fields in enumerate(csv.reader(file, delimiter='\t'), 1):
            if len(fields) not in (6, 7):
                raise ValueError(f'{path}:{line}: unexpected {len(fields)} columns')
            filename = fields[1]
            if Path(filename).name != filename or not filename.endswith('.wav'):
                raise ValueError(f'Unsafe audio filename: {filename}')
            result.append(dict(id=f'fleurs/{split}/{filename}', filename=filename,
                               split=split, corpus='fleurs_vi_vn', reference=fields[2],
                               source_id=fields[0]))
    if len({r['id'] for r in result}) != len(result):
        raise ValueError('Duplicate FLEURS audio IDs')
    return result


def read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError('Cannot write an empty CSV')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as file:
        return [json.loads(line) for line in file if line.strip()]
