# STT prototype: seven-day work plan

Date: 2026-11-02. Use this file for new STT work. Keep `PLAN_DEMO_STT_7_BUOI.md` as the previous plan.

## 1. Scope and dependencies

Build this path: microphone or recorded files -> speech-to-text engine -> subtitles in a web application. Open the application on the laptop. Use the Pi microphone for the device path. Test one file and a list of files. Test a local engine, Google Cloud Speech-to-Text, and Deepgram. Keep the engine choice open until the comparison is complete.

Allow microphone capture during text-to-speech (TTS) playback. First test the actual audio. Add acoustic echo cancellation (AEC) if speaker audio causes a problem. Do not use microphone muting as the default design. Headphones can test playback, but cannot prove that speaker echo is controlled.

Use the existing Pi, webcam microphone, headphones and laptop first. Keep the sign-language recognizer outside this STT change. Define its interface to the application. Use existing sign-language and TTS code only after its owner supplies the interface and a working example. Do not start new sign-language model work.

Use seven work periods. The working schedule is 2–8 November 2026. This is a scheduling assumption, not a confirmed submission date. Ask the user for the actual deadline before a device session is booked. The agent can prepare code and test evidence before that answer.

Keep a small ThingsBoard stage after the STT path works. The user has requested device monitoring. Do not treat this stage as a reason to postpone the first STT path. Confirm whether it must pass in this week before it takes time from required engine comparisons. Do not silently remove the stage.

Account status, API spending limit, current Pi access, final test distance and the submission time are not yet known. Ask for each input before its dependent action. Do not ask for API keys in chat. Do not make paid requests until the user gives a run budget. Keep blocked engines in the comparison table with their actual status.

## 2. Fixed experiment rules

1. Keep B01–B04 and all saved predictions. Use new IDs N01–N07 and new output directories for new work. Do not overwrite a prior run.
2. Use WER_ws as the primary text metric. It counts whitespace units, often Vietnamese syllables. Use CER as a secondary metric. Neither metric proves that meaning is correct.
3. Keep the current scorer for the first new comparison: Unicode NFC, lower case, punctuation replaced by spaces, repeated spaces removed. Keep accents and digits. For CER, remove spaces. Thus `25` and `hai mươi lăm` remain different. Store raw and normalized text. Do not use an engine-specific text correction before scoring.
4. For valid audio with an error or timeout, retain the record and status. Score a missing transcript as empty. Give completion counts with the score. For non-speech audio, count nonempty final captions per audio minute. Do not divide WER by an empty reference.
5. Use the same frozen WAVs for engine quality tests. Use each model's required frontend. Make any noise reduction or AEC change a separate condition. Do not claim that these changes improve accuracy before testing them.
6. For local performance tests, use the same Pi, WAV order, two compute threads where supported, and one loaded model for each pass. Record runtime, checkpoint hashes, numerical type, decoding, OS, temperature, clock and throttling. Keep the Pi free from unrelated work.
7. Measure setup separately from steady processing. The old `load_seconds` includes backend setup and hashes. Do not call it isolated weight-loading time. Record first-call effects. Use one unscored warm-up file, then two passes with reversed engine order. Record OS cache as uncontrolled unless it is measured.
8. Define common timing boundaries before a run. Measure audio already in RAM -> transcript, including the required frontend and decoding, for both local engines. Measure full process wall time separately. If common boundaries are not available, compare only the common full-pass scope and state the model reuse policy. Exclude scoring from both engine timers.
9. For each scope, corpus RTF = total measured seconds / total audio seconds. Do not average per-file RTF to obtain corpus RTF. Distinguish elapsed wall time from CPU time. Keep GPU synchronization around timed GPU work.
10. Cloud timing measures the client request path, network and remote service together. Record the network, API model/version, region, options, request mode, retries, timestamps and billed audio when available. Do not call a cloud-versus-Pi timing difference a controlled hardware comparison.
11. Keep Qwen on a Colab GPU if a new Qwen run is needed. Check current Colab access first. Do not retry Qwen on the laptop CPU.

## 3. Data and selection

