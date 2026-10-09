"""Validate real self-recorded dev WAVs and references before benchmarking."""
import argparse
import wave
from pathlib import Path
from common import read_csv, sha256, write_csv

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--metadata', type=Path, required=True)
    args = parser.parse_args()
    rows = read_csv(args.metadata)
    if len(rows) != 20 or len({r['id'] for r in rows}) != 20:
        raise ValueError('Expected 20 unique recordings for self dev')
    required = ['id', 'audio_path', 'reference', 'speaker', 'session', 'condition', 'consent', 'label_verified']
    output = []
    for row in rows:
        if any(not row.get(field, '').strip() for field in required):
            raise ValueError(f'{row.get("id")}: missing metadata')
        if row['consent'] != 'yes' or row['label_verified'] != 'yes':
            raise ValueError('Recordings need consent and listened-to references')
        path = ROOT / row['audio_path']
        with wave.open(str(path)) as wav:
            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (16000, 1, 2):
                raise ValueError(f'{path}: resample to mono 16kHz PCM16; do not only edit header')
            duration = wav.getnframes() / wav.getframerate()
        output.append(dict(row, split='dev', corpus='self_recorded', duration_s=duration, audio_sha256=sha256(path)))
    write_csv(ROOT / 'experiments/manifests/self_dev20.csv', output)
    print('Verified 20 self-recorded dev WAVs. No test recordings were imported.')


if __name__ == '__main__':
    main()
