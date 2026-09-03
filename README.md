# 模拟面试 AI 助手

本地运行的模拟面试工具：FastAPI 后端 + Vue3 前端。支持账号体系、简历解析、三种角色 Agent 模拟面试（SSE 流式对话 + 语音 + 表情分析）、多维评分报告（雷达图 + 表情时间轴）、历史回看、DOCX/PDF 导出、行业调研、求职渠道 / 讲项目话术，并带官网落地页与管理员后台。

## 技术栈

- 后端：FastAPI + SQLAlchemy + MySQL + Redis
- 前端：Vue 3 + Vite + ECharts
- AI：通义千问 DashScope（OpenAI 兼容模式）
- 语音 / 视觉：浏览器 Web Speech（ASR/TTS）+ face-api.js（本地表情识别）

## 功能模块

| 模块 | 说明 |
|---|---|
| 官网落地页 | `/` 未登录时的产品介绍页（练习流程 / 加分能力 / FAQ），登录后自动进入工作台 |
| 双栏工作台 | 登录后首页：左「简历（可选）」右「岗位 + 面试官」，一键开始面试 |
| 账号 | 注册 / 登录，JWT（24h）认证，路由守卫；管理员后台可管理所有账号与会话 |
| 简历 | 拖拽上传 PDF / DOCX / TXT / MD → 抽取文本 → AI 分析（技能/项目/亮点画像） |
| 模拟面试 | 技术面 / HR 行为面 / 压力面；题卡五阶段：开场自我介绍 → 基础题 → 深度题 → 压力/场景题 → 收尾反问 |
| 语音 | Web Speech：语音输入（ASR）+ AI 朗读（TTS），浏览器原生 |
| 表情分析 | 摄像头 + face-api.js 本地识别表情；画面不上传，仅表情时间轴随面试结束上传 → 报告「表情点评 + 时间轴曲线」 |
| 评分报告 | 雷达图五维（专业技能/沟通表达/逻辑思维/项目经验/岗位匹配）+ 总评 + 匹配度 + 逐题参考要点 + 建议；可导出 DOCX/PDF |
| 行业调研 | 输入陌生行业 → 结构化报告（产业链/头部玩家/商业模式/趋势/岗位技能/面试题） |
| 求职工具 | 求职/接单渠道清单；STAR 法讲项目面试话术 |
| 管理员后台 | `/admin`：查看所有账号与数据量、删除任意用户/会话（管理员账号受保护） |

> 管理员说明：启动时后端自动创建管理员 `admin / 123456`（可用环境变量 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 覆盖）；自行注册的账号默认为普通用户。生产使用请务必修改默认口令。

## 目录结构

```
interview-frontend/            # 项目根
├── backend/                   # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 入口：CORS、8 组路由注册、启动建表
│   │   ├── config.py          # 读项目根 .env（DB/Redis/JWT/DashScope/阶段常量）
│   │   ├── database.py        # SQLAlchemy：create_all 建表 + 增量迁移 + seed 管理员
│   │   ├── models.py          # ORM：users/sessions/messages/reports/industry/project
│   │   ├── auth.py            # PBKDF2 密码哈希 + JWT 签发校验 + get_current_user/require_admin
│   │   ├── redis_client.py    # Redis 封装（会话上下文/简历/题卡/阶段/元信息，全部降级 MySQL）
│   │   ├── routers/           # auth/resume/interview/history/industry/project/export/admin
│   │   ├── services/          # resume_parser / report_service / export_service
│   │   └── services/agents/   # base/resume/question/interviewer/pipeline/scoring/industry/project
│   ├── uploads/  exports/     # 运行期文件（gitignore）
│   └── ...
├── interview-frontend/        # Vue3 + Vite 前端（与项目根目录同名，注意区分）
│   ├── src/views/             # Landing/Login/Home/Interview/Report/History/Industry/Project/Admin
│   ├── src/components/        # VoiceControl/CameraPreview/ScoreRadar/ExpressionChart
│   ├── src/composables/       # useVoice/useExpression/useStreamChat/useTypewriter
│   ├── src/store/auth.js      # 登录态（reactive 单例 + localStorage）
│   ├── src/api/index.js       # axios 封装 + 各业务 API
│   ├── src/router/index.js    # 路由 + 登录/管理员守卫
│   └── public/models/         # face-api.js 表情识别模型
├── .venv/                     # Python 3.11 虚拟环境
├── .env.example               # 配置模板（复制为 .env 填写真实值）
├── .env                       # 真实配置（gitignore，勿提交）
├── requirements.txt           # 后端依赖清单
├── interview_schema.sql       # 建库建表参考脚本（实际由后端 create_all 自动建）
├── start.bat                  # Windows 一键启动（检测 MySQL/Redis → 后端 → 前端 → 开浏览器）
└── dist/                      # 前端构建产物
```

> 根目录下的 `_verify_*.py`、`_e2e_*.py` 等为开发期临时脚本，可忽略。

## 环境要求

- Python 3.11（虚拟环境 `.venv`）
- MySQL（`127.0.0.1:3306`）、Redis（`127.0.0.1:6379`）
- Node.js + npm
- 通义千问 DashScope API Key
- 摄像头 / 麦克风需 Chrome 或 Edge（`localhost` 属安全上下文，可用）

## 快速开始

依赖已装齐时，Windows 下直接双击 `start.bat`：脚本会检查 MySQL/Redis 是否在监听，再分别拉起后端与前端，最后打开浏览器 http://localhost:5173。

手动启动：

```bash
# 0. 确认 MySQL(3306) 与 Redis(6379) 已启动
netstat -ano | grep LISTENING | grep -E ":(3306|6379)"

# 1. 配置环境变量：复制模板并填写真实值（含 DashScope Key）
cp .env.example .env

# 2. 首次安装后端依赖（在 .venv 虚拟环境内）
.venv/Scripts/python.exe -m pip install -r requirements.txt

# 3. 前端依赖
cd interview-frontend
npm install

# 4. 终端 1：后端（端口 8000，首次启动自动建表并创建管理员；需在 backend 目录内执行）
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
# 5. 终端 2：前端（端口 5173，vite 代理 /api → 8000）
cd interview-frontend
npm run dev
```

浏览器打开 http://localhost:5173 → 官网落地页 → 登录/注册 → 双栏工作台选岗位与面试官 → 开始面试。

## 使用提示

- **语音**：面试页点击 🎤 用麦克风回答（说话后停顿自动发送）；🔊 朗读 AI 回复；「自动朗读」开启后 AI 每次回复完自动朗读。
- **表情**：面试页打开摄像头 → 「开始表情跟踪」→ 实时显示当前表情。画面仅本地推理，**不上传**；面试结束时表情时间轴随报告生成「表情时间轴曲线 + 点评」。
- **报告生成中**：点「结束面试」后报告由 AI 后台生成，页面显示骨架屏并自动轮询，生成后自动展示；中途可离开，稍后从「面试历史」查看。
- **导出**：报告页可直接导出 DOCX / PDF（内容含五维评分、匹配分析、建议与表情分析）。
- **管理员**：用 `admin` 账号登录后，左侧栏会出现「账号管理」入口。
- 不支持语音/摄像头的浏览器（如 Firefox 部分功能）会自动降级为纯文字，功能不受影响。

## 常见问题

- **后端建表失败**：确认 MySQL 已启动、`.env` 中账号密码正确。
- **首页显示「摄像头授权被拒绝」**：浏览器地址栏允许摄像头权限后刷新；若确不需要表情分析，直接忽略继续面试即可。
- **SSE 无法流式**：确认通过 vite 代理（前端 5173 访问而非直连 8000）。