Use the existing pilot and development sets to check code and settings. The existing public set is a selected FLEURS dev100 subset. The self dev20 set has one speaker, two bedroom recordings and eighteen cafe recordings. Do not use these different sentences to isolate noise effects. The Zipformer model card lists FLEURS as training data. Exact split/ID overlap has not been established.

Before selecting an engine, reserve a practical new set: 10 development utterances, 20 evaluation utterances, and two minutes of non-speech audio. Ask the user to record these with the actual webcam microphone. Store original audio, reference, speaker/session, distance, environment and consent. The user must listen to and check the references. Keep development and evaluation sessions separate. Use a second speaker only if available; record the limitation if there is one speaker. Keep the 200 reserved public test IDs as a separate optional public comparison.

First use one speaker in a quiet indoor room. Treat distance and dialect coverage as open test inputs. Do not claim far-field, multi-speaker or dialect coverage without those recordings. To test noise, use matched sentences and the same speaker/distance with recorded conditions. Do not create a large collection task for one person in one week.

Before opening evaluation predictions, freeze the candidate configuration and provisional engineering targets. Proposed targets are: at least 95% of speech inputs complete, corpus local RTF below 1 for continuous use, and final subtitle delay p95 at most 3 seconds for short utterances. These are proposed prototype targets, not measured results or a confirmed user requirement. Agree or revise them before the selection run. Report the sample count; p95 from a small set is descriptive.

Choose the lowest development WER_ws among candidates that meet the agreed completion, latency and resource limits. Use CER and manual checks of numbers, names and negation to explain differences. Predefine the manual reference checks. If no engine passes the limits, report that outcome and offer an explicit per-utterance mode. Do not remove Whisper-base because it is slow. Freeze the choice before evaluation; do not select again from evaluation errors.

## 4. Work periods and gates

| Period / ID | Owner and action | Required input | Output and pass condition |
|---|---|---|---|
| 1 / N01 | Agent: inventory source, results, manifests, archives and dependencies. Recompute saved scores. User: supply actual deadline and account status when asked. | B01–B04, source discussions, local data | Inventory and discrepancy list. Every result has an input/model/runtime trace or an explicit missing-source note. No ASR rerun. |
| 2 / N02 | Agent: implement a common local measurement path and test its timer boundaries, timeout records and model reuse. User: provide a Pi session for the device check. | N01, Pi, C0 Whisper-base and C1 Zipformer | New configuration and runner tests. Then one smoke per engine and the same dev20 comparison. Keep tiny separate. Stop each engine after the agreed run limit; retain partial outputs. |
| 3 / N03 | Agent: implement Google and Deepgram adapters. User: configure credentials locally and approve an audio/spending cap. | Accounts, official language/model support check, N01 data | Same-file development outputs or explicit account/service failure. Test one file and a list. Record API options and client timing. Do not invent API results for an unavailable account. |
| 4 / N04 | Agent: add Pi capture, bounded queues, replay and subtitle events. User: test the selected capture device on Pi. | At least one working local or cloud adapter | Microphone -> subtitles and realtime WAV replay. Capture does not wait for network I/O. No silent queue overflow, missing final text or duplicated final segments in scripted tests. |
| 5 / N05 | Agent: connect the web interface. User: run capture on Pi and open the web application on the laptop. | N04, browser, local network | Start/Stop, engine selection, file/batch input, status and subtitles work. Test partial replacement, Stop, long silence, timeout, network loss and restart. Run local without Internet. |
| 6 / N06 | Agent and user: freeze settings, then evaluate reserved audio and live behavior. Test playback with capture enabled. | Checked references, frozen settings, physical speaker if testing echo | Raw predictions, per-segment timestamps, scores, failures, resource readings and selection outcome. Do not claim an echo test passed with headphones. If echo causes a problem, register an AEC condition and retain raw/processed audio for comparison. |
| 7 / N07 | Agent: finish reproducible startup and fault recovery checks. Add the small monitoring stage only after required STT gates pass. | N02–N06 or explicit failure status; monitoring scope decision | Clean-start check, repeatable local startup, preserved incomplete-run status. If monitoring is in scope: telemetry arrives and one configuration has an applied-value response. No claim that MQTT connection proves camera health. |

