"""EdgeVision Talker Gradio 应用入口。"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from typing import List, Optional, Tuple

import cv2
import gradio as gr
import numpy as np
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.audio.tts import TTSEngine
from src.dialogue.manager import DialogueManager
from src.vision.capture import VideoCaptureManager
from src.vision.detector import DetectedObject, ObjectDetector
from src.vision.events import VisionEventManager
from src.vision.gesture import GestureDetector, GestureResult
from src.vision.motion import MotionEventDetector

load_dotenv()

YOLO_TARGET_FPS = 5
GESTURE_TARGET_FPS = 12
MOTION_TARGET_FPS = 10
DISPLAY_FPS = 30

# 浏览器端 Web Speech API（中文识别）
SPEECH_JS = """
function() {
    const textarea = document.querySelector('#user-speech textarea');
    if (!textarea) return [];
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
        alert('当前浏览器不支持 Web Speech API，请使用 Chrome 或手动输入文字。');
        return [];
    }
    const rec = new SR();
    rec.lang = 'zh-CN';
    rec.interimResults = false;
    rec.onresult = (e) => {
        const text = e.results[0][0].transcript;
        textarea.value = text;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    };
    rec.start();
    return [];
}
"""

STARTUP_MESSAGE = (
    "摄像头和麦克风已开启，我会根据画面和你的语音进行回应。"
    "你可以问「你看到什么」，或挥手、竖大拇指与我互动。"
)


class EdgeVisionApp:
    """完整视觉对话助手：摄像头 + 检测 + 手势 + 运动 + 对话 + TTS。"""

    def __init__(self) -> None:
        device_id = int(os.getenv("CAMERA_DEVICE_ID", "0"))
        self._capture = VideoCaptureManager(device_id=device_id)
        self._detector = ObjectDetector(model_path="yolo11n.pt")
        self._gesture = GestureDetector()
        self._motion = MotionEventDetector()
        self._events = VisionEventManager()
        self._dialogue = DialogueManager()
        self._tts = TTSEngine()

        self._latest_detections: List[DetectedObject] = []
        self._latest_gesture = GestureResult(gesture="none", confidence=0.0)
        self._display_frame = self._create_placeholder()
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

        self._camera_on = False
        self._mic_on = True
        self._last_user_text = ""
        self._last_assistant_reply = ""
        self._pending_audio: Optional[str] = None
        self._proactive_lock = threading.Lock()
        self._pending_proactive: List[str] = []

    @staticmethod
    def _create_placeholder() -> np.ndarray:
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

    def start(self) -> Tuple[str, str, str]:
        """启动摄像头与检测线程。"""
        if self._running:
            return self._device_status(), "摄像头已在运行", self._last_assistant_reply

        try:
            self._capture.start()
        except RuntimeError as exc:
            return self._device_status(), f"启动失败：{exc}", self._last_assistant_reply

        self._running = True
        self._camera_on = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        greeting = STARTUP_MESSAGE
        self._last_assistant_reply = greeting
        audio = self._tts.synthesize(greeting)
        self._pending_audio = audio

        status = "摄像头已开启，视觉感知运行中（YOLO 5fps / 手势 12fps / 运动 10fps）"
        return self._device_status(), status, greeting

    def stop(self) -> Tuple[str, str]:
        """停止摄像头。"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._capture.stop()
        self._camera_on = False
        return self._device_status(), "摄像头已关闭"

    def toggle_mic(self, enabled: bool) -> str:
        self._mic_on = enabled
        return self._device_status()

    def _capture_loop(self) -> None:
        while self._running:
            try:
                display_frame = self._capture.read_frame()
                yolo_frame = self._capture.get_frame_for("yolo", YOLO_TARGET_FPS)
                gesture_frame = self._capture.get_frame_for("gesture", GESTURE_TARGET_FPS)
                motion_frame = self._capture.get_frame_for("motion", MOTION_TARGET_FPS)

                detections = self._latest_detections
                if yolo_frame is not None:
                    detections = self._detector.detect(yolo_frame)
                    with self._lock:
                        self._latest_detections = detections

                gesture = self._latest_gesture
                if gesture_frame is not None:
                    gesture = self._gesture.detect(gesture_frame)
                    with self._lock:
                        self._latest_gesture = gesture

                if motion_frame is not None:
                    motion = self._motion.detect(motion_frame, detections)
                    ctx = self._events.update(detections, gesture, motion)
                    for evt in self._events.pop_proactive_events():
                        reply = self._dialogue.reply_for_event(evt.event_type)
                        if reply:
                            with self._proactive_lock:
                                self._pending_proactive.append(reply)

                overlay = self._detector.draw_overlay(display_frame, detections)
                overlay = self._gesture.draw_overlay(overlay, gesture)
                rgb_frame = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)

                with self._lock:
                    self._display_frame = rgb_frame

            except RuntimeError:
                break

            time.sleep(1.0 / DISPLAY_FPS)

    def get_frame(self) -> np.ndarray:
        with self._lock:
            return self._display_frame.copy()

    def get_event_log(self) -> str:
        logs = self._events.event_log
        if not logs:
            return "（暂无事件）"
        return "\n".join(logs[-30:])

    def get_vision_context_json(self) -> str:
        return self._events.context.to_json()

    def get_detection_summary(self) -> str:
        with self._lock:
            detections = list(self._latest_detections)
            gesture = self._latest_gesture

        if not detections and gesture.gesture == "none":
            return "暂无检测结果"

        lines = []
        for det in detections:
            lines.append(
                f"- {det.label}（置信度 {det.confidence:.2f}，位置 {det.position}）"
            )
        if gesture.gesture != "none":
            lines.append(f"- 手势: {gesture.gesture}（{gesture.confidence:.2f}）")
        return "\n".join(lines) if lines else "暂无检测结果"

    def _device_status(self) -> str:
        cam = "🟢 摄像头开启" if self._camera_on else "⚪ 摄像头关闭"
        mic = "🟢 麦克风就绪" if self._mic_on else "⚪ 麦克风关闭"
        llm = "🟢 LLM 已配置" if self._dialogue.llm_available else "⚪ LLM 未配置（模板模式）"
        return f"{cam}  |  {mic}  |  {llm}"

    def on_user_message(self, user_text: str) -> Tuple[str, str, Optional[str]]:
        """处理用户语音/文字输入，生成回复与 TTS。"""
        text = (user_text or "").strip()
        if not text:
            return self._last_user_text, self._last_assistant_reply, self._pending_audio

        if self._tts.is_speaking:
            self._tts.stop()

        ctx = self._events.context.to_dict()
        reply = self._dialogue.generate_reply(text, ctx)
        self._last_user_text = text
        self._last_assistant_reply = reply

        audio_path = None
        if reply and self._mic_on:
            audio_path = self._tts.synthesize(reply)
            self._pending_audio = audio_path

        return text, reply, audio_path

    def check_proactive(self) -> Tuple[str, Optional[str]]:
        """检查并播报主动反馈事件。"""
        with self._proactive_lock:
            if not self._pending_proactive:
                return self._last_assistant_reply, self._pending_audio
            reply = self._pending_proactive.pop(0)

        if self._tts.is_speaking:
            self._tts.stop()

        self._last_assistant_reply = reply
        audio_path = self._tts.synthesize(reply) if self._mic_on else None
        self._pending_audio = audio_path
        return reply, audio_path


