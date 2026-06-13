"""视觉感知模块：摄像头采集、物体检测、手势/运动检测。"""

from src.vision.capture import VideoCaptureManager
from src.vision.detector import ObjectDetector

__all__ = ["VideoCaptureManager", "ObjectDetector"]
