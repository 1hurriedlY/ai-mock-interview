# CLAUDE.md — 模拟面试 AI 助手 项目约定

## 项目简介
模拟面试 AI 助手：FastAPI 后端 + Vue3 前端，本地运行。功能：官网落地页 + 登录工作台（JWT）、简历解析与分析、多角色 Agent 模拟面试（SSE 流式对话 + 语音 + 表情分析）、评分报告（雷达图 + 表情时间轴，后台生成）、历史回看、DOCX/PDF 导出、行业调研、求职渠道/讲项目话术、管理员后台（管账号与会话）。

## 目录结构
- `backend/` — FastAPI 应用（`app/main.py` 入口，注册 8 组路由：auth/resume/interview/history/industry/project/report(export)/admin，另有 `/api/health`；`app/routers/` 各路由模块；`app/services/agents/` Agent：base/resume/question/interviewer/pipeline/scoring/industry/project；`app/services/` 其他业务：resume_parser/report_service/export_service；`app/auth.py` PBKDF2 密码哈希 + JWT + get_current_user/require_admin；`app/config.py` 读 .env；`app/models.py` ORM：users/interview_sessions/chat_messages/interview_reports/industry_reports/project_reports；`app/database.py` 建表/迁移/seed 管理员；`app/redis_client.py` 缓存）
- `interview-frontend/` — Vue3 + Vite（`src/views/` 视图：Landing/Login/Home/Interview/Report/History/Industry/Project/Admin；`src/components/` 组件：VoiceControl/CameraPreview/ScoreRadar/ExpressionChart；`src/composables/`：useVoice/useExpression/useStreamChat/useTypewriter；`src/store/auth.js` 登录态（无 Pinia）；`src/utils/reveal.js`、`src/assets/chartTheme.js`；`src/api/index.js` axios 封装；`src/router/index.js` 路由守卫；`public/models/` face-api.js 模型文件）
- `interview_schema.sql` — MySQL 建库建表脚本（含 users 表），供手动建库参考；实际运行由后端 create_all 建表
- `.venv/` — Python 3.11 虚拟环境，后端依赖已全装齐
- `.env` — 本地配置（MySQL、Redis、JWT_SECRET、DASHSCOPE_API_KEY），已 gitignore，不修改
- `start.bat` — Windows 一键启动（检测 MySQL/Redis → 后端 → 前端 → 开浏览器）
- `backend/uploads/`、`backend/exports/` — 运行期文件，gitignore

## 环境与连接
- MySQL：`127.0.0.1:3306`，root/123456，库 `interview`，连接串带 `charset=utf8mb4`
- Redis：`127.0.0.1:6379`（db0，无密码）。MySQL/Redis 需手动打开，联调前先用 `netstat -ano | grep LISTENING | grep -E ":(3306|6379)"` 确认
- AI：通义千问 DashScope OpenAI 兼容模式，`base_url=https://dashscope.aliyuncs.com/compatible-mode/v1`，`model=qwen-plus`（.env 可切 qwen-turbo/max），Key 读 `.env` 的 `DASHSCOPE_API_KEY`
- 认证：JWT（HS256），secret 读 `.env` 的 `JWT_SECRET`，token 默认 24h 过期；除 `/api/auth/register`、`/api/auth/login`、`/api/health` 外所有接口需 `Authorization: Bearer <token>`；管理接口需 is_admin，见 `app/auth.py` 的 `require_admin`
- 管理员：启动时 `database.py` 自动 seed 账号（默认 admin/123456，环境变量 `ADMIN_USERNAME`/`ADMIN_PASSWORD` 可覆盖），注册账号默认为普通用户

## 运行命令
- 一键（依赖已装齐）：Windows 双击根目录 `start.bat`
- 后端：`cd backend && ../.venv/Scripts/python.exe -m uvicorn app.main:app --reload`（端口 8000）
- 前端：`cd interview-frontend && npm run dev`（端口 5173，vite 代理 `/api` → 8000）

## 代码约定
- 注释/docstring 用中文，标识符用英文
- 数据表由启动时 `database.py` 的 `create_all` 自动建，不手写 DDL；模型变更不删库：新增表/列靠 create_all，旧表缺列走 `_migrate_users_is_admin` 式增量 ALTER（改 database.py 时保持该兜底思路）
- Redis 缓存键：会话上下文 `session:{id}`（最近 20 条，2h）、简历分析 `resume:{id}`（24h）、题卡 `session:{id}:card`、阶段 `session:{id}:stage`、会话元信息 `session:{id}:meta`；一律 try/except 降级到 MySQL，不硬依赖
- Agent 结构：`services/agents/` 下每个 Agent 一个模块，继承 `base.py` 的 BaseAgent（统一封装通义千问非流式/流式/JSON 调用）；`pipeline.py` 编排状态机
- 面试推进：`QuestionAgent` 出题卡（五阶段 opening/basic/deep/stress/closing，每阶段含题与参考要点），存 `session:{id}:card`，推进游标写回题卡 `_state`（stage_idx/question_idx/probes）；`pipeline.advance` 由面试官 Agent 决策，动作 `next`（下一题）/`probe`/`followup`（本题追问）/`finish`（收尾），每题追问上限 2 次（`MAX_PROBES_PER_QUESTION`）
- 流式对话：`POST /interview/{session_id}/chat` 返回 SSE，事件协议：`event: message`（`data: {"delta": "…"}` 逐字）+ `event: done`（`data: {"reply","action","reference","stage","finished"}`）；前端 `useStreamChat` 用原生 fetch 解析（axios 不支持流），vite proxy 需透传 text/event-stream
- 结束面试：`POST /interview/{session_id}/end` 把会话标记 completed 后**立即返回 `generating:true`**，报告由后台线程生成（进程内防重锁 `_REPORT_LOCKS`）；二次 end 幂等返回已有报告或「生成中」；失败落兜底报告（见 `report_service._fallback_report`），不阻塞流程
- 报告导出：路由 `export.py`（prefix `/api/report`）+ 服务 `export_service.py`（python-docx / reportlab，中文系统字体优先）；下载走中性 URL `/api/report/{id}/file` + `X-Export-Format` 请求头（避免 IDM/下载管理器按扩展名截胡），前端 fetch blob + `<a download>` 命名；文件落 `backend/exports/`
- 视觉模块：前端 face-api.js 本地识别表情（TinyFaceDetector + FaceExpressionNet，维护版 fork @vladmandic/face-api），模型文件放 `public/models/`；画面仅本地推理不上传，表情时间轴随 `/api/interview/{id}/end` 上传，评分 Agent 结合表情输出点评，存 `interview_reports.expression_analysis`（JSON：时间轴 + 点评）
- 前端登录态：`src/store/auth.js` 用 reactive 单例 + localStorage（未引 Pinia），路由守卫与 axios 拦截器共用；前端下载报告用 fetch → blob（带 token 的链接不能直接 `<a href>`）

## 红线（任何情况先征求用户同意）
- 不修改 `.env`、密钥、token
- 不自动 git commit / push
- 不删除文件、目录、git 历史
- 安装新 Python 依赖前先征求同意

## 工作方式（分步执行，必须遵守）
- 一次只执行一个任务：完成任务 → 汇报"✅ 已完成任务 N/M（名称）" + 做了什么 + 验证结果 + **总进度 N/M** → 等用户说"继续"才执行下一个任务
- 不得连续执行多个任务、不得一口气做完所有步骤
- 若某任务失败，报告失败原因与修复方案，修复后重新汇报进度
