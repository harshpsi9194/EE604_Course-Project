# Validation record

Revision date: 4 November 2026. Baseline: `c26cb16`.

## Verified in this environment

- **33 automated regression tests passed**: wink release, bilateral blink rejection, hysteresis, cooldown, tracking loss, long stalls, mouth toggles, scroll repeat, pointer bounds, filter behavior, scale/rotation/aspect-ratio geometry, dry-run isolation, invalid command lines, camera errors and newest-frame capture.
- Dependencies installed in an isolated Python 3.12 environment; `pip check` found no broken requirements. Python compilation and whitespace checks for revised files passed. The archived original retains its original whitespace byte-for-byte.
- **Real MediaPipe Face Mesh inference ran successfully**, producing 478 landmarks on the public sample image.
- The complete headless video application processed **180 frames**, detected the face in **150**, completed calibration, handled the **30 blank frames** and resumed tracking.
- Missing-video input returns a clear error and nonzero status.
- Native Windows 64-bit Python 3.11 wheels were successfully resolved/downloaded for the pinned MediaPipe, NumPy, OpenCV and JAXlib versions. This is dependency availability validation, not execution on Windows.
- The preview layout was rendered and visually inspected at a smaller input resolution. No webcam GUI or Tkinter window was exercised interactively here.

## Reproducible measured results

| Measurement | Original setting / raw input | Revised setting / output | Scope |
|---|---:|---:|---|
| PyAutoGUI post-call pause, median | 100.128 ms | 0.061 ms | Actual installed `_handlePause` function; 30 samples each; no native mouse call |
| PyAutoGUI post-call pause, p95 | 100.205 ms | 0.082 ms | Same isolated function |
| Stationary coordinate standard deviation | 2.899 px | 1.010 px | Synthetic 3 px Gaussian noise; seed 604; 300 samples; first 30 excluded |
| Unintended clicks during bilateral blinks | Not measured for original here | 0/100 trials | Synthetic features, including asymmetric opening |
| Deliberate left-wink emitted events | Not measured for original here | 30/30 | Synthetic features, not human accuracy |
| Deliberate right-wink emitted events | Not measured for original here | 30/30 | Synthetic features, not human accuracy |

The pause result demonstrates removal of about **100 ms of configured overhead per public call** in the original move/click path. It does **not** establish an end-to-end speedup factor. The remaining native mouse, camera-driver and display costs were not measured.

For the repeated-image video smoke test only, median inference was **4.969 ms** (p95 **10.480 ms**). Read-complete-to-dry-dispatch was **5.328 ms** median. These are headless Linux server timings, include calibration/no-face frames in the aggregate, and cannot be presented as the latency of a Windows webcam demo. The dry-run dispatch does not issue an operating-system input command.

## Fixture and reproducibility

`tools/validate_pipeline.py --download-sample` explicitly downloads the NASA astronaut sample from scikit-image v0.24.0, creates a temporary 640×480 MJPG video, and deletes that temporary video on completion. It includes 90 face frames (some translated a few pixels), 30 blank frames, and 60 face frames for recovery. This is a repeated photograph, not a recording of a person performing gestures.

Image SHA-256: `88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5`.

Raw outputs:

- `results/validation.csv`: all 180 per-frame records.
- `results/validation.json`: pipeline summary and settings.
- `results/validation_report.json`: full provenance, timings and synthetic checks.

The same script imports the installed PyAutoGUI source without initializing a desktop, extracts its `_handlePause` definition, and executes that real definition for both pause values. Only the library sleep is timed. No simulated OS timings are labeled as measurements.

## What remains to be validated locally

1. Run `mouse-controller.py --dry-run`; verify face/iris tracking and comfortable calibration with your webcam.
2. Run `mouse-controller.py`; verify pause/resume, movement, left/right wink mapping, scroll direction, tracking loss and exit controls. The primary monitor is used.
3. Run the target-practice window; confirm actual desktop clicks reach targets. These interactive behaviors cannot be certified by headless tests.
4. Compare mouse pause 0.1 vs 0 with the same task. Then compare smoothing on/off and latest-frame vs serial capture separately.
5. Record deliberate gestures and ordinary blinks, with independent intended-action labels, to calculate human precision/recall and false-click rates.

**Do not claim 100% accuracy, general user robustness, clinical suitability, or a full-system speedup from these software checks.** The controller uses pretrained landmarks and heuristic gestures; no human validation dataset was available in the repository.
