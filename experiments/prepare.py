"""Freeze IDs, restore only pilot/dev WAVs, and build a small Colab package."""
import argparse
import io
import json
import random
import tarfile
import zipfile
from pathlib import Path
from common import read_csv, read_fleurs, sha256, write_csv

ROOT = Path(__file__).resolve().parents[1]


def selected(rows, count):
    return sorted(random.Random(42).sample(rows, count), key=lambda row: row['id'])


def build_package():
    package = ROOT / 'data/derived/stt_b01_b03_package.zip'
    package.parent.mkdir(parents=True, exist_ok=True)
    excluded = {'__pycache__', 'results', 'attempts', '.ipynb_checkpoints'}
    state_files = {'PROGRESS.md', 'VALIDATION.md', 'verification.json', 'package_receipt.json'}
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as zip:
        for directory in [ROOT / 'experiments', ROOT / 'data/derived/stt_b01_b03']:
            for path in sorted(directory.rglob('*')):
                if path.is_file() and not excluded.intersection(path.parts) and path.name not in state_files:
                    zip.write(path, path.relative_to(ROOT).as_posix())
        self_manifest = ROOT / 'experiments/manifests/self_dev20.csv'
        if self_manifest.exists():
            for row in read_csv(self_manifest):
                source = (ROOT / row['audio_path']).resolve()
                if not source.is_relative_to(ROOT.resolve()) or row['split'] != 'dev':
                    raise ValueError('Only self-recorded dev under the workspace may be packaged')
                if row['consent'] != 'yes' or row['label_verified'] != 'yes' or sha256(source) != row['audio_sha256']:
                    raise ValueError('Self-recorded audio/consent/reference not verified')
                zip.write(source, source.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(package) as zip:
        if zip.testzip() is not None:
            raise ValueError('ZIP CRC failure')
    receipt = dict(package=package.relative_to(ROOT).as_posix(), bytes=package.stat().st_size,
                   sha256=sha256(package), crc_verified=True, contains_test_audio=False)
    (ROOT / 'experiments/package_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))
    return package


def extract_selected(archive, rows, destination):
    """Copy named regular files, never execute archive paths or extract test audio."""
    import soundfile as sf
    pending = {r['filename']: r for r in rows}
    found = set()
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, 'r|gz') as tar:
        for member in tar:
            name = Path(member.name).name
            if name not in pending:
                continue
            if not member.isfile() or name in found:
                raise ValueError(f'Invalid or duplicated tar member: {member.name}')
            data = tar.extractfile(member).read()
            audio, rate = sf.read(io.BytesIO(data), dtype='float32')
            if rate != 16000 or audio.ndim != 1:
                raise ValueError(f'{name}: expected mono 16kHz source')
            duration = len(audio) / rate
            output = destination / name
            # Source FLEURS WAVs are IEEE float; derive PCM16 without changing rate.
            sf.write(output, audio, rate, subtype='PCM_16')
            pending[name]['audio_path'] = output.relative_to(ROOT).as_posix()
            pending[name]['duration_s'] = duration
            pending[name]['audio_sha256'] = sha256(output)
            import hashlib
            pending[name]['source_audio_sha256'] = hashlib.sha256(data).hexdigest()
            found.add(name)
    if found != set(pending):
        raise ValueError(f'Missing audio: {set(pending) - found}')
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / 'data/raw/fleurs/vi_vn')
    parser.add_argument('--package-only', action='store_true', help='Repackage code/selected WAVs without rescanning raw tarballs')
    args = parser.parse_args()
    if args.package_only:
        build_package()
        return
    manifests = ROOT / 'experiments/manifests'
    pilot = selected(read_fleurs(args.source / 'train.tsv', 'train'), 10)
    dev = selected(read_fleurs(args.source / 'dev.tsv', 'dev'), 100)
    reserved = selected(read_fleurs(args.source / 'test.tsv', 'test'), 200)
    # Test references and test WAVs stay outside the Colab package.
    write_csv(manifests / 'test_ids_reserved.csv',
              [dict(id=r['id'], filename=r['filename'], split='test') for r in reserved])
    for split, rows, filename in [('train', pilot, 'pilot.csv'), ('dev', dev, 'fleurs_dev100.csv')]:
        rows = extract_selected(args.source / f'audio/{split}.tar.gz', rows,
                                ROOT / 'data/derived/stt_b01_b03' / split)
        write_csv(manifests / filename, rows)
        print(f'{filename}: {len(rows)} WAVs, {sum(r["duration_s"] for r in rows):.2f}s', flush=True)
    provenance = dict(seed=42, selection='random.sample on original TSV row order; then sort by ID',
                      source='google/fleurs', revision='70bb2e84b976b7e960aa89f1c648e09c59f894dd',
                      pilot=10, dev=100, test_ids_only=200,
                      audio_derivation='soundfile: IEEE float WAV -> PCM16, mono16kHz unchanged',
                      source_tsv_sha256={s: sha256(args.source / f'{s}.tsv') for s in ['train', 'dev', 'test']})
    (manifests / 'selection.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding='utf-8')
    build_package()


if __name__ == '__main__':
    main()
