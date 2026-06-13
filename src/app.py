"""EdgeVision Talker Gradio 应用入口。"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import List, Tuple

import cv2
import gradio as gr
import numpy as np
from dotenv import load_dotenv

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.vision.capture import VideoCaptureManager
from src.vision.detector import DetectedObject, ObjectDetector

load_dotenv()

YOLO_TARGET_FPS = 5
DISPLAY_FPS = 30


class VisionApp:
    """摄像头 + YOLO 检测 + Gradio 预览。"""

    def __init__(self) -> None:
        device_id = int(os.getenv("CAMERA_DEVICE_ID", "0"))
        self._capture = VideoCaptureManager(device_id=device_id)
        self._detector = ObjectDetector(model_path="yolo11n.pt")
        self._latest_detections: List[DetectedObject] = []
        self._display_frame = self._create_placeholder()
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    @staticmethod
    def _create_placeholder() -> np.ndarray:
        """生成占位画面。"""
        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            placeholder,
            "Click Start Camera",
            (120, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (200, 200, 200),
            2,
        )
        return cv2.cvtColor(placeholder, cv2.COLOR_BGR2RGB)

    def start(self) -> str:
        """启动摄像头与检测线程。"""
        if self._running:
            return "摄像头已在运行"

        try:
            self._capture.start()
        except RuntimeError as exc:
            return f"启动失败：{exc}"

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return "摄像头已开启，YOLO 物体检测运行中（5 FPS）"

    def stop(self) -> str:
        """停止摄像头与检测线程。"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._capture.stop()
        return "摄像头已关闭"

    def _capture_loop(self) -> None:
        """后台循环：取帧 + YOLO 检测。"""
        while self._running:
            try:
                display_frame = self._capture.read_frame()
                yolo_frame = self._capture.get_frame_for("yolo", YOLO_TARGET_FPS)

                detections = self._latest_detections
                if yolo_frame is not None:
                    detections = self._detector.detect(yolo_frame)
                    with self._lock:
                        self._latest_detections = detections

                overlay = self._detector.draw_overlay(display_frame, detections)
                rgb_frame = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)

                with self._lock:
                    self._display_frame = rgb_frame

            except RuntimeError:
                break

            time.sleep(1.0 / DISPLAY_FPS)

    def get_frame(self) -> np.ndarray:
        """获取当前带检测框的画面（供 Gradio 刷新）。"""
        with self._lock:
            return self._display_frame.copy()

    def get_detection_summary(self) -> str:
        """返回当前检测结果的文本摘要。"""
        with self._lock:
            detections = list(self._latest_detections)

        if not detections:
            return "暂无检测结果"

        lines = []
        for det in detections:
            lines.append(
                f"- {det.label}（置信度 {det.confidence:.2f}，位置 {det.position}）"
            )
        return "\n".join(lines)


def create_ui() -> gr.Blocks:
    """构建 Gradio 界面。"""
    app = VisionApp()

    with gr.Blocks(title="EdgeVision Talker") as demo:
        gr.Markdown(
            """
            # EdgeVision Talker
            **低成本实时视觉对话助手** — Day 1 MVP：摄像头预览 + YOLO 物体检测
            """
        )

        with gr.Row():
            with gr.Column(scale=2):
                video_output = gr.Image(
                    label="摄像头实时画面（含检测框）",
                    streaming=True,
                    height=480,
                )
            with gr.Column(scale=1):
                status_text = gr.Textbox(label="状态", interactive=False)
                detection_text = gr.Textbox(
                    label="当前检测结果",
                    lines=10,
                    interactive=False,
                )

        with gr.Row():
            start_btn = gr.Button("开启摄像头", variant="primary")
            stop_btn = gr.Button("关闭摄像头")

        start_btn.click(fn=app.start, outputs=status_text)
        stop_btn.click(fn=app.stop, outputs=status_text)

        demo.load(
            fn=app.get_frame,
            outputs=video_output,
            every=0.033,
        )
        demo.load(
            fn=app.get_detection_summary,
            outputs=detection_text,
            every=0.5,
        )

    return demo


def main() -> None:
    """应用入口。"""
    demo = create_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
