"""Local webcam application. --dry-run also accepts a prerecorded video."""
import argparse
from collections import Counter, deque
import csv
from datetime import datetime
import json
from pathlib import Path
import platform
import sys
import time

from .capture import LatestFrameCamera
from .core import Calibration, Config, Controller, extract_features


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--video", type=Path, help="Replay video; requires --dry-run")
    p.add_argument("--dry-run", action="store_true", help="No operating-system mouse actions")
    p.add_argument("--no-preview", action="store_true", help="Headless evaluation; requires --dry-run")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--max-frames", type=int, default=0, help="0 means unlimited")
    p.add_argument("--seconds", type=float, default=0, help="0 means unlimited")
    p.add_argument("--gain-x", type=float, default=4.0)
    p.add_argument("--gain-y", type=float, default=6.0)
    p.add_argument("--swap-winks", action="store_true")
    p.add_argument("--no-smoothing", action="store_true")
    p.add_argument("--serial-camera", action="store_true", help="Disable latest-frame thread for comparison")
    p.add_argument("--mouse-pause", type=float, default=0, help="0.1 restores the original per-call delay")
    p.add_argument("--metrics", type=Path, help="CSV output path; also writes a JSON summary")
    return p


class Mouse:
    def __init__(self, dry_run=False, pause=0):
        self.api = None
        self.screen_size = (1920, 1080)
        self.last_position = None
        if not dry_run:
            try:
                import pyautogui
                self.api = pyautogui
                self.api.FAILSAFE = True
                self.api.PAUSE = pause
                self.screen_size = tuple(self.api.size())
            except Exception as exc:
                raise RuntimeError("Desktop mouse access unavailable. Run locally, or use --dry-run.") from exc

    def dispatch(self, decision):
        if self.api is None:
            return 0
        calls = 0
        self.api.failSafeCheck()
        if decision.cursor is not None and decision.cursor != self.last_position:
            self.api.moveTo(*decision.cursor, duration=0)
            self.last_position = decision.cursor
            calls += 1
        if decision.click:
            self.api.click(button=decision.click)
            calls += 1
        if decision.scroll:
            self.api.scroll(decision.scroll)
            calls += 1
        return calls


class Metrics:
    fields = ["frame", "capture_sequence", "gesture_time_s", "mode", "face", "active", "status",
              "click", "scroll", "cursor_x", "cursor_y", "native_calls", "dropped_frames",
              "capture_wait_ms", "preprocess_ms", "inference_ms", "control_ms",
              "dispatch_ms", "read_to_dispatch_ms", "display_ms", "loop_ms"]

    def __init__(self, path, metadata):
        self.path, self.metadata = path, metadata
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.stream, fieldnames=self.fields, lineterminator="\n")
        self.writer.writeheader()
        self.counts = Counter()
        self.started = time.perf_counter()

    def write(self, row):
        self.writer.writerow(row)
        self.counts["frames"] += 1
        self.counts["face_frames"] += int(row["face"])
        self.counts["dropped_frames"] += row["dropped_frames"]
        if row["click"]:
            self.counts[row["click"] + "_click_events"] += 1
        if row["scroll"]:
            self.counts["scroll_events"] += 1

    def close(self):
        self.stream.close()
        elapsed = time.perf_counter() - self.started
        import numpy as np
        with self.path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        stats = {}
        for name in self.fields:
            if name.endswith("_ms") and rows:
                values = np.array([float(row[name]) for row in rows])
                stats[name] = {"median": float(np.median(values)), "p95": float(np.percentile(values, 95))}
        action_stats = {}
        action_rows = [r for r in rows if int(r["native_calls"]) > 0]
        for name in ("dispatch_ms", "read_to_dispatch_ms"):
            if action_rows:
                values = [float(row[name]) for row in action_rows]
                action_stats[name] = {"median": float(np.median(values)), "p95": float(np.percentile(values, 95))}
        summary = {"metadata": self.metadata, "counts": dict(self.counts), "elapsed_seconds": elapsed,
                   "processed_fps": self.counts["frames"] / max(elapsed, 1e-6), "timings_ms": stats,
                   "native_action_frames": len(action_rows), "native_action_timings_ms": action_stats,
                   "measurement_note": "Read-to-dispatch starts AFTER camera read; excludes sensor/driver and OS display latency. Counts are predictions, NOT accuracy. Dry-run dispatch is NOT OS input latency."}
        self.path.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))


