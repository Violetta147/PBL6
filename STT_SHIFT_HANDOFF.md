# STT implementation and shift handoff

Updated 2026-11-10. The original target was Thursday, 2026-11-05. A replacement deadline is still open. Keep this Git repository and active STT data in the current C-drive workspace. Read `AGENTS.md` and check Git status, then follow [the current session handoff](START_NEXT_CHAT_STT.md). Use `STT_PLAN_1_WEEK.md` and `STT_SYSTEM_SPEC.md` when returning to implementation.

## Next session — use the updated V1 wireframe

Start with Pencil frames **09 · Cài đặt theo nhóm** and **10 · Cài đặt Lịch sử**. Frame 10 now shows the approved history-management layout at 1024 × 600. The title search, last-successful-send time filter and result-wide selection sit above the scrollable list. The delete button stays below it and names the number selected. Changing the search or filter clears the previous selection. Pressing Delete removes the selected conversations immediately. The screenshot depicts 12 matching results, with two excluded and 10 selected. [History-management research and decision](reports/NGHIEN_CUU_TIM_LOC_VA_XOA_LICH_SU.md) · [Pencil wireframe](reports/ui_ux_20261107/assets/wireframe-hoi-thoai-1024x600.pen)

Continue the design review with the touch flow from recording to sending, then reopen a saved conversation and review the Settings history flow with a long list. Keep search for reopening a conversation, export, retention, and the details of TTS open. The history controls in Pencil are design evidence. Application behavior still needs implementation and acceptance checks.

The 1024 × 600 Pencil wireframe places the microphone control immediately to the left of **Gửi**, including when the keyboard is open. The same control shows recording and recognition states. The error appears just above it. Use sections 1–3 and 5–6 of [the product UI/UX specification](STT_PRODUCT_UI_UX.md) as the reference for the confirmed flow and checks.

In V1, pressing **Gửi** during recording stops capture and waits for final text before sending the combined draft. Pressing it during recognition waits for the same result. Pressing the square by itself leaves the text for review. A recognition failure drops the pending send and keeps the draft. An empty transcript also drops the pending send and keeps the draft, with the microphone returning to its ready state. Switching conversations cancels active capture or recognition and drops any send still waiting for the transcript. Opening the History list keeps the current interaction active. [Send behavior and reference apps](reports/NGHIEN_CUU_GUI_KHI_DANG_THU.md)

PBL6 handles speech recognition, reading text aloud, and Settings. Another project can supply recognized-sign text. Sign recognition and its camera path are separate integration work. **Gửi** and **Đọc to** are separate actions, and the user has deferred the details of TTS. The next chat reviews the design. Software implementation, device tests, benchmarks, and purchases follow a separate user request.

