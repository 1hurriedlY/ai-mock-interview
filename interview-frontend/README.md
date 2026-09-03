# 模拟面试 AI 助手（前端）

Vue3 + Vite 前端，调用后端 `http://localhost:8000` 的 `/api` 接口（vite 代理）。项目根目录在仓库一级，见 [根 README](../README.md)。

## 开发

```bash
npm install        # 首次安装依赖
npm run dev        # 启动开发服务器（端口 5173，/api 代理到 8000）
```

## 构建

```bash
npm run build      # 产物输出到 dist/
npm run preview    # 本地预览构建产物
```

## 页面与路由

| 路由 | 页面 | 访问 |
|---|---|---|
| `/` | LandingView（官网落地页） | 公开；已登录访问自动进 `/home` |
| `/login` | LoginView（登录 / 注册切换） | 公开；已登录访问自动进 `/home` |
| `/home` | HomeView（双栏：简历 + 岗位与面试官） | 需登录 |
| `/interview/:id?` | InterviewView（SSE 流式对话 + 语音 + 表情） | 需登录 |
| `/report/:id` | ReportView（评分报告，含导出） | 需登录 |
| `/history` | HistoryView（历史回看 / 删除） | 需登录 |
| `/industry` | IndustryView（行业调研） | 需登录 |
| `/project` | ProjectView（求职渠道 / STAR 话术） | 需登录 |
| `/admin` | AdminView（管理员：账号与会话管理） | 需登录且 `is_admin`；非管理员跳回 `/home` |

守卫逻辑见 `src/router/index.js`；登录态判断用 `src/store/auth.js` 单例（token / username / isAdmin 持久化到 localStorage）。

## 目录

- `src/views/` — 上述 9 个页面
- `src/components/` — ScoreRadar（五维雷达图）/ ExpressionChart（表情时间轴曲线）/ CameraPreview / VoiceControl
- `src/store/auth.js` — 登录态 reactive 单例（无 Pinia），路由守卫与 axios 拦截器共用
- `src/composables/`
  - `useVoice` — Web Speech 封装：语音输入（ASR，停顿自动发送）+ AI 朗读（TTS）
  - `useExpression` — face-api 表情识别封装（动态 import 懒加载；画面本地推理不上传，仅时间轴随面试结束 `/end` 上传）
  - `useStreamChat` — SSE 流式对话（原生 fetch 逐事件解析，axios 不支持流），处理 `message`（delta）/ `done` 事件
  - `useTypewriter` — 把 SSE 增量组装成当前回复文本
- `src/utils/reveal.js` — 落地页滚动渐显指令
- `src/assets/chartTheme.js` — ECharts 主题
- `src/api/index.js` — axios 封装（自动带 JWT token；401 清登录态跳登录），按模块导出 authApi / resumeApi / interviewApi / historyApi / exportApi / industryApi / projectApi / adminApi；报告下载走 fetch → blob（带 token 的 `<a href>` 会被浏览器拦截）
- `public/models/` — face-api.js 表情识别模型（TinyFaceDetector + FaceExpressionNet），需随构建产物部署

## 依赖

- vue 3、vue-router 5、axios、echarts 6、@vladmandic/face-api 1.7（face-api.js 维护版 fork）
- 开发：vite 8、@vitejs/plugin-vue 6
