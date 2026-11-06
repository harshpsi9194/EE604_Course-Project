from dataclasses import replace
import math
from types import SimpleNamespace

import pytest

from imouse.core import Calibration, Config, Controller, Features, OneEuro, extract_features


OPEN = Features(0.5, 0.5, 0.3, 0.3, 0.04, 0)
CAL = Calibration(0.5, 0.5, 0.3, 0.3, 0)


def armed(config=None):
    controller = Controller(CAL, config=config, active=True)
    controller.step(OPEN, 0)
    controller.step(OPEN, 0.2)
    return controller


@pytest.mark.parametrize("eye", ["left", "right"])
def test_deliberate_wink_clicks_once_on_release_and_freezes_pointer(eye):
    c = armed()
    shut = replace(OPEN, **{eye: 0.05}, x=0.8)
    for t in (0.3, 0.4, 0.5):
        result = c.step(shut, t)
        assert result.cursor is None and result.click is None
    result = c.step(OPEN, 0.6)
    assert result.click == eye and result.cursor is None
    assert c.step(OPEN, 0.7).click is None
    assert c.step(OPEN, 0.8).cursor is not None


def test_bilateral_blink_with_asymmetric_opening_never_clicks():
    c = armed()
    for t, f in [(0.3, replace(OPEN, left=0.05)),
                 (0.35, replace(OPEN, left=0.05, right=0.05)),
                 (0.55, replace(OPEN, right=0.05)), (0.65, OPEN)]:
        assert c.step(f, t).click is None


@pytest.mark.parametrize("duration", [0.05, 1.2])
def test_too_short_or_too_long_wink_is_ignored(duration):
    c = armed()
    t = 0.3
    while t < 0.3 + duration:
        c.step(replace(OPEN, left=0.05), t)
        t += min(0.05, duration)
    assert c.step(OPEN, 0.3 + duration).click is None


def test_tracking_loss_cancels_pending_wink_and_rearms():
    c = armed()
    c.step(replace(OPEN, left=0.05), 0.3)
    assert c.step(None, 0.5).cursor is None
    assert c.step(OPEN, 0.6).click is None
    assert c.step(OPEN, 0.6).cursor is None
    assert c.step(OPEN, 0.8).cursor is not None


def test_long_processing_stall_cancels_partial_wink():
    c = armed()
    c.step(replace(OPEN, left=0.05), 0.3)
    result = c.step(OPEN, 1.0)
    assert result.click is None and result.cursor is None


def test_hysteresis_does_not_release_eye_at_intermediate_openness():
    c = armed()
    c.step(replace(OPEN, left=0.1), 0.3)
    assert c.step(replace(OPEN, left=0.19), 0.5).click is None
    assert c.step(replace(OPEN, left=0.26), 0.6).click == "left"


def test_cooldown_prevents_rapid_second_click():
    c = armed()
    c.step(replace(OPEN, left=0.05), 0.3)
    assert c.step(OPEN, 0.5).click == "left"
    c.step(OPEN, 0.63)
    c.step(replace(OPEN, right=0.05), 0.64)
    assert c.step(OPEN, 0.80).click is None


def test_swapping_winks():
    c = armed(Config(swap_winks=True))
    c.step(replace(OPEN, left=0.05), 0.3)
    assert c.step(OPEN, 0.5).click == "right"


def test_mouth_toggle_requires_hold_and_only_fires_once_until_closed():
    c = armed()
    opened = replace(OPEN, mouth=0.7)
    flags = [c.step(opened, t / 10).toggled for t in range(3, 21)]
    assert sum(flags) == 1 and not c.active
    c.step(OPEN, 2.1)
    flags = [c.step(opened, t / 10).toggled for t in range(22, 32)]
    assert sum(flags) == 1 and c.active


def test_brief_mouth_opening_does_not_toggle():
    c = armed()
    c.step(replace(OPEN, mouth=0.7), 0.3)
    assert not c.step(OPEN, 0.5).toggled
    assert c.active


