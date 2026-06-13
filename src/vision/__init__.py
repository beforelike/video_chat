"""视觉感知模块：摄像头采集、物体检测、手势/运动/事件管理。"""

from src.vision.capture import VideoCaptureManager
from src.vision.detector import ObjectDetector
from src.vision.events import VisionContext, VisionEventManager
from src.vision.gesture import GestureDetector, GestureResult
from src.vision.motion import MotionEventDetector, MotionState

__all__ = [
    "VideoCaptureManager",
    "ObjectDetector",
    "GestureDetector",
    "GestureResult",
    "MotionEventDetector",
    "MotionState",
    "VisionEventManager",
    "VisionContext",
]
