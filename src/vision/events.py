"""视觉事件管理与状态缓存。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.vision.detector import DetectedObject
from src.vision.gesture import GestureResult
from src.vision.motion import MotionState

APPEAR_FRAMES = 5
DISAPPEAR_FRAMES = 10
EVENT_COOLDOWN_SEC = 10.0


@dataclass
class VisionContext:
    """结构化视觉上下文。"""

    timestamp: str = ""
    person: Dict[str, Any] = field(default_factory=dict)
    objects: List[Dict[str, Any]] = field(default_factory=list)
    gesture: str = "none"
    face_state: str = "neutral"
    pose: str = "unknown"
    motion: str = "none"
    camera_blocked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "person": self.person,
            "objects": self.objects,
            "gesture": self.gesture,
            "face_state": self.face_state,
            "pose": self.pose,
            "motion": self.motion,
            "camera_blocked": self.camera_blocked,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


@dataclass
class ProactiveEvent:
    """待播报的主动反馈事件。"""

    event_type: str
    message_key: str
    timestamp: str


class VisionEventManager:
    """多帧确认、事件冷却、状态合并。"""

    def __init__(self) -> None:
        self._object_tracker: Dict[str, Dict[str, Any]] = {}
        self._gesture_streak: Dict[str, int] = {}
        self._current_gesture = "none"
        self._motion_cooldown: Dict[str, float] = {}
        self._event_cooldown: Dict[str, float] = {}
        self._event_log: List[str] = []
        self._proactive_queue: List[ProactiveEvent] = []
        self._context = VisionContext()
        self._last_monotonic = 0.0

    @property
    def context(self) -> VisionContext:
        return self._context

    @property
    def event_log(self) -> List[str]:
        return list(self._event_log)

    def pop_proactive_events(self) -> List[ProactiveEvent]:
        """取出并清空待播报事件队列。"""
        events = list(self._proactive_queue)
        self._proactive_queue.clear()
        return events

    def update(
        self,
        detections: List[DetectedObject],
        gesture: GestureResult,
        motion: MotionState,
        now: Optional[float] = None,
    ) -> VisionContext:
        """合并各检测器输出，更新 VisionContext。"""
        import time

        mono = now if now is not None else time.monotonic()
        self._last_monotonic = mono
        ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

        confirmed_objects = self._update_objects(detections, mono)
        confirmed_gesture = self._update_gesture(gesture, mono)
        self._update_motion(motion, mono)

        self._context = VisionContext(
            timestamp=ts,
            person={
                "visible": motion.person_visible,
                "count": motion.person_count,
                "position": motion.person_position,
                "distance": motion.person_distance,
            },
            objects=confirmed_objects,
            gesture=confirmed_gesture,
            face_state="neutral",
            pose="unknown",
            motion=motion.motion if motion.motion != "none" else "none",
            camera_blocked=motion.camera_blocked,
        )

        # 运动事件冷却后触发主动反馈
        if motion.motion in ("user_entered", "user_left", "camera_blocked"):
            self._maybe_emit_proactive(motion.motion, ts, mono)

        if confirmed_gesture in ("wave", "thumbs_up", "open_palm"):
            self._maybe_emit_proactive(confirmed_gesture, ts, mono)

        return self._context

    def _update_objects(
        self,
        detections: List[DetectedObject],
        now: float,
    ) -> List[Dict[str, Any]]:
        """多帧确认物体出现/消失。"""
        seen_keys = set()
        for det in detections:
            key = f"{det.label}_{det.position}"
            seen_keys.add(key)
            tracker = self._object_tracker.setdefault(
                key,
                {"appear": 0, "disappear": 0, "confirmed": False, "det": det},
            )
            tracker["appear"] += 1
            tracker["disappear"] = 0
            tracker["det"] = det

            if not tracker["confirmed"] and tracker["appear"] >= APPEAR_FRAMES:
                tracker["confirmed"] = True
                self._log_event(now, f"检测到 {det.label} ({det.position})")

        for key, tracker in list(self._object_tracker.items()):
            if key in seen_keys:
                continue
            tracker["disappear"] += 1
            tracker["appear"] = 0
            if tracker["confirmed"] and tracker["disappear"] >= DISAPPEAR_FRAMES:
                tracker["confirmed"] = False
                label = tracker["det"].label
                self._log_event(now, f"{label} 已离开画面")

        confirmed = []
        for key, tracker in self._object_tracker.items():
            if tracker["confirmed"]:
                det = tracker["det"]
                confirmed.append(
                    {
                        "name": det.label,
                        "confidence": round(det.confidence, 2),
                        "position": det.position,
                        "box": list(det.box),
                    }
                )
        return confirmed

    def _update_gesture(self, gesture: GestureResult, now: float) -> str:
        """手势多帧确认。"""
        label = gesture.gesture if gesture.confidence >= 0.5 else "none"
        if label == "none":
            self._gesture_streak.clear()
            self._current_gesture = "none"
            return "none"

        streak = self._gesture_streak.get(label, 0) + 1
        self._gesture_streak = {label: streak}

        if streak >= 3 and label != self._current_gesture:
            self._current_gesture = label
            self._log_event(now, f"手势: {label}")
        return self._current_gesture

    def _update_motion(self, motion: MotionState, now: float) -> None:
        """记录运动事件日志。"""
        if motion.motion == "none":
            return
        if motion.motion == "camera_blocked":
            self._log_event(now, "摄像头被遮挡")
        elif motion.motion == "user_entered":
            self._log_event(now, "用户进入画面")
        elif motion.motion == "user_left":
            self._log_event(now, "用户离开画面")
        elif motion.motion == "object_moved":
            self._log_event(now, "画面中有运动")

    def _maybe_emit_proactive(self, event_type: str, ts: str, now: float) -> None:
        """同类事件冷却期内不重复播报。"""
        last = self._event_cooldown.get(event_type)
        if last is not None and now - last < EVENT_COOLDOWN_SEC:
            return
        self._event_cooldown[event_type] = now
        self._proactive_queue.append(
            ProactiveEvent(event_type=event_type, message_key=event_type, timestamp=ts)
        )

    def _log_event(self, now: float, message: str) -> None:
        """写入事件日志（带时间戳）。"""
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"{ts}  {message}"
        self._event_log.append(entry)
        if len(self._event_log) > 100:
            self._event_log = self._event_log[-100:]

    def is_on_cooldown(self, event_type: str, now: Optional[float] = None) -> bool:
        """检查事件是否在冷却期（供测试使用）。"""
        import time

        mono = now if now is not None else time.monotonic()
        last = self._event_cooldown.get(event_type)
        if last is None:
            return False
        return mono - last < EVENT_COOLDOWN_SEC