The [audio design notes](reports/NGHIEN_CUU_AM_THANH_TAM_STT.md#thiết-kế-tăng-dần-từ-v1-đến-v3) describe a shared microphone path across three versions. V1 proposes a temporary WAV for recognition after Stop. V2 reuses capture and sends audio during recording. V3 reuses that transport and adds interim text. The user runs the [Pi measurements](STT_PLAN_1_WEEK.md#approved-version-order), using the adjustable recording duration in Settings for the 10, 30 and 60 second cases. Its default is 120 seconds.

[V1 microphone selection is confirmed](STT_PRODUCT_UI_UX.md#chọn-nguồn-mic-trên-pi). With no saved selection, use the Pi OS PipeWire default source. The user can select a microphone in Settings and the choice persists across restarts. Each recording uses the active source without prompting. If the saved microphone is unavailable, temporarily use the available OS default without overwriting the saved selection. Restore the saved microphone when ready for the next recording, keeping any current recording on its existing source. A newer user selection supersedes the earlier one. Settings shows the selected and actual microphones. Reconnection does not start recording. If no microphone is available, report that beside the mic control when the user attempts to record. The actual Pi behavior remains to be tested.

## Hardware evidence to carry forward

The Nguyễn Hiền sales slip dated 2026-11-07 at 17:25 records one NH2067 7-inch 1024 × 600 touchscreen at 1,090,000 VND and one micro-HDMI to HDMI cable at 75,000 VND, for a total of 1,165,000 VND. The user confirmed display output, touch response, and 3.5 mm headphone playback on Pi 4. The tested display setup uses HDMI for video and one USB data cable for both touch and screen power, with the existing 5 V, 3 A adapter powering the Pi. The exact board revision, display resolution in use, tap accuracy, and kiosk behavior still need checking. The Chromium swipe and RealVNC audio trials are deferred. [BOM](STT_BOM.md) · [NH2067 guide](HUONG_DAN_NH2067_PI4.md)

## Current entry point

Inventory and planning exist. The historical experiment suite passed 22 tests. Preserve B01–B04 and their results. ==V1-P1 implements local Settings and a one-file UI/backend/Electron path with offline tests.== Two user-provided browser API trials are recorded. Pi capture, live transport, and OTA remain incomplete. Full V1 remains unfinished.

An attempted project relocation was stopped during source hashing, before copying or source removal. `D:\PBL6_STT` was not created. The temporary migration script is disabled. Keep the active project here. The earlier 48-file backup archive is separate from that cancelled relocation.

Final-device decision confirmed 2026-11-06: ==**touchscreen interaction and kiosk mode are required**==. Keep the laptop for development and initial V1 checks; later verify boot into the full-screen STT interface and normal operation by touch on the selected NH2067.

Validate **HDMI and USB touch first**. Keep the tested NH2067 setup for the first integration. DSI remains an optional later upgrade. If the user revisits DSI, check the exact Pi 4, OS, display, and cable combination and repeat display, touch, on-screen input, and kiosk tests.

==**Approved stack (2026-11-07): React + TypeScript + Tailwind CSS, Next.js/Node.js, and Electron.**== Implement V1 through the shared Node.js backend/UI and Electron desktop, using `STT_SYSTEM_SPEC.md` as the architecture contract. N02 is unfinished research; it does not block V1 Deepgram, but must precede speed comparisons or speed-based selection of local engines.

## Implementation checkpoint — V1-P1, 2026-11-07

**V1-P1 code is in `stt-app`: local Settings, one-file Deepgram adapter, shared UI and Electron window.** Production build and TypeScript checks passed; 20 backend tests and 8 Chrome/HTTP/Electron tests passed on Windows with offline provider fixtures. The user supplied two completed real single-file browser trials (studio_M1.wav and phone_F1.wav, nova-3/vi, exported .txt; a word error is suspected in phone_F1); evidence is recorded in reports/stt_v1_p1_20261107/user_trial_studio_M1.json and user_trial_phone_F1.json. This is user-provided evidence, not an agent API rerun. Pi capture, LAN control and Linux ARM64/touch/kiosk acceptance remain incomplete. Full V1 remains unfinished.

Read `reports/stt_v1_p1_20261107/BAO_CAO.md` and `stt-app/README.md` for evidence and startup commands. The user approved V1 acceptance through the Pi microphone, draft, send, History and error-recovery flow. Use the existing one-file path for integration checks and the experiment runners for batches. When implementation resumes, complete Pi capture and connect it to the agreed composer states. The N02 timing protocol is documented, and comparable Pi results remain pending. [V1 acceptance](STT_PLAN_1_WEEK.md#approved-version-order) · [Historical timing scope](experiments/inventory_20261102/README.md)

The P1 checkpoint is complete on `master`. Find the latest implementation commit with `git log -1 -- stt-app`. Preserve pre-existing edits and experiment results. From `stt-app`, the prepared Windows command is `npm run desktop`. See `reports/stt_v1_p1_20261107/validation.json` for recorded checks and the NH2067 guide for device observations.

## Five people, one sequence

These are work roles, not five people already assigned or running. The user can hand the next role to another person. ==Use one application and one set of contracts.== Do not create independent replacement projects.

| Shift | Owner role and suggested slot | Deliverable and gate to the next shift |
|---|---|---|
| 1 | Engine/data owner; next available session, 4 November | Prepare Node.js file/provider interfaces and backend Settings for V1 Deepgram; retain explicit readiness/capabilities for future local adapters. Keep C0 Whisper-base and C1 Zipformer distinct. Add same-WAV file/list tests and error records. Set aside new development/evaluation recordings before engine selection. Deepgram uses `language=vi`; the user confirms API access is ready. The user enters the key locally when Settings is available. |
| 2 | Live-audio owner; after shift 1, 4 November | ==**First finish V1 Pi recording and Stop.**== Then add V2 realtime sending, bounded queues and finalization. ==Add V3 interim events only after V2 passes.== Test errors and finalization using fixtures before API/Pi execution. A final-only local engine declares its capability. Leave exact Pi launch instructions. |
| 3 | Web/Settings owner; after shift 2, 4–5 November | ==**Build Settings and V1 final text first.**== Use React/TypeScript, Tailwind CSS and Next.js; connect Electron to the shared UI/backend and distinguish Windows from Linux ARM64 build checks. Then connect V2 final-only streaming and V3 interim text in that order. Verify partial replacement, final commit, stale-session rejection, engine toggles, secret redaction and microphone location. Test file input and a file list through the same selected engine interface. |
| 4 | IoT/update owner; after shift 3, 4 November | Send the defined application telemetry to MQTT and show it on a dashboard. Check ThingsBoard setup against the available PC/server. Implement one small application update with verification, health check, rollback and reported version. Keep failed updates explicit. |
| 5 | Integration/evaluation owner; after shift 4, 5 November | Run clean startup, actual Pi capture, cloud/local failures and same-data comparison. Freeze the chosen settings before evaluation. Check Central Vietnamese desktop speech. Test live text and Stop using real audio. Preserve failures/timeouts and distinguish unavailable functions from completed ones. |

**Each shift should reserve its final hour for tests, documentation, a commit and handoff.** If a dependency is blocked, prepare fixture-tested code and write the exact unblock step; ==do not substitute a mock result for a real device/API check.== Account setup can proceed outside these code shifts, but the next shift must not assume it succeeded.

## Required handoff record

Update the following fields before stopping. Keep it short and factual:

```text
Current shift:
Owner / next owner:
Branch and latest commit:
Working-tree edits that must be preserved:
Implemented command and working directory:
Tests run / result:
Real Pi/API checks completed:
Output file or run ID:
Blocked input and exact action to unblock it:
Next command to run:
```

## Actions when implementation or device testing resumes

1. Read the current session handoff for the active task. When the user resumes coding, read the main plan and system specification before starting the first unfinished implementation step.
2. Hand over the existing workspace and the current entry documents. Inspect Git status and preserve pre-existing changes.
3. ==**Enter the Deepgram key locally**== when the prepared Settings/backend is available. Use `language=vi`. No repeat account/credit confirmation is needed.
4. Prepare the Pi Connect/SSH session for the actual device check. ==**The next owner must supply the exact command and expected output from the implemented runner**==; do not use a guessed command for code that does not yet exist.

==No new purchase is required before software work starts.== Use `STT_BOM.md` to compare options before choosing any purchase ceiling.

Dates in the role table are historical suggested slots. Use the checkpoint above for completion status. A replacement deadline is still open.
