"""Serve the PBL6 sign recognition demo on localhost."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import urllib.parse
import webbrowser

import cv2

from check_clip import ClipRecognizer, ROOT, save_report
from record_webcam import open_clip_writer, open_webcam


AUDIO = ROOT / "local_data" / "tts"


def audio_path(index):
    return AUDIO / f"{index}.mp3"


def open_webcam_safe(index):
    try:
        return open_webcam(index)
    except Exception as err:
        fallback = 0 if index != 0 else 1
        try:
            cam = open_webcam(fallback)
            print(f"Webcam {index} không khả dụng, đã chuyển sang webcam {fallback}.", flush=True)
            return cam
        except Exception:
            raise err


class Demo:
    def __init__(self, camera_index, sample):
        self.camera_index = camera_index
        self.sample = sample
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.camera_ready = False
        self.state = {"phase": "loading", "sample": sample is not None}
        self.jpeg = None
        self.deadline = 0.0
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.model = self.executor.submit(ClipRecognizer)
        self.thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.thread.start()

    def update(self, phase, **details):
        with self.lock:
            self.state = {"phase": phase, "sample": self.sample is not None, **details}

    def start(self):
        with self.lock:
            if self.state["phase"] not in ("ready", "result", "retry"):
                return False
            if not self.camera_ready:
                return False
            self.deadline = time.monotonic() + 3
            self.state = {"phase": "countdown", "sample": self.sample is not None}
            return True

    def snapshot(self):
        with self.lock:
            state = self.state.copy()
            if state["phase"] == "countdown":
                state["remaining"] = max(1, int(self.deadline - time.monotonic() + 0.999))
            elif state["phase"] == "recording":
                state["remaining"] = max(0.0, round(self.deadline - time.monotonic(), 1))
            return state

    def infer(self, path, count):
        report = self.model.result().recognize(path, expected_frames=count)
        destination = save_report(report, "desktop_demo")
        print(f"Report: {destination}", flush=True)
        return report

    def capture_loop(self):
        camera = writer = sample_cap = pending = None
        path = None
        count = 0
        last_preview = 0.0
        fps = 30.0
        try:
            if self.sample is None:
                camera = open_webcam_safe(self.camera_index)
                fps = camera.get(cv2.CAP_PROP_FPS)
                if not 1 <= fps <= 120:
                    fps = 30.0
            else:
                initial_cap = cv2.VideoCapture(str(self.sample))
                clip_fps = initial_cap.get(cv2.CAP_PROP_FPS)
                fps = clip_fps if 1 <= clip_fps <= 120 else 25.0
                try:
                    ok, frame = initial_cap.read()
                    if not ok or frame is None:
                        raise RuntimeError("Không đọc được video đối chứng.")
                    self.publish_frame(frame)
                finally:
                    initial_cap.release()
                self.camera_ready = True

            while not self.stop.is_set():
                if camera is not None:
                    ok, frame = camera.read()
                    if not ok or frame is None:
                        raise RuntimeError("Mất hình từ webcam. Kiểm tra cáp USB rồi mở lại ứng dụng.")
                    self.camera_ready = True
                else:
                    self.stop.wait(0.03)
                now = time.monotonic()
                phase = self.snapshot()["phase"]
                if camera is not None and now - last_preview >= 0.10:
                    self.publish_frame(frame)
                    last_preview = now

                if phase == "loading" and self.model.done():
                    self.model.result()
                    self.update("ready")
                elif phase == "countdown" and now >= self.deadline:
                    self.deadline = now + 4.0
                    if self.sample is not None:
                        sample_cap = cv2.VideoCapture(str(self.sample))
                        self.update("recording")
                    else:
                        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        path = ROOT / "local_data" / f"webcam_{stamp}.avi"
                        path.parent.mkdir(exist_ok=True)
                        writer = open_clip_writer(path, frame, fps)
                        count = 0
                        self.update("recording")
                elif phase == "recording":
                    if self.sample is not None:
                        if sample_cap is not None and now < self.deadline:
                            ok_s, s_frame = sample_cap.read()
                            if ok_s and s_frame is not None:
                                self.publish_frame(s_frame)
                                time.sleep(1.0 / fps)
                            else:
                                sample_cap.release()
                                sample_cap = None
                                self.update("processing")
                                pending = self.executor.submit(self.infer, self.sample, None)
                        else:
                            if sample_cap is not None:
                                sample_cap.release()
                                sample_cap = None
                            self.update("processing")
                            pending = self.executor.submit(self.infer, self.sample, None)
                    else:
                        if now < self.deadline and count < 150:
                            writer.write(frame)
                            count += 1
                        else:
                            writer.release()
                            writer = None
                            self.update("processing")
                            pending = self.executor.submit(self.infer, path, count)
                elif phase == "processing" and pending.done():
                    try:
                        report = pending.result()
                    except Exception as exc:
                        print(f"Recognition failed: {exc}", flush=True)
                        self.update("retry", message="Không xử lý được lượt này. Hãy quay lại, giữ vai và hai tay trong khung.")
                    else:
                        top5 = report.get("top5", [])
                        prediction = top5[0] if top5 else {"gloss": "—", "index": None}
                        index = prediction.get("index")
                        sec = report.get("seconds", {})
                        timing = {
                            "pipeline": round(sec.get("clip_total", 0.0), 2),
                            "extraction": round(sec.get("extraction", 0.0), 2),
                            "adapter": round(sec.get("adapter", 0.0), 2),
                            "forward_first": round(sec.get("forward_first", 0.0), 2),
                        }
                        self.update(
                            "result",
                            gloss=prediction.get("gloss", "—"),
                            index=index,
                            top5=top5,
                            has_audio=audio_path(index).is_file() if index is not None else False,
                            seconds=timing["pipeline"],
                            pipeline=timing["pipeline"],
                            extraction=timing["extraction"],
                            adapter=timing["adapter"],
                            forward_first=timing["forward_first"],
                            timing=timing,
                        )
                    pending = None
        except Exception as exc:
            print(f"Demo failed: {exc}", flush=True)
            self.update("error", message="Không khởi động được camera hoặc mô hình. Xem chi tiết trong PowerShell.")
        finally:
            self.camera_ready = False
            if sample_cap is not None:
                sample_cap.release()
            if writer is not None:
                writer.release()
            if camera is not None:
                camera.release()

    def publish_frame(self, frame):
        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            with self.lock:
                self.jpeg = buffer.tobytes()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)
        self.executor.shutdown(cancel_futures=True)


def make_handler(demo, page, host):
    port = host.split(":")[-1]
    allowed_hosts = {host, f"127.0.0.1:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://{h}" for h in allowed_hosts}

    class Handler(BaseHTTPRequestHandler):
        def send_data(self, data, content_type, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            req_host = self.headers.get("Host")
            if req_host not in allowed_hosts:
                self.send_error(403)
            elif self.path == "/":
                self.send_data(page, "text/html; charset=utf-8")
            elif self.path == "/state":
                self.send_data(json.dumps(demo.snapshot()).encode(), "application/json")
            elif self.path == "/speak" or self.path.startswith("/speak?"):
                state = demo.snapshot()
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                index = None
                if "index" in params:
                    try:
                        index = int(params["index"][0])
                    except ValueError:
                        pass
                if index is None:
                    index = state.get("index")
                if index is not None and audio_path(index).is_file():
                    try:
                        data = audio_path(index).read_bytes()
                    except OSError:
                        self.send_error(404)
                    else:
                        self.send_data(data, "audio/mpeg")
                else:
                    self.send_data(
                        json.dumps({
                            "status": "tts_fallback",
                            "index": index,
                            "gloss": params.get("text", [state.get("gloss", "")])[0],
                        }).encode(),
                        "application/json",
                    )
            elif self.path.startswith("/audio/"):
                try:
                    raw_id = self.path.split("/audio/")[1].split(".mp3")[0]
                    req_index = int(raw_id)
                except (IndexError, ValueError):
                    self.send_error(404)
                    return
                p = audio_path(req_index)
                if not p.is_file():
                    self.send_error(404)
                    return
                try:
                    data = p.read_bytes()
                except OSError:
                    self.send_error(404)
                else:
                    self.send_data(data, "audio/mpeg")
            elif self.path == "/preview" or self.path.startswith("/preview?"):
                with demo.lock:
                    jpeg = demo.jpeg
                if jpeg:
                    self.send_data(jpeg, "image/jpeg")
                else:
                    self.send_response(204)
                    self.end_headers()
            else:
                self.send_error(404)

        def do_POST(self):
            req_host = self.headers.get("Host")
            req_origin = self.headers.get("Origin")
            if (req_host not in allowed_hosts
                    or (req_origin and req_origin not in allowed_origins)
                    or self.headers.get("X-PBL6") != "demo"):
                self.send_error(403)
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length) if length > 0 else b""
            payload = {}
            if body:
                try:
                    payload = json.loads(body.decode("utf-8"))
                except Exception:
                    pass

            if self.path == "/start":
                status = 200 if demo.start() else 409
                self.send_data(json.dumps(demo.snapshot()).encode(), "application/json", status)
            elif self.path == "/speak":
                state = demo.snapshot()
                index = payload.get("index")
                if index is None:
                    index = state.get("index")
                gloss = payload.get("gloss")
                if not gloss:
                    gloss = state.get("gloss", "")
                has_audio = index is not None and audio_path(index).is_file()
                res = {
                    "status": "ok",
                    "index": index,
                    "gloss": gloss,
                    "has_audio": has_audio,
                    "audio_url": f"/audio/{index}.mp3" if has_audio else None,
                }
                self.send_data(json.dumps(res).encode(), "application/json")
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--clip", type=Path, help="Exercise the demo with an existing clip")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    page = Path(__file__).with_name("demo.html").read_bytes()
    host = f"127.0.0.1:{args.port}"
    with ThreadingHTTPServer(("127.0.0.1", args.port), BaseHTTPRequestHandler) as server:
        demo = Demo(args.camera, args.clip)
        server.RequestHandlerClass = make_handler(demo, page, host)
        try:
            print(f"PBL6: http://{host} (Ctrl+C to stop)", flush=True)
            if not args.no_browser:
                webbrowser.open(f"http://{host}")
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            demo.close()


if __name__ == "__main__":
    main()

