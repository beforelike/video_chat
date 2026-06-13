"""VisionEventManager 单元测试。"""

from __future__ import annotations

import sys
import os

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.vision.detector import DetectedObject
from src.vision.events import APPEAR_FRAMES, EVENT_COOLDOWN_SEC, VisionEventManager
from src.vision.gesture import GestureResult
from src.vision.motion import MotionState


def _make_person_det() -> DetectedObject:
    return DetectedObject(
        label="person",
        confidence=0.85,
        box=(100, 100, 300, 400),
        position="center",
    )


def _neutral_motion(**kwargs) -> MotionState:
    defaults = dict(
        motion="none",
        camera_blocked=False,
        person_visible=True,
        person_count=1,
        person_position="center",
        person_distance="near",
        scene_motion=False,
    )
    defaults.update(kwargs)
    return MotionState(**defaults)


def _no_gesture() -> GestureResult:
    return GestureResult(gesture="none", confidence=0.0)


class TestVisionEventManager:
    def test_object_appear_requires_multi_frame(self):
        mgr = VisionEventManager()
        det = _make_person_det()

        for i in range(APPEAR_FRAMES - 1):
            ctx = mgr.update([det], _no_gesture(), _neutral_motion(), now=float(i))
            assert ctx.objects == []

        ctx = mgr.update([det], _no_gesture(), _neutral_motion(), now=float(APPEAR_FRAMES))
        assert len(ctx.objects) == 1
        assert ctx.objects[0]["name"] == "person"

    def test_event_cooldown_blocks_repeat(self):
        mgr = VisionEventManager()
        motion_enter = _neutral_motion(motion="user_entered")

        mgr.update([], _no_gesture(), motion_enter, now=0.0)
        events1 = mgr.pop_proactive_events()
        assert len(events1) == 1

        mgr.update([], _no_gesture(), motion_enter, now=1.0)
        events2 = mgr.pop_proactive_events()
        assert len(events2) == 0

        assert mgr.is_on_cooldown("user_entered", now=5.0)
        assert not mgr.is_on_cooldown("user_entered", now=EVENT_COOLDOWN_SEC + 1)

    def test_gesture_confirmed_after_streak(self):
        mgr = VisionEventManager()
        wave = GestureResult(gesture="wave", confidence=0.9)

        for i in range(3):
            ctx = mgr.update([], wave, _neutral_motion(), now=float(i))

        assert ctx.gesture == "wave"

    def test_context_json_fields(self):
        mgr = VisionEventManager()
        det = DetectedObject("cup", 0.8, (50, 50, 150, 150), "left")
        for i in range(APPEAR_FRAMES):
            ctx = mgr.update([det], _no_gesture(), _neutral_motion(), now=float(i))

        d = ctx.to_dict()
        assert "timestamp" in d
        assert "objects" in d
        assert d["objects"][0]["name"] == "cup"
