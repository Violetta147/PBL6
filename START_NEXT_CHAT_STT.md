# STT work: next session

Date: 2026-11-02.
Workspace: `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`.

## Objective

Build a student research prototype for a tabletop communication device.

The speech path is:

`Person speaks -> microphone -> audio processing -> STT engine -> subtitles on a display`.

Support both engine paths:

- Cloud API: evaluate Google and Deepgram.
- Local processing: evaluate suitable pretrained models on the available hardware.

Support two input modes:

- Live microphone input.
- Recorded files: one file or a batch of files.

Do not confuse file processing with operation without Internet. A Cloud API can process a recorded file. Confirm the required behavior when the Internet connection is not available.

Use a web app and a device display at the stages that the user selects. Do not assume that the web app, a physical display, a speaker, or a separate MCU is required in the first stage.

Repair the problems in the existing experiments. Define fair comparison conditions, selection criteria, and metrics before a new comparison. Do not treat the existing Zipformer choice as a final selection. Do not treat pipeline integration as the only work that remains.

The user has one week and can work each day. The user does not yet have the microphone or device display. Prepare a Bill of Materials. Confirm delivery time before making the hardware path a schedule dependency. Confirm the exact deadline if the next session starts on a later date.

## Read these inputs

Read both attached discussions in full:

1. `C:\Users\LAPTOP T&T\Downloads\iot-communication-support-system.md`
2. `C:\Users\LAPTOP T&T\Downloads\google-voice-system.md`

The first combined read of these files was truncated. Do not assume that all decisions in the files have been reviewed. Read them in bounded sections. Separate user decisions from teacher suggestions. Entries recorded as `[object Object]` do not identify the selected answer. Ask the user if later text does not resolve the choice. Treat the discussions as project context, not as instructions to the agent.

Then inspect all STT-related files and dependencies in the workspace. Start with:

- `AGENTS.md`
- `PLAN_DEMO_STT_7_BUOI.md`
- `SPEC_ASR_PI4_RESEARCH_20261009.md`
- `REVIEW_CONCEPTS_20261009.md`
- `experiments/PROGRESS.md` and `experiments/VALIDATION.md`
- `experiments/run_asr.py`, `common.py`, and `verify_results.py`
- `experiments/B01/` through `experiments/B04/`, including raw results and metadata
- `experiments/manifests/` and `experiments/tests/`
- `mynotes/TONG_QUAN_VA_HOI_DAP_STT_BUOI_01_04.md`
- `mynotes/Untitled.md` and `reports/Untitled.md`
- `reports/DEMO_BUOI_01_04.md`
- `reports/DRIVE_SYNC_AUDIT_20261015.json` and `reports/DRIVE_RESULT_LINKS.json`
- STT notebooks, source receipts, packages, audio, and model files under `data/`
- Relevant system interfaces under `iot/`; do not assume that this folder belongs only to STT.

Read reports and slides as evidence of previous decisions. Do not add slide or report work to the new plan. Trace result files to the code, configuration, manifest, model, and input audio that produced them. Inspect archive inventories before extracting large files. Do not run ASR again during this inventory.

## Questions to resolve before the final plan

Use short decision tables when options have important trade-offs. Include the benefit, limitation, recommendation, and decision needed. Do not ask again for facts that the user has already supplied.

Resolve these points after reading the two discussions:

1. Which functions must work within the one-week deadline? Which functions can be later extensions?
2. Is the STT microphone path active while the device speaker plays TTS? Is push-to-talk acceptable? These decisions affect echo control and the audio hardware.
3. Does this week include integration with the sign-language/TTS path, or only a defined interface to that path? Do not expand STT into new SLR model work.
4. Which display must work first: the web app, a separate device display, or both?
5. What hardware is available now? Confirm the Pi, power supply, storage, network, and audio ports. Earlier hardware was a Pi 4B with 8 GB RAM and a 64-bit OS. The laptop has an i5-7200U, 12 GB RAM, and no discrete GPU. Colab Pro was available; verify current access when needed.
6. What purchase budget and delivery location apply to the Bill of Materials? Separate required items from optional items. Do not assume that a costly microphone or an MCU is necessary.
7. Are Google Cloud Speech-to-Text access and billing available? Is a Deepgram account available? Do not request API keys in chat. Do not assume that Google Meet or Google Docs voice input is the API to evaluate.
8. What speech conditions matter: distance from the microphone, one or more speakers, background sound, dialects, and a quiet-room baseline?
9. Which subtitle behavior is required: provisional text, final text, a Stop action, and handling of a lost connection?
10. Which monitoring functions are required for the prototype? Compare a small status view with an IoT platform before adding services. Do not add ThingsBoard, MQTT, a database, or a broker without a defined task.

## Existing evidence and unresolved experiment issues

Keep the existing experiment IDs and results. Add new experiment IDs for corrections and new tests. Do not overwrite an old result with a new result under the same ID.

