"""MediaPipe 手势识别模块。"""

from __future__ import annotations

import os
import urllib.request
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# MediaPipe 手势名 → 项目事件名
_GESTURE_MAP = {
    "Thumb_Up": "thumbs_up",
    "Open_Palm": "open_palm",
    "Victory": "wave",
    "Pointing_Up": "pointing",
}

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
)
_MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
_MODEL_PATH = os.path.join(_MODEL_DIR, "gesture_recognizer.task")

# 挥手检测：手腕水平位移阈值（归一化坐标）
_WAVE_HISTORY = 8
_WAVE_MIN_SWING = 0.08


@dataclass
class GestureResult:
    """手势识别结果。"""

    gesture: str  # none, wave, thumbs_up, open_palm, pointing
    confidence: float
    raw_label: str = "None"


class GestureDetector:
    """使用 MediaPipe Gesture Recognizer 识别预定义手势。"""

    def __init__(self) -> None:
        self._recognizer = self._create_recognizer()
        self._wrist_history: Deque[float] = deque(maxlen=_WAVE_HISTORY)

    @staticmethod
    def _ensure_model() -> str:
        """确保手势模型已下载。"""
        os.makedirs(_MODEL_DIR, exist_ok=True)
        if not os.path.exists(_MODEL_PATH):
            urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        return _MODEL_PATH

    def _create_recognizer(self) -> vision.GestureRecognizer:
        model_path = self._ensure_model()
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.GestureRecognizerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        return vision.GestureRecognizer.create_from_options(options)

    def detect(self, frame: np.ndarray) -> GestureResult:
        """识别画面中的手势。"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._recognizer.recognize(mp_image)

        if not result.gestures or not result.hand_landmarks:
            self._wrist_history.clear()
            return GestureResult(gesture="none", confidence=0.0)

        top_gesture = result.gestures[0][0]
        raw_label = top_gesture.category_name
        confidence = float(top_gesture.score)

        # 记录手腕水平位置用于挥手检测
        wrist = result.hand_landmarks[0][0]
        self._wrist_history.append(wrist.x)

        mapped = _GESTURE_MAP.get(raw_label, "none")
        if mapped == "open_palm" and self._is_waving():
            mapped = "wave"

        return GestureResult(
            gesture=mapped,
            confidence=confidence,
            raw_label=raw_label,
        )

    def _is_waving(self) -> bool:
        """根据手腕水平摆动判断挥手。"""
        if len(self._wrist_history) < _WAVE_HISTORY:
            return False
        xs = list(self._wrist_history)
        swing = max(xs) - min(xs)
        direction_changes = 0
        for i in range(1, len(xs) - 1):
            prev_delta = xs[i] - xs[i - 1]
            next_delta = xs[i + 1] - xs[i]
            if prev_delta * next_delta < 0:
                direction_changes += 1
        return swing >= _WAVE_MIN_SWING and direction_changes >= 2

    def draw_overlay(
        self,
        frame: np.ndarray,
        gesture: GestureResult,
    ) -> np.ndarray:
        """在画面上绘制手势提示。"""
        if gesture.gesture == "none":
            return frame

        output = frame.copy()
        labels = {
            "wave": "挥手 wave",
            "thumbs_up": "竖大拇指",
            "open_palm": "张开手掌",
            "pointing": "指向",
        }
        text = labels.get(gesture.gesture, gesture.gesture)
        cv2.putText(
            output,
            f"Gesture: {text} ({gesture.confidence:.2f})",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 200, 0),
            2,
            cv2.LINE_AA,
        )
        return output
