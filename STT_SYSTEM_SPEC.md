# STT behavior and IoT scope

Updated 2026-11-13. The active workspace is `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`. Stages 1 & 2 are complete. Giai đoạn 3 (History drawer, Settings, cross-platform Web Audio microphone on Windows and Pi 4) is under active development.

## Product UI/UX direction

Two people share one screen and composer. PBL6 handles speech recognition, reading text aloud, and Settings. Another project can supply text, including recognized-sign text. The user has deferred how TTS will work; V1 sent message cards hide the Read button. See [STT_PRODUCT_UI_UX.md](STT_PRODUCT_UI_UX.md) for confirmed design decisions and open choices. This specification covers technical STT behavior and hardware integration.

## Implementation checkpoint — V1 Stage 2/3 Progress, 2026-11-13

**V1 Stage 1 (Backend Storage, APIs, 92 unit/integration tests) and Stage 2 (1024×600 light-theme UI, Smart Latch composer, inline editing) are complete.** The temporary single-file test route (`/file-upload`) has been removed to keep the repository clean. Stage 3 completes the sliding History drawer (360px), full Settings modal, and cross-platform Web Audio microphone capture for both Windows desktop and Raspberry Pi 4 kiosk mode. All tests (92 passing) run in Node.js test runner with zero external binary dependencies.

Read `reports/stt_v1_p1_20261107/BAO_CAO.md` and `stt-app/README.md` for evidence and startup commands. Use [the current session handoff](START_NEXT_CHAT_STT.md) to begin the next design review. V1 acceptance covers Pi capture and the conversation flow. Use the existing one-file path for integration checks and the experiment runners for batches. Comparable Pi timing results remain pending in N02.

## Final device: touchscreen and kiosk (confirmed 2026-11-06)

==**The final tabletop product uses a touchscreen and kiosk mode, or runs as a native desktop application on Windows.**== Normal user operation must work by touch, including Record/Stop and Settings. Provide on-screen text entry when a field requires typing; essential actions must not depend on mouse hover.

The target deployment runs the Next.js/Node.js STT backend and Electron on the Pi (tabletop device with attached touchscreen) or locally on Windows. In kiosk mode on the Pi, Electron opens the local STT interface in full screen. On Windows, the app runs in a local desktop window. Audio capture occurs locally on the machine running the UI via standard Web Audio API. Operating the Pi device remotely from a laptop over LAN is explicitly not part of the product model: the product is a self-contained device operated on its own display.

The device integration gate is a real boot into the STT interface, followed by touch-only microphone start and stop, Settings, final transcript display, a shared error message location by the microphone, and text entry on the chosen screen. The user selected NH2067 and verified basic display output and touch on Pi 4. The complete touch-only app and kiosk gate remain pending. Complete the V1/V2/V3 gates in order.

### HDMI baseline and optional DSI upgrade

==**First establish a stable HDMI display and USB touch configuration, then consider DSI.**== The HDMI gate covers a cold boot into kiosk, readable text, correctly aligned touch, on-screen text entry, touch controls, and a real STT session with the webcam microphone. Record the screen, cables, power, and OS configuration used. Turning the whole device to share the screen is part of its use on a table.

The first display setup is NH2067 with a micro-HDMI-to-HDMI video cable and one USB data cable for screen power and touch. The existing 5 V, 3 A adapter powers the Pi. See [the BOM](STT_BOM.md) for the recorded purchase and [the NH2067 guide](HUONG_DAN_NH2067_PI4.md) for wiring and remaining checks.

DSI is a later hardware-integration option. Keep the web UI, STT session contract, backend and Deepgram configuration independent of the display connector. Changing to a different screen may require UI layout adjustments, OS display/touch configuration, power and enclosure work. Save the working HDMI configuration before switching; repeat the same acceptance checks on DSI and retain a documented route back to HDMI. Do not assume that every DSI panel works with Pi 4 or the installed OS.

## Approved application architecture — 2026-11-07

==**React + TypeScript + Tailwind CSS build the UI; Next.js/Node.js runs the application backend; Electron provides the desktop application and kiosk window.**== This is the selected stack. Do not default to the earlier FastAPI/plain-JavaScript proposal. Exact dependency versions and packaging tools must be pinned and checked during implementation.

