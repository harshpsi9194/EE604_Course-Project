# iMouse: demo, implementation and viva guide

## Setup on the demonstration laptop

Use the host Windows desktop with a working laptop webcam and Python 3.11 or 3.12. Run from `code/`. A remote notebook cannot directly control your local mouse.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe mouse-controller.py --dry-run
```

Keep both eyes open, mouth closed, and head steady while 45 valid frames are collected. Watch the preview. If the wrong camera opens, add `--camera 1`. If movement is too sensitive, try `--gain-x 3 --gain-y 4`. If wink/button orientation feels reversed, add `--swap-winks`.

Start native control only after the preview looks correct:

```powershell
.venv\Scripts\python.exe mouse-controller.py
```

Desktop mode starts paused. SPACE in the preview or an open-mouth hold of 0.6 seconds enables it. Close the mouth before interacting. A long mouth opening toggles once, not repeatedly. Q/ESC works when the preview has focus. The corner fail-safe requires moving the physical mouse to a primary-display corner.

In another terminal:

```powershell
.venv\Scripts\python.exe tools\target_practice.py
```

Focus the target window and press SPACE to start its ten-target sequence. Use mouth control to enable/pause iMouse while the target window has focus. Its target radius is 38 pixels, with a seeded sequence. Fix the window size across comparisons.

## Suggested 3-minute demonstration

1. Show calibration and identify the preview's state, landmarks, timing and predicted pointer.
2. Enable desktop control and make small movements. Explain that head motion contributes.
3. Blink normally, then wink deliberately and release. Show the difference in emitted clicks.
4. Complete several targets. Right-click in a safe empty area to show the second button.
5. Scroll an ordinary document with head tilt and return upright to stop.
6. Pause by mouth hold, briefly move out of frame, and explain state reset/rearming.
7. Show where session CSV/JSON files are saved. Do not call event counts accuracy.

If the camera fails, check permissions, close other camera apps and test another camera index. Do not switch to a prerecorded demonstration without saying it is prerecorded. If the pointer jumps, pause, recalibrate and reduce gains. Poor lighting or weak eye visibility may require changing the setup rather than the thresholds.

## Architecture walkthrough

| File | Responsibility | Why separated |
|---|---|---|
| `mouse-controller.py` | Calls the application entry point | Stable launch command |
| `imouse/core.py` | Geometry, calibration, filter, temporal policy | Can test without camera or desktop |
| `imouse/capture.py` | Producer thread, one latest-frame slot | Avoid growing application queues |
| `imouse/app.py` | CLI, perception, preview, dispatch, timing logs | Owns I/O and cleanup |
| `tools/target_practice.py` | Ten-target Tkinter task | Measures practical task outcomes |
| `tools/validate_pipeline.py` | Fixture inference, pause benchmark, synthetic tests | Reproducible narrow validation |
| `tests/` | Regression tests | Checks state transitions and failure paths |

The controller's priority is missing-face reset, mouth handling, paused state, eye closure/wink handling, rearming, scrolling, then ordinary pointer movement. This order prevents a mouth opening or eye closure from simultaneously producing ordinary movement. Configuration constants are in `Config` in `core.py`.

## Questions to prepare

**What is actually novel?**
The task-specific integration of calibrated wink recognition, bilateral-blink cancellation and gesture-aware cursor holds into the inherited controller, with adaptive smoothing, capture handling and explicit evaluation. EAR, MediaPipe and One Euro are established techniques. This is an engineering contribution; no global first-of-its-kind claim is supported.

**Why is this not true gaze estimation?**
The code maps iris image coordinates relative to a neutral position. Head translation changes those coordinates. There is no calibrated gaze ray, screen geometry or learned gaze-to-screen mapping.

**Why divide eyelid opening by eye width?**
It reduces sensitivity to image scale compared with a raw gap. Using pixel-space distances respects the image aspect ratio. It does not make the ratio invariant to all head poses, occlusion or lighting.

**Why two thresholds?**
Closing below 0.55 of neutral and reopening at 0.75 creates hysteresis, reducing repeated flips near a single threshold.

**Why click on release?**
The controller can observe duration and bilateral closure before emitting an action. It rejects too-short/too-long winks and cancels a blink. The trade-off is intentional recognition delay: a qualifying wink lasts at least 0.15 seconds.

**What if a blink begins with one eye?**
A later bilateral closure cancels the entire pending wink. Asymmetric reopening does not restore it; both eyes must rearm.

**Why median calibration?**
The median is less affected by occasional outlying feature values than an ordinary mean. Forty-five consecutive valid frames provide a short reference window. The choice is a design default, not a proven optimum.

**Why One Euro rather than a moving average?**
Its cutoff responds to speed, giving stronger smoothing when still and less lag during faster movement. A fixed moving average imposes a window-based trade-off. The current evidence measures stationary jitter only, not comparative movement lag.

**What is the latest-frame trade-off?**
A bounded slot prevents a queue of old application frames, but may skip brief events. Camera exposure/driver buffering remains. Evaluate recognition and latency together.

**Does zero PyAutoGUI pause disable the fail-safe?**
No. The code sets the pause separately and retains the fail-safe. Removing the pause only removes one delay component.

**What does 5.33 ms mean?**
Median read-complete-to-dispatch time in supplied dry-run file replay. It excludes camera exposure/driver latency, real native desktop events and display response. It is not the total time a user experiences.

**Why not report 100% accuracy from the synthetic counts?**
Scripted features bypass perception and do not sample real user variability. The old success counter also lacked independent labels. Real precision and recall need intended-action labels, including misses and false positives.

**What datasets did you use?**
No task-specific training dataset. A repeated NASA/scikit-image image is an inference smoke-test fixture, and deterministic generated feature/noise sequences test controller behavior. Live evaluation remains to be collected.

**Which users may struggle?**
People unable to wink independently or maintain a stable head position may need a different click mechanism. Fatigue, glasses and lighting need evaluation. No clinical accessibility claim is supported.

## Live experiment recording protocol

Use consented trials and pseudonymous participant IDs. Keep video optional; manual intended-action labels are sufficient for the initial project evaluation. Record CPU, OS, Python/library versions, webcam model, requested/actual resolution, lighting, distance, screen resolution, gains and condition order.

For each participant and condition, attempt 20 left winks, 20 right winks, 30 normal blinks, 10 scroll attempts in each direction and 10 toggles. Repeat the ten-target task at least three times when practical. These counts are a plan, not completed results. Alternate condition order to reduce practice/fatigue effects.

For isolated ablations, run:

```powershell
.venv\Scripts\python.exe mouse-controller.py --mouse-pause 0.1 --metrics results\pause_on.csv
.venv\Scripts\python.exe mouse-controller.py --mouse-pause 0 --metrics results\pause_off.csv
.venv\Scripts\python.exe mouse-controller.py --no-smoothing --metrics results\filter_off.csv
.venv\Scripts\python.exe mouse-controller.py --serial-camera --metrics results\serial.csv
```

Use distinct filenames for every repetition. The original script is under `baseline/` but exits on mouth opening and can issue large scroll bursts; rehearse in a benign window before comparing it.

Record intended and emitted action independently in `LIVE_TRIALS_TEMPLATE.csv`. Define a response window before collecting data, and keep it identical across conditions. Count wrong-class clicks, missed intentions and unsolicited clicks explicitly. Report per-class precision TP/(TP+FP), recall TP/(TP+FN), and false clicks per bilateral-blink trial. If a denominator is zero, report undefined rather than silently inserting 0 or 100%.

For target logs, hit fraction = successful clicks / all clicks. Acquisition time for a target is the `seconds_since_target_shown` value on its first successful hit. Miss timestamps are cumulative since target appearance; do not sum them. Report incomplete targets and interrupted runs. Jitter should be measured over a stationary interval with no intentional movement, and live cursor samples should exclude pauses/no-face states.

## Submission check

Every member fills their actual contribution. Include implementation file names, experiments run, analysis performed and specific writing/presentation work where applicable. Do not assign invented responsibilities. Add the final GitHub URL and commit after publishing through your own account. Keep source links and the entire code appendix in the report.
