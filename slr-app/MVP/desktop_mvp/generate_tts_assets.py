"""Generate and verify all 400 Vietnamese TTS MP3 files for the SLR Kiosk MVP."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import json
from pathlib import Path
import re
import time

ROOT = Path(__file__).resolve().parents[1]
LABELS_PATH = ROOT / "deployment" / "handoff_assets" / "label_map_v1.json"
TTS_DIR = ROOT / "local_data" / "tts"
MIN_MP3_BYTES = 500
PARENTHETICAL_INDICES = ("35", "36", "256", "313", "314", "366", "367", "389", "390")


def clean_spoken_text(gloss: str) -> str:
    """Strip parenthetical disambiguation notes so speech sounds natural."""
    return re.sub(r"\s*\([^)]*\)", "", gloss).strip()


def load_label_map() -> dict[str, str]:
    """Load the idx_to_gloss mapping from the frozen handoff label map."""
    data = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    return data["idx_to_gloss"]


def is_valid_mp3_bytes(data: bytes) -> bool:
    """Return True when data is non-trivial and starts with an ID3 or MPEG sync header."""
    if len(data) <= MIN_MP3_BYTES:
        return False
    return data.startswith(b"ID3") or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)


def synthesize_mp3_bytes(spoken_text: str, max_attempts: int = 3) -> bytes:
    """Synthesize Vietnamese MP3 bytes for one phrase with retry backoff."""
    from gtts import gTTS

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            buffer = BytesIO()
            gTTS(text=spoken_text, lang="vi", slow=False).write_to_fp(buffer)
            audio_bytes = buffer.getvalue()
            if not is_valid_mp3_bytes(audio_bytes):
                raise ValueError(
                    f"Synthesized audio for '{spoken_text}' invalid ({len(audio_bytes)} bytes)."
                )
            return audio_bytes
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(1.0 * (2 ** (attempt - 1)))
    raise RuntimeError(
        f"Failed to synthesize '{spoken_text}' after {max_attempts} attempts: {last_error}"
    )


def write_atomic(target: Path, data: bytes) -> None:
    """Write bytes atomically via a temporary file in the same directory."""
    tmp_path = target.with_suffix(".mp3.tmp")
    tmp_path.write_bytes(data)
    tmp_path.replace(target)


def generate_missing(force: bool = False, workers: int = 8) -> None:
    """Generate MP3 assets for all indices missing valid local audio files."""
    idx_to_gloss = load_label_map()
    TTS_DIR.mkdir(parents=True, exist_ok=True)

    grouped_targets: dict[str, list[tuple[str, str, Path]]] = defaultdict(list)
    skipped = 0

    for idx in sorted(idx_to_gloss.keys(), key=int):
        gloss = idx_to_gloss[idx]
        target = TTS_DIR / f"{idx}.mp3"
        if not force and target.is_file() and target.stat().st_size > MIN_MP3_BYTES:
            skipped += 1
            continue
        spoken = clean_spoken_text(gloss)
        grouped_targets[spoken].append((idx, gloss, target))

    if not grouped_targets:
        print(f"All {skipped} TTS MP3 files already exist cleanly.")
        return

    total_targets = sum(len(items) for items in grouped_targets.values())
    print(
        f"Preserved {skipped} existing files; synthesizing {len(grouped_targets)} "
        f"unique phrases for {total_targets} missing labels..."
    )

    completed_phrases = 0
    written_files = 0
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(synthesize_mp3_bytes, spoken): (spoken, items)
            for spoken, items in grouped_targets.items()
        }
        for future in as_completed(future_map):
            spoken, items = future_map[future]
            completed_phrases += 1
            try:
                audio_bytes = future.result()
                for _, _, target in items:
                    write_atomic(target, audio_bytes)
                    written_files += 1
            except Exception as exc:
                failures.append(f"{spoken}: {exc}")
            if completed_phrases % 50 == 0 or completed_phrases == len(grouped_targets):
                print(
                    f"Progress: {completed_phrases}/{len(grouped_targets)} phrases "
                    f"({written_files}/{total_targets} files written)",
                    flush=True,
                )

    if failures:
        raise RuntimeError("Some TTS generations failed:\n" + "\n".join(failures))


def verify_assets() -> None:
    """Verify all 400 label MP3 files exist, are valid MP3s, and print stats."""
    idx_to_gloss = load_label_map()
    missing: list[str] = []
    invalid: list[str] = []
    total_bytes = 0

    for idx in sorted(idx_to_gloss.keys(), key=int):
        target = TTS_DIR / f"{idx}.mp3"
        if not target.is_file():
            missing.append(idx)
            continue
        data = target.read_bytes()
        if not is_valid_mp3_bytes(data):
            invalid.append(f"{idx} ({len(data)} bytes)")
            continue
        total_bytes += len(data)

    if missing or invalid:
        raise AssertionError(
            f"Verification failed: {len(missing)} missing ({missing[:10]}), "
            f"{len(invalid)} invalid ({invalid[:10]})."
        )

    print(
        f"Verified {len(idx_to_gloss)}/{len(idx_to_gloss)} MP3 files cleanly "
        f"in {TTS_DIR} ({total_bytes / (1024 * 1024):.2f} MB total)."
    )
    print("Sample parenthetical label mappings:")
    for idx in PARENTHETICAL_INDICES:
        gloss = idx_to_gloss[idx]
        spoken = clean_spoken_text(gloss)
        size = (TTS_DIR / f"{idx}.mp3").stat().st_size
        print(f"  [{idx}] '{gloss}' -> spoken '{spoken}' ({size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Only verify existing 400 MP3 files")
    parser.add_argument("--force", action="store_true", help="Regenerate all 400 MP3 files")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent TTS workers")
    args = parser.parse_args()

    if not args.verify:
        generate_missing(force=args.force, workers=args.workers)
    verify_assets()


if __name__ == "__main__":
    main()
