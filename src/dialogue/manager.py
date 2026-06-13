"""对话管理模块：规则模板 + LLM 路由。"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

# 手势/运动事件模板
EVENT_TEMPLATES: Dict[str, str] = {
    "wave": "我在，我看到你挥手了。",
    "thumbs_up": "收到，你做了确认手势。",
    "open_palm": "好的，我停下来了。",
    "user_entered": "欢迎回来，我又看到你了。",
    "user_left": "我看到你暂时离开了，我会等你回来。",
    "camera_blocked": "画面好像被遮挡了，我现在看不清。",
}

# 简单视觉问答关键词
VISION_QUERY_PATTERNS = [
    r"你看到什么",
    r"看见什么",
    r"桌上有什么",
    r"桌子上有什么",
    r"画面里有什么",
    r"有什么东西",
]

SYSTEM_PROMPT = """你是一个实时视觉对话助手 EdgeVision Talker。

规则：
1. 你不能声称自己直接理解整张画面或看到像素级细节。
2. 你只能根据系统提供的结构化视觉结果（VisionContext）进行回答。
3. 如果视觉结果置信度低或状态为 unknown，要使用「可能」「看起来像」等不确定性表达。
4. 你的回答要简短自然，优先回应用户当前问题。
5. 普通回复 1 句话，解释类回复最多 2-3 句话。
6. 不要编造 VisionContext 中不存在的物体或状态。"""


class DialogueManager:
    """根据用户文本与视觉上下文生成回复。"""

    def __init__(self) -> None:
        self._api_key = os.getenv("LLM_API_KEY", "").strip()
        self._base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self._model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self._client: Optional[OpenAI] = None
        if self._api_key and self._api_key != "your_api_key_here":
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)

    @property
    def llm_available(self) -> bool:
        return self._client is not None

    def generate_reply(
        self,
        user_text: str,
        vision_context: Dict[str, Any],
        proactive_event: Optional[str] = None,
    ) -> str:
        """生成助手回复。"""
        if proactive_event and proactive_event in EVENT_TEMPLATES:
            return EVENT_TEMPLATES[proactive_event]

        text = (user_text or "").strip()
        if not text:
            return ""

        # 手势关键词
        gesture = vision_context.get("gesture", "none")
        if self._matches_gesture_query(text) and gesture in EVENT_TEMPLATES:
            return EVENT_TEMPLATES[gesture]

        # 简单视觉问答 → 模板
        if self._is_vision_query(text):
            return self._template_vision_answer(vision_context)

        # 运动/遮挡状态问答
        motion_reply = self._template_motion_answer(text, vision_context)
        if motion_reply:
            return motion_reply

        # 复杂问题 → LLM
        if self._client is not None:
            return self._llm_reply(text, vision_context)

        return self._fallback_reply(vision_context)

    def reply_for_event(self, event_type: str) -> str:
        """主动事件播报话术。"""
        return EVENT_TEMPLATES.get(event_type, "")

    @staticmethod
    def _matches_gesture_query(text: str) -> bool:
        keywords = ["挥手", "手势", "大拇指", "手掌"]
        return any(k in text for k in keywords)

    @staticmethod
    def _is_vision_query(text: str) -> bool:
        return any(re.search(p, text) for p in VISION_QUERY_PATTERNS)

    def _template_vision_answer(self, ctx: Dict[str, Any]) -> str:
        """模板填充：列举画面中的物体。"""
        parts: List[str] = []
        person = ctx.get("person", {})
        objects = ctx.get("objects", [])
        gesture = ctx.get("gesture", "none")
        blocked = ctx.get("camera_blocked", False)

        if blocked:
            return EVENT_TEMPLATES["camera_blocked"]

        if person.get("visible"):
            count = person.get("count", 0)
            if count == 1:
                parts.append("我看到一个人在画面中")
            elif count > 1:
                parts.append(f"我看到画面中有 {count} 个人")

        if objects:
            obj_names = []
            for obj in objects:
                name = obj.get("name", "")
                pos = obj.get("position", "")
                conf = obj.get("confidence", 1.0)
                if conf < 0.6:
                    obj_names.append(f"可能有一个{self._cn_name(name)}（{pos}）")
                else:
                    obj_names.append(f"一个{self._cn_name(name)}（{pos}）")
            if obj_names:
                parts.append("桌面上有" + "、".join(obj_names))
        elif not person.get("visible"):
            return "我暂时没看到人或明显的物体，画面可能比较空。"

        if gesture == "wave":
            parts.append("你刚才好像挥了挥手")
        elif gesture == "thumbs_up":
            parts.append("你做了确认手势")

        if not parts:
            return "画面里暂时没检测到明显的物体，你可以把物品放到镜头前让我看看。"

        return "，".join(parts) + "。"

    def _template_motion_answer(self, text: str, ctx: Dict[str, Any]) -> Optional[str]:
        if "遮挡" in text or "挡住" in text:
            if ctx.get("camera_blocked"):
                return EVENT_TEMPLATES["camera_blocked"]
            return "现在画面没有被遮挡，我可以正常看到。"
        if "离开" in text or "在不在" in text:
            if not ctx.get("person", {}).get("visible"):
                return EVENT_TEMPLATES["user_left"]
            return "你还在画面里，我能看到你。"
        return None

    def _llm_reply(self, user_text: str, vision_context: Dict[str, Any]) -> str:
        """调用 LLM 生成回复。"""
        try:
            ctx_json = json.dumps(vision_context, ensure_ascii=False)
            user_msg = f"【视觉上下文】\n{ctx_json}\n\n【用户说】\n{user_text}"
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=200,
                temperature=0.7,
            )
            content = response.choices[0].message.content
            return (content or "").strip() or self._fallback_reply(vision_context)
        except Exception as exc:
            return f"云端回复暂时不可用（{exc}），{self._fallback_reply(vision_context)}"

    def _fallback_reply(self, ctx: Dict[str, Any]) -> str:
        """无 LLM 时的兜底回复。"""
        return (
            "我听到了，不过复杂问题需要配置 LLM_API_KEY 才能更好回答。"
            "你可以问我「你看到什么」或挥手与我互动。"
        )

    @staticmethod
    def _cn_name(label: str) -> str:
        mapping = {
            "person": "人",
            "cup": "杯子",
            "cell phone": "手机",
            "book": "书",
            "chair": "椅子",
            "laptop": "笔记本电脑",
            "keyboard": "键盘",
            "mouse": "鼠标",
            "bottle": "瓶子",
        }
        return mapping.get(label, label)
