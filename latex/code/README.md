# iMouse — Eye-Controlled Mouse

A webcam mouse controller using the original **OpenCV + MediaPipe Face Mesh + PyAutoGUI** pipeline. This revision keeps eye-based pointer movement, wink clicks, head-tilt scrolling and mouth control, while addressing avoidable latency and gesture conflicts.

**Recommended environment: run locally on Windows, with Python 3.11 (64-bit).** Python 3.12 is also supported by the pinned packages. No GPU, training, or Colab is required. Colab's hosted runtime cannot directly operate your local desktop cursor; use it only for offline analysis if needed.

This is a **head-assisted iris-position controller**, not a calibrated point-of-gaze estimator. Small head movements help move the pointer across the screen. MediaPipe iris landmarks alone do not estimate where on the screen someone is looking.

## Quick start on Windows

Download/extract this revised project and open PowerShell in its folder. Install Python 3.11 first if `py -3.11 --version` is unavailable.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe mouse-controller.py --dry-run
```

Use `py -3.12` instead if you have Python 3.12. The commands deliberately use the virtual environment's interpreter directly, so PowerShell activation policy is not a problem. Avoid Python 3.13+ for these pinned MediaPipe packages. Install only one OpenCV distribution in this environment; `opencv-contrib-python` already provides `cv2`.

First preview: sit facing the webcam in steady lighting. Keep both eyes open, mouth closed, and head still for 45 valid frames. Watch the landmark markers and predicted cursor without moving the real mouse. Stop with Q/ESC while the preview has keyboard focus.

Then start real desktop control:

```powershell
.venv\Scripts\python.exe mouse-controller.py
```

After calibration the application starts **paused**. Press SPACE in the preview window, or hold your mouth open for 0.6 seconds and close it, to enable control. A successful calibration should take approximately 1.5 seconds at 30 processed FPS; slower processing takes longer.

## Controls

| Action | Control |
|---|---|
| Move cursor | Move the iris/face position slightly relative to the calibrated center |
| Left click | Close only the left gesture eye for 0.15–1.0 s, then reopen |
| Right click | Close only the other eye for 0.15–1.0 s, then reopen |
| Normal bilateral blink | No click; pointer holds its position |
| Scroll | Tilt head beyond about 12° from calibrated neutral; return upright to stop |
| Pause/resume | Hold mouth open 0.6 s, then close; or SPACE in the preview |
| Recalibrate | C in the preview; control pauses until calibration completes |
| Quit | Q/ESC in the preview, close its window, or Ctrl+C in the terminal |
| Emergency stop | Move the physical mouse to a primary-screen corner; PyAutoGUI fail-safe stays enabled |

The mirrored webcam landmark groups preserve the original click mapping. If the eye/button mapping feels reversed, add `--swap-winks`. Winks are confirmed on reopening; a long hold does not repeatedly click. Pointer movement is frozen while winking or scrolling. The app controls the primary display.

```powershell
# Different webcam
.venv\Scripts\python.exe mouse-controller.py --camera 1

# Reduce pointer sensitivity if it moves too far
.venv\Scripts\python.exe mouse-controller.py --gain-x 3 --gain-y 4

