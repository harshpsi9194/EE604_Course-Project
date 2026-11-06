"""Keep only the latest camera frame instead of queuing stale frames."""
import threading
import time


class LatestFrameCamera:
    def __init__(self, capture):
        self.capture = capture
        self.condition = threading.Condition()
        self.stop_event = threading.Event()
        self.latest = None
        self.sequence = 0
        self.error = None
        self.thread = threading.Thread(target=self._read, name="imouse-camera", daemon=True)
        self.thread.start()

    def _read(self):
        try:
            while not self.stop_event.is_set():
                ok, frame = self.capture.read()
                if not ok:
                    raise RuntimeError("Camera stopped returning frames.")
                timestamp = time.perf_counter()  # Read-complete time, NOT exposure time.
                with self.condition:
                    self.sequence += 1
                    self.latest = (self.sequence, timestamp, frame)
                    self.condition.notify_all()
        except Exception as exc:
            with self.condition:
                self.error = exc
                self.condition.notify_all()
        finally:
            self.capture.release()

    def read(self, after_sequence, timeout=2.0):
        with self.condition:
            self.condition.wait_for(
                lambda: self.sequence > after_sequence or self.error is not None,
                timeout=timeout,
            )
            if self.error is not None:
                raise RuntimeError(str(self.error)) from self.error
            if self.sequence <= after_sequence:
                raise RuntimeError("Camera timed out. Check permissions or try --camera 1.")
            return self.latest

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=2.0)
        # Only the reader releases VideoCapture; releasing during a native read
        # from a second thread can crash some camera backends.
