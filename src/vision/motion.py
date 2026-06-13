"""运动/遮挡/用户状态检测模块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np

from src.vision.detector import DetectedObject


@dataclass
class MotionState:
    """运动与用户状态。"""

    motion: str  # none, user_entered, user_left, camera_blocked, object_moved, scene_changed
    camera_blocked: bool
    person_visible: bool
    person_count: int
    person_position: str  # left, center, right, none
    person_distance: str  # near, medium, far
    scene_motion: bool


class MotionEventDetector:
    """OpenCV 背景差分 + 亮度/方差检测遮挡与用户进出。"""

    def __init__(self) -> None:
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=120, varThreshold=40, detectShadows=False
        )
        self._prev_person_visible = False
        self._blocked_frames = 0
        self._clear_frames = 0

    def detect(
        self,
        frame: np.ndarray,
        detections: Optional[List[DetectedObject]] = None,
    ) -> MotionState:
        """分析画面运动、遮挡与用户可见性。"""
        detections = detections or []
        persons = [d for d in detections if d.label == "person"]
        person_visible = len(persons) > 0
        person_count = len(persons)

        person_position = "none"
        person_distance = "far"
        if persons:
            main_person = max(persons, key=lambda p: (p.box[2] - p.box[0]) * (p.box[3] - p.box[1]))
            person_position = main_person.position
            box_area = (main_person.box[2] - main_person.box[0]) * (
                main_person.box[3] - main_person.box[1]
            )
            frame_area = frame.shape[0] * frame.shape[1]
            ratio = box_area / max(frame_area, 1)
            if ratio > 0.15:
                person_distance = "near"
            elif ratio > 0.05:
                person_distance = "medium"
            else:
                person_distance = "far"

        camera_blocked = self._detect_camera_blocked(frame)
        scene_motion = self._detect_scene_motion(frame)

        motion = "none"
        if camera_blocked:
            motion = "camera_blocked"
        elif person_visible and not self._prev_person_visible:
            motion = "user_entered"
        elif not person_visible and self._prev_person_visible:
            motion = "user_left"
        elif scene_motion and not camera_blocked:
            motion = "object_moved"

        self._prev_person_visible = person_visible

        return MotionState(
            motion=motion,
            camera_blocked=camera_blocked,
            person_visible=person_visible,
            person_count=person_count,
            person_position=person_position,
            person_distance=person_distance,
            scene_motion=scene_motion,
        )

    def _detect_camera_blocked(self, frame: np.ndarray) -> bool:
        """检测摄像头是否被遮挡（低亮度或低方差）。"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        variance = float(np.var(gray))

        blocked_now = mean_brightness < 35 or variance < 500

        if blocked_now:
            self._blocked_frames += 1
            self._clear_frames = 0
        else:
            self._clear_frames += 1
            self._blocked_frames = 0

        # 连续 3 帧确认遮挡，连续 5 帧确认恢复
        if self._blocked_frames >= 3:
            return True
        if self._clear_frames >= 5:
            return False
        return blocked_now

    def _detect_scene_motion(self, frame: np.ndarray) -> bool:
        """背景差分检测画面运动。"""
        fg_mask = self._bg_subtractor.apply(frame)
        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = frame.shape[0] * frame.shape[1]
        ratio = motion_pixels / max(total_pixels, 1)
        return ratio > 0.02