def draw_overlay(cv2, frame, lines, landmarks, active, cursor, screen_size):
    # Preview legibility is independent of the lower-resolution inference input.
    if frame.shape[1] < 640:
        frame = cv2.resize(frame, None, fx=640/frame.shape[1], fy=640/frame.shape[1])
    if landmarks is not None:
        h, w = frame.shape[:2]
        for index in (468, 473, 33, 133, 362, 263, 13, 14):
            p = landmarks[index]
            cv2.circle(frame, (int(p.x * w), int(p.y * h)), 2, (75, 220, 235), -1)
    import numpy as np
    panel = np.zeros((170, frame.shape[1], 3), dtype=np.uint8)
    panel[:] = (28, 24, 22)
    for i, line in enumerate(lines):
        color = (140, 230, 130) if i == 0 and active else (225, 225, 225)
        cv2.putText(panel, line, (12, 24 + i * 26), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)
    if cursor:
        h, w = frame.shape[:2]
        px, py = int(cursor[0] / screen_size[0] * w), int(cursor[1] / screen_size[1] * h)
        cv2.drawMarker(frame, (px, py), (70, 255, 130), cv2.MARKER_CROSS, 18, 2)
    return np.vstack((frame, panel))


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if (args.video or args.no_preview) and not args.dry_run:
        p.error("--video and --no-preview require --dry-run")
    if min(args.width, args.height) < 160 or args.fps <= 0:
        p.error("Use dimensions of at least 160 pixels and positive FPS.")
    if min(args.gain_x, args.gain_y) <= 0 or min(args.mouse_pause, args.seconds, args.max_frames) < 0:
        p.error("Gains must be positive; pause, time limit, and frame limit cannot be negative.")
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Install requirements.txt in Python 3.11/3.12.", file=sys.stderr)
        return 1
    if not hasattr(mp, "solutions"):
        print("Install mediapipe==0.10.21 from requirements.txt for the Face Mesh API.", file=sys.stderr)
        return 1

    capture = reader = mesh = metrics = None
    preview_open = False
    exit_code = 0
    try:
        mouse = Mouse(args.dry_run, args.mouse_pause)
        if args.video:
            if not args.video.is_file():
                raise RuntimeError(f"Video not found: {args.video}")
            capture = cv2.VideoCapture(str(args.video))
        else:
            backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
            capture = cv2.VideoCapture(args.camera, backend)
            if not capture.isOpened() and backend != cv2.CAP_ANY:
                capture.release()
                capture = cv2.VideoCapture(args.camera)
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
            capture.set(cv2.CAP_PROP_FPS, args.fps)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Best effort, backend-dependent.
        if not capture.isOpened():
            raise RuntimeError("Cannot open input. Check webcam permissions, close other camera apps, or try --camera 1.")
        source_fps = capture.get(cv2.CAP_PROP_FPS) or args.fps
        if not (0 < source_fps < 1000):
            source_fps = args.fps
        if not args.video and not args.serial_camera:
            reader = LatestFrameCamera(capture)
        cv2.setNumThreads(1)
        mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False, max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.6, min_tracking_confidence=0.6)
        if not args.no_preview:
            cv2.namedWindow("iMouse", cv2.WINDOW_NORMAL)
            preview_open = True
        config = Config(gain_x=args.gain_x, gain_y=args.gain_y,
                        smoothing=not args.no_smoothing, swap_winks=args.swap_winks)
        controller = None
        samples = []
        calibrating = True
        calibration_start = time.perf_counter()
        path = args.metrics or Path("results") / (datetime.now().strftime("session_%Y%m%d_%H%M%S_%f") + ".csv")
        metadata = {"mode": "dry-run" if args.dry_run else "desktop",
                    "platform": platform.platform(), "python": platform.python_version(),
                    "mediapipe": mp.__version__, "opencv": cv2.__version__,
                    "options": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                    "source_fps": source_fps, "screen_size": mouse.screen_size}
        metrics = Metrics(path, metadata)
        sequence = count = 0
        started = time.perf_counter()
        recent = deque(maxlen=30)
        last_event, event_until = "No gesture yet", 0
        print("iMouse: look straight ahead, both eyes open, mouth closed for calibration.")
        print("SPACE pause/resume | C recalibrate | Q/ESC quit | hold mouth open: pause/resume")
        while True:
            loop_start = time.perf_counter()
            if args.seconds and loop_start - started >= args.seconds:
                break
            previous_sequence = sequence
            if reader:
                sequence, captured_at, frame = reader.read(sequence)
            else:
                ok, frame = capture.read()
                captured_at = time.perf_counter()
                if not ok:
                    if args.video and count:
                        break
                    raise RuntimeError("Input stopped before a frame could be read.")
                sequence += 1
            read_end = time.perf_counter()
            ratio = min(1.0, args.width / frame.shape[1], args.height / frame.shape[0])
            if ratio < 1.0:
                frame = cv2.resize(frame, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            preprocess_end = time.perf_counter()
            prediction = mesh.process(rgb)
            inference_end = time.perf_counter()
            landmarks = prediction.multi_face_landmarks[0].landmark if prediction.multi_face_landmarks else None
            features = extract_features(landmarks, frame.shape[1], frame.shape[0]) if landmarks else None
            # Recorded gestures use video time, independent of replay speed.
            gesture_time = sequence / source_fps if args.video else captured_at
            decision = None
            status = "Calibration: look ahead, eyes open, mouth closed"
            if calibrating:
                if features and features.left > 0.12 and features.right > 0.12 and features.mouth < 0.28:
                    samples.append(features)
                else:
                    samples.clear()
                status += f" ({len(samples)}/45)"
                if len(samples) >= 45:
                    cal = Calibration.from_samples(samples)
                    controller = Controller(cal, mouse.screen_size, config, active=args.dry_run)
                    metrics.metadata["calibration"] = vars(cal)
                    calibrating = False
                    print("Calibration complete. Press SPACE to start desktop control.")
                elif not args.video and time.perf_counter() - calibration_start > 20:
                    status = "Calibration waiting: improve lighting, keep eyes open"
            elif controller:
                decision = controller.step(features, gesture_time)
                status = decision.status
                if decision.click or decision.scroll or decision.toggled:
                    last_event = (f"{decision.click} click" if decision.click else
                                  f"scroll {decision.scroll}" if decision.scroll else "control toggled")
                    event_until = time.perf_counter() + 2
            control_end = time.perf_counter()
            if not controller or not controller.active or features is None or (decision and decision.toggled):
                mouse.last_position = None
            native_calls = mouse.dispatch(decision) if decision else 0
            dispatch_end = time.perf_counter()
            count += 1
            recent.append(dispatch_end)
            fps = (len(recent)-1) / max(recent[-1]-recent[0], 1e-6)
            active = controller.active if controller else False
            key = -1
            if not args.no_preview:
                lines = [f"iMouse | {'DRY RUN' if args.dry_run else 'ACTIVE' if active else 'PAUSED'} | {fps:.1f} FPS",
                         status, f"Inference: {(inference_end-preprocess_end)*1000:.1f} ms | Event: {last_event if time.perf_counter() < event_until else '-'}",
                         "SPACE pause/resume | C recalibrate | Q / ESC quit",
                         "Wink + release: click | Tilt head: scroll",
                         "Hold mouth open 0.6s: pause/resume"]
                display = draw_overlay(cv2, frame, lines, landmarks, active,
                                       controller.last_cursor if controller else None, mouse.screen_size)
                cv2.imshow("iMouse", display)
                key = cv2.waitKey(1) & 0xFF
            display_end = time.perf_counter()
            cursor = decision.cursor if decision and decision.cursor else ("", "")
            metrics.write(dict(frame=count, capture_sequence=sequence,
                gesture_time_s=gesture_time if args.video else captured_at-started, mode=metadata["mode"],
                face=int(features is not None), active=int(active), status=status,
                click=(decision.click or "") if decision else "", scroll=decision.scroll if decision else 0,
                cursor_x=cursor[0], cursor_y=cursor[1], native_calls=native_calls,
                dropped_frames=max(0, sequence-previous_sequence-1),
                capture_wait_ms=(read_end-loop_start)*1000, preprocess_ms=(preprocess_end-read_end)*1000,
                inference_ms=(inference_end-preprocess_end)*1000, control_ms=(control_end-inference_end)*1000,
                dispatch_ms=(dispatch_end-control_end)*1000, read_to_dispatch_ms=(dispatch_end-captured_at)*1000,
                display_ms=(display_end-dispatch_end)*1000, loop_ms=(display_end-loop_start)*1000))
            if key in (ord('q'), 27) or (args.max_frames and count >= args.max_frames):
                break
            if preview_open and cv2.getWindowProperty("iMouse", cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == 32 and controller and not calibrating:
                controller.toggle()
                mouse.last_position = None
            if key == ord('c'):
                calibrating = True
                samples.clear()
                controller = None
                calibration_start = time.perf_counter()
    except KeyboardInterrupt:
        print("Stopped by keyboard.")
    except Exception as exc:
        if type(exc).__name__ == "FailSafeException":
            print("Stopped: cursor reached a screen corner (PyAutoGUI fail-safe).")
        else:
            print(f"iMouse error: {exc}", file=sys.stderr)
            exit_code = 1
    finally:
        if reader:
            reader.close()
        elif capture is not None:
            capture.release()
        if mesh is not None:
            mesh.close()
        if preview_open:
            cv2.destroyAllWindows()
        if metrics:
            metrics.close()
            print(f"Session measurements saved to {metrics.path}")
    return exit_code