Dependencies are gates, not promises that a blocked stage finishes on a calendar day. Agent-only code and fixture tests can proceed while an account or Pi session is unavailable. Do not deploy to the Pi or start model runs from this document without checking their required inputs.

For N02, propose a 300-second per-file limit and a 45-minute per-engine session limit. Ask the user to accept or change these limits before the Pi run. Use a separate benchmark process so a timeout can end a blocked worker and preserve its log. A timeout is an outcome, not a reason to rename tiny as base. Do not use the old Whisper CLI-per-file timer as a warm-model measurement.

## 5. Live input and subtitle contract

Use Pi capture for the device microphone path. Do not accidentally use the laptop microphone because the page is open there. Replay feeds stored audio at its recorded rate and is labeled as replay. A recorded file can use a cloud engine; file input does not imply operation without Internet.

The capture callback writes a small block and returns. A separate worker sends or processes audio. Start with 20 ms capture blocks and a queue limit of two seconds of audio. Treat these values as development settings. On overflow, show an error and record the affected time interval. Do not silently discard audio or accumulate an unlimited delay. Audio blocks are not words and are not independent recognition requests.

Each session has a unique ID. Each subtitle segment has a stable ID and audio start/end times. An interim event replaces the current provisional text for that segment. A final event commits that segment once. Late events from an old session cannot change the new session. A local engine that returns only complete segments must declare that capability; do not invent provisional words.

Stop closes capture, sends any permitted pending audio, requests engine finalization, and waits for final results until a defined timeout. Show `finalizing` during this wait. Then close the session. If finalization fails, preserve the last confirmed text, mark the segment incomplete and show the error. Stop is separate from clearing subtitles and from stopping TTS playback.

The first network-loss implementation must show the failure, preserve confirmed text and offer local restart. Do not silently transfer an active session to another engine or imply uninterrupted transcription. Automatic transfer remains an open product choice. Keep failed/cloud and new/local session IDs separate. Never put cloud credentials in browser code.

Keep incoming speech subtitles separate from the outgoing gloss draft. New glosses can enter the next draft during TTS playback. They do not change the text already approved for playback and are not appended to incoming speech subtitles. A TTS fixture can test this interface, but must be labeled as a fixture.

## 6. Small monitoring stage

The requested direction is Pi -> MQTT -> ThingsBoard on a PC/server. Start with heartbeat, CPU/RAM, temperature and explicit application/camera states. Define states such as `not_started`, `capturing`, `stopped` and `error`; USB detection alone is not a health test. Keep the user web interface separate from the operator dashboard.

One proposed setting is TTS speed for the next playback. Do not implement it before a working TTS interface defines units and allowed values. Store requested and applied values separately, with a version and rejection reason. Check current ThingsBoard documentation and installation requirements before choosing the version. Do not add a separate broker, database, OTA or remote reset without a task that requires it.

## 7. User input at dependent steps

1. Before N02: give the SSH/Connect session to use, confirm the run limit, and run the supplied device-check commands. Return complete output and any error. Do not repeat the previous audio bring-up unless the device has changed or a new test fails.
2. Before N03: state whether Google Cloud STT billing and a Deepgram account are available. Configure credentials outside chat. Set the test-audio and spending cap. The agent then gives the exact local command and expected output for the prepared adapter.
3. Before N06: record and check the small data set. Confirm the main distance, noise condition and available speakers. Do not use model output as a checked reference.
4. Before a purchase: check the group inventory and the exact missing function. Give a purchase ceiling only if a purchase is needed. Verify current stock, accessories and delivery date before the schedule depends on an item.

## 8. Working references

- Local evidence: `experiments/inventory_20261102/evidence.json` and its README.
- Hardware and purchase gates: `STT_BOM.md`.
- Google interim/final result contract: https://docs.cloud.google.com/speech-to-text/docs/reference/rest/v2/StreamingRecognitionResult
- Deepgram finalization and interim results: https://developers.deepgram.com/reference/speech-to-text/listen-streaming
- Raspberry Pi power guidance: https://www.raspberrypi.com/documentation/computers/getting-started.html

Verify exact Vietnamese language support, service model, region, terms and price at N03. No API account, current credit balance or monthly allowance has been verified in this plan.
