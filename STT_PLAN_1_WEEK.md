# STT work plan to 5 November 2026

Updated: 2026-11-04. Deadline: Thursday, 2026-11-05. Keep the active project at `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`. Do not relocate it to drive D. Use this file for new STT work. Keep `PLAN_DEMO_STT_7_BUOI.md` as the previous plan. Use `STT_SYSTEM_SPEC.md` for behavior and `STT_SHIFT_HANDOFF.md` for sequential work by five people.

## 1. Scope and dependencies

Build this path: ==microphone or recorded files -> speech-to-text engine -> subtitles in a web application==. Open the application on the laptop. ==Use the Pi microphone for the device path.== ==**Test one file and a list of files.**== Test local engines and **Deepgram with `language=vi`**. Keep the engine choice open until the comparison is complete.

Allow microphone capture during text-to-speech (TTS) playback. First test the actual audio. Add acoustic echo cancellation (AEC) if speaker audio causes a problem. Do not use microphone muting as the default design. Headphones can test playback, but cannot prove that speaker echo is controlled.

Use the existing Pi, webcam microphone, headphones and laptop first. Build only the STT application in this project. Do not require code or interfaces from another recognition application. Test capture during playback only when an actual playback source is available.

Complete integration and verification by Thursday, 5 November 2026. Use five sequential shifts as specified in `STT_SHIFT_HANDOFF.md`. Each person must leave a runnable command, test result and next action. Do not treat five people as five independent implementations.

Include a small IoT path for STT session state, processing errors, software version and update status. MQTT, a cloud dashboard and over-the-air application updates are relevant. ThingsBoard is a platform candidate, not a previously confirmed platform choice. Do not build CPU/RAM dashboards or unrelated remote controls. See `STT_SYSTEM_SPEC.md` for the data contract.

The user confirms that Deepgram API access is ready. ==**The implementation must accept the API key in backend Settings**== and use `language=vi`. Do not repeat account/credit checks as a planning dependency. The first actual request still supplies its real success/error result. ==Configure the key locally, not in chat.==

## 2. Fixed experiment rules

1. ==**Keep B01–B04 and all saved predictions.**== Use new IDs N01–N07 and new output directories for new work. Do not overwrite a prior run.
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

Before selecting an engine, reserve a practical new set: 10 development utterances, 20 evaluation utterances, and two minutes of non-speech audio. Ask the user to record these with the actual webcam microphone. Store original audio, reference, speaker/session, distance, environment and consent. **The user must listen to and check the references.** Keep development and evaluation sessions separate. Use a second speaker only if available; record the limitation if there is one speaker. Keep the 200 reserved public test IDs as a separate optional public comparison.

Use one foreground speaker near the device, seated or standing. The user and the group are from Da Nang; **prioritize their Central Vietnamese speech**. Measure the actual mouth-to-microphone distance for each session; do not invent a distance from the user's description. Start in a quiet indoor room. Do not promise separation of overlapping speakers. To test noise, use matched sentences and the same speaker/distance with recorded conditions. Keep the collection small enough for the deadline.

Before opening evaluation predictions, freeze the candidate configuration and provisional engineering targets. Proposed targets are: at least 95% of speech inputs complete, corpus local RTF below 1 for continuous use, and final subtitle delay p95 at most 3 seconds for short utterances. ==These are proposed prototype targets, not measured results or a confirmed user requirement.== Agree or revise them before the selection run. Report the sample count; p95 from a small set is descriptive.

Choose the lowest development WER_ws among candidates that meet the agreed completion, latency and resource limits. Use CER and manual checks of numbers, names and negation to explain differences. Predefine the manual reference checks. If no engine passes the limits, report that outcome and offer an explicit per-utterance mode. Do not remove Whisper-base because it is slow. Freeze the choice before evaluation; do not select again from evaluation errors.

## 4. Work periods and gates

| Period / ID | Owner and action | Required input | Output and pass condition |
|---|---|---|---|
| 1 / N01 | Agent: inventory source, results, manifests, archives and dependencies. Recompute saved scores. User: supply actual deadline and account status when asked. | B01–B04, source discussions, local data | Inventory and discrepancy list. Every result has an input/model/runtime trace or an explicit missing-source note. No ASR rerun. |
| 2 / N02 | Agent: implement a common local measurement path and test its timer boundaries, timeout records and model reuse. User: provide a Pi session for the device check. | N01, Pi, C0 Whisper-base and C1 Zipformer | New configuration and runner tests. Then one smoke per engine and the same dev20 comparison. Keep tiny separate. Stop each engine after the agreed run limit; retain partial outputs. |
| 3 / N03 | Agent: implement the Deepgram adapter with `language=vi`. User: enter the API key locally when Settings is ready. | Accounts, official language/model support check, N01 data | Same-file development outputs or explicit account/service failure. Test one file and a list. Record API options and client timing. Do not invent API results for an unavailable account. |
| 4 / N04 | Agent: add Pi capture, bounded queues, replay and subtitle events. User: test the selected capture device on Pi. | At least one working local or cloud adapter | Microphone -> subtitles and realtime WAV replay. Capture does not wait for network I/O. No silent queue overflow, missing final text or duplicated final segments in scripted tests. |
| 5 / N05 | Agent: connect the web interface. User: run capture on Pi and open the web application on the laptop. | N04, browser, local network | Start/Stop, engine selection, file/batch input, status and subtitles work. Test partial replacement, Stop, long silence, timeout, network loss and restart. Run local without Internet. |
| 6 / N06 | Agent and user: freeze settings, then evaluate reserved audio and live behavior. Test playback with capture enabled. | Checked references, frozen settings, physical speaker if testing echo | Raw predictions, per-segment timestamps, scores, failures, resource readings and selection outcome. Do not claim an echo test passed with headphones. If echo causes a problem, register an AEC condition and retain raw/processed audio for comparison. |
| 7 / N07 | Agent: finish reproducible startup, STT telemetry and application update checks. | N02–N06 or explicit failure status; MQTT endpoint and update package | Clean-start check, session/version/error status on the dashboard, one verified application update and failure recovery. Keep an unavailable service explicit. |

