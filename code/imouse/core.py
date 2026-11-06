"""Geometry and gesture logic, independent of the webcam and operating system.

All timers use monotonic seconds. No sleeps or mouse calls belong in this file.
"""
from dataclasses import dataclass
import math
from statistics import median


@dataclass(frozen=True)
class Features:
    x: float
    y: float
    left: float
    right: float
    mouth: float
    roll: float


def extract_features(landmarks, width, height):
    """Use pixel distances so ratios do not depend on frame aspect ratio.

    Left/right preserve the original mirrored-input gesture groups. Iris centers
    are 468 and 473; 477 in the original code is an iris boundary point.
    """
    if len(landmarks) < 478 or width <= 0 or height <= 0:
        return None

    def point(index):
        p = landmarks[index]
        return p.x * width, p.y * height

    def distance(a, b):
        return math.dist(point(a), point(b))

    left_width = distance(33, 133)
    right_width = distance(362, 263)
    mouth_width = distance(61, 291)
    if min(left_width, right_width, mouth_width) < 2:
        return None
    left = (distance(160, 144) + distance(158, 153)) / (2 * left_width)
    right = (distance(385, 380) + distance(387, 373)) / (2 * right_width)
    # Eye corner midpoints avoid eyelid motion being mistaken for head tilt.
    a = tuple((u + v) / 2 for u, v in zip(point(33), point(133)))
    b = tuple((u + v) / 2 for u, v in zip(point(362), point(263)))
    if b[0] <= a[0]:
        return None
    roll = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    iris_a, iris_b = landmarks[468], landmarks[473]
    values = ((iris_a.x + iris_b.x) / 2, (iris_a.y + iris_b.y) / 2,
              left, right, distance(13, 14) / mouth_width, roll)
    if not all(math.isfinite(v) for v in values):
        return None
    if not (0 <= values[0] <= 1 and 0 <= values[1] <= 1):
        return None
    return Features(*values)


@dataclass(frozen=True)
class Calibration:
    x: float
    y: float
    left: float
    right: float
    roll: float

    @classmethod
    def from_samples(cls, samples):
        if len(samples) < 15:
            raise ValueError("Calibration needs at least 15 valid open-eye frames.")
        values = [median(getattr(s, field) for s in samples)
                  for field in ("x", "y", "left", "right", "roll")]
        if min(values[2:4]) < 0.12:
            raise ValueError("Keep both eyes open during calibration.")
        return cls(*values)


@dataclass(frozen=True)
class Config:
    gain_x: float = 4.0
    gain_y: float = 6.0
    close_ratio: float = 0.55
    reopen_ratio: float = 0.75
    wink_min: float = 0.15
    wink_max: float = 1.0
    click_cooldown: float = 0.35
    rearm_seconds: float = 0.12
    mouth_open: float = 0.45
    mouth_close: float = 0.28
    mouth_hold: float = 0.6
    scroll_enter: float = 12.0
    scroll_exit: float = 7.0
    scroll_hold: float = 0.18
    scroll_interval: float = 0.20
    scroll_steps: int = 3
    min_cutoff: float = 1.2
    beta: float = 0.007
    smoothing: bool = True
    swap_winks: bool = False


class OneEuro:
    """Speed-adaptive low-pass filter (Casiez, Roussel and Vogel, CHI 2012).

    This implementation uses screen pixels and seconds, so beta has pixel units.
    The derivative is computed from successive RAW input samples.
    """
    def __init__(self, min_cutoff=1.2, beta=0.007):
        self.min_cutoff, self.beta = min_cutoff, beta
        self.reset()

    def reset(self):
        self.t = self.raw = self.value = None
        self.derivative = 0.0

    @staticmethod
    def alpha(cutoff, dt):
        return 1.0 / (1.0 + 1.0 / (2.0 * math.pi * cutoff * dt))

    def __call__(self, value, now):
        if self.t is None:
            self.t, self.raw, self.value = now, value, value
            return value
        dt = max(now - self.t, 1e-6)
        velocity = (value - self.raw) / dt
        a = self.alpha(1.0, dt)
        self.derivative += a * (velocity - self.derivative)
        cutoff = self.min_cutoff + self.beta * abs(self.derivative)
        a = self.alpha(cutoff, dt)
        self.value += a * (value - self.value)
        self.t, self.raw = now, value
        return self.value


@dataclass
class Decision:
    cursor: tuple | None = None
    click: str | None = None
    scroll: int = 0
    toggled: bool = False
    status: str = "Tracking"


