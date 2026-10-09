"""Run one pretrained checkpoint on one frozen manifest; no training."""
import argparse
import importlib.metadata
import json
import os
import platform
import sys
import tarfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from common import read_csv, read_jsonl, score, sha256

ROOT = Path(__file__).resolve().parents[1]
ZIPFORMER_PACKAGE = 'sherpa-onnx-zipformer-vi-30M-int8-2026-02-09'
ZIPFORMER_URL = f'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{ZIPFORMER_PACKAGE}.tar.bz2'
QWEN_REVISION = '5eb144179a02acc5e5ba31e748d22b0cf3e303b0'


def environment():
    versions = {}
    for name in ['torch', 'numpy', 'openai-whisper', 'sherpa-onnx', 'qwen-asr', 'transformers',
                 'soundfile', 'huggingface-hub', 'accelerate', 'librosa', 'qwen-omni-utils']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return dict(python=sys.version, platform=platform.platform(), processor=platform.processor(),
                packages=versions, COLAB_RELEASE_TAG=os.environ.get('COLAB_RELEASE_TAG'),
                framework_env={name: os.environ.get(name) for name in ['USE_TF', 'USE_FLAX']})


def load_backend(model_name, device, threads):
    import numpy as np
    import soundfile as sf
    cache = ROOT / 'data/models'
    cache.mkdir(parents=True, exist_ok=True)
    if model_name == 'zipformer':
        import sherpa_onnx
        model_dir = cache / ZIPFORMER_PACKAGE
        required = ['encoder.int8.onnx', 'decoder.onnx', 'joiner.int8.onnx', 'tokens.txt']
        archive = cache / f'{ZIPFORMER_PACKAGE}.tar.bz2'
        if not all((model_dir / name).is_file() for name in required):
            if not archive.exists():
                partial = archive.with_suffix('.part')
                urllib.request.urlretrieve(ZIPFORMER_URL, partial)
                partial.replace(archive)
            with tarfile.open(archive, 'r:bz2') as tar:
                for name in required:
                    member = tar.getmember(f'{ZIPFORMER_PACKAGE}/{name}')
                    if not member.isfile():
                        raise ValueError(f'Invalid model member {name}')
                    model_dir.mkdir(parents=True, exist_ok=True)
                    (model_dir / name).write_bytes(tar.extractfile(member).read())
        recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(model_dir / required[0]), decoder=str(model_dir / required[1]),
            joiner=str(model_dir / required[2]), tokens=str(model_dir / required[3]),
            num_threads=threads, sample_rate=16000, feature_dim=80,
            decoding_method='greedy_search', provider='cpu')

        def infer(audio):
            stream = recognizer.create_stream()
            stream.accept_waveform(16000, audio)
            recognizer.decode_stream(stream)
            return stream.result.text

        details = dict(checkpoint='hynt/Zipformer-30M-RNNT-6000h', package=ZIPFORMER_PACKAGE,
                       runtime='sherpa-onnx offline ONNX INT8', device='cpu', threads=threads,
                       decoding='greedy_search', source=ZIPFORMER_URL,
                       weights_sha256={name: sha256(model_dir / name) for name in required})
        return infer, lambda: None, details

    import torch
    torch.manual_seed(42)
    torch.set_num_threads(threads)
    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA requested but not available')

    def synchronize():
        if device == 'cuda':
            torch.cuda.synchronize()

    details = dict(device=device, threads=threads,
                   gpu=torch.cuda.get_device_name(0) if device == 'cuda' else None)
    if model_name == 'whisper':
        import whisper
        model = whisper.load_model('base', device=device, download_root=str(cache / 'whisper'))

        def infer(audio):
            with torch.inference_mode():
                return model.transcribe(audio, language='vi', task='transcribe', temperature=0.0,
                                        condition_on_previous_text=False, fp16=device == 'cuda',
                                        verbose=None)['text']

        details.update(checkpoint='openai/whisper-base multilingual', runtime='openai-whisper',
                       weights_url=whisper._MODELS['base'],
                       weights_sha256=sha256(cache / 'whisper/base.pt'),
                       decoding=dict(language='vi', task='transcribe', temperature=0.0,
                                     condition_on_previous_text=False, fp16=device == 'cuda'))
    elif model_name == 'qwen':
        from huggingface_hub import snapshot_download
        from qwen_asr import Qwen3ASRModel
        local = snapshot_download('Qwen/Qwen3-ASR-0.6B', revision=QWEN_REVISION,
                                  cache_dir=str(cache / 'huggingface'),
                                  local_dir=str(cache / 'Qwen3-ASR-0.6B' / QWEN_REVISION),
                                  token=False,
                                  allow_patterns=['*.json', '*.safetensors', '*.txt', '*.model', '*.jinja'])
        dtype = torch.bfloat16 if device == 'cuda' and torch.cuda.is_bf16_supported() else torch.float32
        model = Qwen3ASRModel.from_pretrained(local, dtype=dtype, device_map=device,
                                            max_inference_batch_size=1, max_new_tokens=512)

        def infer(audio):
            with torch.inference_mode():
                return model.transcribe(audio=(np.asarray(audio), 16000), language='Vietnamese')[0].text

        details.update(checkpoint='Qwen/Qwen3-ASR-0.6B', revision=QWEN_REVISION,
                       runtime='qwen-asr Transformers', dtype=str(dtype),
                       decoding=dict(language='Vietnamese', batch_size=1, max_new_tokens=512))
    else:
        raise ValueError(model_name)
    return infer, synchronize, details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['whisper', 'zipformer', 'qwen'], required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto')
    parser.add_argument('--threads', type=int, default=2)
    args = parser.parse_args()
    if args.model == 'qwen':
        # This backend uses PyTorch. Avoid loading unused TensorFlow/Flax on RAM-limited PCs.
        os.environ['USE_TF'] = '0'
        os.environ['USE_FLAX'] = '0'
    rows = read_csv(args.manifest)
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Manifest empty or duplicate IDs')
    if any(r['split'] not in ['train', 'dev'] for r in rows):
        raise ValueError('B01-B03 only accept train pilot/dev; test is reserved')
    if any(r['corpus'] == 'self_recorded' and r.get('label_verified') != 'yes' for r in rows):
        raise ValueError('Self-recorded references must be listened to and verified')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = args.output.with_suffix('.run.json')
    signature = dict(model=args.model, manifest_sha256=sha256(args.manifest),
                     runner_sha256=sha256(__file__), scoring_sha256=sha256(ROOT / 'experiments/common.py'),
                     requested_device=args.device, threads=args.threads)
    prior = []
    if args.output.exists():
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        if metadata['signature'] != signature:
            raise ValueError('Existing run uses different code/data/settings. Use a new output path.')
        prior = read_jsonl(args.output)
        ids = [r['id'] for r in prior]
        if len(set(ids)) != len(ids) or not set(ids).issubset({r['id'] for r in rows}):
            raise ValueError('Invalid existing prediction IDs')
        if len(prior) == len(rows) and metadata.get('finished'):
            print(f'Already complete: {args.output}', flush=True)
            return
    else:
        metadata = dict(signature=signature, environment=environment(),
                        started_utc=datetime.now(timezone.utc).isoformat(), finished=False)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    start = time.perf_counter()
    infer, synchronize, details = load_backend(args.model, args.device, args.threads)
    metadata.update(backend=details, load_seconds=time.perf_counter() - start, environment=environment())
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    import soundfile as sf
    processed = {r['id'] for r in prior}
    with args.output.open('a', encoding='utf-8') as output:
        for row in rows:
            if row['id'] in processed:
                continue
            record = dict(row, model=args.model, prediction='', status='error', error='', elapsed_s=None)
            try:
                audio_path = ROOT / row['audio_path']
                if sha256(audio_path) != row['audio_sha256']:
                    raise ValueError('Audio hash mismatch')
                audio, rate = sf.read(audio_path, dtype='float32')
                if rate != 16000 or audio.ndim != 1:
                    raise ValueError('Expected mono 16kHz audio, resample before inference')
                record['duration_s'] = len(audio) / rate
                synchronize()
                start = time.perf_counter()
                record['prediction'] = infer(audio).strip()
                synchronize()
                record.update(elapsed_s=time.perf_counter() - start, status='ok')
            except Exception as error:
                record['error'] = f'{type(error).__name__}: {error}'
            record.update(score(record['reference'], record['prediction'] if record['status'] == 'ok' else ''))
            output.write(json.dumps(record, ensure_ascii=False) + '\n')
            output.flush()
            processed.add(row['id'])
            print(f'{len(processed)}/{len(rows)} {record["status"]} {row["id"]}', flush=True)
    metadata.update(finished=True, ended_utc=datetime.now(timezone.utc).isoformat(),
                    total=len(rows), completed=sum(r['status'] == 'ok' for r in read_jsonl(args.output)))
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
