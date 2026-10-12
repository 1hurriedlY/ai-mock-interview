# Slide Outline

## Meta
- Topic: Lollipop · AI 模拟面试 —— 项目实习答辩
- Scenario: 课程实习答辩，面向老师/评委，重点展示项目完成度、技术方案与个人收获
- Content Source: provided（项目仓库 README / AGENTS.md / 项目约定）
- Style: Lollipop 产品视觉规范 —— 粉彩渐变背景、白色悬浮卡片、黑色胶囊按钮、玻璃拟态；标题大字号、图表化表达
- Slide Count: 12
- Generated At: 2026-09-07T17:10:00+08:00

## Source Materials
项目仓库：README.md（功能模块/技术栈/数据库结构）、AGENTS.md（架构约定、会员机制、SSE 协议、Agent 流水线）。答辩需要预留项目演示截图位（用户自行贴图）。

## Slide-by-Slide Outline
1. **Slide 1 — 封面** — 「Lollipop · AI 模拟面试」项目实习答辩，姓名/班级/日期占位 | Layout: L01 | Image provided: no | Chart: no
2. **Slide 2 — 汇报目录** — 项目背景 / 方案设计 / 功能演示 / 技术亮点 / 成果收获 / 展望 | Layout: L19 | Chart: no
3. **Slide 3 — 项目背景与痛点** — 求职面试缺乏低成本练习途径：真人模拟贵、网课无反馈、AI 工具不成体系 | Layout: L07 三卡片 | Chart: no
4. **Slide 4 — 方案总览** — 一句话定位 + 五大能力：多角色模拟面试 / 多维评分报告 / 语音+表情 / 行业调研 / 会员运营 | Layout: L16 IconRow | Chart: no
5. **Slide 5 — 系统架构与技术栈** — 前后端分离架构图：Vue3+Vite ⇄ FastAPI ⇄ MySQL/Redis/通义千问，Agent 分层 | Layout: 自绘架构示意（2col） | Chart: yes(SVG)
6. **Slide 6 — 核心功能①：AI 模拟面试** — 三种面试官 × 难度 × 学历，五阶段题卡，SSE 打字机流式，语音问答，表情识别 | Layout: L05（左文右演示占位图） | Image provided: placeholder
7. **Slide 7 — 核心功能②：多维评分报告** — 五维雷达图 + 岗位匹配 + 表情时间轴 + 逐题参考要点，DOCX/PDF 导出 | Layout: L06（左演示占位图右文） | Image provided: placeholder
8. **Slide 8 — 核心功能③：题库与会员体系** — 题库审核流转 + AI 批量出题；免费 3 场 + 模拟支付/兑换码；管理后台 | Layout: L08 对比双栏（各含小演示占位） | Image provided: placeholder
9. **Slide 9 — 项目演示（大图页）** — 整页演示占位：可放落地页/工作台/面试页截图 | Layout: L14 HeroImage | Image provided: placeholder
10. **Slide 10 — 技术亮点与难点** — SSE 打字机协议 / 表情本地推理不上传 / Redis 降级容错 / 增量迁移不删库 / 报告后台生成 | Layout: L16 四要点 | Chart: no
11. **Slide 11 — 项目成果与个人收获** — KPI 数字：9 组路由 / 9 张表 / 11 个页面 / 5 阶段题卡；收获：全栈能力 + AI 工程化 | Layout: L11 ThreeKPIs + 收获 | Chart: yes(KPI)
12. **Slide 12 — 不足与展望 · 致谢** — 待改进（真实支付接入/题库规模化）+ 展望（更多角色/移动端）；感谢聆听 | Layout: L20 Closing | Chart: no

## Visual Rhythm Notes
- 深色强调页位置：Slide 9（演示页深色 hero，突出截图）；封面/结尾用较饱和渐变
- 演示占位图位置：Slide 6、7、8（小图）、Slide 9（整页大图）——浅灰占位框，用户自行替换为真实截图
- Chart-bearing slides: 5（架构示意 SVG）、11（KPI 数字）
- Slides are viewed on large screens, often from a distance. Small text is unreadable. Every text element must be sized generously and fill its container space rather than floating in emptiness.
- Slides should feel visually rich and layered, not like text pasted on rectangles. Decorative elements add polish, and SVG charts communicate data far more effectively than text or numbers alone.
