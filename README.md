# 模拟面试 AI 助手

本地运行的模拟面试工具：FastAPI 后端 + Vue3 前端。支持账号体系、简历解析、三种角色 Agent 模拟面试（SSE 流式对话 + 语音 + 表情分析，可选难度/学历）、多维评分报告（雷达图 + 表情时间轴，后台生成）、历史回看、DOCX/PDF 导出、行业调研、求职渠道 / 讲项目话术、**会员机制（免费 3 场 + 兑换码/模拟支付开通）**，并带官网落地页、独立设置页与管理员后台。

## 技术栈

- 后端：FastAPI + SQLAlchemy + MySQL + Redis
- 前端：Vue 3 + Vite + ECharts
- AI：通义千问 DashScope（OpenAI 兼容模式）
- 语音 / 视觉：浏览器 Web Speech（ASR/TTS）+ face-api.js（本地表情识别）

## 功能模块

| 模块 | 说明 |
|---|---|
| 官网落地页 | `/` 未登录时的产品介绍页（练习流程 / 加分能力 / FAQ），登录后自动进入工作台 |
| 双栏工作台 | 登录后首页：左「简历（可选）」右「面试配置」，可选**难度（简单/中等/困难）· 学历（不限/大专/本科/硕士）· 面试官**（下拉选择），一键开始面试 |
| 账号 | 注册 / 登录，JWT（24h）认证，路由守卫；侧栏**用户头像**（按用户名自动生成）→ 小窗：设置 / 退出（管理员另有「管理后台」入口） |
| 用户设置 | `/settings` 独立设置页：背景动态效果、页面过渡动效、AI 回复自动朗读、默认面试官（偏好存本机，即时全局生效） |
| 会员机制 | 免费 3 场面试 / 免费导出 2 次；`/membership` 会员中心：套餐（月 ¥9.9 / 年 ¥99）**模拟支付**开通、兑换码激活；权益拦截在后端（start/export 402 引导升级） |
| 简历 | 拖拽上传 PDF / DOCX / TXT / MD → 抽取文本 → AI 分析（技能/项目/亮点画像） |
| 模拟面试 | 技术面 / HR 行为面 / 压力面 × 难度 × 学历；难度学历决定出题深度与开场定位；题卡五阶段：开场自我介绍 → 基础题 → 深度题 → 压力/场景题 → 收尾反问 |
| 语音 | Web Speech：语音输入（ASR）+ AI 朗读（TTS），浏览器原生 |
| 表情分析 | 摄像头 + face-api.js 本地识别表情；画面不上传，仅表情时间轴随面试结束上传 → 报告「表情点评 + 时间轴曲线」 |
| 评分报告 | 雷达图五维（专业技能/沟通表达/逻辑思维/项目经验/岗位匹配）+ 总评 + 匹配度 + 逐题参考要点 + 建议；可导出 DOCX/PDF |
| 行业调研 | 输入陌生行业 → 结构化报告（产业链/头部玩家/商业模式/趋势/岗位技能/面试题） |
| 求职工具 | 求职/接单渠道清单；STAR 法讲项目面试话术 |
| 管理员后台 | `/admin`：统计卡 + 多页签管理——账号（删除级联清理）、面试会话（审阅/删除）、行业调研记录、求职项目记录、**会员管理（会员列表/手动开通/生成兑换码）**，均支持搜索筛选；管理员账号受保护 |

> 管理员说明：启动时后端自动创建管理员 `admin / 123456`（可用环境变量 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 覆盖）；自行注册的账号默认为普通用户。生产使用请务必修改默认口令。

## 目录结构