| Layer | Responsibility |
|---|---|
| React + TypeScript | Recording controls, Web Audio API capture, 16kHz mono WAV encoding, session state, transcript/error display, and Settings. |
| Tailwind CSS | Touch-friendly layout, readable subtitles, and controls that work without hover on 1024×600 displays. |
| Next.js/Node.js backend | Authoritative sessions, persistent SQLite/JSON conversation storage, validated Settings, Deepgram provider requests, and audio reception. |
| Electron | Load the local application UI in a desktop window; configure media permissions (`permission === 'media'`); support kiosk mode on Pi and windowed mode on Windows. |
| OS & Audio Hardware (Windows WASAPI / Pi PipeWire) | Expose real microphone hardware via Chromium's native audio subsystem to Web Audio API, eliminating external CLI tools (SoX/arecord). |

Audio capture uses the standard **Web Audio API** in the client interface, providing consistent behavior across Windows (WASAPI) and Raspberry Pi OS Bookworm (PipeWire/ALSA). In `electron/main.cjs`, Electron grants `media` (microphone) permission exclusively for the local application origin (`http://127.0.0.1:*`). The client packages recorded speech into standard 16kHz mono WAV format (44-byte RIFF header) and posts it to the backend for Deepgram `nova-3/vi` transcription. In V1, Stop ends the recording and initiates transcription. A successful result is placed in the composer. If recognition fails, the interface keeps the draft, restores the ready microphone icon, and shows the user-facing error message beside the microphone.

