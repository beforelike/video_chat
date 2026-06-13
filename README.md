# EdgeVision Talker

低成本实时视觉对话助手 — 本地视觉感知 + 云端语义生成。

## 项目简介

EdgeVision Talker 通过端侧计算机视觉（YOLO、MediaPipe、OpenCV）将摄像头画面解析为结构化视觉事件，再结合语音识别（ASR）与对话模型（LLM）实现「看得见、听得懂、说得自然」的 AI 助手。

**核心设计**：视频流不直接上传云端，仅将结构化 JSON 文本发送给对话模块。

## 环境要求

| 项 | 最低要求 |
|----|----------|
| Python | 3.9+ |
| 内存 | 8 GB |
| 摄像头 | USB 720p+（可选，无摄像头可运行单元测试） |
| 浏览器 | Chrome / Edge（Web Speech API 语音输入） |
| GPU | 可选（CPU 可运行 yolo11n） |

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/beforelike/video_chat.git
cd video_chat
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

首次运行会自动下载：
- `yolo11n.pt` 模型（约 5 MB）
- MediaPipe `gesture_recognizer.task` 模型（首次手势识别时）

### 4. 配置环境变量（可选）

```bash
cp .env.example .env
```

编辑 `.env`：

```env
LLM_API_KEY=your_api_key_here      # 复杂问答需要
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
CAMERA_DEVICE_ID=0
```

未配置 `LLM_API_KEY` 时，系统使用模板回复（手势、进出、遮挡、简单视觉问答）。

### 5. 启动应用

```bash
python -m src.app
```

浏览器访问 http://127.0.0.1:7860

### 6. 演示流程

1. 点击 **开启摄像头**，等待 YOLO 与手势模型加载
2. 将手机、杯子等物品放入画面
3. 输入或语音说：「你看到桌上有什么？」
4. 挥手、竖大拇指测试手势回复
5. 离开画面 5 秒后回来，观察主动反馈
6. 用手遮挡摄像头，观察遮挡提示

## 项目结构

```
video_chat/
├── doc/                    # 需求与设计文档
├── src/
│   ├── vision/
│   │   ├── capture.py      # 摄像头采集与降帧
│   │   ├── detector.py     # YOLO 物体检测
│   │   ├── gesture.py      # MediaPipe 手势识别
│   │   ├── motion.py       # 运动/遮挡/用户状态
│   │   └── events.py       # VisionEventManager
│   ├── audio/
│   │   └── tts.py          # edge-tts 语音合成
│   ├── dialogue/
│   │   └── manager.py      # 模板 + LLM 对话路由
│   └── app.py              # Gradio 应用入口
├── tests/
│   ├── test_events.py
│   └── test_dialogue.py
├── requirements.txt
├── .env.example
└── README.md
```

## 功能清单

| 功能 | 状态 | 模块 |
|------|------|------|
| 摄像头预览 + 检测框 overlay | ✅ | capture.py, detector.py |
| YOLO 物体检测（5 FPS） | ✅ | detector.py |
| MediaPipe 手势（挥手/大拇指/手掌） | ✅ | gesture.py |
| 用户进出/遮挡检测 | ✅ | motion.py |
| 多帧确认 + 事件冷却 | ✅ | events.py |
| 模板对话 + 可选 LLM | ✅ | dialogue/manager.py |
| TTS 语音播报 | ✅ | audio/tts.py |
| 浏览器 ASR（Web Speech API） | ✅ | app.py |
| 主动反馈（进出/遮挡/手势） | ✅ | app.py + events.py |
| 事件日志 + VisionContext JSON | ✅ | app.py |

## 测试

```bash
# 语法检查
python -m compileall src tests

# 导入验证
python -c "from src.app import create_ui; from src.dialogue.manager import DialogueManager; from src.vision.events import VisionEventManager; print('imports ok')"

# 单元测试
python -m pytest tests/ -v
```

详见 [TESTING.md](./TESTING.md)。

## 依赖说明

| 库 | 用途 |
|----|------|
| opencv-python | 摄像头采集、运动/遮挡检测 |
| ultralytics | YOLO11n 物体检测 |
| mediapipe | 手势识别 |
| gradio | Web UI |
| edge-tts | 语音合成 |
| openai | LLM API（OpenAI 兼容） |
| python-dotenv | 环境变量 |
| pytest | 单元测试 |

## 开发规范

请参阅 `doc/开发规范.md` 与 `doc/训练营代码提交要求.md`。

## 许可证

本项目为训练营参赛作品，原创功能部分见各 PR 描述。
