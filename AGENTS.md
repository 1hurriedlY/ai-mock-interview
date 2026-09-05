# AGENTS.md — 模拟面试 AI 助手 项目约定

## 项目简介
模拟面试 AI 助手：FastAPI 后端 + Vue3 前端，本地运行。功能：官网落地页 + 登录工作台（JWT）、简历解析与分析、多角色 Agent 模拟面试（SSE 流式对话 + 语音 + 表情分析，可选难度/学历）、评分报告（雷达图 + 表情时间轴，后台生成）、历史回看、DOCX/PDF 导出、行业调研、求职渠道/讲项目话术、管理员后台（管账号/会话/行业/项目/会员）、**会员机制（免费 3 场 + 兑换码/模拟支付）**、用户头像与独立设置页（/settings）。

## 目录结构
- `backend/` — FastAPI 应用（`app/main.py` 入口，注册 9 组路由：auth/resume/interview/history/industry/project/report(export)/member(会员)/admin，另有 `/api/health`；`app/routers/` 各路由模块；`app/services/agents/` Agent：base/resume/question/interviewer/pipeline/scoring/industry/project；`app/services/` 其他业务：resume_parser/report_service/export_service/membership_service；`app/auth.py` PBKDF2 密码哈希 + JWT + get_current_user/require_admin；`app/config.py` 读 .env；`app/models.py` ORM：users/interview_sessions/chat_messages/interview_reports/industry_reports/project_reports/membership_codes/member_orders；`app/database.py` 建表/迁移/seed 管理员；`app/redis_client.py` 缓存）
- `interview-frontend/` — Vue3 + Vite（`src/views/` 视图：Landing/Login/Home/Interview/Report/History/Industry/Project/Admin/Settings/Membership；`src/components/` 组件：VoiceControl/CameraPreview/ScoreRadar/ExpressionChart；`src/composables/`：useVoice/useExpression/useStreamChat/useTypewriter；`src/store/auth.js` 登录态与 `src/store/member.js` 会员态（均无 Pinia）；`src/utils/`：reveal.js（滚动浮现）/ avatar.js（用户名哈希头像）/ settings.js（用户偏好 msi_ 前缀 localStorage）；`src/assets/chartTheme.js`；`src/api/index.js` axios 封装；`src/router/index.js` 路由守卫；`public/models/` face-api.js 模型文件）
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
- 数据表由启动时 `database.py` 的 `create_all` 自动建，不手写 DDL；模型变更不删库：新增表/列靠 create_all，旧表缺列走 `_migrate_users_is_admin` / `_migrate_session_fields`（interview_sessions.difficulty/education 补列）/ `_migrate_member_fields`（users.member_until/free_quota_used/export_quota_used 补列）式增量 ALTER（改 database.py 时保持该兜底思路）；**新表 membership_codes/member_orders 不建库级外键**（规避 MySQL 对部分 FK DDL 的 3780 兼容问题），孤儿数据由 admin.delete_user 业务层清理
- Redis 缓存键：会话上下文 `session:{id}`（最近 20 条，2h）、简历分析 `resume:{id}`（24h）、题卡 `session:{id}:card`、阶段 `session:{id}:stage`、会话元信息 `session:{id}:meta`；一律 try/except 降级到 MySQL，不硬依赖
- Agent 结构：`services/agents/` 下每个 Agent 一个模块，继承 `base.py` 的 BaseAgent（统一封装通义千问非流式/流式/JSON 调用）；`pipeline.py` 编排状态机
- 面试推进：`QuestionAgent` 出题卡（五阶段 opening/basic/deep/stress/closing，每阶段含题与参考要点），存 `session:{id}:card`，推进游标写回题卡 `_state`（stage_idx/question_idx/probes）；`pipeline.advance` 由面试官 Agent 决策，动作 `next`（下一题）/`probe`/`followup`（本题追问）/`finish`（收尾），每题追问上限 2 次（`MAX_PROBES_PER_QUESTION`）
- 难度 / 学历：`interview_sessions` 存 `difficulty`（easy/medium/hard，默认 medium）与 `education`（any/college/bachelor/master，默认 any）；`QuestionAgent.generate_card` 接收两者并写入题卡指令（【面试难度】调深度、【学历门槛】匹配定位）；`POST /interview/start` 白名单校验并存入会话 meta；开场白会告知「本场将按 X 难度 / 学历 Y 的定位出题」
- 流式对话：`POST /interview/{session_id}/chat` 返回 SSE，事件协议：`event: message`（`data: {"delta": "…"}` 按 3 字/20ms 分批推，制造打字机节奏）+ `event: done`（`data: {"reply","action","reference","stage","finished"}`）；前端 `useStreamChat` 用原生 fetch 解析（axios 不支持流），vite proxy 需透传 text/event-stream
- 结束面试：`POST /interview/{session_id}/end` 把会话标记 completed 后**立即返回 `generating:true`**，报告由后台线程生成（进程内防重锁 `_REPORT_LOCKS`）；二次 end 幂等返回已有报告或「生成中」；失败落兜底报告（见 `report_service._fallback_report`），不阻塞流程
- 报告导出：路由 `export.py`（prefix `/api/report`）+ 服务 `export_service.py`（python-docx / reportlab，中文系统字体优先）；下载走中性 URL `/api/report/{id}/file` + `X-Export-Format` 请求头（避免 IDM/下载管理器按扩展名截胡），前端 fetch blob + `<a download>` 命名；文件落 `backend/exports/`
- 视觉模块：前端 face-api.js 本地识别表情（TinyFaceDetector + FaceExpressionNet，维护版 fork @vladmandic/face-api），模型文件放 `public/models/`；画面仅本地推理不上传，表情时间轴随 `/api/interview/{id}/end` 上传，评分 Agent 结合表情输出点评，存 `interview_reports.expression_analysis`（JSON：时间轴 + 点评）
- 前端登录态：`src/store/auth.js` 用 reactive 单例 + localStorage（未引 Pinia），路由守卫与 axios 拦截器共用；前端下载报告用 fetch → blob（带 token 的链接不能直接 `<a href>`）
- 用户偏好：`utils/settings.js` 读 localStorage（键 `msi_bgFx`/`msi_reduceMotion`/`msi_autoSpeak`/`msi_defaultRole`）；独立设置页 `/settings` 改动后 dispatch `window` 自定义事件 `msi:prefs`，App 监听同步背景涟漪显隐与 `<html class="reduce-motion">`；头像 `utils/avatar.js` 按用户名哈希生成渐变（同名字头像稳定），入口在侧栏底部，点头像弹小窗（设置→ /settings、管理后台→ /admin（仅 admin）、退出登录）
- 管理接口：`routers/admin.py` 仅 `require_admin`：users（列表/删除）、sessions（列表 /`{id}` 审阅详情 /删除）、industry（列表/删除）、project（列表/删除）、members（列表 /手动开通 /兑换码生成·列表）；前台 `/admin` 多页签管理台（统计卡 + 搜索筛选 + 会话审阅弹窗 + 会员管理）
- 会员机制（权益判断唯一出口 `services/membership_service.py`）：非会员免费 3 场面试 + 2 次导出，套餐 month/year（金额单位分）；`is_member/free_left/ensure_allowed/consume_free` 四个函数集中判权；`interview.py start` 与 `export.py` 在生成前 `ensure_allowed`（不足抛 402 中文），成功后非会员 `consume_free` 并在同一请求 commit。兑换码/模拟支付：`routers/membership.py`（/api/member/status、codes/redeem、orders、orders/{id}/mock-pay），订单状态机与幂等按真实支付标准；接真实支付时替换 mock-pay 为渠道回调即可
- 前端会员态：`store/member.js` reactive 单例（登录时随 token 刷新，登出清空）；`/membership` 页展示额度/套餐/模拟收银台/兑换码；首页「开始面试」额度预检 + 后端 402 引导跳会员中心；报告页导出 402 弹窗引导；头像小窗头部显示「会员·至 xx / 免费面试 N 次」并含会员中心入口

## 红线（任何情况先征求用户同意）
- 不修改 `.env`、密钥、token
- 不自动 git commit / push
- 不删除文件、目录、git 历史
- 安装新 Python 依赖前先征求同意

## 工作方式（分步执行，必须遵守）
- 一次只执行一个任务：完成任务 → 汇报"✅ 已完成任务 N/M（名称）" + 做了什么 + 验证结果 + **总进度 N/M** → 等用户说"继续"才执行下一个任务
- 不得连续执行多个任务、不得一口气做完所有步骤
- 若某任务失败，报告失败原因与修复方案，修复后重新汇报进度
