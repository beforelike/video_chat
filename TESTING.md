# EdgeVision Talker 测试报告

> 测试日期：2026-06-13

## 测试环境

- OS: Windows 10
- Python: 3.9+
- 项目路径: `video_chat/`

## 测试项与结果

| # | 测试项 | 命令 | 结果 |
|---|--------|------|------|
| 1 | Python 语法检查 | `python -m compileall src tests` | ✅ PASS |
| 2 | 模块导入 | `python -c "from src.app import create_ui; ..."` | ✅ PASS |
| 3 | DialogueManager 模板路由 | `pytest tests/test_dialogue.py -v` | ✅ PASS（12/12） |
| 4 | VisionEventManager 多帧/冷却 | `pytest tests/test_events.py -v` | ✅ PASS（4/4） |
| 5 | 全部单元测试 | `pytest tests/ -v` | ✅ PASS（16/16） |
| 6 | UI 创建 | `create_ui()` | ✅ PASS |
| 7 | 应用启动 | `python -m src.app` | ✅ PASS（http://127.0.0.1:7860 返回 200） |

## 单元测试覆盖

### DialogueManager (`tests/test_dialogue.py`)

- 手势模板：wave、thumbs_up
- 运动模板：user_entered、user_left、camera_blocked
- 视觉问答：「你看到什么」「桌上有什么」
- 低置信度不确定性措辞（「可能」）
- 无 LLM 时兜底回复

### VisionEventManager (`tests/test_events.py`)

- 物体多帧确认（5 帧出现）
- 事件冷却（10 秒内不重复）
- 手势连续帧确认
- VisionContext JSON 字段完整性

## 手动演示检查清单

- [ ] 开启摄像头，画面 ≥ 24 FPS
- [ ] YOLO 检测框显示 person/cup/cell phone
- [ ] 挥手/竖大拇指触发手势提示与回复
- [ ] 输入「你看到什么」得到模板列举
- [ ] 离开画面触发 user_left 主动播报
- [ ] 遮挡摄像头触发 camera_blocked 播报
- [ ] TTS 音频播放正常
- [ ] 配置 LLM_API_KEY 后复杂问题走云端

## 已知限制

1. **挥手检测**：MediaPipe 无原生 wave 类别，通过 Open_Palm + 手腕水平摆动启发式检测，准确率受环境影响。
2. **ASR**：依赖浏览器 Web Speech API（Chrome/Edge），非 Chromium 浏览器需手动输入文字。
3. **人脸/姿态**：MVP 未接入 MediaPipe Face/Pose，face_state/pose 固定为 neutral/unknown。
4. **TTS 打断**：检测到用户发送新消息时会停止合成，但无法在播报过程中通过麦克风 VAD 自动打断。
5. **无摄像头环境**：单元测试与导入可正常运行；完整演示需 USB 摄像头。

## 阻塞项

- 无阻塞项（依赖可通过 `pip install -r requirements.txt` 安装）
- 首次运行需网络下载 YOLO 与 MediaPipe 模型
