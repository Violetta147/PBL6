# M1 local 07b inspector

Run these blocks in the same Terminal tab with `deployment/` as your working directory. Setup uses `deployment/.venv-m1` and creates it with Python 3.11 if needed. Adding the project root to Python’s import path lets you run `deployment.m1` while staying in `deployment/`.

```sh
cd "/Users/vohoangminh/PBL6/PBL6_Revamped/deployment" &&
  m1_root="$(cd .. && pwd -P)" &&
  export PYTHONPATH="$m1_root${PYTHONPATH:+:$PYTHONPATH}" &&
  m1_python="$PWD/.venv-m1/bin/python" &&
  { [ -x "$m1_python" ] || python3.11 -m venv .venv-m1; } &&
  "$m1_python" -m pip install -r m1/requirements.txt
```

To check the model bundle after setup:

```sh
"$m1_python" -m deployment.m1 preflight
```

Change `Config.rest` in [segmenter.py](segmenter.py#L9) to adjust the default rest confirmation in seconds. It applies both at the start of a replay and after a movement. Existing replays retain their saved settings.

## Try replay with a local dataset clip

This command works before you download the model. It saves the generated run directory in the shell variable used by the browser command.

```sh
m1_video="$m1_root/dataset/raw/vsl400_input/Part_1/front_view/003082.mp4"
m1_demo_config="$(mktemp)"
printf '%s\n' '{"rest": 0.30}' > "$m1_demo_config"
m1_run="$("$m1_python" -m deployment.m1 replay "$m1_video" --boundaries-only --config "$m1_demo_config")" &&
  open "http://127.0.0.1:8765" &&
  "$m1_python" -m deployment.m1 serve "$m1_run"
```

If the browser opens before the server starts, reload the page. Press **Ctrl+C** in Terminal when you finish reviewing. This sample uses a 0.30-second rest threshold because its trailing rest is shorter than the default 0.35 seconds. Click the start and end markers in the Boundary timeline to jump to those frames.

## Run with the trained model and your recording

Download the run from Google Drive at `MyDrive/PBL6_Cloud/training/architecture_comparison/sl_gcn_bone_07b/07b_bone_seed42`. Copy its contents into the directory opened by this command. Include `best.pt`, `best.pt.sha256`, `config.json`, `label_map.json`, and the complete `code/` snapshot. Use artifacts from your trusted training run.

```sh
m1_bundle="$m1_root/models/checkpoints/sl_gcn_bone_07b/07b_bone_seed42"
mkdir -p "$m1_bundle" && open "$m1_bundle"
```

After copying the bundle, run the following block and select your recording in the Mac file picker. It starts the review server only if preflight and replay succeed.

```sh
"$m1_python" -m deployment.m1 preflight &&
  m1_video="$(osascript -e 'POSIX path of (choose file with prompt "Choose an M1 recording")')" &&
  m1_run="$("$m1_python" -m deployment.m1 replay "$m1_video")" &&
  open "http://127.0.0.1:8765" &&
  "$m1_python" -m deployment.m1 serve "$m1_run"
```

In the browser, mark the start and end of each reference movement and click **Classify manual cut**. Select automatic and manual segments to compare model positions and predictions. Each position shows the source frame, real mask, time input, and eight feature channels.

Replay requires usable decoder timestamps. Segment intermediates use lossless FFV1 AVI. The original timestamps remain in `frames.json`, while segment extraction uses the intermediary's constant frame rate. Variable frame rate inference timing parity remains to be validated.

Use **Open video** in the browser to select another recording during the same server session. It creates a separate replay with the current run’s settings and mode. The previous URL still opens the previous recording. Browser-selected videos and their runs are saved locally under `../outputs/m1/` with the standard setup.

## Evaluate the reviewed recording

After saving the manual cuts, press **Ctrl+C** in Terminal. Run this block in the same tab. It lists the saved revisions and prompts you to select one per reference movement.

```sh
"$m1_python" - "$m1_run" <<'PYTHON'
import json
import sys
from pathlib import Path

from deployment.m1.evaluation import evaluate

run = Path(sys.argv[1])
cuts = sorted((run / "annotations").glob("*.json"))
if not cuts:
    raise SystemExit("This run has no manual cuts. Save cuts in the browser first.")

for number, path in enumerate(cuts, start=1):
    cut = json.loads(path.read_text())
    print(f"{number}. {cut['start']:.3f} to {cut['end']:.3f} s ({path.stem})")

with open("/dev/tty") as terminal:
    print("Enter cut numbers separated by spaces: ", end="", flush=True)
    try:
        numbers = [int(value) for value in terminal.readline().split()]
        if not numbers or any(number < 1 or number > len(cuts) for number in numbers):
            raise ValueError("Choose at least one number from the list.")
        evaluate(run, [cuts[number - 1].stem for number in numbers])
    except ValueError as error:
        raise SystemExit(str(error))

print(run / "evaluation.json")
PYTHON
```

Run the state-machine tests from `deployment/`.

```sh
"$m1_python" -m unittest deployment.m1.test_segmenter
```

The report includes coverage, boundary offsets, misses, splits, merges, and unmatched automatic segments. Review unmatched segments before interpreting them as idle triggers.

## Recording checklist

Record two takes of each scenario, 20–40 seconds each. Reserve the second take for evaluation. Include arms-down-separated movements, repeated movements, one/two-arm activity, held raised hands, idle/repositioning, and occlusion/unfinished movement. Keep the torso and wrists visible. Begin/end ordinary recordings with three seconds of rest. Store originals under `../dataset/raw/m1_recordings`.

## Verification status and remaining work

The state-machine unit tests run without model dependencies. Checkpoint inference, frozen-loader parity, dependency installation, and browser behavior require verification. The 07b bundle and personal recordings were absent during implementation.

This initial implementation still needs the 20-clip validation selection/decoding manifest, comprehensive adapter parity tests, normalized-skeleton/bone visualizations, prediction agreement and idle-duration metrics, a full timing breakdown, and the reserved-recording evaluation. The preprocessing policy uses repository v3 defaults with association ambiguity margin 0.001 and pair guard enabled. Validate this against the downloaded run's cache provenance before accepting model results.
