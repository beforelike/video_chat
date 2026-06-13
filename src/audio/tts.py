"""语音合成（TTS）模块。"""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from typing import Optional

import edge_tts

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


class TTSEngine:
    """使用 edge-tts 生成语音。"""

    def __init__(self, voice: str = DEFAULT_VOICE) -> None:
        self._voice = voice
        self._speaking = False
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def stop(self) -> None:
        """请求停止当前播报。"""
        self._stop_flag.set()

    async def _synthesize(self, text: str, output_path: str) -> None:
        communicate = edge_tts.Communicate(text, self._voice)
        await communicate.save(output_path)

    def synthesize(self, text: str) -> Optional[str]:
        """将文本合成为音频文件，返回文件路径。"""
        if not text.strip():
            return None

        self._stop_flag.clear()
        with self._lock:
            self._speaking = True

        try:
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            asyncio.run(self._synthesize(text, path))
            if self._stop_flag.is_set():
                if os.path.exists(path):
                    os.remove(path)
                return None
            return path
        except Exception:
            return None
        finally:
            with self._lock:
                self._speaking = False