def create_ui() -> gr.Blocks:
    app = EdgeVisionApp()

    with gr.Blocks(title="EdgeVision Talker") as demo:
        gr.Markdown(
            """
            # EdgeVision Talker
            **低成本实时视觉对话助手** — 本地视觉感知 + 模板/LLM 对话 + 语音播报
            """
        )

        device_status = gr.Textbox(
            label="设备状态",
            value=app._device_status(),
            interactive=False,
        )

        with gr.Row():
            with gr.Column(scale=2):
                video_output = gr.Image(
                    label="摄像头实时画面（含检测框与手势）",
                    streaming=True,
                    height=480,
                )
            with gr.Column(scale=1):
                event_log = gr.Textbox(
                    label="事件日志",
                    lines=12,
                    interactive=False,
                )
                context_json = gr.Textbox(
                    label="当前视觉上下文 (JSON)",
                    lines=12,
                    interactive=False,
                )
                detection_text = gr.Textbox(
                    label="当前检测摘要",
                    lines=6,
                    interactive=False,
                )

        with gr.Row():
            start_btn = gr.Button("开启摄像头", variant="primary")
            stop_btn = gr.Button("关闭摄像头")
            mic_toggle = gr.Checkbox(label="启用语音播报 (TTS)", value=True)

        gr.Markdown("### 语音对话")
        with gr.Row():
            user_speech = gr.Textbox(
                label="用户语音/文字",
                placeholder="输入文字，或点击下方「语音输入」使用浏览器识别…",
                elem_id="user-speech",
                scale=4,
            )
            send_btn = gr.Button("发送", variant="primary", scale=1)
            voice_btn = gr.Button("🎤 语音输入", scale=1)

        assistant_reply = gr.Textbox(label="助手回复", interactive=False)
        tts_audio = gr.Audio(label="助手语音播报", interactive=False)

        start_btn.click(
            fn=app.start,
            outputs=[device_status, detection_text, assistant_reply],
        )
        stop_btn.click(fn=app.stop, outputs=[device_status, detection_text])
        mic_toggle.change(fn=app.toggle_mic, inputs=mic_toggle, outputs=device_status)

        send_btn.click(
            fn=app.on_user_message,
            inputs=user_speech,
            outputs=[user_speech, assistant_reply, tts_audio],
        )
        user_speech.submit(
            fn=app.on_user_message,
            inputs=user_speech,
            outputs=[user_speech, assistant_reply, tts_audio],
        )
        voice_btn.click(fn=None, inputs=None, outputs=None, js=SPEECH_JS)

        video_timer = gr.Timer(0.033)
        log_timer = gr.Timer(0.5)
        proactive_timer = gr.Timer(1.0)

        video_timer.tick(fn=app.get_frame, outputs=video_output)
        log_timer.tick(
            fn=lambda: (app.get_event_log(), app.get_vision_context_json(), app.get_detection_summary()),
            outputs=[event_log, context_json, detection_text],
        )
        proactive_timer.tick(
            fn=app.check_proactive,
            outputs=[assistant_reply, tts_audio],
        )

    return demo


def main() -> None:
    demo = create_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