```
interview-frontend/                     # 仓库根
├── backend/                            # —— FastAPI 后端 ——
│   ├── app/
│   │   ├── main.py                     # 应用入口：CORS、注册 9 组路由(/api/*)、/api/health、启动建表
│   │   ├── config.py                   # 读项目根 .env：MySQL/Redis/JWT/DashScope + 运行期目录(uploads/exports) + 题卡阶段常量
│   │   ├── database.py                 # SQLAlchemy engine/SessionLocal/Base；init_db：create_all 建表 + 增量迁移(用户/会话/会员) + seed 管理员(admin/123456)
│   │   ├── models.py                   # ORM：users / interview_sessions / chat_messages / interview_reports / industry_reports / project_reports / membership_codes / member_orders（见「数据库结构」）
│   │   ├── auth.py                     # PBKDF2 密码哈希；JWT 签发/校验(24h)；get_current_user / require_admin 依赖
│   │   ├── redis_client.py             # Redis 薄封装：会话上下文/简历/题卡/阶段/元信息；全部 try/except 降级 MySQL，不阻塞主流程
│   │   ├── routers/                    # 路由模块（每个文件一类接口，见下表）
│   │   │   ├── auth.py                 #   注册/登录/当前用户（公开）
│   │   │   ├── resume.py               #   简历上传与解析（PDF/DOCX/TXT/MD → 文本 + AI 画像）
│   │   │   ├── interview.py            #   面试核心：roles/start(额度拦截)/chat(SSE 打字机)/end(报告后台生成)
│   │   │   ├── history.py              #   当前用户会话列表/详情/删除（回看）
│   │   │   ├── export.py               #   报告导出(额度拦截)：docx/pdf 生成 + 中性下载 /file(X-Export-Format)
│   │   │   ├── industry.py             #   行业调研：research 生成结构化报告 + 历史
│   │   │   ├── project.py              #   求职渠道清单 / 讲项目话术脚本 + 历史
│   │   │   ├── membership.py           #   会员：status / 兑换码激活 / 模拟支付订单
│   │   │   └── admin.py                #   管理端：users/sessions/industry/project/members 列表·详情·删除（require_admin）
│   │   ├── services/                   # 业务服务（非 Agent）
│   │   │   ├── resume_parser.py        #   简历文件解析（pypdf / python-docx，含表格文本）
│   │   │   ├── report_service.py       #   评分报告组装与落库（失败给兜底报告）
│   │   │   ├── export_service.py       #   DOCX/PDF 渲染（中文系统字体优先）
│   │   │   └── membership_service.py   #   会员纯逻辑：套餐/额度/兑换码/模拟支付（权益判断唯一出口）
│   │   └── services/agents/            # Agent 层（继承 base.py 的 BaseAgent，封装通义千问调用）
│   │       ├── base.py                 #   BaseAgent：非流式/流式/JSON 对话封装
│   │       ├── resume_agent.py         #   简历画像（技能/项目/亮点/教育）
│   │       ├── question_agent.py       #   出题卡：五阶段 × 角色 × 难度 × 学历
│   │       ├── interviewer_agent.py    #   面试官：决策 next/probe/followup/finish 与回复
│   │       ├── pipeline.py             #   面试流水线状态机（题卡游标推进、追问上限）
│   │       ├── scoring_agent.py        #   评分：五维/匹配度/建议/表情点评
│   │       ├── industry_agent.py       #   行业结构化调研
│   │       └── project_agent.py        #   渠道清单 / STAR 讲项目话术
│   ├── uploads/  exports/              # 运行期文件（上传样例/导出产物，gitignore）
│   └── ...                             # 开发期临时脚本按需查看
├── interview-frontend/                 # —— Vue3 + Vite 前端 ——
│   ├── index.html                      # HTML 入口
│   ├── vite.config.js                  # dev 代理 /api → :8000（SSE 透传）
│   └── src/
│       ├── main.js                     # 创建应用：挂载 App + 路由 + 全局样式
│       ├── App.vue                     # 布局外壳：背景涟漪 / 侧栏胶囊导航 / 用户头像小窗 / 路由出口
│       ├── style.css                   # 设计令牌(变量) + 全局基础类(card/btn/glass/reveal 等)
│       ├── views/                      # 页面（每页一个 SFC）
│       │   ├── LandingView.vue         #  官网落地页 /（公开）
│       │   ├── LoginView.vue           #  登录/注册（毛玻璃卡）
│       │   ├── HomeView.vue            #  工作台：简历上传 + 岗位/难度/学历/面试官下拉
│       │   ├── InterviewView.vue       #  面试页：SSE 打字机、语音条、摄像头表情、结束跳报告
│       │   ├── ReportView.vue          #  报告页：雷达图/匹配/建议/表情 + DOCX/PDF 导出；生成中自动轮询
│       │   ├── HistoryView.vue         #  面试历史列表/详情
│       │   ├── IndustryView.vue        #  行业调研
│       │   ├── ProjectView.vue         #  求职渠道/讲项目话术
│       │   ├── AdminView.vue           #  管理后台（多页签：用户/会话/行业/项目/会员）
│       │   ├── SettingsView.vue        #  用户设置页 /settings
│       │   └── MembershipView.vue      #  会员中心 /membership：状态/套餐模拟支付/兑换码
│       ├── components/                 # 可复用组件
│       │   ├── VoiceControl.vue        #  麦克风说话/朗读控制条
│       │   ├── CameraPreview.vue       #  摄像头预览 + 实时表情徽标
│       │   ├── ScoreRadar.vue          #  五维评分雷达图（ECharts）
│       │   └── ExpressionChart.vue     #  表情时间轴曲线（ECharts）
│       ├── composables/                # 组合式逻辑
│       │   ├── useStreamChat.js        #  SSE 聊天（fetch 流式解析，axios 不支持流）
│       │   ├── useTypewriter.js        #  打字机文本拼接
│       │   ├── useVoice.js             #  Web Speech：ASR 语音输入 + TTS 朗读
│       │   └── useExpression.js        #  face-api 表情识别采样（每 2s，仅本地）
│       ├── store/auth.js               #  登录态单例（token/username/is_admin ⇄ localStorage）
│       ├── store/member.js             #  会员状态单例（/member/status 缓存：is_member/额度/套餐）
│       ├── utils/
│       │   ├── reveal.js               #  滚动浮现工具（IntersectionObserver + 兜底）
│       │   ├── avatar.js               #  头像生成（用户名哈希 → 渐变 + 首两字符）
│       │   └── settings.js             #  用户偏好读写（msi_* localStorage + 事件）
│       ├── api/index.js                #  axios 实例(baseURL=/api, Bearer, 401 登出) + 各业务 API
│       └── router/index.js             #  路由表 + 登录/管理员守卫
│   └── public/models/                  # face-api.js 表情识别模型
├── requirements.txt                    # 后端 Python 依赖清单（pip install -r）
├── .env.example                        # 配置模板（复制为 .env 填真实值）
├── .env                                # 真实配置（gitignore，勿提交）
├── interview_schema.sql                # 建库参考脚本（实际运行由后端 create_all 自动建）
├── start.bat                           # Windows 一键启动（检测 MySQL/Redis → 后端 → 前端 → 开浏览器）
├── CLAUDE.md                           # 给 AI 协作者的开发约定（本文件）
└── README.md                           # 本文档
```