The V1 composer accepts **Gửi** during recording or recognition. It stops capture if needed, waits for the final transcript of the same recording, inserts it at the composer caret, and submits the resulting draft once. If recognition fails, it drops the pending send and keeps the draft. If sending a message fails, the draft remains intact in the composer, the Send button immediately re-enables for retry, and an error message **“Không gửi được. Hãy thử lại.”** appears beside the microphone button, disappearing when the user edits text, taps the microphone, or retries. The failed message is not shown in the conversation and does not create an entry in History if it was the first turn. Switching conversations or closing the app discards unsent drafts, but opening **Settings** and returning to **Conversation** preserves the current draft in the composer. [Composer send behavior](reports/NGHIEN_CUU_GUI_KHI_DANG_THU.md#quyết-định-cho-pbl6-v1) · [Send failure handling](reports/NGHIEN_CUU_XU_LY_GUI_LOI.md)

Microphone selection in **Settings** uses `navigator.mediaDevices.enumerateDevices()` filtered to `audioinput`, listing friendly hardware names on both Windows and Pi. A `devicechange` event listener automatically updates device choices when a microphone is plugged in or unplugged. The user's selection is saved in persistent settings. If no microphone is available when tapping the mic button, the application displays **“Không tìm thấy mic. Hãy kết nối mic rồi thử lại.”** beside the button. If the active microphone is disconnected mid-recording, the application stops capture, cancels any pending **Gửi**, displays **“Mic bị ngắt kết nối. Đang nhận dạng phần đã thu.”** beside the microphone, and transcribes any captured audio into the composer for review before manual send (or keeps the existing draft and reports an error if no audio was captured or recognition fails). Reconnecting a microphone never auto-starts recording. [Microphone selection and review criteria](STT_PRODUCT_UI_UX.md#chọn-nguồn-micro-và-quản-lý-thu-âm-cross-platform-windows--pi-4)

Enter the Deepgram key through Settings and keep it on the backend machine. Return only redacted configuration/key-presence status; do not persist or expose the key in browser storage, Electron renderer code or logs. Future local engines may use separate Python/native adapters when required; the historical Python experiment scripts remain unchanged and do not require a FastAPI service for V1.

Desktop verification covers both Windows desktop builds and Linux ARM64 Pi kiosk builds. Verify production startup, backend readiness/failure, close/restart cleanup, touch input and on-screen keyboard, and boot into Electron kiosk on the actual Pi at device integration. Package updates must cover the Electron application and its backend together.

## Input and text

==**Audio capture operates locally on the host device (Pi kiosk or Windows desktop) via Web Audio API.**== V1 records then recognizes after Stop. Later versions stream audio during capture. A cloud service can process a file for integration checks. A local engine can work without Internet after its model is installed.

Support one foreground speaker at near-device distance, seated or standing. The group is from Da Nang; prioritize their Central Vietnamese speech. Record the actual distance in experiments. Do not claim overlapping-speaker separation. One microphone can contain several voices; separate online meeting participants can instead supply separate source streams. That is a different input contract.

Each session has a unique ID. Each segment has an ID, audio time range and revision. Sent messages record their input source tags (`voice`, `keyboard`, or multiple when combined) in underlying persistence data, while the UI completely hides these tags from users. ==Replace provisional text for that segment. Commit final text once.== Reject late events from an earlier session. Do not append each provisional hypothesis to the final transcript.

==**Stop ends capture**==, sends the permitted pending audio, requests provider finalization and waits for a bounded time. Show `finalizing`. ==**On timeout, retain confirmed text and mark the pending part incomplete.**== Keep Stop, clear-text and file-save as separate actions. The capture callback must not wait for a provider or MQTT response.

## Settings

| Group | Controls | Application rule |
|---|---|---|
| Cloud engine | Deepgram enable, API key, test connection, model, `language=vi` | ==**Store the key on the backend and redact it from responses/logs.**== The user confirms access is ready; report the actual first request result. |
| Local engines | Enable/disable, model directory, readiness, compute threads | Enabled and currently selected are separate states. Show missing model/runtime. Do not trigger a large model download from a toggle without stating the download. |
| Capture | Pi audio device, input level, supported format, capture mode | Verify the actual device format and convert when necessary. Show which machine captures audio. |
| Subtitles | Live provisional text, final text, font size, line length | The UI must distinguish provisional text from confirmed text. Capability depends on the engine. |
| Segmentation / Timing | Silence/end-of-utterance rule, maximum recording duration (seconds, default 120, range 5–300), recognition timeout (seconds, default 60, range 5–300) | Validate integer range 5–300 with inline prompts; prompt to save changes (Save, Discard, Stay) when navigating away. Keep advanced values validated. |
| Recovery | Connection status, local restart option, retry policy | Preserve confirmed text. A restart creates a new session; do not claim gap-free automatic transfer. |
| Data | Save/export transcript, optional audio retention and cloud upload | Default telemetry contains operational metadata. Upload transcript or audio only when that setting is enabled. |
| Software | Installed version, available update, verification and result | Do not apply an update during an active capture session. |

Apply engine, language and capture-format changes to the next session. Settings must state when a restart is needed. A disabled local engine cannot be selected for recovery. ==A connection test must report its real result; a saved key is not proof of access.==

## Record-once versus live text

| Design                                                  | Technical work                                                                                          | User experience                                                          | Use in this project                                                           |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Record once, transcribe after Stop                      | Capture, file encoding, one request, wait, error handling                                               | No words until capture ends and recognition returns                      | First diagnostic path and an explicit alternate mode                          |
| Streaming service with interim results                  | Persistent transport, concurrent send/receive, bounded buffering, revisions, finalization and reconnect | Words can change while the person speaks                                 | Preferred live-text path, subject to actual language/service testing          |
| Offline model repeatedly decoding a moving audio window | Window policy, repeated compute, overlap merging, stability and duplicate control                       | Can approximate changing text, with more compute and reconciliation work | Separate local experiment; do not assume the Pi can sustain it                |
| Offline model after utterance segmentation              | Capture plus segmentation and final segment decoding                                                    | Final chunks appear after each closed utterance                          | Useful local path, explicitly distinct from within-utterance provisional text |

The main extra difficulty in live text is maintaining a correct session across asynchronous events, not drawing changing words. Native streaming APIs reduce recognition work but do not solve application Stop, queue overflow or stale events. Engineering difficulty ratings are relative, not implementation-time guarantees.

## IoT responsibilities

| Path | Purpose | Initial data/behavior |
|---|---|---|
| Pi -> speech cloud | Speech recognition | Audio through the provider's supported HTTP/streaming transport; no separate MQTT step required |
| Pi -> web application | User interaction | Subtitles, capture state, Settings and recognition results |
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
