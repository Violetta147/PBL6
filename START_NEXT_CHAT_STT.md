# STT: continue here

Date: 2026-11-02. Deadline: Thursday, 2026-11-05.

Keep the active project at `C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6`. The user explicitly cancelled relocation to drive D. The attempted relocation stopped during source hashing, before copying or source removal. `D:\PBL6_STT` was not created. The temporary migration script is disabled. The earlier archive of 48 backup files is a separate completed operation.

Read these current documents:

1. [Main plan](STT_PLAN_1_WEEK.md).
2. [System behavior, Settings and IoT](STT_SYSTEM_SPEC.md).
3. [Sequential handoff for five people](STT_SHIFT_HANDOFF.md).
4. [Single BOM and options comparison](STT_BOM.md).
5. [Verified historical evidence](experiments/inventory_20261102/README.md).

Build STT only: microphone or files -> local/cloud recognizer -> subtitles in a web application. Require provisional text that can change, final text, and correct Stop/finalization. Support file/list input too. Use one foreground speaker at desktop distance and prioritize Central Vietnamese. Use the Pi webcam microphone already tested and the laptop display first. Capture during playback is allowed; evaluate AEC later if the actual playback test shows a problem.

The user has a Deepgram account and has used it in LearnHarness. Direct API access and remaining credit have not been checked. Google Cloud billing is not set up. Evaluate documented Speech-to-Text V2 and the current `chirp_3` candidate when account setup permits. Do not request secrets in chat or assume unused trial credit.

Settings includes cloud configuration, enabled local engines, active engine, capture source, subtitle options, segmentation, recovery, retention and installed software version. The STT IoT path covers application/session/error/version telemetry, dashboard and an actual application OTA update. ThingsBoard is a candidate, not a previously confirmed platform. Device resource dashboards and arbitrary remote controls are outside the current product scope.

The two earlier discussions have been read in full. A separate exporter chat completed a tool in Downloads, and another chat owns the dictation source study. Neither task blocks the STT implementation. New user decisions in the current documents take precedence over older exported conversations.

Keep B01–B04 results and user edits. Existing 22 tests and the evidence audit passed. The new application is not implemented merely because these documents exist. Start the next unfinished shift in the handoff. Inspect Git status, update related documentation/tests, run appropriate checks, and commit each completed change according to AGENTS.md.