class Controller:
    """Blink rejection, wink release detection, and gesture-aware cursor freezing."""
    def __init__(self, calibration, screen_size=(1920, 1080), config=None, active=False):
        self.calibration = calibration
        self.width, self.height = screen_size
        self.config = config or Config()
        self.active = active
        self.filters = [OneEuro(self.config.min_cutoff, self.config.beta) for _ in range(2)]
        self.last_click = self.last_scroll = -math.inf
        self.last_seen = None
        self.last_cursor = None
        self.reset_tracking()

    def reset_tracking(self):
        self.closed = [False, False]
        self.ready = False
        self.open_since = None
        self.wink_eye = None
        self.wink_since = None
        self.mouth_since = None
        self.mouth_latched = False
        self.mouth_is_open = False
        self.scroll_direction = 0
        self.scroll_since = None
        for filt in self.filters:
            filt.reset()

    def toggle(self):
        self.active = not self.active
        self.reset_tracking()

    def step(self, features, now):
        result = Decision(status="Paused" if not self.active else "Tracking")
        if features is None:
            self.reset_tracking()
            self.last_seen = None
            result.status = "No face - movement stopped"
            return result
        # A long stall must not turn an old partial gesture into a new action.
        if self.last_seen is not None and now - self.last_seen > 0.5:
            self.reset_tracking()
        self.last_seen = now
        c, cal = self.config, self.calibration

        threshold = c.mouth_close if self.mouth_is_open else c.mouth_open
        self.mouth_is_open = features.mouth > threshold
        if self.mouth_is_open:
            if self.mouth_since is None:
                self.mouth_since = now
            if not self.mouth_latched and now - self.mouth_since >= c.mouth_hold:
                self.active = not self.active
                self.mouth_latched = True
                result.toggled = True
            self.ready = False
            self.open_since = None
            self.wink_eye = self.wink_since = None
            self.scroll_direction = 0
            result.status = ("Active" if self.active else "Paused") + " - close mouth"
            return result
        self.mouth_since, self.mouth_latched = None, False
        if not self.active:
            return result

        for i, ratio in enumerate((features.left / cal.left, features.right / cal.right)):
            self.closed[i] = ratio < (c.reopen_ratio if self.closed[i] else c.close_ratio)
        both_open = not any(self.closed)
        both_closed = all(self.closed)

        if not both_open:
            self.open_since = None
            self.scroll_direction = 0
            # Any bilateral closure cancels the WHOLE gesture, even if one eye
            # opens first. This prevents natural blinks becoming clicks.
            if both_closed:
                self.ready = False
                self.wink_eye = self.wink_since = None
            elif self.ready:
                eye = "left" if self.closed[0] else "right"
                if self.wink_eye is None:
                    self.wink_eye, self.wink_since = eye, now
                elif eye != self.wink_eye:
                    self.ready = False
                    self.wink_eye = self.wink_since = None
            result.status = "Eyes closed - cursor held"
            return result

        # Emit a single click after a deliberate unilateral wink is released.
        if self.wink_eye is not None:
            duration = now - self.wink_since
            if c.wink_min <= duration <= c.wink_max and now - self.last_click >= c.click_cooldown:
                result.click = self.wink_eye
                if c.swap_winks:
                    result.click = "right" if result.click == "left" else "left"
                self.last_click = now
            self.wink_eye = self.wink_since = None
            self.ready = False
            self.open_since = now
        if not self.ready:
            if self.open_since is None:
                self.open_since = now
            if now - self.open_since < c.rearm_seconds:
                result.status = "Hold eyes open"
                return result
            self.ready = True
            for filt in self.filters:
                filt.reset()

        tilt = features.roll - cal.roll
        direction = -1 if tilt > c.scroll_enter else (1 if tilt < -c.scroll_enter else 0)
        if self.scroll_direction and abs(tilt) > c.scroll_exit:
            # Keep the current direction within the hysteresis band.
            direction = 1 if tilt < 0 else -1
        if direction:
            if direction != self.scroll_direction:
                self.scroll_direction, self.scroll_since = direction, now
            if now - self.scroll_since >= c.scroll_hold and now - self.last_scroll >= c.scroll_interval:
                result.scroll = direction * c.scroll_steps
                self.last_scroll = now
            result.status = "Scroll up" if direction > 0 else "Scroll down"
            return result
        if self.scroll_direction:
            for filt in self.filters:
                filt.reset()
        self.scroll_direction = 0

        # Preserve the original head-assisted iris-position mapping, with a
        # calibrated neutral center and gain to reach the whole screen.
        x = (0.5 + (features.x - cal.x) * c.gain_x) * (self.width - 1)
        y = (0.5 + (features.y - cal.y) * c.gain_y) * (self.height - 1)
        x = min(max(x, 2), self.width - 3)
        y = min(max(y, 2), self.height - 3)
        if c.smoothing:
            x, y = [f(v, now) for f, v in zip(self.filters, (x, y))]
        self.last_cursor = (round(x), round(y))
        result.cursor = self.last_cursor
        return result