def test_paused_controller_never_dispatches_gestures():
    c = Controller(CAL)
    for t in range(10):
        result = c.step(replace(OPEN, x=0.8, roll=20, left=0.05), t / 10)
        assert result.cursor is None and result.click is None and result.scroll == 0


@pytest.mark.parametrize("tilt,expected", [(15, -3), (-15, 3)])
def test_scroll_hold_repeat_hysteresis_and_cursor_freeze(tilt, expected):
    c = armed()
    assert c.step(replace(OPEN, roll=tilt), 0.3).scroll == 0
    result = c.step(replace(OPEN, roll=tilt), 0.5)
    assert result.scroll == expected and result.cursor is None
    assert c.step(replace(OPEN, roll=tilt), 0.6).scroll == 0
    assert c.step(replace(OPEN, roll=math.copysign(9, tilt)), 0.8).scroll == expected
    assert c.step(OPEN, 0.9).cursor is not None


def test_neutral_roll_calibration_is_subtracted():
    c = Controller(replace(CAL, roll=10), active=True)
    f = replace(OPEN, roll=10)
    c.step(f, 0)
    assert c.step(f, 0.2).scroll == 0


def test_screen_bounds_avoid_failsafe_corners():
    c = armed(Config(smoothing=False))
    for x, y in [(0, 0), (1, 1), (0, 1), (1, 0)]:
        result = c.step(replace(OPEN, x=x, y=y), 0.3)
        assert 2 <= result.cursor[0] <= 1917
        assert 2 <= result.cursor[1] <= 1077


def test_one_euro_reduces_stationary_jitter_and_resets():
    f = OneEuro()
    data = [100 + (-1)**i * 3 for i in range(100)]
    filtered = [f(v, i / 30) for i, v in enumerate(data)]
    assert max(filtered[30:]) - min(filtered[30:]) < 3
    f.reset()
    assert f(42, 10) == 42


def test_speed_adaptive_filter_responds_faster_than_fixed_filter():
    adaptive, fixed = OneEuro(beta=0.007), OneEuro(beta=0)
    adaptive(0, 0)
    fixed(0, 0)
    assert adaptive(500, 1/30) > fixed(500, 1/30)


def test_calibration_is_robust_to_small_number_of_outliers():
    samples = [OPEN] * 43 + [replace(OPEN, x=0.9)] * 2
    assert Calibration.from_samples(samples).x == 0.5
    with pytest.raises(ValueError):
        Calibration.from_samples([OPEN])


def make_landmarks(scale=1, angle=0, width=640, height=480):
    points = {33:(200,180), 133:(240,180), 160:(212,174), 144:(212,186),
              158:(228,174), 153:(228,186), 362:(300,180), 263:(340,180),
              385:(312,174), 380:(312,186), 387:(328,174), 373:(328,186),
              61:(240,250), 291:(300,250), 13:(270,248), 14:(270,252),
              468:(220,180), 473:(320,180)}
    result = [SimpleNamespace(x=0.5, y=0.5) for _ in range(478)]
    radians = math.radians(angle)
    for index, (x,y) in points.items():
        x, y = (x-270)*scale, (y-200)*scale
        rx = x*math.cos(radians) - y*math.sin(radians) + 270
        ry = x*math.sin(radians) + y*math.cos(radians) + 200
        result[index] = SimpleNamespace(x=rx/width, y=ry/height)
    return result


@pytest.mark.parametrize("scale,angle,width,height", [(0.5,0,640,480), (1.5,0,640,480), (1,20,640,480), (1,0,1280,720)])
def test_geometric_ratios_are_scale_roll_and_aspect_invariant(scale, angle, width, height):
    f = extract_features(make_landmarks(scale, angle, width, height), width, height)
    assert f.left == pytest.approx(0.3)
    assert f.right == pytest.approx(0.3)
    assert f.mouth == pytest.approx(4/60)
    assert f.roll == pytest.approx(angle)


def test_invalid_meshes_do_not_produce_actions():
    assert extract_features([], 640, 480) is None
    points = make_landmarks()
    points[468].x = float("nan")
    assert extract_features(points, 640, 480) is None
