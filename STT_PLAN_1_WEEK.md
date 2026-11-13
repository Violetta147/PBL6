# STT work plan to 5 November 2026

Updated 2026-11-08. The original target was Thursday, 2026-11-05. A replacement deadline is still open. Keep the active project at `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`. This file is the STT implementation plan. Keep `PLAN_DEMO_STT_7_BUOI.md` as the previous plan, `STT_SYSTEM_SPEC.md` for technical behavior, and `STT_SHIFT_HANDOFF.md` for shift sequencing.

## Next session — review one STT interaction

Start with [the current session handoff](START_NEXT_CHAT_STT.md). The 1024 × 600 wireframe shows the confirmed microphone states. Use it as the reference for recording, stopping, reviewing the recognized text in the shared composer, and sending it to the conversation. The first successful send adds the conversation to History. Implementation, device tests, benchmarks, and purchases follow separate user requests.

Use [the BOM](STT_BOM.md) for the confirmed purchase and pending hardware checks. The 7-inch NH2067 and its HDMI cable have been purchased and initially tested on Pi 4. The total project spending ceiling, test distance, exact board revision, and stand remain open. DSI is an optional later upgrade after HDMI and USB touch are stable.

## Product UI/UX decisions

Two people share a screen and composer. PBL6 handles speech-to-text, text-to-speech, and Settings. Text can come from another project, including sign recognition. The user has deferred the details of TTS, with **Đọc to** and **Gửi** kept as separate actions; in V1 UI, sent message cards hide the Read button. Read [the UI/UX specification](STT_PRODUCT_UI_UX.md) for confirmed rules and open choices. The implementation milestones below cover STT.

## 1. Scope and dependencies

Recognize speech from a microphone and show the result in the shared application. The application operates as a standalone tabletop device (Pi 4 with touchscreen in kiosk mode) or as a native Windows desktop app. Audio capture uses cross-platform Web Audio API. Use **Deepgram with `language=vi`** for V1. Research batches continue using experiment runners.

==**Final product decision (2026-11-06): use a touchscreen and kiosk mode (Pi) or standalone desktop window (Windows).**== Normal operation functions fully by touch or mouse. Remote control from a laptop over LAN is not part of the product. NH2067 is the selected display for the Pi tabletop device.

==**Display integration order (2026-11-06): stabilize HDMI video and USB touch first, then consider DSI as an optional upgrade.**== Preserve the approved V1/V2/V3 order. Before any DSI switch, keep the working HDMI configuration, verify the exact Pi 4, OS, display, and cable combination, and repeat display, touch, on-screen input, and kiosk startup checks.

**The tested HDMI and USB setup** uses NH2067, a micro-HDMI-to-HDMI cable, and one USB data cable for screen power and touch. The existing 5 V, 3 A adapter powers the Pi. Display output and touch response were confirmed by the user. Active resolution, swiping, touch accuracy, and kiosk behavior remain device acceptance checks. [BOM](STT_BOM.md) · [NH2067 guide](HUONG_DAN_NH2067_PI4.md)

Carry forward the longer-term target of allowing microphone capture during TTS playback. Revisit it after TTS design resumes. Test echo with an actual speaker before choosing acoustic echo cancellation (AEC). Headphone playback has been verified as an audio-output check.

Use the existing Pi, webcam microphone, headphones, and laptop for the STT milestones. Keep the STT flow independent of the sign-recognition project. Capture during playback can be tested when a playback source is available.

The original integration target was Thursday, 5 November 2026; it is now past and is not evidence of completion. Use five sequential shifts as specified in `STT_SHIFT_HANDOFF.md`. Each person must leave a runnable command, test result and next action. Do not treat five people as five independent implementations.

Include a small IoT path for STT session state, processing errors, software version and update status. MQTT, a cloud dashboard and over-the-air application updates are relevant. ThingsBoard is a platform candidate, not a previously confirmed platform choice. Do not build CPU/RAM dashboards or unrelated remote controls. See `STT_SYSTEM_SPEC.md` for the data contract.

The user confirms that Deepgram API access is ready. ==**The implementation must accept the API key in backend Settings**== and use `language=vi`. Do not repeat account/credit checks as a planning dependency. The first actual request still supplies its real success/error result. ==Configure the key locally, not in chat.==

### Selected software stack and next implementation target — 2026-11-07

==**Approved stack (2026-11-07): React + TypeScript + Tailwind CSS, Next.js/Node.js, and Electron.**== Use one shared UI across Windows desktop and Raspberry Pi kiosk. Audio capture uses Web Audio API directly in Chromium/Electron. Backend Settings holds the Deepgram key. Do not add FastAPI as the default V1 backend. The application structure is defined in `STT_SYSTEM_SPEC.md`; exact versions/build tooling remain implementation decisions.

**Proceed with V1 Deepgram before V2/V3. N02 remains separate, unfinished research.** The common timing protocol is documented, and the old runners and results still have different timing scopes. Finish the comparable Pi runs in N02 before a speed comparison or speed-based local-engine selection. Preserve the B01–B04 results with their original timing scopes.

