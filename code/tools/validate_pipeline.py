"""Reproducible checks using real Face Mesh inference, without an OS mouse.

python tools/validate_pipeline.py --download-sample
The downloaded NASA image is only a smoke-test fixture, not a gesture dataset.
"""
import argparse
import ast
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from imouse.app import main
from imouse.core import Calibration, Controller, Features, OneEuro


def summary(values):
    import numpy as np
    return {"median_ms": float(np.median(values)), "p95_ms": float(np.percentile(values, 95))}


def measure_library_pause():
    """Run the INSTALLED library's real pause function, without importing X11.

    No fake cursor timings: this ONLY measures the library's post-call sleep.
    """
    source = Path(importlib.util.find_spec("pyautogui").origin).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_handlePause")
    module = ast.Module(body=[function], type_ignores=[])
    output = {}
    for pause in (0.1, 0.0):
        namespace = {"time": time, "PAUSE": pause}
        exec(compile(module, "pyautogui._handlePause", "exec"), namespace)
        values = []
        for _ in range(30):
            start = time.perf_counter()
            namespace["_handlePause"](True)
            values.append((time.perf_counter()-start)*1000)
        output[str(pause)] = summary(values)
    return {"scope": "Actual PyAutoGUI _handlePause only; excludes native mouse APIs, camera, inference and display.",
            "samples_per_setting": 30, "pause_seconds": output}


def synthetic_experiments():
    import numpy as np
    rng = np.random.default_rng(604)
    f = Features(0.5,0.5,0.3,0.3,0.04,0)
    c = Controller(Calibration(0.5,0.5,0.3,0.3,0), active=True)
    natural_blinks, wink_counts = 0, {"left":0,"right":0}
    t = 0.0
    # Include one-eye onset and asymmetric release of ordinary bilateral blinks.
    for _ in range(100):
        sequence = [f]*10 + [replace(f,left=0.03)] + [replace(f,left=0.03,right=0.03)]*3 + [replace(f,right=0.03)] + [f]*10
        for sample in sequence:
            t += 1/30
            natural_blinks += c.step(sample,t).click is not None
    for eye in ("left", "right"):
        for _ in range(30):
            sequence = [f]*15 + [replace(f,**{eye:0.03})]*8 + [f]*15
            for sample in sequence:
                t += 1/30
                event = c.step(sample,t).click
                if event:
                    wink_counts[event] += 1
    raw = 500 + rng.normal(0,3,300)
    filt = OneEuro()
    filtered = np.array([filt(v,i/30) for i,v in enumerate(raw)])
    return {"scope": "Synthetic landmark features; software regression evidence, NOT human gesture accuracy.",
            "bilateral_blink_trials":100, "unintended_clicks":natural_blinks,
            "deliberate_winks_per_eye":30, "emitted_clicks":wink_counts,
            "stationary_input_std_px":float(np.std(raw[30:])),
            "filtered_std_px":float(np.std(filtered[30:]))}


def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path)
    p.add_argument("--download-sample", action="store_true")
    p.add_argument("--output", type=Path, default=ROOT / "results" / "validation")
    args=p.parse_args()
    if not args.image and not args.download_sample:
        p.error("Supply --image or --download-sample.")
    import cv2
    import numpy as np
    source_url="https://raw.githubusercontent.com/scikit-image/scikit-image/v0.24.0/skimage/data/astronaut.png"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="imouse-check-") as tmp:
        image_path=args.image
        if image_path is None:
            image_path=Path(tmp)/"astronaut.png"
            urllib.request.urlretrieve(source_url, image_path)
        image=cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Cannot read {image_path}")
        canvas=np.zeros((480,640,3),dtype=np.uint8)
        canvas[:,80:560]=cv2.resize(image,(480,480))
        video=Path(tmp)/"fixture.avi"
        writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),30,(640,480))
        if not writer.isOpened():
            raise RuntimeError("MJPG video writer unavailable.")
        for i in range(180):
            # 90 face frames, 30 blank frames, 60 face frames after reacquisition.
            frame=np.zeros_like(canvas) if 90 <= i < 120 else canvas.copy()
            if 60 <= i < 90:
                matrix=np.float32([[1,0,3*np.sin(i/5)],[0,1,0]])
                frame=cv2.warpAffine(frame,matrix,(640,480))
            writer.write(frame)
        writer.release()
        csv_path=args.output.with_suffix(".csv")
        code=main(["--video",str(video),"--dry-run","--no-preview","--metrics",str(csv_path)])
        if code:
            raise RuntimeError("Video application failed.")
        pipeline=json.loads(csv_path.with_suffix(".json").read_text())
        assert pipeline["counts"]["frames"] == 180
        assert 140 <= pipeline["counts"]["face_frames"] <= 155
        assert "calibration" in pipeline["metadata"]
        report={"environment":{"python":platform.python_version(),"platform":platform.platform()},
                "fixture":{"description":"Repeated NASA astronaut still with a small synthetic translation and 30 blank frames; NOT a live webcam or gesture dataset.",
                           "source":source_url if args.download_sample else "User-supplied image",
                           "sha256":hashlib.sha256(image_path.read_bytes()).hexdigest()},
                "pipeline":pipeline, "pause_microbenchmark":measure_library_pause(),
                "synthetic_experiments":synthetic_experiments()}
        report_path=args.output.parent/(args.output.name+"_report.json")
        report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps(report,indent=2))


if __name__ == "__main__":
    run()
