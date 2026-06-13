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
| 摄像头 | USB 720p+ |
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

首次运行会自动下载 `yolo11n.pt` 模型（约 5 MB）。

### 4. 配置环境变量（可选，Day 2 LLM 接入时需要）

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY
```

### 5. 启动应用

```bash
python -m src.app
```

浏览器访问 http://127.0.0.1:7860 ，点击「开启摄像头」即可看到实时画面与 YOLO 检测框。

## 项目结构

```
video_chat/
├── doc/                    # 需求与设计文档
├── src/
│   ├── vision/             # 视觉感知（摄像头、YOLO、手势、运动）
│   ├── audio/              # 语音（ASR、TTS）
│   ├── dialogue/           # 对话管理（模板 + LLM）
│   └── app.py              # Gradio 应用入口
├── requirements.txt
├── .env.example
└── README.md
```

## 当前进度（Day 1 上午）

- [x] OpenCV 摄像头采集
- [x] YOLO11n 物体检测 + 检测框 overlay
- [x] Gradio 实时预览界面
- [ ] MediaPipe 手势识别（Day 1 下午）
- [ ] ASR + TTS 语音闭环（Day 1 下午）
- [ ] 规则引擎对话（Day 1 晚）

## 依赖说明

| 库 | 用途 |
|----|------|
| opencv-python | 摄像头采集、图像处理 |
| ultralytics | YOLO11n 物体检测 |
| mediapipe | 手势/人脸/姿态识别（待接入） |
| gradio | Web UI |
| edge-tts | 语音合成（待接入） |
| openai | LLM API 调用（待接入） |

## 开发规范

请参阅 `doc/开发规范.md` 与 `doc/训练营代码提交要求.md`：

- 每个功能使用独立分支开发
- PR 粒度尽量小，描述清晰完整
- 持续提交 commit，避免最后一天突击提交
- README 中列明所有依赖

## 许可证

本项目为训练营参赛作品，原创功能部分见各 PR 描述。
