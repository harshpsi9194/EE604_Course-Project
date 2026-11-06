# Revision audit

Baseline: `aksht17/iMouse`, commit `c26cb16`. The original script is copied byte-for-byte to `baseline/mouse-controller.original.py`; the original report PDF is unchanged.

| Finding in original | Change | Classification |
|---|---|---|
| Every `moveTo` call inherits the 0.1 s PyAutoGUI pause | Set `PAUSE=0`; keep `FAILSAFE=True`; issue one `click(button=...)` call for either button | Latency engineering, not research novelty by itself |
| Serial camera read, inference and dispatch can leave frames waiting | Latest-frame reader with a single slot; log skipped sequence IDs | Latency engineering; camera-driver buffering still exists |
| Cursor uses landmark 477, an iris boundary point | Average iris center landmarks 468 and 473 | Geometric correction/stability improvement |
| Raw eyelid y-gap threshold changes with face scale and tilt | Pixel-distance eye aspect ratio; neutral per-eye calibration; hysteresis | Established method adapted to this project; cite prior work |
| Bilateral blink satisfies both wink conditions; first tested eye wins | Cancel bilateral closures; require stable reopening; click once on a completed unilateral wink | Interaction-logic contribution to this baseline |
| Cursor moves while wink changes the eye landmarks | Freeze pointer during closures, release confirmation and scrolling | Part of the proposed gesture-aware control extension |
| Direct full-frame-to-screen mapping provides a limited practical motion region | Calibrated center and adjustable gain; primary-screen bounds | Usability extension; still head-assisted, not true gaze estimation |
| No filtering | One Euro filter on screen coordinates, responsive to motion speed | Existing published algorithm; cite its authors |
| Scroll compares eyelid positions and emits ±300 units | Eye-corner roll relative to neutral; angular hysteresis; ±3 steps at controlled intervals | Practical control improvement; per-app scroll distance varies |
| Report promises mouth toggle; code exits instead | Sustained mouth-open toggle with one event per open/close cycle | Report/code consistency fix |
| Hard-coded 300 s session limit | Run until exit, or optional `--seconds` limit | Demo reliability |
| Every detected event is recorded as a successful attempt | Log event counts and actual timing stages; remove the unsupported accuracy claim | Evaluation correction |
| Camera/window resources may survive an exception; Face Mesh not explicitly closed | Central cleanup, clear errors, context-aware dry run | Reliability fix |
| No dependency file or setup guide | Pin tested Face Mesh-compatible packages; provide Windows setup and tests | Reproducibility |

## Intended contribution

The defensible project extension is the **combination of calibrated gesture detection, gesture-aware pointer freezing, adaptive smoothing and bounded-frame processing**, evaluated against the original controller. None of the individual building blocks should be claimed as a newly invented algorithm. A broad literature search and real user comparisons would be needed to support a stronger research novelty claim.

## Scope kept

Same webcam input, pretrained MediaPipe Face Mesh, OpenCV processing, PyAutoGUI output, mouse actions and basic gesture vocabulary. No model training, extra sensors, cloud inference, object detector, or change to an unrelated project. The code is split into modules to make the behavior testable; this is an implementation organization change.

## Remaining verification

The development environment has no physical Windows webcam or interactive desktop. Actual OS mouse responsiveness, comfortable thresholds for the user, long-session behavior and the Tkinter demo need to be exercised locally. See `docs/VALIDATION.md`; successful automated tests do not establish human accuracy.
