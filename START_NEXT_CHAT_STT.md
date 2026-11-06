# STT: continue here

Updated: 2026-11-07. Original target: Thursday, 2026-11-05 (past); no replacement deadline has been agreed.

Keep the active project at `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`. The user explicitly cancelled relocation to drive D. The attempted relocation stopped during source hashing, before copying or source removal. `D:\PBL6_STT` was not created. The temporary migration script is disabled. The earlier archive of 48 backup files is a separate completed operation.

Read these current documents:

1. [Main plan](STT_PLAN_1_WEEK.md).
2. [System behavior, Settings and IoT](STT_SYSTEM_SPEC.md).
3. [Sequential handoff for five people](STT_SHIFT_HANDOFF.md).
4. [Single BOM and options comparison](STT_BOM.md).
5. [Verified historical evidence](experiments/inventory_20261102/README.md).

Build STT only: microphone or files -> local/cloud recognizer -> subtitles in a web application. Require provisional text that can change, final text, and correct Stop/finalization. Support file/list input too. Use one foreground speaker at desktop distance and prioritize Central Vietnamese. Use the Pi webcam microphone already tested and the laptop display first. Capture during playback is allowed; evaluate AEC later if the actual playback test shows a problem.


Final product decision (2026-11-06): **touchscreen and kiosk mode**. The Pi must start the STT interface in full screen after boot, with normal operation by touch. Use the laptop for development and initial V1 testing. The screen model is not selected; physical touchscreen/kiosk acceptance comes at device integration. Keep V1 before V2/V3.

**Display sequence: stabilize HDMI + USB touch before evaluating DSI as an optional upgrade.** Keep the working HDMI configuration; verify Pi 4/OS/cable/power compatibility and repeat screen, touch, on-screen entry and kiosk boot checks before accepting DSI. Neither display path has been tested in this chat. See the dedicated HDMI + USB section in `STT_BOM.md` for the first screen, micro-HDMI cable, USB touch data cable and model-specific power; DSI purchase research follows that section. Screen model and price are not selected.

==**Approved stack (2026-11-07): React + TypeScript + Tailwind CSS, Next.js/Node.js, and Electron.**== Use a shared UI for laptop development/browser checks and the final Pi desktop application. On the device, Electron opens the local Next.js UI; Node.js manages Pi capture, Settings and Deepgram. Keep keys on the backend. See `STT_SYSTEM_SPEC.md` for the architecture and desktop verification gates.

**Next implementation target: V1 with Deepgram. N02 remains unfinished research, not a prerequisite for V1.** Complete N02 before using local timing/RTF to compare speed or choose a local engine based on speed. Preserve B01–B04 and the documented timing-scope limitations.

Settings includes cloud configuration, enabled local engines, active engine, capture source, subtitle options, segmentation, recovery, retention and installed software version. The STT IoT path covers application/session/error/version telemetry, dashboard and an actual application OTA update. ThingsBoard is a candidate, not a previously confirmed platform. Device resource dashboards and arbitrary remote controls are outside the current product scope.

The two earlier discussions have been read in full. A separate exporter chat completed a tool in Downloads, and another chat owns the dictation source study. Neither task blocks the STT implementation. New user decisions in the current documents take precedence over older exported conversations.

Keep B01–B04 results and user edits. Existing 22 tests and the evidence audit passed. V1-P1 has an implementation and offline tests; the full application, real API and Pi gates are not complete. Start the next unfinished shift in the handoff. Inspect Git status, update related documentation/tests, run appropriate checks, and commit each completed change according to AGENTS.md.

## Implementation checkpoint — V1-P1, 2026-11-07

**V1-P1 code is in `stt-app`: local Settings, one-file Deepgram adapter, shared UI and Electron window.** Production build and TypeScript checks passed; 20 backend tests and 7 Chrome/HTTP/Electron tests passed on Windows with offline provider fixtures. No real Deepgram request, Pi capture, batch, LAN control or Linux ARM64/touch/kiosk acceptance has been completed. Full V1 remains unfinished.

Read `reports/stt_v1_p1_20261107/BAO_CAO.md` and `stt-app/README.md` for evidence and startup/trial commands. The next user action is to enter the key locally and try one short file, returning the outcome/error without credentials. Pause at this report checkpoint for the user's next decision before expanding to batch/Pi. N02 remains unfinished; preserve B01–B04 and the timing-scope caveat.

Use Deepgram with `language=vi`; the user confirms API access is ready. Provide local key entry in Settings. Implement V1 record-then-transcribe, V2 streaming with final-only display, then V3 interim/final live text. Near-device seated and standing speech are valid; record actual distance and use the group's Da Nang speech. No old multiple-choice answers are required to begin.
