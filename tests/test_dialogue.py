"""DialogueManager 单元测试。"""

from __future__ import annotations

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.dialogue.manager import DialogueManager, EVENT_TEMPLATES


MOCK_CONTEXT = {
    "timestamp": "2026-06-13T20:30:10+08:00",
    "person": {"visible": True, "count": 1, "position": "center", "distance": "near"},
    "objects": [
        {"name": "cup", "position": "left", "confidence": 0.77, "box": [120, 300, 200, 420]},
        {"name": "cell phone", "position": "right", "confidence": 0.82, "box": [420, 210, 520, 360]},
    ],
    "gesture": "none",
    "face_state": "neutral",
    "pose": "unknown",
    "motion": "none",
    "camera_blocked": False,
}


class TestDialogueManager:
    def setup_method(self):
        os.environ.pop("LLM_API_KEY", None)
        self.dm = DialogueManager()

    def test_wave_template_via_proactive(self):
        reply = self.dm.reply_for_event("wave")
        assert reply == EVENT_TEMPLATES["wave"]

    def test_thumbs_up_template(self):
        reply = self.dm.reply_for_event("thumbs_up")
        assert "确认手势" in reply

    def test_user_entered_template(self):
        reply = self.dm.reply_for_event("user_entered")
        assert "欢迎回来" in reply

    def test_user_left_template(self):
        reply = self.dm.reply_for_event("user_left")
        assert "离开" in reply

    def test_camera_blocked_template(self):
        reply = self.dm.reply_for_event("camera_blocked")
        assert "遮挡" in reply

    def test_vision_query_template(self):
        reply = self.dm.generate_reply("你看到桌上有什么？", MOCK_CONTEXT)
        assert "杯子" in reply
        assert "手机" in reply

    def test_vision_query_what_do_you_see(self):
        reply = self.dm.generate_reply("你看到什么？", MOCK_CONTEXT)
        assert "人" in reply or "杯子" in reply

    def test_gesture_in_vision_answer(self):
        ctx = {**MOCK_CONTEXT, "gesture": "wave"}
        reply = self.dm.generate_reply("你看到什么？", ctx)
        assert "挥手" in reply

    def test_camera_blocked_context(self):
        ctx = {**MOCK_CONTEXT, "camera_blocked": True}
        reply = self.dm.generate_reply("你看到什么？", ctx)
        assert "遮挡" in reply

    def test_empty_input_returns_empty(self):
        reply = self.dm.generate_reply("", MOCK_CONTEXT)
        assert reply == ""

    def test_fallback_without_llm(self):
        reply = self.dm.generate_reply("你觉得我现在心情怎么样？", MOCK_CONTEXT)
        assert "LLM" in reply or "听到" in reply

    def test_low_confidence_uncertainty(self):
        ctx = {
            **MOCK_CONTEXT,
            "objects": [{"name": "cup", "position": "left", "confidence": 0.45, "box": []}],
        }
        reply = self.dm.generate_reply("你看到什么？", ctx)
        assert "可能" in reply
