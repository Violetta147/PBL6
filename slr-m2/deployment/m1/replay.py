import subprocess
import sys
import time
import uuid
from pathlib import Path
from dataclasses import asdict
import numpy as np
from .common import ROOT, SCHEMA, sha, write, check_bundle
from .segmenter import Config, Segmenter, arm_states


def cut(video, times, start, end, destination):
    import cv2
    capture = cv2.VideoCapture(str(video))
    fps = capture.get(cv2.CAP_PROP_FPS)
    size = (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    writer = cv2.VideoWriter(str(destination), cv2.VideoWriter_fourcc(*'FFV1'), fps, size)
    if not writer.isOpened():
        capture.release()
        raise ValueError('Cannot open lossless segment writer')
    mapping = []
    try:
        for index,timestamp in enumerate(times):
            ok, frame = capture.read()
            if not ok:
                raise ValueError('Video decoding ended before expected frame')
            if start <= timestamp <= end:
                writer.write(frame)
                mapping.append(index)
    finally:
        capture.release()
        writer.release()
    if not mapping:
        raise ValueError('Cut contains no frames')
    return mapping


def predict_segment(run, segment, bundle, times):
    folder = run/'segments'/segment['segment_id']
    folder.mkdir(parents=True, exist_ok=False)
    metadata = __import__('json').loads((run/'run.json').read_text())
    mapping = cut(metadata['video'], times, segment['start'], segment['end'], folder/'clip.avi')
    write(folder/'source_frames.json', mapping)
    subprocess.run([sys.executable, '-m', 'deployment.m1.inference', str(bundle),
                    str(folder/'clip.avi'), str(folder)], cwd=ROOT, check=True)
    segment['artifact'] = str(folder.relative_to(run))


def replay(video, bundle, output, config=None, boundaries_only=False):
    import cv2
    import mediapipe as mp
    config = config or Config()
    identity = None if boundaries_only else check_bundle(bundle)
    if identity:
        identity.pop('labels')
    video = Path(video).resolve()
    run = Path(output)/uuid.uuid4().hex
    run.mkdir(parents=True)
    metadata = dict(schema_version=SCHEMA, session_id='replay-'+run.name, epoch=0,
                    video=str(video), video_sha256=sha(video), config=asdict(config),
                    model=identity, status='processing', mode='fresh_extraction')
    write(run/'run.json', metadata)
    detector = Segmenter(config)
    events, frames, times = [], [], []
    capture = cv2.VideoCapture(str(video))
    started = time.perf_counter()
    try:
        if not capture.isOpened():
            raise ValueError('Cannot open video')
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not np.isfinite(fps) or fps <= 0:
            raise ValueError('Video has no valid FPS')
        with mp.solutions.pose.Pose(model_complexity=1, smooth_landmarks=False) as pose_model:
            while True:
                ok, image = capture.read()
                if not ok:
                    break
                index = len(times)
                timestamp = capture.get(cv2.CAP_PROP_POS_MSEC)/1000
                if not np.isfinite(timestamp) or (times and timestamp <= times[-1]):
                    raise ValueError('Decoder timestamps are invalid; convert recording to constant frame rate')
                result = pose_model.process(cv2.cvtColor(image,cv2.COLOR_BGR2RGB))
                pose = [[float('nan')]*3 for _ in range(8)]
                visibility = [0.]*8
                if result.pose_landmarks:
                    landmarks = result.pose_landmarks.landmark
                    for slot,joint in enumerate((11,12,13,14,15,16,23,24)):
                        point = landmarks[joint]
                        pose[slot] = [point.x,point.y,point.z]
                        visibility[slot] = point.visibility
                arms = arm_states(pose,visibility,config)
                events.extend(detector.feed(timestamp,arms))
                times.append(timestamp)
                frames.append(dict(frame_id=index,timestamp=timestamp,state=detector.state,arms=arms,
                                   pose=[[v if np.isfinite(v) else None for v in p] for p in pose],visibility=visibility))
        if not times:
            raise ValueError('No decoded frames')
        events.extend(detector.finish())
        metadata['extraction_seconds'] = time.perf_counter()-started
        write(run/'frames.json', frames)
        write(run/'events.json', events)
        for segment in events:
            if segment.get('status') == 'complete' and not boundaries_only:
                predict_segment(run, segment, bundle, times)
        write(run/'events.json', events)
        metadata['status'] = 'complete'
    except Exception as error:
        metadata.update(status='failed', error=str(error))
        raise
    finally:
        capture.release()
        write(run/'run.json', metadata)
    return run
