import asyncio
import sys
import threading
import uuid
from pathlib import Path
import numpy as np
from .common import read, write, ROOT, SCHEMA, sha
from .replay import predict_segment


def app_for(run, bundle):
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse
    from pydantic import BaseModel
    run = Path(run).resolve()
    metadata = read(run/'run.json')
    if metadata['schema_version'] != SCHEMA:
        raise ValueError('Unsupported run schema')
    initial_run = run
    runs = {run.name: (run, metadata)}
    app = FastAPI()

    def selected(run_id):
        if run_id is None:
            return runs[initial_run.name]
        if run_id not in runs:
            raise HTTPException(404, 'Replay is unavailable in this server session')
        return runs[run_id]

    @app.post('/open-video')
    async def open_video(request: Request, filename: str, run_id: str | None = None):
        _, previous = selected(run_id)
        suffix = Path(filename).suffix.lower()
        if suffix not in {'.mp4', '.mov', '.m4v', '.avi', '.webm', '.mkv'}:
            raise HTTPException(415, 'Choose an MP4, MOV, M4V, AVI, WebM or MKV video.')
        uploads = initial_run.parent / 'videos'
        uploads.mkdir(exist_ok=True)
        path = uploads / (uuid.uuid4().hex + suffix)
        size = 0
        try:
            with path.open('xb') as handle:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > 512 * 1024 * 1024:
                        raise HTTPException(413, 'Choose a video smaller than 512 MB.')
                    handle.write(chunk)
            if not size:
                raise HTTPException(400, 'The selected video is empty.')
            config = path.with_suffix('.json')
            write(config, previous['config'])
            command = [
                sys.executable, '-m', 'deployment.m1', '--bundle', str(Path(bundle).resolve()),
                'replay', str(path), '--output', str(initial_run.parent), '--config', str(config),
            ]
            if previous['model'] is None:
                command.append('--boundaries-only')
            try:
                process = await asyncio.create_subprocess_exec(
                    *command, cwd=ROOT, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()
                if process.returncode:
                    details = stderr.decode(errors='replace').strip().splitlines()
                    raise ValueError(details[-1] if details else 'Replay process failed')
                new_run = Path(stdout.decode().strip().splitlines()[-1])
            finally:
                config.unlink(missing_ok=True)
        except HTTPException:
            path.unlink(missing_ok=True)
            raise
        except Exception as error:
            path.unlink(missing_ok=True)
            raise HTTPException(422, f'Could not open the video: {error}') from error
        runs[new_run.name] = (new_run, read(new_run / 'run.json'))
        return {'run_id': new_run.name}

    lock = threading.Lock()
    class Cut(BaseModel):
        start: float
        end: float
    @app.get('/')
    def index():
        return FileResponse(Path(__file__).with_name('index.html'))
    @app.get('/video')
    def video(run_id: str | None = None):
        run, metadata = selected(run_id)
        if sha(metadata['video']) != metadata['video_sha256']:
            raise HTTPException(409, 'Source video changed')
        return FileResponse(metadata['video'])
    @app.get('/data')
    def data(run_id: str | None = None):
        run, metadata = selected(run_id)
        return dict(run=metadata, frames=read(run/'frames.json'), events=read(run/'events.json'),
                    annotations=[read(p) for p in sorted((run/'annotations').glob('*.json'))])
    @app.get('/tensor/{segment_id}')
    def tensor(segment_id: str, run_id: str | None = None):
        run, metadata = selected(run_id)
        folder = (run/'segments'/segment_id).resolve()
        if folder.parent != run/'segments':
            raise HTTPException(400,'Invalid segment ID')
        if not (folder/'prediction.json').exists():
            raise HTTPException(404,'No prediction artifact')
        prediction = read(folder/'prediction.json')
        if sha(folder/'input.npz') != prediction['input_sha256']:
            raise HTTPException(409,'Input checksum mismatch')
        with np.load(folder/'input.npz',allow_pickle=False) as arrays:
            result = {key:arrays[key].tolist() for key in arrays.files}
        result.update(prediction=prediction, source_frames=read(folder/'source_frames.json'))
        return result
    @app.post('/cuts')
    def manual(cut: Cut, run_id: str | None = None):
        run, metadata = selected(run_id)
        times = [frame['timestamp'] for frame in read(run/'frames.json')]
        if not np.isfinite([cut.start,cut.end]).all() or not 0 <= cut.start < cut.end <= times[-1]:
            raise HTTPException(
                400, f'Use a start before the end and an end at or before the last '
                     f'decoded frame ({times[-1]} s). Click Mark end at the end of '
                     'playback to select that frame.',
            )
        with lock:
            revision = uuid.uuid4().hex
            segment = dict(schema_version=SCHEMA, segment_id='manual-'+revision, revision=revision,
                           start=cut.start,end=cut.end,status='complete')
            try:
                predict_segment(run,segment,bundle,times)
            except Exception as error:
                raise HTTPException(422,str(error)) from error
            (run/'annotations').mkdir(exist_ok=True)
            write(run/'annotations'/f'{revision}.json',segment)
        return segment
    return app
