# STT evidence inventory — 2026-11-02

Use [the current work plan](../../STT_PLAN_1_WEEK.md) and [the single BOM](../../STT_BOM.md) for new work. This inventory did not run ASR, call APIs or deploy to the Pi.

## Evidence files

- `files.json`: snapshot of 961 non-environment files, with roles and sizes, before backup relocation. Environment contents are counted in `evidence.json` groups, not listed individually. `.git` is excluded.
- `evidence.json`: manifest hashes, saved-run score recomputation, independent JiWER verification, notebook source metadata, local model checks, historical runner matches, source-receipt hashes and six ZIP member inventories/CRC checks. Read each run's explicit verification scope; a null error field alone is not a pass certificate.
- `archive_manifest.json`: source/destination paths, byte counts, SHA-256 and verification status for 48 backup files. Both backup directories now reside under `D:\PBL6_archive\20261102_STT_backups\data\`. The old directories contain `ARCHIVED_TO_D.json` pointers. Resolve historical backup references with the manifest. No active ASR source or notebook referenced these backup directories.

## Verification

The existing suite passed 22 tests, zero failures, with `data\stt_venv\Scripts\python.exe -m unittest discover -s experiments/tests -v`. It checks scoring, audio preparation, Qwen GPU policy, notebook behavior and measurement helpers. It is not a live STT check.

All four audio manifests matched local WAV hashes: pilot10, FLEURS dev100, self dev20 and paired self dev4. The public test manifest contains 200 reserved IDs, not restored test audio or reference text.

There are 17 nonempty saved JSONL files. Stored per-row scoring matched recomputation in all 17. Thirteen complete, full-manifest runs also passed `verify()` checks against IDs, references, audio hashes and independent JiWER corpus scores. Three smoke files and the unfinished six-row Qwen CPU attempt are outside that full-manifest claim.

Thirty current-code hash comparisons were made. Four historical runner hashes differ from current `run_asr.py`; all four were found exactly in Git. B01 pilot and B02 FLEURS runs match commit `13421d4d7d18a1f965f7a002120c0cc4549b828e`. The cancelled Qwen CPU attempt matches `4ce005e06d6523d1261e791010f0f947aae986ff`. Saved metadata remains unchanged. Use those versions to reproduce the historical runs.

Twenty-eight available local weight-file comparisons matched saved backend hashes. Whisper GGML weights and the Pi binary are not in this laptop tree: retain their metadata, but do not call this a fresh Pi-file verification. Qwen weights are absent locally; they are not needed to inspect saved predictions.

Five experiment notebooks were inspected as JSON/source metadata. Existing notebook tests passed. Six ZIPs under `data/derived` were listed and passed CRC without extraction. This does not claim all raw compressed corpus archives were opened or notebook inference cells were rerun.

All 48 archived backup files matched destination hashes and sizes: 5,843,130 bytes. No raw audio, model, environment, experiment result, `.git`, user-edited document, cloud file or `iot` item was moved. The presentation-tool environment stays because `reports/render_slides.mjs` and its test use it. The file snapshot predates the move; the relocation manifest describes current backup locations.

## Findings that affect new experiments

- B01 is a train pilot. B02/B03 use selected development data, not the full FLEURS dev split. The paired four recordings overlap self dev20; do not count them as 24 independent items. Two extra cafe versions remain outside the main 20.
- Self dev20 has one speaker and different sentences across two bedroom and eighteen cafe items. It does not isolate noise effects. Zipformer lists FLEURS among training sources; exact overlap has not been established.
- Laptop CPU and Colab A100 quality outputs use the same audio, but their timings are not a controlled hardware comparison.
- Zipformer/Pi has two full passes with one model setup per pass. Whisper-base/Pi has one-file smoke only. Tiny is a different checkpoint. The Whisper CLI starts per WAV; its timer scope differs from Zipformer ASR-call and full-runner scopes. No speedup ratio follows from these different scopes. Backend `load_seconds` is broader than isolated weight load. GPU synchronization already exists.
- The old `whisper_protocol.md` permits stopping at base smoke. The later plan retains base as a baseline. N02 must use a stated run limit and new IDs, without rewriting old results as complete.
- The Zipformer runtime is an offline recognizer. Segmentation can feed it, but does not make it native streaming. Saved file results do not measure live subtitle delay, Stop or connection-failure behavior.
- No measured cloud API output was found in the historical inventory. Current provider decisions are in the main plan.
- The newer discussion confirms webcam capture and headphone playback on Pi. Old statements that no microphone is available are stale. This is historical user-confirmed evidence, not a device test performed in this chat.
- `iot` contains one PowerPoint file; no STT service or firmware source was found there. Keep it. Its presence does not establish that integration exists.
- Drive receipts describe 2026-10-15 checks; they do not prove current cloud synchronization. This inventory made no cloud changes or cloud revalidation.

## Decisions and remaining inputs
