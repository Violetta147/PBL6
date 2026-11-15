"""Preview a Windows webcam and record one short clip when the user presses R."""
import argparse
from datetime import datetime
from pathlib import Path
import time

import cv2

ROOT = Path(__file__).resolve().parents[1]
WINDOW = "PBL6 webcam - R: record, Q: quit"


def open_webcam(index):
    camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError(f"Cannot open webcam {index}.")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)
    return camera


def open_clip_writer(path, frame, fps):
    if not 1 <= fps <= 120:
        fps = 30.0
    height, width = frame.shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height))
    if not writer.isOpened():
        writer.release()
        raise RuntimeError("Cannot create the AVI file.")
    return writer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()
    camera = open_webcam(args.camera)
    writer = None
    try:
        phase = "preview"
        count = 0
        while True:
            ok, frame = camera.read()
            if not ok or frame is None:
                raise RuntimeError("Webcam stopped returning frames.")
            now = time.monotonic()
            if phase == "countdown" and now >= begin:
                phase = "recording"
                started = now
                path = ROOT / "local_data" / ("webcam_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".avi")
                path.parent.mkdir(exist_ok=True)
                writer = open_clip_writer(path, frame, camera.get(cv2.CAP_PROP_FPS))
            if phase == "recording":
                if count >= 150 or now - started >= 4:
                    writer.release()
                    writer = None
                    print(f"Saved {count} frames in {now - started:.2f}s: {path}")
                    return
                writer.write(frame)
                count += 1
            preview = frame.copy()
            message = "Keep shoulders and hands visible. R to start."
            if phase == "countdown":
                message = f"Get ready: {max(1, int(begin - now + 0.999))}"
            elif phase == "recording":
                message = f"RECORDING  {count} frames"
            cv2.putText(preview, message, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.63, (0, 240, 255), 2)
            cv2.imshow(WINDOW, preview)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                if writer is not None:
                    writer.release()
                    writer = None
                    print(f"Recording stopped early. Partial clip: {path}")
                return
            if key in (ord("r"), ord("R")) and phase == "preview":
                begin = time.monotonic() + 3
                phase = "countdown"
    finally:
        if writer is not None:
            writer.release()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
