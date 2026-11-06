# Research, software and data sources

These sources support the report prepared on 6 November 2026. They are credited technical foundations and contextual references. The documentation does not assert that every source was historically consulted by the original team. No YouTube tutorial is claimed as an implementation source.

| Source | Link | Role |
|---|---|---|
| Supplied baseline project | https://github.com/aksht17/iMouse/tree/c26cb16 | Historical reference listed in the archive; baseline code inspected locally. Remote content could not be retrieved in this session. |
| MediaPipe Face Mesh | https://chuoling.github.io/mediapipe/solutions/face_mesh.html | Official legacy solution documentation aligned with the pinned API |
| MediaPipe Iris | https://chuoling.github.io/mediapipe/solutions/iris.html | Iris landmarks and explicit limitation: no screen point-of-gaze inference |
| MediaPipe source | https://github.com/google-ai-edge/mediapipe | Pretrained perception framework source |
| Soukupova and Cech, CVWW 2016 | https://cmp.felk.cvut.cz/ftp/articles/cech/Soukupova-CVWW-2016.pdf | EAR and temporal blink detection; our code uses rules rather than their SVM |
| Casiez, Roussel and Vogel, CHI 2012 | https://gery.casiez.net/1euro/ | Original One Euro filter, explanation and tuning |
| One Euro implementations | https://github.com/casiez/OneEuroFilter | Prior implementation reference, not a claim of copied source |
| PyAutoGUI docs | https://pyautogui.readthedocs.io/en/latest/index.html#fail-safes | Default pause, primary-screen API and fail-safe behavior |
| PyAutoGUI source | https://github.com/asweigart/pyautogui | Desktop event library used in the project |
| OpenCV VideoCapture | https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html | Acquisition API reference |
| OpenCV source | https://github.com/opencv/opencv | Computer-vision dependency source |
| NumPy source | https://github.com/numpy/numpy | Numerical arrays and deterministic noise generation |
| JAX source | https://github.com/jax-ml/jax | Pinned dependency compatibility; no project model training |
| pytest source | https://github.com/pytest-dev/pytest | Development test dependency |
| Astronaut image docs | https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.astronaut | NASA photograph of Eileen Collins used as a smoke-test image |
| Versioned fixture image | https://github.com/scikit-image/scikit-image/blob/v0.24.0/skimage/data/astronaut.png | Exact source URL recorded in validation |
| Instructor template | https://www.overleaf.com/latex/templates/cvpr-2022-author-kit/qbmjsdxryffn | Currently resolves to CVPR 2026 template, matching the supplied archive |
| Official author kit | https://github.com/cvpr-org/author-kit | Template upstream |

## Data provenance

No task-specific training/fine-tuning dataset exists in the supplied project. The repeated-image fixture has 180 frames: 90 face frames, 30 blank frames and 60 face frames. Some frames have a small synthetic horizontal translation. The original image SHA-256 in the archived report is `88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5`.

`tools/validate_pipeline.py` generates synthetic bilateral blinks, unilateral winks and a stationary noisy coordinate trace. The 300-sample noise trace uses seed 604 and nominal standard deviation 3 pixels. It discards the first 30 points for the standard-deviation summary. These are software validation inputs, not a human gaze dataset.

The 33 test cases were rerun successfully during documentation preparation. Synthetic outputs reproduced exactly. Pipeline timing and pause microbenchmark values are supplied historical measurements. The current documentation does not assert that those timing experiments were rerun on this machine.

## Final project repository

[INSERT FINAL REVISED REPOSITORY URL AND COMMIT]

The historical baseline link must not be substituted for a verified link containing the submitted revision. Preserve attribution and applicable dependency licenses when publishing.