> 根目录下的 `_verify_*.py`、`_e2e_*.py` 等为开发期临时脚本，可忽略；`dist/` 为前端构建产物。

## 数据库结构

后端使用 SQLAlchemy ORM，表由启动时 `database.py` 的 `create_all` 自动创建；旧表缺列走增量迁移（`_migrate_users_is_admin`、`_migrate_session_fields`），**不删库、不手动改表**。以下为 6 张表（括号内为说明）：

### users —— 用户
| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK 自增 | |
| username | VARCHAR(64) UNIQUE | 登录名（唯一） |
| password_hash | VARCHAR(255) | PBKDF2 哈希（不存明文） |
| is_admin | BOOL | 管理员标记（默认 0；admin 账号由启动 seed） |
| member_until | DATETIME | 会员到期时间（NULL=非会员；判断以服务器时间为准） |
| free_quota_used | INT | 免费面试已用场次（默认 0，会员不计） |
| export_quota_used | INT | 免费导出已用次数（默认 0，会员不计） |
| created_at | DATETIME | 注册时间 |

### interview_sessions —— 面试会话
| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| user_id | FK → users.id（CASCADE） | 所属用户 |
| job_title | VARCHAR(255) | 目标岗位 |
| interviewer_role | VARCHAR(32) | technical / HR / stress |
| difficulty | VARCHAR(16) | easy / medium / hard（默认 medium） |
| education | VARCHAR(16) | any / college / bachelor / master（默认 any） |
| resume_text | TEXT | 简历文本快照（供 Agent，可为空） |
| status | VARCHAR(32) | in_progress / completed |
| created_at / ended_at | DATETIME | 开始 / 结束时间 |

关联：1 会话 → N 条 chat_messages（级联删）；1 会话 → 至多 1 条 interview_reports。

### chat_messages —— 会话消息
| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| session_id | FK → interview_sessions.id（CASCADE） | |
| role | VARCHAR(16) | user / assistant / system |
| content | TEXT | 消息正文 |
| reference | TEXT | AI 回复的参考要点（回看用，可空） |
| created_at | DATETIME | |

### interview_reports —— 评分报告（1:1 会话）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| session_id | FK → interview_sessions.id（CASCADE） | |
| summary | TEXT | 总体评语 |
| overall_score | INT | 总分 0-100 |
| dimensions | TEXT | 五维评分 JSON 字符串 |
| match_analysis | TEXT | 岗位匹配度 JSON（等级/理由/亮点/待加强） |
| suggestions | TEXT | 改进建议 JSON 数组 |
| expression_analysis | TEXT | 表情时间轴 + 点评 JSON |
| created_at | DATETIME | |

