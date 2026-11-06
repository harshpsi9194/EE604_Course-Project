import sys
from types import SimpleNamespace
import threading
import time

import pytest

from imouse.app import Mouse, main
from imouse.capture import LatestFrameCamera
from imouse.core import Decision


def test_mouse_has_no_default_delay_and_preserves_fail_safe(monkeypatch):
    calls = []
    api = SimpleNamespace(PAUSE=0.1, FAILSAFE=False, size=lambda: (1920,1080),
        failSafeCheck=lambda: calls.append("check"),
        moveTo=lambda *args, **kwargs: calls.append(("move", args)),
        click=lambda **kwargs: calls.append(("click", kwargs)),
        scroll=lambda value: calls.append(("scroll", value)))
    monkeypatch.setitem(sys.modules, "pyautogui", api)
    mouse = Mouse()
    assert api.PAUSE == 0 and api.FAILSAFE
    mouse.dispatch(Decision(cursor=(20,30)))
    mouse.dispatch(Decision(cursor=(20,30)))
    mouse.dispatch(Decision(click="right"))
    assert len([c for c in calls if isinstance(c, tuple) and c[0] == "move"]) == 1
    assert ("click", {"button":"right"}) in calls
    assert calls.count("check") == 3


def test_dry_run_does_not_import_desktop_api(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyautogui", None)
    Mouse(dry_run=True).dispatch(Decision(cursor=(10,20), click="left", scroll=3))


@pytest.mark.parametrize("argv", [["--video", "test.mp4"], ["--no-preview"], ["--gain-x", "0"], ["--max-frames", "-1"]])
def test_invalid_cli_combinations_exit_before_hardware_access(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_latest_frame_capture_drops_old_frames_and_releases_camera():
    class FakeCamera:
        released = False
        n = 0
        def read(self):
            time.sleep(0.005)
            self.n += 1
            return True, self.n
        def release(self):
            self.released = True
    camera = FakeCamera()
    reader = LatestFrameCamera(camera)
    first = reader.read(0)
    with reader.condition:
        assert reader.condition.wait_for(lambda: reader.sequence >= first[0] + 4, timeout=1)
    second = reader.read(first[0])
    reader.close()
    assert second[0] >= first[0] + 4
    assert second[2] == second[0]
    assert camera.released and not reader.thread.is_alive()


def test_camera_failure_is_reported_and_released():
    camera = SimpleNamespace(read=lambda: (False,None), release=lambda: None)
    reader = LatestFrameCamera(camera)
    with pytest.raises(RuntimeError, match="stopped returning"):
        reader.read(0)
    reader.close()
