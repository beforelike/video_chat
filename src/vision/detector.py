"""YOLO 物体检测模块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class DetectedObject:
    """检测结果。"""

    label: str
    confidence: float
    box: Tuple[int, int, int, int]
    position: str


# 类别置信度阈值（遵循需求文档 NFR-01）
DEFAULT_CONFIDENCE = 0.5
CLASS_THRESHOLDS = {
    "person": 0.6,
    "cell phone": 0.55,
}


class ObjectDetector:
    """使用 YOLO11n 进行 COCO 80 类物体检测。"""

    def __init__(self, model_path: str = "yolo11n.pt") -> None:
        self._model = YOLO(model_path)

    def detect(self, frame: np.ndarray) -> List[DetectedObject]:
        """检测画面中的物体，返回过滤后的结果。"""
        results = self._model(frame, verbose=False)
        if not results:
            return []

        detections: List[DetectedObject] = []
        frame_width = frame.shape[1]

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                label = result.names[class_id]
                threshold = CLASS_THRESHOLDS.get(label, DEFAULT_CONFIDENCE)

                if confidence < threshold:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                position = self._calc_position((x1 + x2) // 2, frame_width)
                detections.append(
                    DetectedObject(
                        label=label,
                        confidence=confidence,
                        box=(x1, y1, x2, y2),
                        position=position,
                    )
                )

        return detections

    @staticmethod
    def _calc_position(center_x: int, frame_width: int) -> str:
        """根据检测框中心 x 坐标划分 left / center / right。"""
        if frame_width <= 0:
            return "center"

        ratio = center_x / frame_width
        if ratio < 0.33:
            return "left"
        if ratio > 0.66:
            return "right"
        return "center"

    def draw_overlay(
        self,
        frame: np.ndarray,
        detections: List[DetectedObject],
    ) -> np.ndarray:
        """在画面上绘制检测框与标签。"""
        output = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = det.box
            color = (0, 200, 100)
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            label_text = f"{det.label} {det.confidence:.2f} ({det.position})"
            cv2.putText(
                output,
                label_text,
                (x1, max(y1 - 8, 16)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )

        return output