V1 Stage 1 and Stage 2 are complete (92/92 tests passing). Stage 3 completes the sliding History drawer, Settings modal, and cross-platform Web Audio microphone capture for both Windows desktop and Raspberry Pi OS Bookworm. All temporary test pages have been removed to keep the repo clean. Keep fixture tests and real API checks distinct. Include clean startup commands and trial instructions.

The user confirmed on 2026-11-10 that batch processing is outside V1 acceptance. Research batches run against a manifest through experiment runners. Use known audio files in the existing P1 path for integration checks when needed. [Product UI scope](STT_PRODUCT_UI_UX.md#phương-án-đang-thảo-luận) · [Experiment inventory](experiments/inventory_20261102/README.md)

## Implementation checkpoint — V1-P1, 2026-11-07

**V1 Stage 1 and Stage 2 code is in `stt-app` (92 passing tests).** Production build and TypeScript checks passed. Stage 1 & 2 delivered local storage, API routes, and 1024×600 UI with smart-latch composer. Standalone device capture on Pi 4 kiosk mode remains an integration gate. Stage 3 is underway.

Read `reports/stt_v1_p1_20261107/BAO_CAO.md` and `stt-app/README.md` for evidence and startup commands. Use the updated wireframe as the reference when implementing Pi capture. N02 remains unfinished. Preserve B01–B04 and the timing-scope caveat.

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
| 5 / N05 | Agent: connect the web interface. User: verify capture and UI on Windows desktop and Pi kiosk. | N04, browser, local desktop/kiosk | Start/Stop, engine selection, status and subtitles work. Test partial replacement, Stop, long silence, timeout, network loss and restart. Run local without Internet. |
| 6 / N06 | Agent and user: freeze settings, then evaluate reserved audio and live behavior. Test playback with capture enabled. | Checked references, frozen settings, physical speaker if testing echo | Raw predictions, per-segment timestamps, scores, failures, resource readings and selection outcome. Do not claim an echo test passed with headphones. If echo causes a problem, register an AEC condition and retain raw/processed audio for comparison. |
| 7 / N07 | Agent: finish reproducible startup, STT telemetry and application update checks. | N02–N06 or explicit failure status; MQTT endpoint and update package | Clean-start check, session/version/error status on the dashboard, one verified application update and failure recovery. Keep an unavailable service explicit. |

Dependencies are gates, not promises that a blocked stage finishes on a calendar day. Agent-only code and fixture tests can proceed while an account or Pi session is unavailable. ==Do not deploy to the Pi or start model runs from this document without checking their required inputs.==

For N02, propose a 300-second per-file limit and a 45-minute per-engine session limit. Ask the user to accept or change these limits before the Pi run. Use a separate benchmark process so a timeout can end a blocked worker and preserve its log. A timeout is an outcome, not a reason to rename tiny as base. Do not use the old Whisper CLI-per-file timer as a warm-model measurement.

## 5. Live input and subtitle contract

Capture audio directly on the active device (Raspberry Pi kiosk or Windows desktop) via standard Web Audio API. Replay feeds stored audio at its recorded rate and is labeled as replay. A recorded file can use a cloud engine; file input does not imply operation without Internet.

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

Verify Vietnamese language support, service model, region, terms, and price for N03. The P1 report records two user-provided browser trials with Deepgram Nova-3 and `language=vi`. The remaining live Pi checks are a separate gate.

## Approved version order

| Version | Behavior | Completion gate |
|---|---|---|
| V1 | ==**Record on Pi, Stop, transcribe and send; Settings**== | On Pi, Stop leaves text in the draft for review. Sent message cards hide the Read button. **Gửi** during recording or recognition waits for final text and sends the combined draft once. On recognition failure, drop the pending send, show the error by the microphone, keep the draft and allow another recording. On send failure, keep the draft in the composer, keep **Gửi** enabled, show “Không gửi được. Hãy thử lại.” beside the microphone, and do not add to History if it was the first turn. Opening Settings preserves composer drafts. Reopen the saved conversation and send again. |
| V2 | Stream audio while recording; display final transcript after Stop | Capture/send/receive do not block each other; Stop preserves the audio tail and final text. |
| V3 | Show revisable interim text and committed final segments | Replacement, event ordering, duplicate prevention and late results pass tests. |

For V1 verification, the user runs the tests on the Pi and the agent prepares instructions and analyzes the returned output. **Settings** has an adjustable maximum recording duration in seconds, with a default of **120 seconds** and a validated range of **5 to 300 seconds** (rejecting empty or out-of-range inputs with an inline prompt). For the duration series, the user sets 10, 30 and 60 seconds in turn, starts recording through the normal microphone control and lets it stop automatically. Record the actual captured duration, backend memory baseline and peak, including the upload stage. Use test timestamps from automatic Stop until the final text is visible in the composer. Keep any manual Stop timing case separate and restore the previous duration setting after the series. [Audio sizing and measurement rationale](reports/NGHIEN_CUU_AM_THANH_TAM_STT.md#số-tệp-tải-ghi-và-tốc-độ-nói)

==**Complete V1 before V2, and V2 before V3.**== Experimental WER_ws, CER, timing, RTF and RAM remain research measurements. They do not add a product resource-management system. Do not use library adoption as evidence that a provider has better recognition quality. Compare the actual configurations on the same data.
