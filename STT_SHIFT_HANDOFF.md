# Sequential STT work until Thursday

Updated: 2026-11-07. Original target: Thursday, 2026-11-05 (past); no replacement deadline has been agreed. Keep this Git repository and active STT data in the current C-drive workspace. Read `AGENTS.md`, `STT_PLAN_1_WEEK.md` and `STT_SYSTEM_SPEC.md` first.

## Next session: BOM decisions and shopping plan — 2026-11-07

**The Nguyễn Hiền sales slip dated 2026-11-07 at 17:25 records one NH2067 7-inch 1024 × 600 touchscreen at 1,090,000 VND and one micro-HDMI to HDMI cable at 75,000 VND.** The merchandise total was 1,165,000 VND. Use `STT_BOM.md` for the USB touch, power, and accessory checks. Follow the user's direction before starting P2 or running benchmarks.

Use `START_NEXT_CHAT_STT.md` for the concise P1 handoff and reading order. P1 code is complete at the single-file checkpoint with two user browser trials and the Windows desktop visibility fix. Full V1 remains unfinished. On 2026-11-07, the user reported a working NH2067 connection and responsive touch on Pi 4. Touch felt different from a phone. The active display resolution, tap accuracy, and kiosk behavior still need checking.

## UI/UX discussion to carry forward — 2026-11-07

Read [STT_PRODUCT_UI_UX.md](STT_PRODUCT_UI_UX.md): the final product must support two-person multimodal communication. Discuss the conversation layout, sign/voice/text paths, TTS, Settings and a new palette. The supplied image is a layout reference; its palette is rejected. Coordinate screen viewing/touch needs with BOM choices. No UI redesign or sign/TTS implementation is assigned by this documentation update; retain the STT version gates.

## Current entry point

Inventory and planning exist. The historical experiment suite passed 22 tests. B01–B04 results remain unchanged. ==V1-P1 now implements local Settings and a one-file UI/backend/Electron path with offline tests; two user-provided browser API trials have completed, while Pi acceptance, batch, live transport and OTA remain incomplete.== ==**P1 checkpoint is implemented; the next session focuses on BOM decisions and shopping planning.**== Full V1 remains unfinished.

An attempted project relocation was stopped during source hashing, before copying or source removal. `D:\PBL6_STT` was not created. The temporary migration script is disabled. Keep the active project here. The earlier 48-file backup archive is separate from that cancelled relocation.

Final-device decision confirmed 2026-11-06: ==**touchscreen interaction and kiosk mode are required**==. Keep the laptop for development and initial V1 checks; later verify boot into the full-screen STT interface and normal operation by touch on the selected NH2067.

Display sequence: **validate HDMI + USB touch first; DSI is a later optional upgrade**. Keep the successful HDMI configuration and actual test record. Check the candidate DSI screen against Pi 4 and the installed OS, then retest touch, orientation, on-screen entry, boot/kiosk and a real STT session. DSI procurement and switching must not block initial V1 work. The first screen integration requires an HDMI touchscreen, Pi 4 micro-HDMI video cable, USB touch data cable and model-specific power; use the HDMI + USB hardware section in `STT_BOM.md`.

==**Approved stack (2026-11-07): React + TypeScript + Tailwind CSS, Next.js/Node.js, and Electron.**== Implement V1 through the shared Node.js backend/UI and Electron desktop, using `STT_SYSTEM_SPEC.md` as the architecture contract. N02 is unfinished research; it does not block V1 Deepgram, but must precede speed comparisons or speed-based selection of local engines.

## Implementation checkpoint — V1-P1, 2026-11-07

**V1-P1 code is in `stt-app`: local Settings, one-file Deepgram adapter, shared UI and Electron window.** Production build and TypeScript checks passed; 20 backend tests and 8 Chrome/HTTP/Electron tests passed on Windows with offline provider fixtures. The user supplied two completed real single-file browser trials (studio_M1.wav and phone_F1.wav, nova-3/vi, exported .txt; a word error is suspected in phone_F1); evidence is recorded in reports/stt_v1_p1_20261107/user_trial_studio_M1.json and user_trial_phone_F1.json. This is user-provided evidence, not an agent API rerun. Pi capture, batch, LAN control and Linux ARM64/touch/kiosk acceptance remain incomplete. Full V1 remains unfinished.

Read `reports/stt_v1_p1_20261107/BAO_CAO.md` and `stt-app/README.md` for evidence and startup/trial commands. The user has returned the initial single-file result. The immediate next-session priority is BOM decisions and shopping planning; batch then Pi capture remain the proposed software sequence when the user resumes implementation. N02 remains unfinished; preserve B01–B04 and the timing-scope caveat.

Current handoff: shift 1, V1-P1 checkpoint complete; full V1 pending; branch `master`. Find the implementation commit with `git log -1 -- stt-app`. Preserve all pre-existing document edits and experiment results. From `stt-app`, the prepared Windows command is `npm run desktop` (dependencies and build already present on this machine). Tests: 20 backend and 8 UI/HTTP/Electron passed; production build and TypeScript passed. P1 real checks: two user-provided browser file/API trials and a suspected word error in phone_F1. Evidence: `reports/stt_v1_p1_20261107/validation.json`. The initial Pi display and touch check is recorded separately in `STT_BOM.md`. Next hardware step: characterize touch behavior on the selected display.

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

## Immediate user actions

1. Read the main plan, then the system specification. Begin the first unfinished shift; no old questionnaire reconstruction is required.
2. For the next person, give this workspace path and these three entry documents. They must inspect current Git status rather than reset the working tree.
3. ==**Enter the Deepgram key locally**== when the prepared Settings/backend is available. Use `language=vi`. No repeat account/credit confirmation is needed.
4. Prepare the Pi Connect/SSH session for the actual device check. ==**The next owner must supply the exact command and expected output from the implemented runner**==; do not use a guessed command for code that does not yet exist.

==No new purchase is required before software work starts.== Use `STT_BOM.md` to compare options before choosing any purchase ceiling.

The update date is 7 November. Dates in the role table are historical suggested slots, not a new schedule or proof of completion. Record unfinished stages honestly; no replacement deadline has been agreed.
