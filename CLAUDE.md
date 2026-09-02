# CLAUDE.md — 模拟面试 AI 助手 项目约定

## 项目简介
模拟面试 AI 助手：FastAPI 后端 + Vue3 前端，本地运行。功能：注册登录（JWT）、简历解析与分析、多角色 Agent 模拟面试（流式对话 + 语音 + 表情分析）、评分报告（雷达图 + 表情时间轴）、历史回看、DOCX/PDF 导出、行业调研、求职渠道/讲项目话术。

## 目录结构
- `backend/` — FastAPI 应用（`app/main.py` 入口；`app/routers/` 路由：auth/resume/interview/history/export/industry/project；`app/services/agents/` Agent：base/resume/question/interviewer/scoring/pipeline/industry/project；`app/services/` 其他业务：resume_parser/report_service/export_service；`app/auth.py` JWT 认证；`app/config.py` 读 .env；`app/models.py` ORM；`app/redis_client.py` 缓存）
- `interview-frontend/` — Vue3 + Vite（`src/views/` 视图：Login/Home/Interview/Report/History/Industry/Project；`src/components/` 组件；`src/composables/useVoice.js` 语音封装、`useExpression.js` 表情识别封装；`src/api/index.js` axios 封装；`src/router/index.js` 路由守卫；`public/models/` face-api.js 模型文件）
- `interview_schema.sql` — MySQL 建库建表脚本（含 users 表），供手动建库参考；实际运行由后端 create_all 建表
- `.venv/` — Python 3.11 虚拟环境，后端依赖已全装齐
- `.env` — 本地配置（MySQL、Redis、JWT_SECRET、DASHSCOPE_API_KEY），已 gitignore，不修改
- `backend/uploads/`、`backend/exports/` — 运行期文件，gitignore

## 环境与连接
- MySQL：`127.0.0.1:3306`，root/123456，库 `interview`，连接串带 `charset=utf8mb4`
- Redis：`127.0.0.1:6379`（db0，无密码）。MySQL/Redis 需手动打开，联调前先用 `netstat -ano | grep LISTENING | grep -E ":(3306|6379)"` 确认
- AI：通义千问 DashScope OpenAI 兼容模式，`base_url=https://dashscope.aliyuncs.com/compatible-mode/v1`，`model=qwen-plus`（.env 可切 qwen-turbo/max），Key 读 `.env` 的 `DASHSCOPE_API_KEY`
- 认证：JWT（HS256），secret 读 `.env` 的 `JWT_SECRET`，token 默认 24h 过期；除 `/api/auth/register`、`/api/auth/login`、`/api/health` 外所有接口需 `Authorization: Bearer <token>`

## 运行命令
- 后端：`cd backend && ../.venv/Scripts/python.exe -m uvicorn app.main:app --reload`（端口 8000）
- 前端：`cd interview-frontend && npm run dev`（端口 5173，vite 代理 `/api` → 8000）

## 代码约定
- 注释/docstring 用中文，标识符用英文
- 数据表由启动时 `create_all` 自动建，不手写 DDL；模型变更不删库，增量加列
- Redis 缓存：会话上下文 `session:{id}`、简历分析 `resume:{id}`、题卡 `session:{id}:card`、阶段 `session:{id}:stage`；一律 try/except 降级到 MySQL，不硬依赖
- Agent 结构：`services/agents/` 下每个 Agent 一个模块，继承 `base.py` 的 BaseAgent（统一封装通义千问非流式/流式/JSON 调用）；`pipeline.py` 编排状态机（简历分析 → 题卡生成 → 面试官提问 → 评分）
- 前端流式对话用原生 fetch 解析 SSE（axios 不支持），vite proxy 需透传 text/event-stream
- 视觉模块：前端 face-api.js 本地识别表情（TinyFaceDetector + FaceExpressionNet），模型文件放 `public/models/`；表情序列面试结束时随 `/api/interview/{id}/end` 上传，评分 Agent 结合表情输出点评，存 `interview_reports.expression_analysis`（JSON：时间轴 + 点评）

## 红线（任何情况先征求用户同意）
- 不修改 `.env`、密钥、token
- 不自动 git commit / push
- 不删除文件、目录、git 历史
- 安装新 Python 依赖前先征求同意

## 工作方式（分步执行，必须遵守）
- 一次只执行一个任务：完成任务 → 汇报"✅ 已完成任务 N/M（名称）" + 做了什么 + 验证结果 + **总进度 N/M** → 等用户说"继续"才执行下一个任务
- 不得连续执行多个任务、不得一口气做完所有步骤
- 若某任务失败，报告失败原因与修复方案，修复后重新汇报进度
