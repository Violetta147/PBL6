# Sequential STT work until Thursday

Updated: 2026-11-04. Deadline: Thursday, 2026-11-05. Keep this Git repository and active STT data in the current C-drive workspace. Read `AGENTS.md`, `STT_PLAN_1_WEEK.md` and `STT_SYSTEM_SPEC.md` first.

## Current entry point

Inventory and planning exist. The historical experiment suite passed 22 tests. B01–B04 results remain unchanged. ==The new application, Settings, live transport and OTA path are not implemented by these documents.== ==**Start shift 1 below**==; do not report them as finished.

An attempted project relocation was stopped during source hashing, before copying or source removal. `D:\PBL6_STT` was not created. The temporary migration script is disabled. Keep the active project here. The earlier 48-file backup archive is separate from that cancelled relocation.

Final-device decision confirmed 2026-11-06: ==**touchscreen interaction and kiosk mode are required**==. Keep the laptop for development and initial V1 checks; later verify boot into the full-screen STT interface and normal operation by touch on the actual device. Screen hardware is not selected yet.

## Five people, one sequence

These are work roles, not five people already assigned or running. The user can hand the next role to another person. ==Use one application and one set of contracts.== Do not create independent replacement projects.

| Shift | Owner role and suggested slot | Deliverable and gate to the next shift |
|---|---|---|
| 1 | Engine/data owner; next available session, 4 November | Prepare local/file interfaces and provider configuration. Keep C0 Whisper-base and C1 Zipformer distinct. Add same-WAV file/list tests and error records. Set aside new development/evaluation recordings before engine selection. Deepgram uses `language=vi`; the user confirms API access is ready. The user enters the key locally when Settings is available. |
| 2 | Live-audio owner; after shift 1, 4 November | ==**First finish V1 Pi recording and Stop.**== Then add V2 realtime sending, bounded queues and finalization. ==Add V3 interim events only after V2 passes.== Test errors and finalization using fixtures before API/Pi execution. A final-only local engine declares its capability. Leave exact Pi launch instructions. |
| 3 | Web/Settings owner; after shift 2, 4–5 November | ==**Build Settings and V1 final text first.**== Then connect V2 final-only streaming and V3 interim text in that order. Verify partial replacement, final commit, stale-session rejection, engine toggles, secret redaction and microphone location. Test file input and a file list through the same selected engine interface. |
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
4. For Google, check Free Trial eligibility and whether the required payment-method verification is acceptable. Creating a project alone is not the full API setup. If setup is unavailable, record the block and continue the other engines.
4. Prepare the Pi Connect/SSH session for the actual device check. ==**The next owner must supply the exact command and expected output from the implemented runner**==; do not use a guessed command for code that does not yet exist.

==No new purchase is required before software work starts.== Use `STT_BOM.md` to compare options before choosing any purchase ceiling.

The current date is 4 November. The five roles are sequential handoffs, not proof that earlier dated work was completed. Preserve the Thursday deadline; record any unfinished stage honestly.
