# EdgeVision Talker — PR 提交记录

> 遵循 [训练营代码提交要求](./训练营代码提交要求.md)：每个 PR 只做一件事，合并后主分支保持可运行。

---

## PR #1 — feat: 初始化 EdgeVision Talker MVP 项目骨架

**分支**：`main`（`72531e3`）  
**状态**：已合并

### 功能描述

初始化项目结构与 Day 1 上午 MVP：摄像头采集、YOLO 物体检测、Gradio 实时预览。运行 `python -m src.app` 可开启摄像头并看到 YOLO 检测框。

### 实现思路

- `VideoCaptureManager`：OpenCV 取帧，支持按模块降帧分发
- `ObjectDetector`：Ultralytics YOLO11n，置信度过滤（person>0.6, cell phone>0.55）
- Gradio Timer 刷新画面与检测结果文本

### 测试方式

```bash
pip install -r requirements.txt
python -m src.app
# 浏览器打开 http://127.0.0.1:7860 ，点击「开启摄像头」
```

---

## PR #2 — fix: 适配 Gradio 6 使用 Timer 定时刷新画面

**分支**：`main`（`4a71c7f`）  
**状态**：已合并

### 功能描述

修复 Gradio 6.x API 变更导致的画面无法刷新问题，保证摄像头预览稳定更新。

### 实现思路

使用 Gradio 6 的 `gr.Timer` 组件替代旧版定时机制驱动帧刷新。

### 测试方式

```bash
python -m src.app
# 确认画面持续刷新，非静态占位图
```

---

## PR #3 — feat: 添加 MotionEventDetector 运动与遮挡检测

**分支**：`feat/motion-detector`  
**状态**：已合并

### 功能描述

检测用户进入/离开画面、摄像头被遮挡、画面运动等状态，输出 `MotionState` 结构化数据。

### 实现思路

OpenCV MOG2 背景差分 + 亮度/方差遮挡检测 + YOLO person 进出判断。

### 测试方式

```bash
python -c "from src.vision.motion import MotionEventDetector; print('OK')"
python -m src.app
```

---

## PR #4 — feat: 添加 GestureDetector MediaPipe 手势识别

**分支**：`feat/gesture-detector`  
**状态**：已合并

### 功能描述

识别挥手、竖大拇指、张开手掌等手势，支持 overlay 提示。

### 实现思路

MediaPipe Gesture Recognizer + 挥手启发式（手腕摆动）。

### 测试方式

```bash
python -c "from src.vision.gesture import GestureDetector; print('OK')"
```

---

## PR #5 — feat: 添加 VisionEventManager 视觉事件管理

**分支**：`feat/vision-event-manager`  
**状态**：已合并

### 功能描述

合并检测输出为 VisionContext JSON；多帧确认、10 秒冷却、事件日志与主动反馈队列。

### 测试方式

```bash
pytest tests/test_events.py -v
```

---

## PR #6 — feat: 添加 DialogueManager 对话管理与模板路由

**分支**：`feat/dialogue-manager`  
**状态**：已合并

### 功能描述

模板回复 + 按需 LLM；支持视觉问答、手势/运动事件话术。

### 测试方式

```bash
pytest tests/test_dialogue.py -v
```

---

## PR #7 — feat: 添加 TTSEngine 语音合成

**分支**：`feat/tts-engine`  
**状态**：已合并

### 功能描述

edge-tts 合成 MP3，支持停止播报。

### 测试方式

```bash
python -c "from src.audio.tts import TTSEngine; t=TTSEngine(); print(t.synthesize('测试'))"
```

---

## PR #8 — feat: Gradio 全功能集成视觉语音对话

**分支**：`feat/gradio-full-integration`  
**状态**：已合并

### 功能描述

整合全部模块：事件日志、VisionContext、语音对话、TTS、Web Speech ASR、主动反馈。

### 测试方式

```bash
python -m src.app
pytest tests/ -v
```

---

## PR #9 — docs: 更新 README、测试文档与 PR 规范

**分支**：`docs/readme-and-testing`  
**状态**：待合并

### 功能描述

README 安装与演示说明、TESTING.md 测试报告、PR 模板与提交记录、pytest 依赖。

### 测试方式

按 README 走通 3 分钟演示脚本；`pytest tests/ -v` 全部通过。

---

## 推荐合并顺序

```text
PR #3 → #4 → #5 → #6 → #7 → #8 → #9
```
