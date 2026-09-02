# 模拟面试 AI 助手

本地运行的模拟面试工具：FastAPI 后端 + Vue3 前端。支持账号体系、简历分析、多角色 Agent 模拟面试（流式对话 + 语音 + 表情分析）、多维评分报告（雷达图 + 表情时间轴）、历史回看、DOCX/PDF 导出、行业调研、求职渠道 / 讲项目话术。

## 功能模块

| 模块 | 说明 |
|---|---|
| 账号 | 注册 / 登录，JWT（24h）认证，路由守卫 |
| 简历 | 上传 PDF/DOCX → 抽取文本 → AI 分析（技能/项目/亮点画像） |
| 模拟面试 | 技术面 / HR 面 / 压力面；题卡五阶段：开场自我介绍 → 基础题 → 深度题 → 压力/场景题 → 收尾反问 |
| 语音 | Web Speech：语音输入（ASR）+ AI 朗读（TTS），浏览器原生 |
| 表情分析 | 摄像头 + face-api.js 本地识别表情；实时徽标；结束上传时间轴 → 报告「表情点评 + 时间轴曲线」 |
| 评分报告 | 雷达图五维（专业技能/沟通表达/逻辑思维/项目经验/岗位匹配）+ 总评 + 匹配度 + 建议，可导出 DOCX/PDF |
| 行业调研 | 输入陌生行业 → 结构化报告（产业链/头部玩家/商业模式/趋势/岗位技能/面试题） |
| 求职工具 | 求职/接单渠道清单；STAR 法讲项目面试话术 |

## 目录结构

```
interview-frontend/            # Vue3 + Vite 前端
backend/                       # FastAPI 后端
  app/
    main.py                    # 入口：CORS、路由、启动建表
    config.py                  # 读 .env 配置
    models.py                  # ORM：users/sessions/messages/reports/industry/project
    routers/                   # auth/resume/interview/history/industry/project/export
    services/agents/           # base/resume/question/interviewer/scoring/pipeline/industry/project
    services/                  # resume_parser / report_service / export_service
  uploads/  exports/           # 运行期文件（gitignore，目录自带 .gitignore）
interview_schema.sql           # 建库建表参考脚本（实际由后端 create_all 自动建）
.env.example                   # 配置模板（复制为 .env 填写真实值）
.env                          # 真实配置（gitignore，勿提交）
```

## 环境要求

- Python 3.11（虚拟环境 `.venv`）
- MySQL（`127.0.0.1:3306`）、Redis（`127.0.0.1:6379`）
- Node.js + npm
- 通义千问 DashScope API Key
- 摄像头 / 麦克风需 Chrome 或 Edge（`localhost` 属安全上下文，可用）

## 首次安装

```bash
# 1. 配置环境变量：复制模板并填写真实值（含 DashScope Key）
cp .env.example .env

# 2. 后端依赖（在 .venv 虚拟环境内）
.venv/Scripts/python.exe -m pip install -r requirements.txt

# 3. 前端依赖
cd interview-frontend
npm install
```

## 启动（需先打开 MySQL 与 Redis）

```bash
# 终端 1：后端（端口 8000，首次启动自动建表）
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000 --app-dir backend

# 终端 2：前端（端口 5173，vite 代理 /api → 8000）
cd interview-frontend
npm run dev
```

浏览器打开 http://localhost:5173 → 注册/登录 → 首页选岗位与面试官角色 → 开始面试。

## 语音与表情使用提示

- **语音**：面试页点击 🎤 用麦克风回答（说话后停顿自动发送）；🔊 朗读 AI 回复；「自动朗读」开启后 AI 每次回复完自动朗读。
- **表情**：面试页右侧「📷 打开摄像头（表情分析）」→ 点击「开始表情跟踪」→ 右上角实时显示当前表情；结束时表情时间轴随报告生成「表情时间轴曲线 + 点评」。画面仅本地推理，不上传。
- 不支持语音/摄像头的浏览器（如 Firefox 部分功能）会自动降级为纯文字，功能不受影响。

## 常见问题

- **后端建表失败**：确认 MySQL 已启动、`.env` 中账号密码正确。
- **首页显示「摄像头授权被拒绝」**：浏览器地址栏允许摄像头权限后刷新；若确不需要表情分析，直接忽略继续面试即可。
- **SSE 无法流式**：确认通过 vite 代理（前端 5173 访问而非直连 8000）。