### industry_reports —— 行业调研报告
| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| user_id | FK → users.id（CASCADE） | |
| industry_name | VARCHAR(255) | 调研行业 |
| content | TEXT | 结构化报告 JSON 字符串 |
| created_at | DATETIME | |

### project_reports —— 求职渠道 / 讲项目话术
| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| user_id | FK → users.id（CASCADE） | |
| type | VARCHAR(32) | channels（渠道清单）/ script（讲项目话术） |
| project_name | VARCHAR(255) | type=script 时填写的项目名 |
| content | TEXT | 内容 JSON 字符串 |
| created_at | DATETIME | |

### membership_codes —— 会员兑换码
| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| code | VARCHAR(32) UNIQUE | 兑换码（如 MB-XXXXX-XXXXX） |
| grant_days | INT | 激活赠送天数 |
| used_by | BIGINT | 已使用的用户 id（NULL=未使用；**无库级外键**，删除用户时业务层解绑） |
| used_at / created_at | DATETIME | 使用 / 创建时间 |

### member_orders —— 会员订单（模拟支付）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| user_id | BIGINT | 下单用户（**无库级外键**，删除用户时业务层级联清理） |
| plan | VARCHAR(16) | month（月度）/ year（年度） |
| plan_name | VARCHAR(32) | 套餐名 |
| amount_cents | INT | 金额（分） |
| grant_days | INT | 开通天数 |
| status | VARCHAR(16) | pending / paid / refunded |
| created_at / paid_at | DATETIME | 下单 / 支付时间 |

> 说明：`dimensions / match_analysis / suggestions / expression_analysis / content` 等长内容统一用 **TEXT 存 JSON 字符串**（读写时业务层 `json.dumps/loads`），不使用 MySQL JSON 类型，方便跨库兼容。新表 membership_codes / member_orders 刻意不建库级外键（规避 MySQL 对部分 FK DDL 的 3780 兼容问题），由 `admin.delete_user` 业务层清理。

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

浏览器打开 http://localhost:5173 → 官网落地页 → 登录/注册 → 工作台选简历（可选）与面试配置（岗位 + 难度/学历/面试官）→ 开始面试。

## 使用提示

- **面试配置**：首页「面试配置」工具条里点难度 / 学历 / 面试官弹出下拉选择；难度学历会写入题卡指令并体现在开场白（如「按困难难度 / 学历本科定位出题」）。
- **语音**：面试页点击 🎤 用麦克风回答（说话后停顿自动发送）；🔊 朗读 AI 回复；可在「设置」里开启「AI 回复自动朗读」。
- **表情**：面试页打开摄像头 → 「开始表情跟踪」→ 实时显示当前表情。画面仅本地推理，**不上传**；面试结束时表情时间轴随报告生成「表情时间轴曲线 + 点评」。
- **报告生成中**：点「结束面试」后报告由 AI 后台生成，页面显示骨架屏并自动轮询，生成后自动展示；中途可离开，稍后从「面试历史」查看。
- **导出**：报告页可直接导出 DOCX / PDF（内容含五维评分、匹配分析、建议与表情分析）。
- **设置**：点左下角头像 → 「设置」，可开关背景/页面动效、AI 自动朗读、默认面试官；浏览器 `Esc` 可返回。
- **会员**：非会员可免费体验 3 场面试、免费导出 2 次报告；额度用完会被后端拦截（402）并引导到 `/membership`，可在会员中心用兑换码或「模拟支付」开通会员（月 ¥9.9 / 年 ¥99，不会产生真实扣费）。管理员在后台「会员管理」页签可手动开通或批量生成兑换码。
- **管理员**：用 `admin` 账号登录后，点左下角头像 → 「管理后台」。
- 不支持语音/摄像头的浏览器（如 Firefox 部分功能）会自动降级为纯文字，功能不受影响。

## 常见问题

- **后端建表失败**：确认 MySQL 已启动、`.env` 中账号密码正确。
- **首页显示「摄像头授权被拒绝」**：浏览器地址栏允许摄像头权限后刷新；若确不需要表情分析，直接忽略继续面试即可。
- **SSE 无法流式**：确认通过 vite 代理（前端 5173 访问而非直连 8000）。