# Lower image size only if the normal 640x480 setting is still slow
.venv\Scripts\python.exe mouse-controller.py --width 480 --height 360
```

Smaller frames may hurt eye tracking. Normalized thresholds improve scale tolerance, but do not guarantee invariance to lighting, glasses, extreme poses or tiny faces. Start with a single face, a stable camera and comfortable, small movements.

## Demo and measurements

The preview shows control state, gesture events, processing FPS, landmarks, and inference time. Each session saves a CSV and JSON summary under `results/`.

For a simple target-clicking demo, open a second terminal in the project folder:

```powershell
.venv\Scripts\python.exe tools\target_practice.py
```

Press SPACE in the target window to begin, then use the mouth gesture to enable iMouse. Hit the ten green targets with wink clicks. Target results measure **click hit/miss outcomes and task completion time**, not gesture-classification accuracy or algorithm latency. The target window uses standard-library Tkinter. Keyboard controls apply to the window currently in focus; mouth control continues while the target window has focus.

To replay a consented recording without controlling the desktop:

```powershell
.venv\Scripts\python.exe mouse-controller.py --video my_recording.mp4 --dry-run --metrics results\local_replay.csv
```

For headless analysis, also add `--no-preview`. Begin the recording with eyes open and mouth closed for calibration. Replay uses the video's time base for gesture duration; it is not slowed to real-time playback.

## What changed

- Removed PyAutoGUI's default 100 ms pause after each public mouse call. Retained corner fail-safe and explicit exit controls.
- Added a latest-frame camera reader so processing does not build a queue of old frames. Requested 640×480, 30 FPS and a short backend buffer; actual camera settings depend on the driver.
- Replaced a single iris boundary landmark with the average of the two iris center landmarks.
- Added neutral calibration, pointer gain and a speed-adaptive One Euro filter.
- Replaced fixed image-coordinate eyelid gaps with calibrated eye aspect ratios, hysteresis, bilateral-blink cancellation and one click per completed wink.
- Replaced the 300-unit scroll burst with small, rate-limited scroll steps using a head-roll angle.
- Made the mouth gesture pause/resume, matching the original report, and removed the forced five-minute exit.
- Added cleanup/error handling, a preview mode, real measurements, regression tests and reproducible validation.

See [CHANGELOG.md](CHANGELOG.md) for the full audit, [report notes](docs/REPORT_NOTES.md) for contribution/novelty wording and report corrections, and [validation](docs/VALIDATION.md) for the exact test scope. The original PDF is preserved as the historical report; its code appendix and results do not describe this revision. The original script is preserved verbatim under `baseline/`.

## Verification and comparison

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe tools\validate_pipeline.py --download-sample
```

The last command explicitly downloads one public NASA astronaut image from scikit-image. It creates a temporary 180-frame video, runs real Face Mesh inference, checks face loss/recovery, and records a narrowly scoped library-delay benchmark and synthetic-feature checks. It is **not** a human accuracy test or webcam benchmark.

For local comparisons, keep camera, lighting, person, task and resolution fixed:

```powershell
# Only reintroduce the original library pause
.venv\Scripts\python.exe mouse-controller.py --mouse-pause 0.1 --metrics results\local_pause_100ms.csv

# Optimized delay setting
.venv\Scripts\python.exe mouse-controller.py --mouse-pause 0 --metrics results\local_pause_0ms.csv

# Other independent ablations
.venv\Scripts\python.exe mouse-controller.py --no-smoothing --metrics results\local_no_filter.csv
.venv\Scripts\python.exe mouse-controller.py --serial-camera --metrics results\local_serial_capture.csv
```

The pause comparison changes only one optimization; it is not the complete original-vs-new comparison. Repeat each condition several times in alternating order. Use `native_action_timings_ms` to exclude paused/no-action frames when comparing mouse dispatch. `timings_ms` includes every processed frame, including calibration and no-face frames.

## Files

- `mouse-controller.py`: small entry point, same launch filename as before.
- `imouse/core.py`: landmark geometry, calibration, filter and gesture state machine.
- `imouse/capture.py`: bounded latest-frame camera capture.
- `imouse/app.py`: camera/inference, mouse dispatch, preview and measurements.
- `tools/`: reproducible validation and target-practice demo.
- `tests/`: headless regression tests.
- `docs/`: report notes, references, validation and local evaluation plan.

For macOS, camera and Accessibility permissions are required; it has not been exercised here. Linux desktop control requires a compatible desktop backend (typically X11). The supplied validation was run headlessly on Linux; Windows webcam, native cursor operation and the interactive target window still need a local smoke test.
