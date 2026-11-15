"""End-to-end integration test for SLR Kiosk demo server and API."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
DEMO_PY = ROOT / "desktop_mvp" / "demo.py"
SAMPLE_CLIP = ROOT / "local_data" / "014159.mp4"

def find_python():
    candidates = [
        sys.executable,
        r"C:\Users\LAPTOP T&T\miniconda3\envs\pbl6_slr\python.exe",
        str(Path(sys.executable).parents[1] / "envs" / "pbl6_slr" / "python.exe"),
    ]
    for c in candidates:
        if Path(c).is_file():
            try:
                out = subprocess.run([c, "-c", "import mediapipe; _ = mediapipe.solutions"], capture_output=True, timeout=5)
                if out.returncode == 0:
                    return c
            except Exception:
                pass
    return sys.executable

PYTHON = find_python()

def test_demo_server():
    port = 8791
    host = f"127.0.0.1:{port}"
    print(f"Launching demo server on {host} with clip {SAMPLE_CLIP}...")
    proc = subprocess.Popen(
        [PYTHON, str(DEMO_PY), "--clip", str(SAMPLE_CLIP), "--port", str(port), "--no-browser"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # 1. Wait for server to bind and respond to /
        server_ready = False
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://{host}/", timeout=1) as resp:
                    if resp.status == 200:
                        content = resp.read().decode("utf-8")
                        assert "Nhận dạng ký hiệu tiếng Việt" in content
                        assert "Kiosk 1024×600" in content
                        assert "timing-table" in content
                        assert "pipeline" in content
                        assert "mediapipe extraction" in content
                        assert "tiền xử lý" in content
                        assert "SL-GCL forward first inference" in content
                        assert "btn-confirm" in content
                        assert "btn-retry" in content
                        assert "transform: scaleX(-1)" in content
                        assert "posture-guide" in content
                        assert "isLiveCameraPhase" in content
                        assert '<img id="preview" alt="Khung hình camera" hidden>' in content
                        assert "preview.removeAttribute" in content
                        assert 'btnStart.click()' in content
                        assert 'currentState.phase === "retry"' in content
                        print("[PASS] GET / returns valid Kiosk HTML with Mode B timing table, UI mirroring, posture guide, and retry action bindings.")
                        server_ready = True
                        break
            except Exception:
                time.sleep(0.5)

        if not server_ready:
            raise RuntimeError("Demo server failed to start within timeout.")

        # 1b. Verify /preview endpoints (with and without query string)
        for preview_url in (f"http://{host}/preview", f"http://{host}/preview?t={int(time.time()*1000)}"):
            preview_ok = False
            for _ in range(25):
                try:
                    with urllib.request.urlopen(preview_url, timeout=2) as resp:
                        if resp.status == 200:
                            assert resp.headers.get("Content-Type") == "image/jpeg"
                            img_data = resp.read()
                            assert len(img_data) > 100, f"Preview image too small: {len(img_data)}"
                            assert img_data.startswith(b"\xff\xd8"), "Invalid JPEG header in preview stream"
                            preview_ok = True
                            break
                        elif resp.status == 204:
                            time.sleep(0.2)
                except Exception:
                    time.sleep(0.2)
            assert preview_ok, f"{preview_url} did not yield a valid JPEG frame within timeout"
        print("[PASS] GET /preview and GET /preview?t=... return valid JPEG camera frames.")

        # 2. Check /state in ready phase
        ready = False
        for _ in range(60):
            with urllib.request.urlopen(f"http://{host}/state", timeout=2) as resp:
                data = json.loads(resp.read().decode())
                print(f"State: {data.get('phase')}")
                if data.get("phase") == "ready":
                    ready = True
                    break
            time.sleep(1)

        assert ready, "Server did not enter ready phase"
        print("[PASS] /state transitioned to 'ready'.")

        # 3. Post /start to begin recognition
        req = urllib.request.Request(
            f"http://{host}/start",
            data=b"",
            headers={"Origin": f"http://{host}", "X-PBL6": "demo", "Host": host},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            print(f"Started response: phase={data.get('phase')}")
            assert data.get("phase") == "countdown"
        print("[PASS] POST /start successfully entered 'countdown'.")

        # 4. Wait for result phase
        result_state = None
        for _ in range(90):
            with urllib.request.urlopen(f"http://{host}/state", timeout=2) as resp:
                data = json.loads(resp.read().decode())
                phase = data.get("phase")
                print(f"Phase: {phase}, Remaining: {data.get('remaining')}")
                if phase == "result":
                    result_state = data
                    break
                elif phase == "error":
                    raise RuntimeError(f"Server entered error state: {data.get('message')}")
            time.sleep(1)

        assert result_state is not None, "Did not reach result phase within timeout"
        print(f"[PASS] /state reached 'result': gloss={result_state.get('gloss')}, index={result_state.get('index')}")

        # 5. Verify timing breakdown metrics
        assert "timing" in result_state, "timing key missing from result state"
        timing = result_state["timing"]
        print(f"Timing breakdown: {timing}")
        for k in ("pipeline", "extraction", "adapter", "forward_first"):
            assert k in timing, f"Missing {k} in timing breakdown"
            assert isinstance(timing[k], (int, float)), f"{k} is not a numeric value: {timing[k]}"
            assert timing[k] >= 0, f"{k} is negative: {timing[k]}"

        # Verify top-level convenience metrics
        assert "pipeline" in result_state
        assert "extraction" in result_state
        assert "adapter" in result_state
        assert "forward_first" in result_state
        print("[PASS] All 4 timing breakdown metrics verified!")

        # 6. Verify top5 candidate list
        top5 = result_state.get("top5", [])
        assert len(top5) > 0, "No top5 candidates returned"
        assert top5[0]["gloss"] == "Dài", f"Expected Top-1 'Dài', got {top5[0]['gloss']}"
        print(f"[PASS] Top candidates: {[c['gloss'] for c in top5[:3]]}")

        # 7. Verify /audio/<index>.mp3 for Top-1, Top-2, Top-3, and parenthetical labels
        idx = result_state.get("index")
        audio_checks = [
            (idx, "Top-1 Dài"),
            (274, "Top-2 Rộng"),
            (70, "Top-3 Cái bàn"),
            (389, "Parenthetical Đẹp (người)"),
        ]
        for audio_idx, desc in audio_checks:
            with urllib.request.urlopen(f"http://{host}/audio/{audio_idx}.mp3", timeout=2) as resp:
                assert resp.status == 200
                audio_bytes = resp.read()
                assert len(audio_bytes) > 500, f"Audio {audio_idx}.mp3 too small: {len(audio_bytes)}"
                assert resp.headers.get("Content-Type") == "audio/mpeg"
            print(f"[PASS] GET /audio/{audio_idx}.mp3 ({desc}) served {len(audio_bytes)} bytes.")

        # 8. Verify /speak endpoint (GET & POST)
        with urllib.request.urlopen(f"http://{host}/speak?index={idx}", timeout=2) as resp:
            data = resp.read()
            assert len(data) > 0
            assert resp.headers.get("Content-Type") == "audio/mpeg"
        print(f"[PASS] GET /speak?index={idx} returned audio stream.")

        speak_req = urllib.request.Request(
            f"http://{host}/speak",
            data=json.dumps({"index": idx, "gloss": "Dài"}).encode("utf-8"),
            headers={"Origin": f"http://{host}", "X-PBL6": "demo", "Host": host, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(speak_req, timeout=2) as resp:
            speak_res = json.loads(resp.read().decode())
            assert speak_res.get("status") == "ok"
            assert speak_res.get("index") == idx
            assert speak_res.get("gloss") == "Dài"
            assert speak_res.get("has_audio") is True
        print("[PASS] POST /speak with payload returned valid acknowledgment.", flush=True)

        # 9. Verify restarting via POST /start while in result phase
        restart_req = urllib.request.Request(
            f"http://{host}/start",
            data=b"",
            headers={"Origin": f"http://{host}", "X-PBL6": "demo", "Host": host},
            method="POST",
        )
        with urllib.request.urlopen(restart_req, timeout=2) as resp:
            restart_data = json.loads(resp.read().decode())
            print(f"Restart response from result: phase={restart_data.get('phase')}")
            assert restart_data.get("phase") == "countdown"
            assert restart_data.get("remaining") in (1, 2, 3)
        print("[PASS] POST /start from 'result' phase successfully re-entered 'countdown'.")

        # 10. Verify host and origin handling (localhost and evil.com)
        localhost_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/state",
            headers={"Host": f"localhost:{port}"},
        )
        with urllib.request.urlopen(localhost_req, timeout=2) as resp:
            assert resp.status == 200
        print("[PASS] Server accepts Host: localhost as well as 127.0.0.1.")

        evil_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/start",
            data=b"",
            headers={"Origin": "http://evil.com", "X-PBL6": "demo", "Host": f"127.0.0.1:{port}"},
            method="POST",
        )
        try:
            urllib.request.urlopen(evil_req, timeout=2)
            assert False, "Should have rejected evil.com"
        except urllib.error.HTTPError as e:
            assert e.code == 403, f"Expected 403, got {e.code}"
        print("[PASS] POST /start from unauthorized evil.com origin properly rejected with 403 Forbidden.")

        # 11. Verify Demo start() transitions from 'retry' phase
        sys.path.insert(0, str(ROOT / "desktop_mvp"))
        from demo import Demo, make_handler
        from http.server import ThreadingHTTPServer
        import threading

        class MockDemo:
            def __init__(self, sample):
                self.lock = threading.Lock()
                self.sample = sample
                self.camera_ready = True
                self.state = {"phase": "retry", "sample": True, "message": "Không xử lý được lượt này. Hãy quay lại, giữ vai và hai tay trong khung."}
                self.deadline = 0.0

            start = Demo.start
            update = Demo.update
            snapshot = Demo.snapshot

        mock_demo = MockDemo(SAMPLE_CLIP)
        assert mock_demo.snapshot()["phase"] == "retry"
        assert "Không xử lý được lượt này" in mock_demo.snapshot()["message"]
        # Trigger start from retry
        assert mock_demo.start() is True, "Demo.start() failed from retry phase"
        snap = mock_demo.snapshot()
        assert snap["phase"] == "countdown"
        assert snap["remaining"] == 3
        assert "message" not in snap, "Stale retry message leaked into countdown"

        # Verify conflict rejection during countdown, recording, processing
        mock_demo.state["phase"] = "countdown"
        assert mock_demo.start() is False
        mock_demo.state["phase"] = "recording"
        assert mock_demo.start() is False
        mock_demo.state["phase"] = "processing"
        assert mock_demo.start() is False

        # Verify camera not ready rejection
        mock_demo.state["phase"] = "retry"
        mock_demo.camera_ready = False
        assert mock_demo.start() is False
        print("[PASS] Demo.start() handling in 'retry' phase verified: cleanly clears prompt, starts 3s countdown, and guards state transitions.")

        # 12. Deep verification: Live HTTP server receiving POST /start in 'retry' phase
        retry_demo = MockDemo(SAMPLE_CLIP)
        retry_port = 8793
        retry_host = f"127.0.0.1:{retry_port}"
        retry_server = ThreadingHTTPServer(("127.0.0.1", retry_port), make_handler(retry_demo, DEMO_PY.with_name("demo.html").read_bytes(), retry_host))
        retry_thread = threading.Thread(target=retry_server.serve_forever, daemon=True)
        retry_thread.start()
        try:
            # 12a. Verify initial /state over HTTP is 'retry'
            with urllib.request.urlopen(f"http://{retry_host}/state", timeout=2) as resp:
                data = json.loads(resp.read().decode())
                assert data["phase"] == "retry"
                assert "Không xử lý được lượt này" in data["message"]

            # 12b. Issue POST /start from 'retry' phase over HTTP with correct headers
            retry_post = urllib.request.Request(
                f"http://{retry_host}/start",
                data=b"",
                headers={"Origin": f"http://{retry_host}", "X-PBL6": "demo", "Host": retry_host},
                method="POST",
            )
            with urllib.request.urlopen(retry_post, timeout=2) as resp:
                assert resp.status == 200
                res_data = json.loads(resp.read().decode())
                assert res_data["phase"] == "countdown"
                assert res_data["remaining"] == 3
                assert "message" not in res_data

            # 12c. Verify subsequent GET /state is 'countdown' with no residual retry message
            with urllib.request.urlopen(f"http://{retry_host}/state", timeout=2) as resp:
                data = json.loads(resp.read().decode())
                assert data["phase"] == "countdown"
                assert "message" not in data

            # 12d. Verify 409 Conflict when attempting second start during active countdown
            conflict_post = urllib.request.Request(
                f"http://{retry_host}/start",
                data=b"",
                headers={"Origin": f"http://{retry_host}", "X-PBL6": "demo", "Host": retry_host},
                method="POST",
            )
            try:
                urllib.request.urlopen(conflict_post, timeout=2)
                assert False, "Expected HTTP 409 Conflict"
            except urllib.error.HTTPError as err:
                assert err.code == 409

            # 12e. Verify 409 Conflict if camera is not ready
            retry_demo.state["phase"] = "retry"
            retry_demo.camera_ready = False
            cam_unready_post = urllib.request.Request(
                f"http://{retry_host}/start",
                data=b"",
                headers={"Origin": f"http://{retry_host}", "X-PBL6": "demo", "Host": retry_host},
                method="POST",
            )
            try:
                urllib.request.urlopen(cam_unready_post, timeout=2)
                assert False, "Expected HTTP 409 when camera not ready"
            except urllib.error.HTTPError as err:
                assert err.code == 409

            print("[PASS] Live HTTP integration for 'retry' -> 'countdown' verified: HTTP 200 status, snapshot schema, message cleanup, and 409 conflict guards.")
        finally:
            retry_server.shutdown()

        print("\n=== ALL E2E INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == "__main__":
    test_demo_server()