Dependencies are gates, not promises that a blocked stage finishes on a calendar day. Agent-only code and fixture tests can proceed while an account or Pi session is unavailable. ==Do not deploy to the Pi or start model runs from this document without checking their required inputs.==

For N02, propose a 300-second per-file limit and a 45-minute per-engine session limit. Ask the user to accept or change these limits before the Pi run. Use a separate benchmark process so a timeout can end a blocked worker and preserve its log. A timeout is an outcome, not a reason to rename tiny as base. Do not use the old Whisper CLI-per-file timer as a warm-model measurement.

## 5. Live input and subtitle contract

Use Pi capture for the device microphone path. Do not accidentally use the laptop microphone because the page is open there. Replay feeds stored audio at its recorded rate and is labeled as replay. A recorded file can use a cloud engine; file input does not imply operation without Internet.

The capture callback writes a small block and returns. A separate worker sends or processes audio. Start with 20 ms capture blocks and a queue limit of two seconds of audio. Treat these values as development settings. On overflow, show an error and record the affected time interval. Do not silently discard audio or accumulate an unlimited delay. Audio blocks are not words and are not independent recognition requests.

Each session has a unique ID. Each subtitle segment has a stable ID and audio start/end times. An interim event replaces the current provisional text for that segment. A final event commits that segment once. Late events from an old session cannot change the new session. A local engine that returns only complete segments must declare that capability; do not invent provisional words.

==Stop closes capture==, sends any permitted pending audio, requests engine finalization, and waits for final results until a defined timeout. Show `finalizing` during this wait. Then close the session. If finalization fails, preserve the last confirmed text, mark the segment incomplete and show the error. Stop is separate from clearing subtitles and from stopping TTS playback.

The first network-loss implementation must show the failure, preserve confirmed text and offer local restart. Do not silently transfer an active session to another engine or imply uninterrupted transcription. Automatic transfer remains an open product choice. Keep failed/cloud and new/local session IDs separate. ==Never put cloud credentials in browser code.==

Implement versions in the approved order: ==V1 records then transcribes after Stop==; ==V2 streams audio but displays text after Stop==; ==V3 displays revisable interim text while recording and commits final text==. Keep each earlier mode usable. Live interim text is the V3 requirement, not a condition for calling V1 complete. The engine capability must be explicit; an engine that only returns final segments cannot claim to provide word updates while the segment is still being recorded.

## 6. Small monitoring stage

Use Pi -> MQTT -> cloud/dashboard for application telemetry. Start with session state, chosen engine, request completion/error counts, processed audio seconds, software version and update status. Keep the user web interface separate from the operator dashboard. MQTT is not required for sending audio to a speech provider. Do not add a separate broker when the selected platform already provides the needed endpoint.

Provide local Settings for cloud authentication, enabled local engines, selected engine, microphone, language, subtitle behavior and data retention. Do not add arbitrary remote commands. Over-the-air updates mean updating the Pi application package in this stage. Include package verification, version reporting, a health check and rollback. MCU firmware updates require an actual MCU task and remain a separate implementation choice.

## 7. User input at dependent steps

1. Before N02: give the SSH/Connect session to use, confirm the run limit, and run the supplied device-check commands. Return complete output and any error. Do not repeat the previous audio bring-up unless the device has changed or a new test fails.
2. Before N03: provide a local API-key input in Settings and use Deepgram with `language=vi`. The user confirms API access is ready.
3. Before N06: record and check the small Central Vietnamese data set at the intended desktop distance. Store the measured distance and noise condition. Do not use model output as a checked reference.
4. Before a purchase: compare alternatives in the BOM by benefit, limitation, extra cost and delivery. The user has not set a purchase ceiling and does not require the cheapest option. Do not ask for a ceiling before providing that comparison.

## 8. Working references

- Local evidence: `experiments/inventory_20261102/evidence.json` and its README.
- Hardware and purchase gates: `STT_BOM.md`.
- Deepgram finalization and interim results: https://developers.deepgram.com/reference/speech-to-text/listen-streaming
- Raspberry Pi power guidance: https://www.raspberrypi.com/documentation/computers/getting-started.html

Verify exact Vietnamese language support, service model, region, terms and price at N03. The user confirms Deepgram access is ready; an actual request has not yet been tested in this project.

## Approved version order

| Version | Behavior | Completion gate |
|---|---|---|
| V1 | ==**Record, Stop, transcribe; file/list input; Settings**== | ==**A real recording yields one final transcript or a clear error.**== |
| V2 | Stream audio while recording; display final transcript after Stop | Capture/send/receive do not block each other; Stop preserves the audio tail and final text. |
| V3 | Show revisable interim text and committed final segments | Replacement, event ordering, duplicate prevention and late results pass tests. |

==**Complete V1 before V2, and V2 before V3.**== Experimental WER_ws, CER, timing, RTF and RAM remain research measurements. They do not add a product resource-management system. Do not use library adoption as evidence that a provider has better recognition quality. Compare the actual configurations on the same data.
