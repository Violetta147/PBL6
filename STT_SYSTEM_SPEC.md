# STT behavior and IoT scope

Updated: 2026-11-07. Active workspace: `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`. Original target: Thursday, 2026-11-05 (past); no replacement deadline has been agreed. This is a specification; ==it does not assert that these functions have been implemented.==

## Implementation checkpoint — V1-P1, 2026-11-07

**V1-P1 code is in `stt-app`: local Settings, one-file Deepgram adapter, shared UI and Electron window.** Production build and TypeScript checks passed; 20 backend tests and 7 Chrome/HTTP/Electron tests passed on Windows with offline provider fixtures. No real Deepgram request, Pi capture, batch, LAN control or Linux ARM64/touch/kiosk acceptance has been completed. Full V1 remains unfinished.

Read `reports/stt_v1_p1_20261107/BAO_CAO.md` and `stt-app/README.md` for evidence and startup/trial commands. The next user action is to enter the key locally and try one short file, returning the outcome/error without credentials. Pause at this report checkpoint for the user's next decision before expanding to batch/Pi. N02 remains unfinished; preserve B01–B04 and the timing-scope caveat.

## Final device: touchscreen and kiosk (confirmed 2026-11-06)

==**The final tabletop product uses a touchscreen and kiosk mode.**== Normal user operation must work by touch, including Record/Stop and Settings. Provide on-screen text entry when a field requires typing; essential actions must not depend on mouse hover.

The target deployment runs the Next.js/Node.js STT backend and Electron on the Pi. After boot, the backend starts and Electron opens the local STT interface in kiosk mode on the attached touchscreen. The Pi microphone remains the capture source selected by the user. The laptop remains the development and initial V1 test interface.

The device integration gate is a real boot into the STT interface followed by touch-only Record/Stop, Settings, final transcript/error display and required text entry on the chosen screen. Kiosk mode and touchscreen operation are requirements, not implemented or verified features. Screen model, size, connection and power are not selected yet. Complete the V1/V2/V3 gates in order.

### HDMI baseline and optional DSI upgrade

==**First establish a stable HDMI display + USB touch configuration, then consider DSI.**== The HDMI gate covers a cold boot into kiosk, readable subtitles, correctly aligned touch including after rotation, touch-only Record/Stop and Settings, required on-screen text entry, and a real STT session with the webcam microphone. Record the screen, cables, power and OS configuration used. These are acceptance checks, not completed tests.

DSI is a later hardware-integration option. Keep the web UI, STT session contract, backend and Deepgram configuration independent of the display connector. Changing to a different screen may require UI layout adjustments, OS display/touch configuration, power and enclosure work. Save the working HDMI configuration before switching; repeat the same acceptance checks on DSI and retain a documented route back to HDMI. Do not assume that every DSI panel works with Pi 4 or the installed OS.

## Approved application architecture — 2026-11-07

==**React + TypeScript + Tailwind CSS build the UI; Next.js/Node.js runs the application backend; Electron provides the desktop application and kiosk window.**== This is the selected stack. Do not default to the earlier FastAPI/plain-JavaScript proposal. Exact dependency versions and packaging tools must be pinned and checked during implementation.

| Layer | Responsibility |
|---|---|
| React + TypeScript | Recording controls, session state, per-file/batch status, transcript/error display and Settings. |
| Tailwind CSS | Touch-friendly layout, readable subtitles and controls that work without hover. |
| Next.js/Node.js backend | Authoritative sessions, validated Settings, selected capture device, audio/file handling and provider requests. Keep capture work separate from network waits. |
| Electron | Load the local application UI in a desktop window; support the final device kiosk experience and desktop lifecycle. |
| Pi OS and audio/display support | Expose the actual microphone and touchscreen; start the backend and desktop application after boot. |

On the final device, the Next.js/Node.js backend and Electron run on the Pi. The OS starts the backend; Electron loads its local UI when ready. The backend controls the selected Pi microphone through a Pi capture adapter. For V1: Record -> capture -> Stop -> finish the audio file -> backend sends a prerecorded request to Deepgram with `language=vi` -> final transcript or explicit error. A file or batch uses the same provider interface, with independent status/results per file. Electron does not add streaming to V1.

During development, run the application on the laptop. For device tests, the laptop browser may open the shared UI served by the Pi backend; the selected capture source remains on the Pi. A laptop desktop build must identify which backend it controls and must not silently switch to its own microphone. This is one application with a shared UI and contracts, not separate desktop and web implementations.

Enter the Deepgram key through Settings and keep it on the backend machine. Return only redacted configuration/key-presence status; do not persist or expose the key in browser storage, Electron renderer code or logs. Future local engines may use separate Python/native adapters when required; the historical Python experiment scripts remain unchanged and do not require a FastAPI service for V1.

Desktop verification must distinguish Windows laptop builds from Linux ARM64 Pi builds. Verify production startup, backend readiness/failure, close/restart cleanup, touch input and on-screen keyboard, and boot into Electron kiosk on the actual Pi at device integration. Package updates must cover the Electron application and its backend together. Hardware/runtime support, startup time, resource use and touch responsiveness are not established by selecting this stack.

## Input and text

==**Capture on the Pi for the device path.**== Show the selected capture source in the web application on the laptop. ==A laptop browser must not silently substitute its own microphone.== ==Support live capture, record-once capture, one file and a file list.== A cloud service can process a file. A local engine can work without Internet after its model is installed.