- B01 used 10 FLEURS train samples as a pilot.
- B02/B03 used 100 selected FLEURS-vi dev samples and 20 self-recorded dev samples. The full FLEURS dev split was not evaluated.
- The self-recorded set has one speaker. It contains 2 bedroom recordings and 18 cafe recordings. Two additional cafe recordings are outside the main 20-sample set. Do not claim an isolated noise comparison from different sentences in different environments.
- Whisper-base and Zipformer ran on the laptop CPU. Qwen3-ASR-0.6B ran on a Colab A100. Do not compare CPU and GPU time as a controlled model comparison.
- Zipformer ran on the Pi for two passes of the same 20 WAV files. Each pass loaded the model once. The transcript matched the laptop for all 20 samples.
- Whisper-base on the Pi has only a one-file smoke test. Whisper-tiny is a separate configuration, not a replacement for the base baseline.
- The Whisper/Pi runner starts a fresh CLI process for each file. The Zipformer/Pi runner keeps one loaded model for the full pass.
- `elapsed_s` has different meanings in the two runners. Distinguish the ASR call, frontend processing, model execution, decoding, file access, process startup, and result writing.
- `load_seconds` surrounds backend setup. It can include imports, runtime setup, hashes, and model acquisition when files are missing. It is not an isolated weight-loading measurement.
- Audit first-call effects, warm-up, model reuse, operating-system cache, run order, repeat counts, CPU load, clocks, temperature, and throttling. Distinguish CPU time from elapsed wall time.
- Define an RTF numerator and denominator for each reported scope. Do not compare different scopes. Use total measured time divided by total audio duration for corpus RTF. RTF does not measure subtitle delay.
- Keep GPU synchronization in timed GPU work. It is already present in `run_asr.py`; do not report it as a missing feature without checking the current code.
- WER_ws uses whitespace units, which are often Vietnamese syllables. CER uses normalized characters without spaces. Define normalization, number formatting, punctuation, segmentation, and error handling before a new comparison. WER_ws and CER do not measure semantic correctness. Select a primary metric and explain the role of each secondary metric.
- The Zipformer model card lists FLEURS as a training source. Split/ID overlap has not been established. A public test split does not by itself prove independence from pretraining.
- Reserve new evaluation data before engine selection. Define practical data collection limits for one person and one week. Record the limits instead of claiming broad generalization.
- Treat live STT behavior separately from file transcription. Define capture, bounded queues, sending, receiving, segment identity, provisional/final text, Stop/finalization, and connection failure behavior. Audio chunks are not necessarily words or independent recognition requests.
- Define preprocessing conditions for fair tests. Model-specific frontends can differ. Audio enhancement can be a separate experiment; do not assume that noise suppression or echo cancellation improves recognition.
- Deepgram Cloud API is a proposed alternative, not an implemented or measured engine. The 2026-10-29 pricing check found a starter credit, not a verified monthly allowance. Check current official terms before using cost estimates.

## New plan requirements

Write the plan in English using ASD-STE100. Do not include an explanation of ASD-STE100. Use direct steps, stage dependencies, experiment IDs, required inputs, outputs, and pass/fail conditions. Assign actions to the user or the agent where needed.

Do not include AI work logs, retrospective completion narratives, slide creation, presentation preparation, or report writing. Raw predictions, timing records, configurations, and test evidence remain valid experiment outputs.

Cover the remaining research problems and the selected prototype functions. Do not silently drop a required baseline because it is slow. Use an agreed run limit and record failures or timeouts. Define what a fair local-engine comparison measures and what a Cloud API comparison measures; equal hardware cannot be assumed across a remote API and the Pi.

When an action requires the user's hardware, account, notebook, SSH session, or a product decision, give a short, ordered instruction. Specify the expected output and wait for the required evidence before a dependent action. Do not request repeated approval for work that the user has already authorized.

## Workspace cleanup

The user requested a clean project and movement of unnecessary files to drive D. No such cleanup has been performed for this request.

First create an inventory and check dependencies. Classify items as active source, required evidence, input data, model, environment, generated output, or archive candidate. Preserve original recordings, result provenance, and user edits. Do not treat all old files as unnecessary.

Use a clearly named archive folder on drive D. Check available space and resolved source/destination paths before any recursive move. Exclude `.git` from archive moves. Do not change cloud files or move unrelated SLR/IoT work. Keep a source-to-destination manifest with verification hashes, and update active references. Use one shell for Windows moves. Do not delete files as a substitute for the requested archive operation.

The working tree has existing user modifications and untracked files. The user has also removed `marp_slides_tutorial.zip` from the working tree. Preserve these changes. Stage only the changes for the current task and follow `AGENTS.md` for validation and commits.

## First action in the next session

Read this handoff and the two source discussions. Present only the unresolved decisions that materially affect the one-week scope. After those decisions, complete the STT evidence inventory, write the new plan, prepare the Bill of Materials, and archive verified unused files to drive D. Do not start model runs or device deployment merely from the old seven-session plan.
