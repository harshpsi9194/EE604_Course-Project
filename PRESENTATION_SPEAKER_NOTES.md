## Slide 1: iMouse

Introduce the project as head-assisted iris-position mouse control. The code uses image position and does not estimate screen gaze. Replace team placeholders before presenting.



## Slide 2: Problem statement

The input is one RGB camera stream. Outputs are primary-screen movement, clicks, scrolling and pause/resume. Accessibility is motivation, not a clinically validated outcome.



## Slide 3: Why the baseline needs a control layer

The baseline is inspected from baseline/mouse-controller.original.py. It uses landmark 477, direct screen mapping and fixed gaps. Its success counters mark triggered events as successful without independent ground truth.

Source: supplied baseline/mouse-controller.original.py

## Slide 4: Literature and technical foundations

MediaPipe supplies pretrained landmarks. Soukupova and Cech use EAR and an SVM over a temporal window. We reuse the geometry, not their classifier. One Euro is established prior work. PyAutoGUI documents the default pause.

Sources: MediaPipe docs; Soukupova & Cech (CVWW 2016); Casiez et al. (CHI 2012); PyAutoGUI docs

## Slide 5: Project contribution

Defend novelty as a course-level engineering extension. The strongest contribution is interaction-aware coordination plus reproducible evaluation. Practical advantage still needs a matched live-user experiment.

Source: imouse/core.py, capture.py and app.py

## Slide 6: System overview

Perception produces feature geometry. Neutral calibration configures the gesture gate. The gate either permits filtered pointer movement or dispatches a gesture action. No-face input resets the tracking state.

Source: imouse/app.py and imouse/core.py

## Slide 7: Calibration and geometry

Distances use pixel coordinates x times width and y times height. Otherwise rectangular images distort the ratio. Both open-eye baselines and neutral position are medians over 45 consecutive valid frames. The application clears samples on invalid frames.

Sources: core.py extract_features / Calibration; Soukupova & Cech, 2016

## Slide 8: Wink clicks and blink rejection

After 0.12 seconds open, the controller is ready. A unilateral closure lasting 0.15 to 1 second emits one click upon release, provided cooldown permits it. Bilateral closure cancels the whole pending gesture even if the eyes reopen at different times.

Source: Controller.step in imouse/core.py

## Slide 9: Pointer control and smoothing

The same mapping is applied to x and y with gains 4 and 6. Coordinates clamp inside screen edges. One Euro filters each coordinate with min cutoff 1.2 Hz and beta 0.007. The derivative uses raw successive samples and is itself smoothed at 1 Hz.

Sources: core.py OneEuro / Controller; https://gery.casiez.net/1euro/

## Slide 10: Scrolling, pause and interface

Mouth toggle happens at the 0.6 second threshold, not on release. Closing the mouth releases the latch and allows normal operation. The preview must have keyboard focus for its shortcuts. Use the physical corner fail-safe if needed.

Source: core.py Config and Controller.step; app.py preview

## Slide 11: Experimental evidence

Separate supplied timings from newly rerun checks. Supplied Linux logs use Python 3.12.14, MediaPipe 0.10.21, OpenCV 4.11.0. CPU model is absent. The repeat-image fixture is unpaced file replay. Synthetic gesture tests bypass perception.

Sources: results/validation_report.json; tools/validate_pipeline.py; fresh pytest run

## Slide 12: Offline pipeline timing

Values come from the archive, not a fresh pipeline run. Read-to-dispatch is measured after read completes, excluding sensor/driver and display response. The 130.14 FPS is file-processing throughput. No native mouse actions occurred.

Source: supplied results/validation_report.json, all 180 frames

## Slide 13: Synthetic gesture checks

Blink sequences include one-eye onset and asymmetric release, while winks last eight samples at 30 Hz. The exact expected outputs were reproduced. These are software checks, not 100 percent human recognition accuracy.

Source: tools/validate_pipeline.py synthetic_experiments(), reproduced

## Slide 14: Stationary synthetic jitter

300 raw values are generated around 500 pixels with Gaussian sigma 3 and seed 604. Population standard deviation excludes the first 30 samples. Reduction is 65.17 percent. This is one coordinate, not live 2D pointer error.

Source: reproduced synthetic_experiments(); same values as supplied validation_report.json

## Slide 15: Avoidable library delay

This runs the actual installed PyAutoGUI _handlePause function in isolation without native desktop calls. Thirty repetitions per setting. A zero pause still has small scheduling overhead. Do not describe this as full system latency or a complete baseline speedup.

Source: validation_report.json pause_microbenchmark; PyAutoGUI fail-safe documentation

## Slide 16: Live evaluation and ablations

This is a proposed experiment, not completed data. Keep camera, lighting, user, resolution and task fixed. Alternate baseline and revised conditions. Label intentions independently. Use native_action_timings_ms for mouse-active frames and do not infer accuracy from event counts.

Source: supplied docs/REPORT_NOTES.md; evaluation protocol in the handoff guide

## Slide 17: Demo sequence

Start the local application in dry-run and check calibration. Desktop mode starts paused. Open target_practice in another terminal, focus its window and press SPACE to begin. Use mouth control because the preview has lost focus. Demonstrate natural blink rejection, then deliberate clicks, scroll and pause. Have a consented recording as backup if available, without presenting replay as live.

Commands and troubleshooting: DEMO_AND_VIVA_GUIDE.md

## Slide 18: Limitations and conclusion

The revision improves explicit control behavior, supported by tests and limited offline evidence. Do not claim clinical accessibility, accurate screen gaze, universal lighting robustness or a full-system latency improvement. Possible next work is alternative click input and human evaluation.



## Slide 19: References and submission details

Full URLs and source roles are in the report bibliography and SOURCES.md. Replace the final repository and contribution placeholders. Every group member must submit a report with their own specific contribution. The old repository is a baseline reference and may not contain this revision.