Support one foreground speaker at near-device distance, seated or standing. The group is from Da Nang; prioritize their Central Vietnamese speech. Record the actual distance in experiments. Do not claim overlapping-speaker separation. One microphone can contain several voices; separate online meeting participants can instead supply separate source streams. That is a different input contract.

Each session has a unique ID. Each segment has an ID, audio time range and revision. ==Replace provisional text for that segment. Commit final text once.== Reject late events from an earlier session. Do not append each provisional hypothesis to the final transcript.

==**Stop ends capture**==, sends the permitted pending audio, requests provider finalization and waits for a bounded time. Show `finalizing`. ==**On timeout, retain confirmed text and mark the pending part incomplete.**== Keep Stop, clear-text and file-save as separate actions. The capture callback must not wait for a provider or MQTT response.

## Settings

| Group | Controls | Application rule |
|---|---|---|
| Cloud engine | Deepgram enable, API key, test connection, model, `language=vi` | ==**Store the key on the backend and redact it from responses/logs.**== The user confirms access is ready; report the actual first request result. |
| Local engines | Enable/disable, model directory, readiness, compute threads | Enabled and currently selected are separate states. Show missing model/runtime. Do not trigger a large model download from a toggle without stating the download. |
| Capture | Pi audio device, input level, supported format, capture mode | Verify the actual device format and convert when necessary. Show which machine captures audio. |
| Subtitles | Live provisional text, final text, font size, line length | The UI must distinguish provisional text from confirmed text. Capability depends on the engine. |
| Segmentation | Silence/end-of-utterance rule, maximum segment duration | Keep advanced values validated. A silence threshold does not identify a complete grammatical sentence. |
| Recovery | Connection status, local restart option, retry policy | Preserve confirmed text. A restart creates a new session; do not claim gap-free automatic transfer. |
| Data | Save/export transcript, optional audio retention and cloud upload | Default telemetry contains operational metadata. Upload transcript or audio only when that setting is enabled. |
| Software | Installed version, available update, verification and result | Do not apply an update during an active capture session. |

Apply engine, language and capture-format changes to the next session. Settings must state when a restart is needed. A disabled local engine cannot be selected for recovery. ==A connection test must report its real result; a saved key is not proof of access.==

## Record-once versus live text

| Design | Technical work | User experience | Use in this project |
|---|---|---|---|
| Record once, transcribe after Stop | Capture, file encoding, one request, wait, error handling | No words until capture ends and recognition returns | First diagnostic path and an explicit alternate mode |
| Streaming service with interim results | Persistent transport, concurrent send/receive, bounded buffering, revisions, finalization and reconnect | Words can change while the person speaks | Preferred live-text path, subject to actual language/service testing |
| Offline model repeatedly decoding a moving audio window | Window policy, repeated compute, overlap merging, stability and duplicate control | Can approximate changing text, with more compute and reconciliation work | Separate local experiment; do not assume the Pi can sustain it |
| Offline model after utterance segmentation | Capture plus segmentation and final segment decoding | Final chunks appear after each closed utterance | Useful local path, explicitly distinct from within-utterance provisional text |

The main extra difficulty in live text is maintaining a correct session across asynchronous events, not drawing changing words. Native streaming APIs reduce recognition work but do not solve application Stop, queue overflow or stale events. Engineering difficulty ratings are relative, not implementation-time guarantees.

## IoT responsibilities

| Path | Purpose | Initial data/behavior |
|---|---|---|
| Pi -> speech cloud | Speech recognition | Audio through the provider's supported HTTP/streaming transport; no separate MQTT step required |
| Pi -> web application | User interaction | Subtitles, capture state, Settings and explicit errors |
| Pi -> MQTT -> cloud dashboard | Manage the STT application | Device/application identity, session state, selected engine, completed/failed requests, processed audio seconds, software version and update status |
| Cloud package service -> Pi | Application OTA | Announce a version; retrieve its package; authenticate the publisher, verify integrity, install into a versioned directory, run a health check, switch or roll back, report result |

Keep CPU/RAM monitoring and arbitrary remote controls outside the product scope. Research resource measurements remain valid experiment outputs; they are not a requirement for a device-management dashboard.

==ThingsBoard remains a candidate== for telemetry, dashboard and update-package distribution. The earlier discussion proposed evaluating it; the user did not confirm every feature in the teacher's later summary. Choose it only if its current setup fits the deadline. A web application for subtitles and a ThingsBoard dashboard have different purposes.

For OTA, MQTT can carry update metadata/status and a supported transport can deliver the package. A checksum alone cannot authenticate the publisher. The device must implement installation and rollback; a package upload to ThingsBoard is not an end-to-end update. Do not deliver arbitrary shell commands as an update feature. Keep model downloads separate from a small application update.

Firmware is relevant when an MCU has a defined task such as a physical input control. STT does not require adding an MCU to show firmware activity. Pi application OTA and MCU firmware OTA are different targets.

## Active provider and version order

==**Use Deepgram**== with **`language=vi`**. The user confirms that API access is ready. Provide the key input in backend Settings. Keep local engines available as separate configurations. No executable decompilation is needed.

==Implement V1 record-then-transcribe, V2 streaming audio with final-only display, and V3 streaming audio with interim/final display, in that order.== **Retain the earlier modes and test each gate before progressing.**

Official provider reference: https://developers.deepgram.com/docs/models-languages-overview

Official update reference: https://thingsboard.io/docs/user-guide/ota-updates/
