"""摄像头采集与降帧分发。"""

from __future__ import annotations

import time
from typing import Dict, Optional

import cv2
import numpy as np


class VideoCaptureManager:
    """管理摄像头取帧，并按模块需求降帧分发。"""

    def __init__(self, device_id: int = 0) -> None:
        self._device_id = device_id
        self._cap: Optional[cv2.VideoCapture] = None
        self._last_frame_time: Dict[str, float] = {}
        self._running = False

    def start(self) -> None:
        """打开摄像头。"""
        if self._running:
            return

        self._cap = cv2.VideoCapture(self._device_id)
        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开摄像头设备 {self._device_id}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._running = True

    def read_frame(self) -> np.ndarray:
        """读取一帧画面，用于实时显示。"""
        if not self._running or self._cap is None:
            raise RuntimeError("摄像头未启动，请先调用 start()")

        ret, frame = self._cap.read()
        if not ret or frame is None:
            raise RuntimeError("读取摄像头帧失败")

        return frame

    def get_frame_for(self, module: str, target_fps: int) -> Optional[np.ndarray]:
        """按目标帧率为指定模块降帧取帧。"""
        if target_fps <= 0:
            return None

        now = time.monotonic()
        interval = 1.0 / target_fps
        last_time = self._last_frame_time.get(module, 0.0)

        if now - last_time < interval:
            return None

        self._last_frame_time[module] = now
        return self.read_frame()

    def stop(self) -> None:
        """释放摄像头资源。"""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running
